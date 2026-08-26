"""
Layer 1 Perception — Static Analysis Finding Filter & Prioritizer.
Takes raw Slither output and produces a ranked list of the most
actionable, high-impact findings for downstream LLM triage.

v2.0: Real filtering logic with severity/impact/confidence ranking,
      deduplication, and noise detector suppression.
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Low-value detectors to suppress (same list as confidence_filter.py)
NOISE_DETECTORS = {
    "naming-convention", "dead-code", "solc-version", "pragma",
    "assembly", "low-level-calls", "similar-names", "too-many-digits",
    "const-immutable", "unused-state", "unused-return", "constable-states",
    "external-function", "missing-zero-check", "reentrancy-benign",
    "reentrancy-events", "timestamp",
}

# Impact ordering for sorting
IMPACT_RANK = {
    "high": 0,
    "medium": 1,
    "low": 2,
    "informational": 3,
    "optimization": 4,
}

CONFIDENCE_RANK = {
    "high": 0,
    "medium": 1,
    "low": 2,
}


def filter_findings(
    slither_output: Any,
    max_findings: int = 5,
    min_confidence: str = "medium",
    suppress_noise: bool = True,
) -> List[Dict[str, Any]]:
    """
    Filters and ranks Slither findings by impact and confidence.

    Args:
        slither_output: Raw Slither JSON output dict
        max_findings: Maximum number of findings to return
        min_confidence: Minimum confidence level ('high', 'medium', 'low')
        suppress_noise: If True, filters out known low-value detectors

    Returns:
        List of finding dicts sorted by impact (high first), deduplicated
    """
    # Extract detectors from Slither output structure
    if not isinstance(slither_output, dict):
        return []

    detectors = slither_output.get("results", {}).get("detectors", [])
    if not detectors:
        return []

    # Confidence threshold
    allowed_confidence = {"high"}
    if min_confidence.lower() in ("medium", "low"):
        allowed_confidence.add("medium")
    if min_confidence.lower() == "low":
        allowed_confidence.add("low")

    filtered = []
    seen_signatures = set()

    for det in detectors:
        check = str(det.get("check", det.get("detector", ""))).lower()
        confidence = str(det.get("confidence", "medium")).lower()
        impact = str(det.get("impact", "medium")).lower()

        # Skip noise detectors
        if suppress_noise and check in NOISE_DETECTORS:
            continue

        # Check confidence threshold
        if confidence not in allowed_confidence:
            continue

        # Skip purely informational/optimization findings
        if impact in ("informational", "optimization"):
            continue

        # Deduplication — same detector + same first element
        elements = det.get("elements", [])
        first_file = elements[0].get("source_mapping", {}).get("filename_short", "") if elements else ""
        sig = f"{check}::{first_file}"
        if sig in seen_signatures:
            continue
        seen_signatures.add(sig)

        filtered.append(det)

    # Sort by impact (high > medium > low) then by confidence (high > medium > low)
    filtered.sort(key=lambda d: (
        IMPACT_RANK.get(str(d.get("impact", "medium")).lower(), 3),
        CONFIDENCE_RANK.get(str(d.get("confidence", "medium")).lower(), 2),
    ))

    result = filtered[:max_findings]
    logger.info(f"Filtered {len(detectors)} raw detectors → {len(result)} actionable findings")
    return result
