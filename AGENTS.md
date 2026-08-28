# Repository Agent Instructions

## Secret scanning and credential safety

- Run Gitleaks only in repositories the user owns or is explicitly authorized to audit. If authorization is unclear, stop before scanning and ask for confirmation.
- Treat every suspected secret as sensitive. Never print, quote, copy, commit, upload, or include a complete secret, private key, seed phrase, password, token, or credential in output. Redact values (for example, `prefix...suffix`) and report only the minimum location and classification needed for remediation.
- Never test, validate, authenticate with, or otherwise use a discovered third-party credential. Never import or use a wallet private key or seed phrase, query its balance through the key, sign a transaction, or attempt to move funds.
- Prefer passive, offline detection. Do not enable credential verification or contact an external service to determine whether a finding is live.
- For each finding, report only the repository-relative file path, line number when safe, secret type, severity, and remediation. Do not include the matched value or surrounding content that could reconstruct it.
- For a confirmed project-owned secret: revoke or rotate it first, replace it with an environment variable or approved secret manager, remove it from Git history when appropriate, and run Gitleaks again. Do not declare remediation complete until the re-scan passes.
- Do not weaken `.gitleaks.toml`, add an allowlist entry, or suppress a finding merely to make CI pass. Any exception requires a documented false-positive rationale and human review.
- Prefer a dedicated branch and pull request for security changes. Do not commit directly to the default branch. Keep secret-scanning changes reviewable and require the Gitleaks check to pass before merge.

