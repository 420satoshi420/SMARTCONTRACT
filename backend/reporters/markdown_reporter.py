"""
Markdown and Foundry report generator supporting Jinja2 with built-in pure-Python fallback.
Supports Immunefi V2.2, Code4rena, and Sherlock audit report formats.
"""
from pathlib import Path
from typing import Optional, List
from ..core.context import AuditSession, Severity, FindingStatus, TriagedFinding


class MarkdownReporter:
    def __init__(self, templates_dir: Optional[str] = None):
        if not templates_dir:
            templates_dir = str(Path(__file__).resolve().parent.parent.parent / "templates")
        self.templates_dir = templates_dir
        self._has_jinja = False
        try:
            from jinja2 import Environment, FileSystemLoader
            self.env = Environment(loader=FileSystemLoader(templates_dir), autoescape=False)
            self._has_jinja = True
        except ImportError:
            self.env = None

    def _format_unified_diff(self, f: TriagedFinding) -> str:
        """Helper to generate clean unified diff patch."""
        if f.mitigation_diff and f.mitigation_diff.strip():
            return f.mitigation_diff.strip()
        
        contract = f.contract_name or "TargetContract"
        func = f.function_name or "execute"
        patch = f.blue_team_defense.remediation_patch or f.recommended_mitigation or "nonReentrant guard applied."
        patch_clean = patch.strip().replace("\n", " ")
        
        return f"--- a/{contract}.sol\n+++ b/{contract}.sol\n@@ -10,5 +10,7 @@ function {func}()\n-    // Vulnerable execution without guard\n+    // Remediated: {patch_clean}"

    def generate_bounty_report(self, session: AuditSession, preset: str = "immunefi") -> str:
        preset_clean = preset.lower()
        # Compute statistics
        validated_count = sum(1 for f in session.triaged_findings if f.status == FindingStatus.VALIDATED)
        challenged_count = sum(1 for f in session.triaged_findings if f.status == FindingStatus.CHALLENGED)
        rejected_count = sum(1 for f in session.triaged_findings if f.status == FindingStatus.REJECTED or f.final_severity == Severity.FALSE_POSITIVE)

        critical_count = sum(1 for f in session.triaged_findings if f.final_severity == Severity.CRITICAL and f.status == FindingStatus.VALIDATED)
        high_count = sum(1 for f in session.triaged_findings if f.final_severity == Severity.HIGH and f.status == FindingStatus.VALIDATED)
        medium_count = sum(1 for f in session.triaged_findings if f.final_severity == Severity.MEDIUM and f.status == FindingStatus.VALIDATED)
        low_count = sum(1 for f in session.triaged_findings if f.final_severity in (Severity.LOW, Severity.INFORMATIONAL) and f.status == FindingStatus.VALIDATED)

        if self._has_jinja and self.env:
            try:
                template = self.env.get_template("bounty_report.md.jinja2")
                return template.render(
                    session=session,
                    preset=preset_clean,
                    validated_count=validated_count,
                    challenged_count=challenged_count,
                    rejected_count=rejected_count,
                    critical_count=critical_count,
                    high_count=high_count,
                    medium_count=medium_count,
                    low_count=low_count,
                )
            except Exception:
                pass

        # Pure Python Built-in Fallback Rendering
        preset_title = "IMMUNEFI V2.2"
        if preset_clean in ("code4rena", "c4"):
            preset_title = "CODE4RENA"
        elif preset_clean == "sherlock":
            preset_title = "SHERLOCK"

        lines = [
            "# Ethereum Smart Contract Security Audit & Bug Bounty Report\n",
            f"**Target File:** `{session.target_file}`  ",
            f"**Solidity Pragma:** `{session.context.pragma_version}`  ",
            "**Audit Framework:** `EthAudit-Agent (Red/Blue Multi-Agent System)`  ",
            f"**Report Preset:** `{preset_title}`  \n",
            "---\n",
            "## Executive Summary\n",
            "| Total Findings | Validated Bugs | Challenged / Needs Review | Filtered False Positives |",
            "|:--------------:|:--------------:|:-------------------------:|:------------------------:|",
            f"| {len(session.triaged_findings)} | {validated_count} | {challenged_count} | {rejected_count} |\n",
            "### Findings Severity Distribution",
            f"- **Critical:** {critical_count}",
            f"- **High:** {high_count}",
            f"- **Medium:** {medium_count}",
            f"- **Low / Informational:** {low_count}\n",
            "---\n",
            "## Triaged Findings Summary\n",
            "| ID | Title | Target Contract | Threat Vector | Red Team Severity | Blue Team Status | Final Severity |",
            "|:---|:------|:----------------|:--------------|:------------------|:-----------------|:---------------|"
        ]

        for f in session.triaged_findings:
            anchor = f"{f.id.lower()}-{f.title.lower().replace(' ', '-').replace('/', '').replace('(', '').replace(')', '')}"
            lines.append(
                f"| [{f.id}](#{anchor}) | {f.title} | `{f.contract_name}` | {f.threat_vector} | {f.red_team_analysis.severity.value} | {f.status.value} | **{f.final_severity.value}** |"
            )

        lines.append("\n---\n")
        lines.append("## Detailed Vulnerability Analysis\n")

        for f in session.triaged_findings:
            target_str = f"{f.contract_name}.{f.function_name}" if f.function_name else f.contract_name
            swc_str = f" (`{f.red_team_analysis.swc_id}`)" if f.red_team_analysis.swc_id else ""
            bounty_str = f"${f.bounty_estimate_usd:,.0f}" if f.bounty_estimate_usd else "$0"
            lines.extend([
                f"### {f.id}: {f.title}\n",
                f"- **Target:** `{target_str}`",
                f"- **Threat Vector:** {f.threat_vector}{swc_str}",
                f"- **Assessed Severity:** **{f.final_severity.value}** (Status: *{f.status.value}*)",
                f"- **Confidence Score:** {f.confidence_score}% | **Composite Score:** {f.composite_score} | **Estimated Bounty:** {bounty_str}\n",
                "#### Vulnerability Description",
                f"{f.red_team_analysis.description}\n",
                "#### Adversarial Threat Model (Red Team)",
                "**Attack Preconditions:**"
            ])
            for pre in f.red_team_analysis.attack_preconditions:
                lines.append(f"- {pre}")
            
            lines.append("\n**Theoretical Attack Mechanics:**")
            for i, step in enumerate(f.red_team_analysis.theoretical_attack_steps):
                lines.append(f"{i+1}. {step}")

            lines.extend([
                "\n**Claimed Impact:**",
                f"> {f.red_team_analysis.impact}\n",
                "#### Defensive Verification & Triage (Blue Team)",
                f"- **Triage Result:** `{f.blue_team_defense.status.value}`",
                "- **Compiler / Architecture Safeguards Present:**"
            ])

            if f.blue_team_defense.defense_mechanisms_present:
                for def_m in f.blue_team_defense.defense_mechanisms_present:
                    lines.append(f"  - `{def_m}`")
            else:
                lines.append("  - None detected in vulnerable code flow.")

            lines.extend([
                "\n**Blue Team Analysis Notes:**",
                f"{f.blue_team_defense.notes}\n",
                "#### Proof of Concept (PoC) & Attack Trace"
            ])

            if f.proof_of_concept_logic:
                lines.extend([
                    "```solidity",
                    f"{f.proof_of_concept_logic}",
                    "```\n"
                ])
            else:
                lines.extend([
                    "1. **Prank Setup:** Initialize attacker address `0xBAD...` with necessary capital.",
                    f"2. **State Manipulation:** Call `{target_str}()` to initiate vulnerable state transition.",
                    "3. **Exploit Extraction:** Re-enter or exploit unconstrained logic before state sync.",
                    "4. **Invariant Break Verification:** Verify state invariant failure and unauthorized fund extraction.\n"
                ])

            if f.blue_team_defense.foundry_invariant_spec:
                lines.extend([
                    "#### Invariant Test Specification (Foundry / Forge)",
                    "```solidity",
                    f"{f.blue_team_defense.foundry_invariant_spec}",
                    "```\n"
                ])

            diff_str = self._format_unified_diff(f)
            lines.extend([
                "#### Recommended Remediation",
                f"{f.recommended_mitigation}\n",
                "#### Unified Patch Diff (`mitigation_diff`)",
                "```diff",
                f"{diff_str}",
                "```\n",
                "---\n"
            ])

        lines.extend([
            "## Disclaimer",
            "*This report was generated by an automated multi-agent adversarial simulation system. All findings must be validated in local sandbox environments before deployment.*"
        ])

        return "\n".join(lines)

    def generate_foundry_invariants(self, session: AuditSession) -> str:
        valid_invariants = [
            f for f in session.triaged_findings
            if f.blue_team_defense.foundry_invariant_spec and f.status == FindingStatus.VALIDATED
        ]
        # Find main target contract (prefer contract over interface/library)
        contract_name = "Target"
        for c in session.context.contracts:
            if c.kind == "contract":
                contract_name = c.name
                break
        if contract_name == "Target" and session.context.contracts:
            contract_name = session.context.contracts[-1].name

        if self._has_jinja and self.env:
            try:
                template = self.env.get_template("foundry_invariant.sol.jinja2")
                return template.render(
                    session=session,
                    contract_name=contract_name,
                    invariants=valid_invariants
                )
            except Exception:
                pass

        # Fallback pure-Python rendering
        lines = [
            "// SPDX-License-Identifier: MIT",
            f"pragma solidity {session.context.pragma_version};\n",
            'import "forge-std/Test.sol";',
            'import "forge-std/StdInvariant.sol";\n',
            "/**",
            f" * @title {contract_name}InvariantTest",
            " * @notice Automated Invariant and Property Test Suite generated by EthAudit-Agent Blue Team",
            " */",
            f"contract {contract_name}InvariantTest is StdInvariant, Test {{",
            "    address internal targetContract;",
            "    address internal attacker = address(0xBAD);",
            "    address internal alice = address(0xA11CE);",
            "    address internal bob = address(0xB0B);\n",
            "    function setUp() public virtual {",
            "        vm.deal(attacker, 100 ether);",
            "        vm.deal(alice, 50 ether);",
            "        vm.deal(bob, 50 ether);",
            "    }\n"
        ]

        for f in valid_invariants:
            lines.extend([
                "    /**",
                f"     * @notice Invariant for Finding {f.id}: {f.title}",
                f"     * Threat Vector: {f.threat_vector}",
                "     */",
                f"    {f.blue_team_defense.foundry_invariant_spec}\n"
            ])

        lines.append("}")
        return "\n".join(lines)

    def generate_foundry_handler(self, session: AuditSession) -> str:
        contract_name = "Target"
        for c in session.context.contracts:
            if c.kind == "contract":
                contract_name = c.name
                break
        if contract_name == "Target" and session.context.contracts:
            contract_name = session.context.contracts[-1].name

        if self._has_jinja and self.env:
            try:
                template = self.env.get_template("foundry_handler.sol.jinja2")
                return template.render(
                    session=session,
                    contract_name=contract_name,
                )
            except Exception:
                pass

        # Fallback pure-Python rendering
        lines = [
            "// SPDX-License-Identifier: MIT",
            f"pragma solidity {session.context.pragma_version};\n",
            'import "forge-std/Test.sol";\n',
            "/**",
            f" * @title {contract_name}Handler",
            " * @notice Actor Handler for Bounded Property-Based Invariant Fuzzing",
            " * Generated by EthAudit-Agent Blue Team",
            " */",
            f"contract {contract_name}Handler is Test {{",
            "    address internal targetContract;",
            "    uint256 public ghost_depositSum;",
            "    uint256 public ghost_withdrawSum;",
            "    uint256 public ghost_actorCalls;\n",
            "    constructor(address _target) {",
            "        targetContract = _target;",
            "    }\n",
            "    function deposit(uint256 amount) public {",
            "        amount = bound(amount, 1 wei, 1000 ether);",
            "        vm.deal(msg.sender, amount);",
            "        vm.prank(msg.sender);",
            '        (bool success, ) = targetContract.call{value: amount}(abi.encodeWithSignature("deposit()"));',
            "        if (success) { ghost_depositSum += amount; ghost_actorCalls++; }",
            "    }\n",
            "    function withdraw(uint256 amount) public {",
            "        amount = bound(amount, 1 wei, 1000 ether);",
            "        vm.prank(msg.sender);",
            '        (bool success, ) = targetContract.call(abi.encodeWithSignature("withdraw(uint256)", amount));',
            "        if (success) { ghost_withdrawSum += amount; ghost_actorCalls++; }",
            "    }",
            "}"
        ]
        return "\n".join(lines)
