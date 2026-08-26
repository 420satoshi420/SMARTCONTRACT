---
trigger: always_on
description: Automatically execute terminal commands to diagnose, run tests, apply fixes, and verify code changes proactively without waiting for manual command execution.
---

# Autonomous Terminal & Fixing Rule

1. **Direct Terminal Execution**: When a code change, diagnostic, test, or scan is needed, execute the command directly using `run_command` in the appropriate directory (`/Users/wakeup/Desktop/eth-hunter`).
2. **Immediate Verification**: After making edits to fix bugs or errors, immediately run the corresponding test or compiler command to verify that the fix worked.
3. **No Unnecessary Prompts**: Do not ask the user to manually run commands unless external credentials (passwords, private secrets) or explicit physical inputs are required.
