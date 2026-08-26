#!/usr/bin/env python3
"""
Automated Batch Target Scanner for Smart Contract Bug Bounty Hunting.
Pulls target GitHub repositories, watches commits, computes unified diffs (GitDeltaScanner),
maps changed line spans to Solidity AST nodes, runs multi-agent audits,
and dispatches webhook notifications for high-impact findings.
"""
import os
import sys
import subprocess
import shutil
import time
import re
import argparse
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from eth_audit_agent.core.context import ContractContext, SolidityContract, SolidityFunction
from eth_audit_agent.core.parser import SolidityParser
from eth_audit_agent.core.solc_selector import SolcSelector
from eth_audit_agent.agents.base import get_llm_backend
from eth_audit_agent.agents.red_team import RedTeamAgent
from eth_audit_agent.agents.blue_team import BlueTeamAgent
from eth_audit_agent.orchestrator.debater import AuditDebater
from eth_audit_agent.reporters.markdown_reporter import MarkdownReporter
from eth_audit_agent.reporters.webhook_notifier import WebhookNotifier

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("BatchScanner")


@dataclass
class FileDiff:
    """Represents a unified git diff hunk for a single Solidity file."""
    file_path: str
    change_type: str  # 'added', 'modified', 'deleted'
    modified_line_ranges: List[Tuple[int, int]] = field(default_factory=list)  # [(start_line, end_line), ...]
    patch: str = ""


