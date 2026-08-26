#!/usr/bin/env python3
"""
Eth-Hunter Full Suite Orchestrator
Executes batch Slither static audits across all target contracts, runs Foundry
reproducible invariant tests, updates the findings ledger, deduplicates portfolio
records, and generates ready-to-submit Immunefi packages.
"""

import os
import sys
import time
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONTRACTS_DIR = PROJECT_ROOT / "contracts"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

def run_command(cmd, desc):
    print(f"\n=======================================================")
    print(f"🚀 {desc}")
    print(f"=======================================================")
    res = subprocess.run(cmd, shell=True, cwd=str(PROJECT_ROOT))
    if res.returncode != 0:
        print(f"⚠️ Warning: Command exited with code {res.returncode}")
    else:
        print(f"✅ Step Completed Successfully!")

def main():
    start_time = time.time()
    print("🛡️  Starting Full Eth-Hunter Pipeline Execution...")
    
    # 1. Audit Target.sol
    run_command(
        "source backend/venv/bin/activate && python3 scripts/audit_pipeline.py --target contracts/target-repo/Target.sol --preset immunefi",
        "Auditing contracts/target-repo/Target.sol"
    )

    # 2. Audit sample_vulnerable_vault.sol
    run_command(
        "source backend/venv/bin/activate && python3 scripts/audit_pipeline.py --target contracts/examples/sample_vulnerable_vault.sol --preset immunefi",
        "Auditing contracts/examples/sample_vulnerable_vault.sol"
    )

    # 3. Audit sample_v4_hook_and_erc4626.sol
    run_command(
        "source backend/venv/bin/activate && python3 scripts/audit_pipeline.py --target contracts/examples/sample_v4_hook_and_erc4626.sol --preset immunefi",
        "Auditing contracts/examples/sample_v4_hook_and_erc4626.sol"
    )

    # 4. Audit historical_defi_playground.sol
    run_command(
        "source backend/venv/bin/activate && python3 scripts/audit_pipeline.py --target contracts/examples/historical_defi_playground.sol --preset immunefi",
        "Auditing contracts/examples/historical_defi_playground.sol"
    )

    # 5. Run Foundry PoC Test Suite
    run_command(
        "forge test -vvv",
        "Executing Foundry PoC & Invariant Test Suite"
    )

    # 6. Deduplicate and Package Submissions
    run_command(
        "source backend/venv/bin/activate && python3 scripts/deduplicate_findings.py",
        "Deduplicating Findings & Packaging Immunefi Submissions"
    )

    elapsed = time.time() - start_time
    print(f"\n🎉 ALL OPERATIONS COMPLETED IN {elapsed:.2f}s!")

if __name__ == "__main__":
    main()
