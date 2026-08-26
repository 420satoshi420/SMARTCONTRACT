#!/usr/bin/env python3
"""
Eth-Hunter Real-Time Smart Contract Security & Static Analysis Pipeline
Executes automated Slither analysis, Foundry invariant tests, and compiles
structured defensive audit reports with remediation steps.
"""

import os
import sys
import json
import time
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
CONTRACTS_DIR = PROJECT_ROOT / "contracts"
REPORTS_DIR = PROJECT_ROOT / "results" / "reports"
CACHE_DIR = PROJECT_ROOT / "cache"

SEVERITY_MAP = {
    "High": "CRITICAL / HIGH",
    "Medium": "MEDIUM",
    "Low": "LOW",
    "Informational": "INFORMATIONAL",
    "Optimization": "GAS OPTIMIZATION"
}

REMEDIATION_GUIDE = {
    "reentrancy-eth": "Apply Checks-Effects-Interactions (CEI) pattern or use OpenZeppelin ReentrancyGuard.",
    "reentrancy-no-eth": "Ensure internal state is updated before invoking external token transfer or hooks.",
    "arbitrary-send-erc20": "Verify sender authorization using `msg.sender` checks before initiating ERC20 `transferFrom`.",
    "unchecked-transfer": "Use OpenZeppelin's `SafeERC20` wrapper (`safeTransfer` / `safeTransferFrom`) to handle non-standard return values.",
    "solc-version": "Lock pragma version to a current, stable release (e.g. ^0.8.20) and avoid deprecated compilers.",
    "shadowing-state": "Rename local or inherited variables to avoid state shadowing.",
    "unprotected-upgrade": "Ensure initialize / upgrade functions are guarded by `onlyOwner` or access control modules."
}

def log(msg: str, level: str = "INFO"):
    timestamp = time.strftime("%H:%M:%S")
    symbols = {"INFO": "ℹ️", "SUCCESS": "✅", "WARN": "⚠️", "ERROR": "❌", "AUDIT": "🛡️"}
    sym = symbols.get(level, "•")
    print(f"[{timestamp}] {sym} {msg}")

def ensure_venv():
    """Ensure we are running inside or activating the python venv."""
    venv_bin = BACKEND_DIR / "venv" / "bin"
    if venv_bin.exists():
        os.environ["PATH"] = f"{venv_bin}:{os.environ.get('PATH', '')}"
        os.environ["VIRTUAL_ENV"] = str(BACKEND_DIR / "venv")

def auto_select_solc(target_path: Path):
    """Detects Solidity pragma in target and selects the appropriate solc version."""
    import re
    files_to_check = [target_path] if target_path.is_file() else list(target_path.glob("**/*.sol"))
    for f in files_to_check:
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
            m = re.search(r'pragma\s+solidity\s+[\^>=<~]*\s*([0-9]+\.[0-9]+\.[0-9]+)', content)
            if m:
                ver = m.group(1)
                log(f"Detected Solidity pragma {ver} in {f.name}", "INFO")
                subprocess.run(["solc-select", "use", ver], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
        except Exception:
            pass

def run_slither(target_path: Path, output_json: Path) -> Optional[Dict[str, Any]]:
    """Runs Slither static analyzer on target path."""
    auto_select_solc(target_path)
    log(f"Running Slither analyzer on: {target_path}", "AUDIT")
    cmd = [
        "slither",
        str(target_path),
        "--json",
        str(output_json)
    ]
    
    env = os.environ.copy()
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=str(PROJECT_ROOT), env=env)
        if output_json.exists():
            with open(output_json, "r", encoding="utf-8") as f:
                data = json.load(f)
            log(f"Slither completed with output saved to {output_json.name}", "SUCCESS")
            return data
        else:
            log(f"Slither did not produce JSON output. Stderr: {proc.stderr[:300]}", "WARN")
            return None
    except FileNotFoundError:
        log("Slither executable not found. Make sure slither-analyzer is installed.", "ERROR")
        return None
    except Exception as e:
        log(f"Unexpected error running Slither: {e}", "ERROR")
        return None

def run_foundry_tests() -> Optional[Dict[str, Any]]:
    """Runs forge test if foundry.toml is detected."""
    foundry_toml = PROJECT_ROOT / "foundry.toml"
    if not foundry_toml.exists():
        return None
    
    log("Running Foundry test suite and invariant assertions...", "AUDIT")
    try:
        cmd = ["forge", "test", "--summary"]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=str(PROJECT_ROOT))
        return {
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "passed": proc.returncode == 0
        }
    except Exception as e:
        log(f"Foundry test execution skipped: {e}", "WARN")
        return None

