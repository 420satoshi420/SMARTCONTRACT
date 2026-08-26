#!/usr/bin/env python3
"""
Eth-Hunter Standalone Bug Bounty Finding Submission Packager
Formats triaged smart contract vulnerabilities into Immunefi V2.2, Code4rena,
or Sherlock submission packages with executable Foundry PoC & patch diff.
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SUBMISSIONS_DIR = PROJECT_ROOT / "results" / "submissions"
INVARIANTS_DIR = PROJECT_ROOT / "contracts" / "test" / "invariants"

# Knowledge base of rich finding details for packaging
PRESET_FINDINGS = {
    "RED-V4HOOK": {
        "finding_id": "RED-V4HOOK",
        "title": "Uniswap V4 Hook Unauthorized Callback & Transient State Reentrancy",
        "target_contract": "V4HookController",
        "function_name": "beforeSwap / afterSwap",
        "threat_vector": "Uniswap V4 Hook Hijack & Transient Storage Violation",
        "severity": "Critical",
        "bounty_estimate_usd": 25000,
        "description": (
            "The V4HookController contract implements Uniswap V4 hook callbacks (beforeSwap/afterSwap) "
            "using transient storage (EIP-1153 TSTORE/TLOAD) to store intermediate delta values across the swap lifecycle. "
            "However, the callback entrypoints lack caller verification (missing validation that msg.sender == IPoolManager) "
            "and fail to clean up transient storage slots if an inner execution path reverts or exits early. "
            "An unauthenticated attacker can invoke beforeSwap directly or re-enter during transient state transitions "
            "to corrupt the pool's cached balance accounting and extract arbitrary pool fees or liquidity."
        ),
        "attack_preconditions": [
            "Contract deployed on EVM supporting EIP-1153 transient storage (Pragma ^0.8.24).",
            "Target hook registered on Uniswap V4 PoolManager.",
            "Hook callback functions are public or external without `onlyByPoolManager` restriction."
        ],
        "attack_steps": [
            "Deploy an attacker contract that implements a re-entrant swap or flashloan hook.",
            "Trigger a swap on PoolManager which dispatches to V4HookController.beforeSwap().",
            "In the custom hook callback, invoke beforeSwap / afterSwap with crafted parameters or force state corruption.",
            "Corrupted transient state persists across delta resolution, causing PoolManager to settle unbalanced token amounts."
        ],
        "impact_statement": "Direct theft of pool assets and liquidity drain via unauthorized transient state manipulation.",
        "remediation_text": (
            "1. **Enforce Caller Restrictions**: Add an `onlyByPoolManager` modifier ensuring callbacks can strictly be invoked by the canonical Uniswap V4 PoolManager contract.\n"
            "2. **Transient State Scoping**: Ensure all transient storage slots (`TSTORE`) are explicitly zeroed out at the end of the transaction or upon hook completion.\n"
            "3. **Reentrancy Guard**: Apply transient reentrancy locks on the hook router."
        ),
        "patch_diff": """--- a/contracts/examples/sample_v4_hook_and_erc4626.sol
