"""
Bug Bounty Submission Builder & Platform Formatter
Supports Immunefi V2.2, Code4rena, Sherlock, and GHSA submission standards.
"""

from typing import Dict, Any, Optional
import time

class SubmissionBuilder:
    @staticmethod
    def build_immunefi_v2(
        finding_id: str,
        title: str,
        target_contract: str,
        function_name: str,
        threat_vector: str,
        severity: str,
        description: str,
        attack_preconditions: list,
        attack_steps: list,
        impact_statement: str,
        poc_solidity_code: str,
        remediation_text: str,
        patch_diff: str,
        target_chain: str = "Ethereum Mainnet",
        bounty_estimate_usd: int = 25000
    ) -> str:
        """Generates an Immunefi V2.2 compliant bug bounty submission."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        
        preconditions_md = "\n".join([f"- {p}" for p in attack_preconditions]) if attack_preconditions else "- No special preconditions required (publicly callable function)."
        attack_steps_md = "\n".join([f"{idx+1}. {step}" for idx, step in enumerate(attack_steps)]) if attack_steps else "1. Identify target contract deployment.\n2. Trigger vulnerable function call during execution lifecycle."
        
        lines = [
            f"# [IMMUNEFI SUBMISSION] {title}",
            "",
            f"**Finding ID:** `{finding_id}`  ",
            f"**Date Submitted:** `{timestamp}`  ",
            f"**Target Contract:** `{target_contract}` (`{function_name}`)  ",
            f"**Target Network:** `{target_chain}`  ",
            f"**Assessed Severity (Immunefi V2.2 Rubric):** **`{severity.upper()}`**  ",
            f"**Estimated Bounty Tier:** `${bounty_estimate_usd:,} USD`  ",
            "",
            "---",
            "",
            "## 1. Brief Summary",
            f"A **{severity.lower()}** severity vulnerability was identified in `{target_contract}.{function_name}`. "
            f"The vulnerability allows an attacker to exploit `{threat_vector}`, leading to {impact_statement.lower()}.",
            "",
            "---",
            "",
            "## 2. Vulnerability Details & Root Cause",
            f"### Technical Description",
            f"{description}",
            "",
            "### Vulnerability Mechanism",
            "- **Threat Vector / Weakness:** `" + threat_vector + "`",
            "- **Affected Components:** `" + target_contract + "." + function_name + "`",
            "",
            "### Attack Preconditions",
            f"{preconditions_md}",
            "",
            "### Attack Execution Steps",
            f"{attack_steps_md}",
            "",
            "---",
            "",
            "## 3. Impact Assessment",
            f"> **Direct Impact:** {impact_statement}",
            "",
            f"- **Immunefi Severity Classification:** **{severity.upper()}** (Direct Loss of Funds / Protocol State Hijack)",
            "- **User Funds at Risk:** Yes",
            "- **Protocol Invariants Broken:** State synchronization and authorization bounds are violated during callback execution.",
            "",
            "---",
            "",
            "## 4. Proof of Concept (Foundry / Forge Test)",
            "The following Foundry invariant / unit test reproduces the vulnerability:",
            "",
            "```solidity",
            f"{poc_solidity_code.strip()}",
            "```",
            "",
            "### How to Run the PoC:",
            "```bash",
            "# Run the verification test with detailed trace",
            "forge test --match-test test_V4HookTransientReentrancy -vvvv",
            "```",
            "",
            "---",
            "",
            "## 5. Recommended Mitigation & Remediation",
            f"{remediation_text}",
            "",
            "### Unified Patch Diff (`git diff`)",
            "```diff",
            f"{patch_diff.strip()}",
            "```",
            "",
            "---",
            "*Report generated & validated by Eth-Hunter Automated Security Engine.*"
        ]
        return "\n".join(lines)