def parse_slither_results(slither_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extracts structured findings from Slither JSON report."""
    findings = []
    if not slither_data or not slither_data.get("results"):
        return findings
    
    detectors = slither_data["results"].get("detectors", [])
    for d in detectors:
        check = d.get("check", "unknown")
        confidence = d.get("confidence", "Medium")
        impact = d.get("impact", "Low")
        description = d.get("description", "").strip()
        
        first_line = description.split("\n")[0] if description else check
        recommendation = REMEDIATION_GUIDE.get(check, "Review Solidity documentation and apply defensive programming checks.")
        
        elements = d.get("elements", [])
        affected_files = []
        for el in elements:
            src = el.get("source_mapping", {})
            fname = src.get("filename_short", "")
            lines = src.get("lines", [])
            if fname and lines:
                affected_files.append(f"{fname}:{lines[0]}-{lines[-1] if len(lines) > 1 else lines[0]}")
        
        findings.append({
            "check": check,
            "title": first_line,
            "impact": impact,
            "confidence": confidence,
            "severity_label": SEVERITY_MAP.get(impact, "LOW"),
            "description": description,
            "recommendation": recommendation,
            "locations": list(set(affected_files))
        })
    return findings

def generate_markdown_report(target_name: str, preset: str, findings: List[Dict[str, Any]], foundry_res: Optional[Dict[str, Any]]) -> str:
    """Generates a professional Markdown security audit report."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    
    crit_count = sum(1 for f in findings if f["impact"] == "High")
    med_count = sum(1 for f in findings if f["impact"] == "Medium")
    low_count = sum(1 for f in findings if f["impact"] in ["Low", "Informational"])
    
    lines = [
        f"# Smart Contract Security Audit Report: {target_name}",
        f"**Audit Preset Format:** `{preset.capitalize()}`  ",
        f"**Date:** `{timestamp}`  ",
        f"**Framework:** Slither Static Analyzer & Foundry Test Engine  ",
        "",
        "---",
        "",
        "## 1. Executive Summary",
        "",
        f"A security evaluation was conducted on target `{target_name}`. "
        f"A total of **{len(findings)}** issues were triaged across the codebase.",
        "",
        "| Severity Level | Count | Status |",
        "| :--- | :---: | :--- |",
        f"| 🚨 Critical / High | `{crit_count}` | Requires Immediate Patch |",
        f"| ⚠️ Medium | `{med_count}` | Recommended Remediation |",
        f"| ℹ️ Low / Informational | `{low_count}` | Code Quality / Optimization |",
        "",
        "---",
        "",
        "## 2. Detailed Findings & Remediation Steps",
        ""
    ]
    
    if not findings:
        lines.append("✅ **No vulnerabilities detected.** Code conforms to standard checks.")
    else:
        for idx, f in enumerate(findings, 1):
            impact_badge = "🔴" if f["impact"] == "High" else ("🟡" if f["impact"] == "Medium" else "🔵")
            lines.extend([
                f"### {idx}. {impact_badge} [{f['severity_label']}] {f['title']}",
                f"- **Vulnerability Type:** `{f['check']}`",
                f"- **Confidence:** `{f['confidence']}`",
                f"- **Affected Locations:** `{', '.join(f['locations']) if f['locations'] else 'Target Contract'}`",
                "",
                "#### Description",
                "```text",
                f"{f['description']}",
                "```",
                "",
                "#### Defensive Remediation",
                f"> **Actionable Patch Recommendation:**  ",
                f"> {f['recommendation']}",
                "",
                "---"
            ])
            
    if foundry_res:
        lines.extend([
            "## 3. Foundry Invariant & Unit Test Suite Execution",
            f"**Status:** {'PASS' if foundry_res['passed'] else 'FAIL'}",
            "```text",
            f"{foundry_res['stdout'][:2000]}",
            "```",
            ""
        ])
        
    lines.append("\n*Report compiled autonomously by Eth-Hunter Security Engine.*")
    return "\n".join(lines)

def run_audit(target: str, preset: str = "immunefi") -> Path:
    ensure_venv()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    target_path = Path(target)
    if not target_path.is_absolute():
        target_path = PROJECT_ROOT / target
        
    if not target_path.exists():
        log(f"Target path does not exist: {target_path}", "ERROR")
        sys.exit(1)
        
    log(f"Starting audit pipeline for: {target_path.name}", "INFO")
    timestamp_slug = int(time.time())
    output_json = CACHE_DIR / f"slither_{target_path.stem}_{timestamp_slug}.json"
    report_file = REPORTS_DIR / f"audit_{target_path.stem}_{timestamp_slug}.md"
    
    # 1. Run Slither
    slither_data = run_slither(target_path, output_json)
    findings = parse_slither_results(slither_data) if slither_data else []
    
    # 2. Run Foundry
    foundry_res = run_foundry_tests()
    
    # 3. Generate Report
    report_md = generate_markdown_report(target_path.stem, preset, findings, foundry_res)
    report_file.write_text(report_md, encoding="utf-8")
    
    # 4. Save Summary JSON
    summary_file = REPORTS_DIR / f"summary_{target_path.stem}_{timestamp_slug}.json"
    summary_file.write_text(json.dumps({
        "target": str(target_path),
        "preset": preset,
        "timestamp": timestamp_slug,
        "findings_count": len(findings),
        "findings": findings
    }, indent=2), encoding="utf-8")
    
    log(f"Audit report successfully generated: {report_file}", "SUCCESS")
    print(f"\n📄 Markdown Report: {report_file}")
    print(f"📊 Total Findings: {len(findings)}\n")
    return report_file

def main():
    parser = argparse.ArgumentParser(description="Eth-Hunter Smart Contract Security & Static Analysis Pipeline")
    parser.add_argument("--target", "-t", default="contracts/target-repo", help="Path to contract file or directory")
    parser.add_argument("--preset", "-p", choices=["immunefi", "code4rena", "sherlock"], default="immunefi", help="Audit report format")
    args = parser.parse_args()
    
    run_audit(args.target, args.preset)

if __name__ == "__main__":
    main()