class GitDeltaScanner:
    """Clones, updates, and computes incremental git diffs on Solidity targets."""

    @staticmethod
    def get_commit_hash(repo_dir: Path, ref: str = "HEAD") -> str:
        """Returns the full commit SHA for the given git reference."""
        try:
            res = subprocess.run(
                ["git", "rev-parse", ref],
                cwd=str(repo_dir),
                capture_output=True,
                text=True,
                check=True
            )
            return res.stdout.strip()
        except Exception:
            return ""

    @staticmethod
    def clone_or_update(
        repo_url: str,
        cache_dir: Path = Path("cache_repos"),
        depth: int = 2
    ) -> Tuple[Path, str, str, bool]:
        """
        Clones remote repository (depth >= 2 to support HEAD~1) or updates existing repo.
        Returns: (target_dir, old_commit_sha, new_commit_sha, is_updated)
        """
        cache_dir.mkdir(parents=True, exist_ok=True)
        repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
        target_dir = cache_dir / repo_name

        if not target_dir.exists():
            logger.info(f"Cloning {repo_url} (depth={depth}) into {target_dir}...")
            subprocess.run(
                ["git", "clone", "--depth", str(depth), repo_url, str(target_dir)],
                check=True,
                capture_output=True,
                text=True
            )
            head_sha = GitDeltaScanner.get_commit_hash(target_dir, "HEAD")
            return target_dir, "", head_sha, True

        # Existing repository: fetch latest
        old_head = GitDeltaScanner.get_commit_hash(target_dir, "HEAD")
        try:
            subprocess.run(["git", "fetch", "--depth", str(depth), "origin"], cwd=str(target_dir), capture_output=True)
            subprocess.run(["git", "pull", "--ff-only"], cwd=str(target_dir), capture_output=True)
        except Exception as e:
            logger.debug(f"Git pull update note for {target_dir}: {e}")

        new_head = GitDeltaScanner.get_commit_hash(target_dir, "HEAD")
        is_updated = (old_head != new_head)
        return target_dir, old_head, new_head, is_updated

    @staticmethod
    def get_diff(repo_dir: Path, base_ref: str = "HEAD~1", head_ref: str = "HEAD") -> str:
        """Extracts git diff output between two refs."""
        try:
            res = subprocess.run(
                ["git", "diff", "-U3", base_ref, head_ref],
                cwd=str(repo_dir),
                capture_output=True,
                text=True
            )
            if res.returncode == 0:
                return res.stdout
            # Fallback if base_ref (e.g. HEAD~1) fails on shallow clone
            fallback_res = subprocess.run(
                ["git", "diff", "-U3", "HEAD"],
                cwd=str(repo_dir),
                capture_output=True,
                text=True
            )
            return fallback_res.stdout
        except Exception as e:
            logger.warning(f"Failed to obtain git diff: {e}")
            return ""

    @staticmethod
    def parse_diff(diff_text: str) -> List[FileDiff]:
        """
        Parses unified git diff text and returns a list of FileDiff objects
        with 1-indexed modified line ranges.
        """
        file_diffs: List[FileDiff] = []
        if not diff_text or not diff_text.strip():
            return file_diffs

        # Split diff by file header
        file_sections = re.split(r"(?=diff --git )", diff_text)

        for sec in file_sections:
            if not sec.strip():
                continue

            # Extract target file path: +++ b/(...)
            m_path = re.search(r"\+\+\+ b/(.*)", sec)
            if not m_path:
                continue
            fpath = m_path.group(1).strip()
            if not fpath.endswith(".sol"):
                continue

            # Determine change type
            change_type = "modified"
            if "new file mode" in sec:
                change_type = "added"
            elif "deleted file mode" in sec:
                change_type = "deleted"

            # Parse chunk ranges: @@ -old,count +new,count @@
            ranges: List[Tuple[int, int]] = []
            for chunk in re.finditer(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", sec):
                new_start = int(chunk.group(3))
                new_count = int(chunk.group(4)) if chunk.group(4) is not None else 1
                end_line = new_start + max(1, new_count) - 1
                ranges.append((new_start, end_line))

            file_diffs.append(
                FileDiff(
                    file_path=fpath,
                    change_type=change_type,
                    modified_line_ranges=ranges,
                    patch=sec,
                )
            )

        return file_diffs

    @staticmethod
    def map_diff_to_context(
        repo_dir: Path,
        file_diffs: List[FileDiff],
        full_context: ContractContext
    ) -> ContractContext:
        """
        Maps modified line spans to contracts and functions in full_context,
        tagging is_modified=True on affected nodes and returning a targeted delta ContractContext.
        """
        if not file_diffs:
            return full_context

        modified_contracts: List[SolidityContract] = []
        modified_functions_summary: List[str] = []

        # Create mapping of file diffs by normalized path
        diff_by_file = {d.file_path.replace("\\", "/"): d for d in file_diffs}

        for contract in full_context.contracts:
            contract_modified = False

            # Check if file has diffs
            matching_diff = None
            for fpath, diff in diff_by_file.items():
                if fpath in contract.name or any(fpath in str(p) for p in [full_context.file_path]):
                    matching_diff = diff
                    break
            if not matching_diff and file_diffs:
                # If cannot match by filename, match against all diff ranges
                matching_diff = file_diffs[0]

            if matching_diff:
                for func in contract.functions:
                    for start_r, end_r in matching_diff.modified_line_ranges:
                        # Check intersection of function span [func.start_line, func.end_line] with diff [start_r, end_r]
                        if not (func.end_line < start_r or func.start_line > end_r):
                            func.is_modified = True
                            contract_modified = True
                            summary_tag = f"{contract.name}.{func.name}"
                            if summary_tag not in modified_functions_summary:
                                modified_functions_summary.append(summary_tag)
                            break

                # Also check if contract-level variables/inheritance were touched
                for start_r, end_r in matching_diff.modified_line_ranges:
                    if not (contract.end_line < start_r or contract.start_line > end_r):
                        contract_modified = True
                        break

            if contract_modified:
                contract.is_modified = True
                if contract not in modified_contracts:
                    modified_contracts.append(contract)

        delta_meta = {
            "is_delta": True,
            "modified_files": [d.file_path for d in file_diffs],
            "modified_functions": modified_functions_summary,
            "diff_count": len(file_diffs),
        }

        return ContractContext(
            file_path=full_context.file_path,
            pragma_version=full_context.pragma_version,
            imports=full_context.imports,
            contracts=modified_contracts if modified_contracts else full_context.contracts,
            slither_findings=full_context.slither_findings,
            full_source=full_context.full_source,
            defense_tags=full_context.defense_tags,
            delta_metadata=delta_meta,
            address=full_context.address,
            chain_id=full_context.chain_id,
            contract_name=full_context.contract_name,
        )


def scan_target(
    target_path_or_url: str,
    output_dir: str = "results/drafts",
    delta_mode: bool = False,
    base_ref: str = "HEAD~1",
    head_ref: str = "HEAD"
) -> Optional[ContractContext]:
    """Scans a local directory, file, or remote git repo, optionally applying delta diff parsing."""
    is_git = target_path_or_url.startswith("http") or target_path_or_url.endswith(".git")

    if is_git:
        target_dir, old_sha, new_sha, is_updated = GitDeltaScanner.clone_or_update(target_path_or_url)
    else:
        target_dir = Path(target_path_or_url).resolve()

    logger.info(f"🚀 Scanning target: {target_dir}")

    # 1. Parse and extract context
    if target_dir.is_dir():
        context = SolidityParser.parse_directory(str(target_dir), auto_slither=True)
    elif target_dir.is_file():
        context = SolidityParser.parse_file(str(target_dir))
    else:
        logger.warning(f"Target path does not exist: {target_dir}")
        return None

    if not context.contracts:
        logger.warning(f"No Solidity contracts detected in {target_dir}")
        return None

    # Apply Delta Diff filter if requested
    if delta_mode and (is_git or (target_dir / ".git").exists()):
        diff_text = GitDeltaScanner.get_diff(target_dir, base_ref=base_ref, head_ref=head_ref)
        file_diffs = GitDeltaScanner.parse_diff(diff_text)
        if file_diffs:
            logger.info(f"⚡ Applying Delta Diff: {len(file_diffs)} modified Solidity file(s)")
            context = GitDeltaScanner.map_diff_to_context(target_dir, file_diffs, context)

    logger.info(f"✅ Ingested {len(context.contracts)} contracts. Target pragma: {context.pragma_version}")

    # 2. Dynamic compiler version adjustment
    if context.pragma_version != "unknown":
        v = SolcSelector.detect_version(f"pragma solidity {context.pragma_version};")
        if v:
            SolcSelector.switch_version(v)

    # 3. Multi-Agent Audit Debate
    provider = os.getenv("LLM_PROVIDER", "mock")
    llm_client = get_llm_backend(provider=provider)
    debater = AuditDebater(RedTeamAgent(llm_client), BlueTeamAgent(llm_client))
    session = debater.run_session(context)

    # 4. Generate Reports
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_file = out_dir / f"audit_{target_dir.stem}_{int(time.time())}.md"

    reporter = MarkdownReporter()
    report_content = reporter.generate_bounty_report(session)
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_content)

    logger.info(f"📝 Report written to {report_file}")

    # 5. Leaderboard & Wallet Updates
    try:
        from server import update_leaderboard
        for f in session.triaged_findings:
            sev_str = f.final_severity.value if hasattr(f.final_severity, 'value') else str(f.final_severity)
            if sev_str in ["Critical", "High", "Medium"]:
                bounty_map = {"Critical": 25000, "High": 10000, "Medium": 3000}
                bounty_val = bounty_map.get(sev_str, 1000)
                conf = int(f.red_team_analysis.confidence * 10) if hasattr(f, 'red_team_analysis') and f.red_team_analysis else 85
                update_leaderboard(target_dir.name, f.title, sev_str, conf, bounty_val)
                logger.info(f"🏆 Finding Logged: [{sev_str}] {f.title} (Est: ${bounty_val:,})")
    except Exception as e:
        logger.debug(f"Leaderboard sync note: {e}")

    # 6. Dispatch Webhook Alerts if Critical/High bugs exist
    notifier = WebhookNotifier()
    notifier.notify_audit_completed(session)

    return context