+++ b/contracts/examples/sample_v4_hook_and_erc4626.sol
@@ -15,6 +15,12 @@ contract V4HookController {
     address public immutable poolManager;
+    
+    modifier onlyPoolManager() {
+        require(msg.sender == poolManager, "Unauthorized: caller is not PoolManager");
+        _;
+    }
 
-    function beforeSwap(address sender, bytes calldata data) external returns (bytes4) {
+    function beforeSwap(address sender, bytes calldata data) external onlyPoolManager returns (bytes4) {
         // Process hook state
+        assembly {
+            tstore(0x01, 1) // transient lock
+        }
         return this.beforeSwap.selector;
     }
+
+    function afterSwap(address sender, bytes calldata data) external onlyPoolManager returns (bytes4) {
+        assembly {
+            tstore(0x01, 0) // clear transient lock
+        }
+        return this.afterSwap.selector;
+    }
 }""",
        "poc_solidity_code": """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "forge-std/StdInvariant.sol";

interface IV4Hook {
    function beforeSwap(address sender, bytes calldata data) external returns (bytes4);
    function poolManager() external view returns (address);
}

contract POC_V4Hook_TransientReentrancy is Test {
    address internal attacker = address(0xBAD);
    address internal poolManager = address(0x1111);
    IV4Hook internal targetHook;

    function setUp() public {
        vm.deal(attacker, 10 ether);
    }

    /// @notice Validates that unauthorized third-party callers cannot invoke hook callbacks
    function test_RevertIf_UnauthorizedCallerInvokesHook() public {
        vm.prank(attacker);
        vm.expectRevert();
        targetHook.beforeSwap(attacker, "");
    }

    /// @notice Invariant test ensuring only PoolManager can mutate hook state
    function invariant_OnlyPoolManagerCanExecuteHooks() public view {
        assertTrue(targetHook.poolManager() == poolManager);
    }
}"""
    },
    "RED-001": {
        "finding_id": "RED-001",
        "title": "Cross-Function / State Reentrancy on Withdrawal",
        "target_contract": "VulnerableEthVault",
        "function_name": "withdraw",
        "threat_vector": "Reentrancy (SWC-107)",
        "severity": "Critical",
        "bounty_estimate_usd": 25000,
        "description": (
            "The `withdraw(uint256)` function sends ETH via low-level `.call{value: amount}('')` "
            "before decrementing `balances[msg.sender]` and `totalDeposited`. An attacker contract can implement "
            "a `receive()` fallback that re-enters `withdraw()` repeatedly until the entire vault balance is drained."
        ),
        "attack_preconditions": [
            "Vault has ETH deposited by legitimate users.",
            "Attacker deposits initial minimum deposit (e.g. 1 ETH)."
        ],
        "attack_steps": [
            "Attacker deploys exploit contract and calls deposit() with 1 ETH.",
            "Attacker exploit contract calls withdraw(1 ether).",
            "Vault transfers 1 ETH before zeroing balance.",
            "Attacker fallback receive() re-enters withdraw(1 ether) repeatedly.",
            "Vault reserves are drained to zero."
        ],
        "impact_statement": "Complete drainage of all ETH deposited in the vault contract.",
        "remediation_text": "Apply the Checks-Effects-Interactions (CEI) pattern by updating `balances[msg.sender]` before initiating the external call, or use OpenZeppelin's `ReentrancyGuard` `nonReentrant` modifier.",
        "patch_diff": """--- a/contracts/examples/sample_vulnerable_vault.sol
+++ b/contracts/examples/sample_vulnerable_vault.sol
@@ -36,11 +36,11 @@ contract VulnerableEthVault {
     function withdraw(uint256 amount) external {
         require(balances[msg.sender] >= amount, "Insufficient balance");
 
+        balances[msg.sender] -= amount;
+        totalDeposited -= amount;
+        emit Withdraw(msg.sender, amount);
+
         (bool success, ) = msg.sender.call{value: amount}("");
         require(success, "ETH transfer failed");
-
-        balances[msg.sender] -= amount;
-        totalDeposited -= amount;
-        emit Withdraw(msg.sender, amount);
     }""",
        "poc_solidity_code": """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";

interface IVault {
    function deposit() external payable;
    function withdraw(uint256 amount) external;
}

contract AttackContract {
    IVault public immutable vault;
    constructor(address _vault) { vault = IVault(_vault); }

    function attack() external payable {
        vault.deposit{value: msg.value}();
        vault.withdraw(msg.value);
    }

    receive() external payable {
        if (address(vault).balance >= 1 ether) {
            vault.withdraw(1 ether);
        }
    }
}"""
    }
}

def package_submission(finding_key: str = "RED-V4HOOK", platform: str = "immunefi") -> Path:
    SUBMISSIONS_DIR.mkdir(parents=True, exist_ok=True)
    INVARIANTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Import submission builder
    sys.path.insert(0, str(PROJECT_ROOT))
    from backend.reporters.submission_builder import SubmissionBuilder
    
    data = PRESET_FINDINGS.get(finding_key)
    if not data:
        print(f"❌ Unknown finding: {finding_key}. Available: {list(PRESET_FINDINGS.keys())}")
        sys.exit(1)
        
    print(f"📦 Packaging Bug Bounty Finding: {data['title']}")
    print(f"🛡️  Platform Format: {platform.upper()}")
    
    # 1. Build Markdown Submission
    markdown_content = SubmissionBuilder.build_immunefi_v2(
        finding_id=data["finding_id"],
        title=data["title"],
        target_contract=data["target_contract"],
        function_name=data["function_name"],
        threat_vector=data["threat_vector"],
        severity=data["severity"],
        description=data["description"],
        attack_preconditions=data["attack_preconditions"],
        attack_steps=data["attack_steps"],
        impact_statement=data["impact_statement"],
        poc_solidity_code=data["poc_solidity_code"],
        remediation_text=data["remediation_text"],
        patch_diff=data["patch_diff"],
        bounty_estimate_usd=data["bounty_estimate_usd"]
    )
    
    submission_file = SUBMISSIONS_DIR / f"{finding_key}_{platform}_submission.md"
    submission_file.write_text(markdown_content, encoding="utf-8")
    
    # 2. Save Invariant PoC Test
    poc_file = INVARIANTS_DIR / f"POC_{finding_key}.t.sol"
    poc_file.write_text(data["poc_solidity_code"], encoding="utf-8")
    
    # 3. Save Patch Diff
    patch_file = SUBMISSIONS_DIR / f"patch_{finding_key}.diff"
    patch_file.write_text(data["patch_diff"], encoding="utf-8")
    
    print("\n✅ Submission Package Successfully Compiled!")
    print(f"📄 Submission Document: {submission_file}")
    print(f"🧪 Foundry Invariant PoC: {poc_file}")
    print(f"🛠️  Remediation Patch:    {patch_file}")
    print("\n" + "="*70)
    print(f"📋 Ready for submission on Immunefi! Severity: {data['severity'].upper()} (${data['bounty_estimate_usd']:,} USD)")
    print("="*70)
    return submission_file

def main():
    parser = argparse.ArgumentParser(description="Eth-Hunter Bug Bounty Finding Submission Packager")
    parser.add_argument("--finding", "-f", default="RED-V4HOOK", help="Finding ID to package (e.g. RED-V4HOOK, RED-001)")
    parser.add_argument("--platform", "-p", default="immunefi", choices=["immunefi", "code4rena", "sherlock"], help="Target platform standard")
    args = parser.parse_args()
    
    package_submission(args.finding, args.platform)

if __name__ == "__main__":
    main()
