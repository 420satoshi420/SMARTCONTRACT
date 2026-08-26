---
name: eth-hunter-automation
description: Automatically execute terminal commands, run tests, fix code issues, and orchestrate smart contract audits for Eth-Hunter. Use when running scans, fixing broken tests, diagnosing runtime failures, or executing terminal workflows autonomously.
---

# Eth-Hunter Terminal & Audit Automation Skill

This skill provides standard procedures for autonomous terminal execution, bug fixing, test running, and audit pipeline orchestration within Eth-Hunter.

## Core Directives for Autonomous Terminal Execution

1. **Proactive Command Execution**:
   - Always run commands directly via `run_command` to inspect, diagnose, build, test, and fix without requiring manual user copy-pasting.
   - Run commands in the workspace root (`/Users/wakeup/Desktop/eth-hunter`) or backend directory (`/Users/wakeup/Desktop/eth-hunter/backend`).

2. **Automated Verification Loop**:
   - After applying any code fix or configuration change, immediately execute verification commands:
     - Python syntax/import check: `python3 -m py_compile <file>`
     - Unit tests: `pytest tests/` (or `python3 -m unittest discover`)
     - Foundry test compilation & execution: `forge test -vvv`
     - Audit loop dry-run: `python3 autonomous_loop.py --target contracts/examples/sample_vulnerable_vault.sol --skip-if-clean`

3. **Autonomous Bug Remediation Protocol**:
   - **Step 1: Diagnose**: Run the failing command, capture stdout/stderr, and identify root cause (missing import, broken path, schema mismatch).
   - **Step 2: Edit**: Apply minimal, precise edits using `replace_file_content` or `multi_replace_file_content`.
   - **Step 3: Verify**: Re-run the command immediately to confirm resolution.
   - **Step 4: Report**: Summarize the fix and outcome clearly with links to modified files.