def main():
    parser = argparse.ArgumentParser(description="EthAudit-Agent Batch & Delta Target Scanner")
    parser.add_argument("targets", nargs="*", default=[], help="Target file paths, directories, or Git repository URLs")
    parser.add_argument("--delta", action="store_true", help="Enable delta diff scanning mode between commits")
    parser.add_argument("--base-ref", default="HEAD~1", help="Base commit ref for git diff (default: HEAD~1)")
    parser.add_argument("--head-ref", default="HEAD", help="Head commit ref for git diff (default: HEAD)")
    parser.add_argument("--output-dir", default="results/drafts", help="Output directory for generated reports")

    args = parser.parse_args()

    targets = args.targets
    if not targets:
        # Default scan examples directory
        examples_dir = BASE_DIR / "examples"
        targets = [str(f) for f in examples_dir.glob("*.sol")]

    logger.info(f"🎯 Starting Batch Audit Sweep on {len(targets)} targets (Delta mode: {args.delta})...")
    for target in targets:
        try:
            scan_target(
                target,
                output_dir=args.output_dir,
                delta_mode=args.delta,
                base_ref=args.base_ref,
                head_ref=args.head_ref
            )
        except Exception as e:
            logger.error(f"Error scanning {target}: {e}")

    logger.info("🎉 Batch Audit Sweep completed successfully across all targets!")


if __name__ == "__main__":
    main()
