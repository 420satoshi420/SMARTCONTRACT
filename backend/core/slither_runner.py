"""
Automated Slither Static Analysis Runner and Output Normalizer.
"""
import os
import shutil
import subprocess
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class SlitherRunner:
    """Executes and parses Slither static analysis on Solidity files or Foundry projects."""

    @staticmethod
    def is_slither_available() -> bool:
        """Check if slither CLI is installed on the system."""
        return shutil.which("slither") is not None

    @classmethod
    def run_analysis(
        cls,
        target_path: str,
        output_json_path: Optional[str] = None,
        timeout: int = 120
    ) -> List[Dict[str, Any]]:
        """
        Runs Slither against a file or directory and returns a normalized list of findings.
        If Slither is not installed or fails, returns an empty list gracefully.
        """
        if not cls.is_slither_available():
            logger.info("Slither CLI not detected on system. Skipping automated static analysis.")
            return []

        path = Path(target_path)
        if not path.exists():
            logger.warning(f"Target path does not exist: {target_path}")
            return []

        # Default temporary json output if not specified
        json_out = output_json_path or str(path.parent / ".slither_output.json")

        cmd = [
            "slither",
            str(path.resolve()),
            "--json",
            json_out,
            "--exclude-informational",
            "--exclude-low"
        ]

        try:
            # Slither returns non-zero when vulnerabilities are found, so check=False
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            
            if Path(json_out).exists():
                with open(json_out, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    detectors = data.get("results", {}).get("detectors", [])
                    raw_normalized = cls._normalize_findings(detectors)
                    try:
                        from core.confidence_filter import ConfidenceFilter
                        filter_eng = ConfidenceFilter(min_confidence="Medium")
                        return filter_eng.filter_and_rank(raw_normalized, max_items=10)
                    except Exception:
                        return raw_normalized
        except subprocess.TimeoutExpired:
            logger.warning("Slither execution timed out.")
        except Exception as e:
            logger.warning(f"Slither execution encountered an error: {e}")
        finally:
            # Clean up temporary file if auto-generated
            if not output_json_path and Path(json_out).exists():
                try:
                    os.remove(json_out)
                except Exception:
                    pass

        return []

    @classmethod
    def _normalize_findings(cls, detectors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extracts key signals from Slither raw detectors into a compact format."""
        normalized = []
        for d in detectors:
            check = d.get("check", "unknown")
            impact = d.get("impact", "Medium")
            confidence = d.get("confidence", "Medium")
            description = d.get("description", "").strip()
            
            # Extract elements / line numbers
            elements = []
            for elem in d.get("elements", []):
                elem_type = elem.get("type", "")
                elem_name = elem.get("name", "")
                source_mapping = elem.get("source_mapping", {})
                lines = source_mapping.get("lines", [])
                filename = source_mapping.get("filename_short", "")
                if elem_name:
                    elements.append({
                        "type": elem_type,
                        "name": elem_name,
                        "filename": filename,
                        "lines": lines
                    })

            normalized.append({
                "detector": check,
                "impact": impact,
                "confidence": confidence,
                "description": description,
                "elements": elements
            })
        return normalized
