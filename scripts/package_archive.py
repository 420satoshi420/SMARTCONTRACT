#!/usr/bin/env python3
"""
Eth-Hunter Submission Archive & Distribution Packager
Packages all 25 Immunefi V2.2 markdown reports, Foundry PoC invariant suites,
and defensive remediation patches into a structured, production-ready distribution archive.
"""

import os
import sys
import json
import time
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SUBMISSIONS_DIR = PROJECT_ROOT / "results" / "submissions"
BATCH_DIR = SUBMISSIONS_DIR / "batch"
ARCHIVE_DIR = SUBMISSIONS_DIR / "archive"
TESTS_DIR = PROJECT_ROOT / "contracts" / "test" / "invariants"
REPORTS_DIR = PROJECT_ROOT / "results" / "reports"
ALL_FINDINGS_DIR = PROJECT_ROOT / "results" / "all_findings"

def package_submission_archive():
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp_str = time.strftime("%Y%m%d_%H%M%S")
    zip_name = f"ETH_HUNTER_IMMUNEFI_SUBMISSIONS_{timestamp_str}.zip"
    latest_zip_name = "ETH_HUNTER_IMMUNEFI_SUBMISSIONS_LATEST.zip"
    zip_path = ARCHIVE_DIR / zip_name
    latest_zip_path = ARCHIVE_DIR / latest_zip_name

    print(f"📦 Packaging submission archive: {zip_path.name}...")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Add Master Summaries
        if (ALL_FINDINGS_DIR / "DEDUPLICATED_SUMMARY.md").exists():
            zf.write(ALL_FINDINGS_DIR / "DEDUPLICATED_SUMMARY.md", "README_PORTFOLIO.md")
        if (ALL_FINDINGS_DIR / "INDEX.md").exists():
            zf.write(ALL_FINDINGS_DIR / "INDEX.md", "ALL_FINDINGS_INDEX.md")
        if (ALL_FINDINGS_DIR / "deduplicated.json").exists():
            zf.write(ALL_FINDINGS_DIR / "deduplicated.json", "data/deduplicated.json")

        # 2. Add 25 Batch Immunefi Submissions
        if BATCH_DIR.exists():
            for f in sorted(BATCH_DIR.glob("*.md")):
                zf.write(f, f"submissions/{f.name}")

        # 3. Add Foundry Invariant & PoC Test Suites
        if TESTS_DIR.exists():
            for f in sorted(TESTS_DIR.glob("*.sol")):
                zf.write(f, f"contracts/test/invariants/{f.name}")

        # 4. Add Remediation Patches
        for f in sorted(SUBMISSIONS_DIR.glob("*.diff")):
            zf.write(f, f"patches/{f.name}")

        # 5. Add Core Slither & Static Audit Reports
        if REPORTS_DIR.exists():
            for f in sorted(REPORTS_DIR.glob("*.md")):
                zf.write(f, f"reports/{f.name}")

    # Create / Update symlink or copy to LATEST.zip
    try:
        import shutil
        shutil.copyfile(zip_path, latest_zip_path)
    except Exception as e:
        print(f"Notice: {e}")

    file_size_kb = zip_path.stat().st_size / 1024
    print(f"✅ Submission Archive Successfully Created!")
    print(f"📄 Archive File: {zip_path} ({file_size_kb:.1f} KB)")
    print(f"🔗 Latest Bundle: {latest_zip_path}")
    return zip_path

if __name__ == "__main__":
    package_submission_archive()
