"""
Slither Static Analysis Scanner with proper error handling.
Wraps the slither CLI tool and returns structured findings.

v2.0: Robust error handling, timeout management, and Slither availability detection.
"""

import subprocess
import json
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


def is_slither_available() -> bool:
    """Check if slither is installed and accessible in PATH."""
    return shutil.which("slither") is not None


def fast_scan(
    target_path: Path,
    filter_paths: str = "test|mock|node_modules|lib",
    timeout: int = 180,
) -> Tuple[Dict[str, Any], bool]:
    """
    Runs slither static analysis on a target path.

    Returns:
        Tuple of (findings_dict, had_error)
        findings_dict has structure: {"results": {"detectors": [...]}, ...}
    """
    target = Path(target_path)

    if not is_slither_available():
        logger.warning("Slither not installed. Install: pip install slither-analyzer")
        return {"results": {"detectors": []}, "error": "slither not installed"}, True

    if not target.exists():
        return {"results": {"detectors": []}, "error": f"Target not found: {target}"}, True

    cmd = [
        "slither", str(target),
        "--filter-paths", filter_paths,
        "--json", "-",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if result.stdout and result.stdout.strip():
            try:
                findings = json.loads(result.stdout)
                detector_count = len(findings.get("results", {}).get("detectors", []))
                logger.info(f"Slither found {detector_count} detectors for {target.name}")
                return findings, False
            except json.JSONDecodeError:
                logger.warning(f"Slither output is not valid JSON for {target.name}")
                return {
                    "results": {"detectors": []},
                    "raw_stdout": result.stdout[:2000],
                    "raw_stderr": result.stderr[:1000] if result.stderr else "",
                }, True

        # No stdout — slither may have errored
        return {
            "results": {"detectors": []},
            "raw_stderr": result.stderr[:1000] if result.stderr else "No output",
        }, True

    except subprocess.TimeoutExpired:
        logger.warning(f"Slither timed out ({timeout}s) for {target.name}")
        return {"results": {"detectors": []}, "error": f"Timeout ({timeout}s)"}, True
    except Exception as e:
        logger.warning(f"Slither execution failed: {e}")
        return {"results": {"detectors": []}, "error": str(e)}, True
