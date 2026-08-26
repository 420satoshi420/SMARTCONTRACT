"""
High-Performance Confidence Evaluator and False-Positive Filter for ETH Hunter.
Filters out low-confidence static analysis noise and optimizes LLM token efficiency.

v2.0: Proof-Level Calibrated Scoring
- Confidence scores are CAPPED by proof level (no high scores without real evidence)
- Theoretical-only findings max out at 40%
- Static analysis confirmed findings max at 60%
- Fork-reproduced findings max at 90%
- Mainnet-simulated (Tenderly/cast) max at 100%
"""

from typing import List, Dict, Any, Optional
from enum import Enum


class ConfidenceLevel(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    INFORMATIONAL = "Informational"


class ProofLevel(str, Enum):
    """
    Evidence tier that CAPS the maximum confidence a finding can achieve.
    This is the key mechanism preventing inflated scores on unverified findings.
    """
    THEORETICAL = "Theoretical"          # LLM/heuristic-only analysis — cap at 40%
    STATIC_CONFIRMED = "Static"          # Slither/Semgrep confirmed — cap at 60%
    FORK_REPRODUCED = "Fork Reproduced"  # Foundry fork test passes — cap at 90%
    MAINNET_SIMULATED = "Mainnet Sim"    # Tenderly/cast simulation — cap at 100%

    @property
    def max_confidence(self) -> int:
        return _PROOF_CAPS[self]


_PROOF_CAPS = {
    ProofLevel.THEORETICAL: 40,
    ProofLevel.STATIC_CONFIRMED: 60,
    ProofLevel.FORK_REPRODUCED: 90,
    ProofLevel.MAINNET_SIMULATED: 100,
}


# Detectors known to produce high false-positive rates or low-value noise
NOISY_DETECTORS = {
    "naming-convention",
    "dead-code",
    "solc-version",
    "pragma",
    "assembly",
    "low-level-calls",
    "similar-names",
    "too-many-digits",
    "const-immutable",
    "unused-state",
    "unused-return",
    "constable-states",
    "external-function",
    "missing-zero-check",     # often false positive in known-deployer contexts
    "reentrancy-benign",      # informational reentrancy — not exploitable
    "reentrancy-events",      # event ordering — not financially exploitable
    "timestamp",              # miner manipulation window is usually <15s
}

# High-impact security critical detectors that warrant immediate deep inspection
HIGH_PRIORITY_DETECTORS = {
    "reentrancy-eth",
    "reentrancy-no-eth",
    "arbitrary-send-erc20",
    "arbitrary-send-eth",
    "suicidal",
    "unprotected-upgrade",
    "controlled-delegatecall",
    "tx-origin",
    "unchecked-transfer",
    "shadowing-state",
    "uninitialized-state",
    "uninitialized-storage",
    "oracle-manipulation",
    "arbitrary-send-erc20-permit",
    "domain-separator-collision",
    "delegatecall-loop",
    "msg-value-loop",
    "storage-array",
    "weak-prng",
}


class ConfidenceFilter:
    """Intelligent confidence triage and efficiency filter for smart contract findings."""

    def __init__(self, min_confidence: str = "Medium", min_score: int = 40):
        self.min_confidence = min_confidence.lower()
        self.min_score = min_score
        self._seen_signatures: set = set()  # deduplication

    def should_process_detector(self, detector: Dict[str, Any]) -> bool:
        """
        Determines if a static analysis finding is confident and severe enough
        to justify downstream LLM synthesis and PoC generation.
        """
        check_name = detector.get("check", detector.get("detector", "")).lower()
        confidence = str(detector.get("confidence", "Medium")).lower()
        impact = str(detector.get("impact", "Medium")).lower()

        # Always skip known low-value noise unless explicitly auditing styling
        if check_name in NOISY_DETECTORS:
            return False

        # Fast-track high-priority security vulnerabilities
        if any(h in check_name for h in HIGH_PRIORITY_DETECTORS):
            return True

        # Check confidence threshold
        if self.min_confidence == "high" and confidence != "high":
            return False
        elif self.min_confidence == "medium" and confidence not in ["high", "medium"]:
            # Drop low-confidence findings to maintain high efficiency
            return False

        return True

    def _make_signature(self, finding: Dict[str, Any]) -> str:
        """Creates a dedup signature to avoid reporting the same finding twice."""
        check = finding.get("check", finding.get("detector", "unknown"))
        elements = finding.get("elements", [])
        first_file = ""
        first_line = 0
        if elements:
            first_file = elements[0].get("filename", "")
            lines = elements[0].get("lines", [])
            first_line = lines[0] if lines else 0
        return f"{check}::{first_file}::{first_line}"

    def calculate_confidence_score(
        self,
        base_confidence: int,
        impact: str,
        detector_name: str,
        proof_level: ProofLevel = ProofLevel.THEORETICAL,
        blue_team_status: str = "",
        has_compilable_poc: bool = False,
        forge_test_passed: bool = False,
        on_chain_tvl_usd: float = 0.0,
        contract_balance_eth: float = 0.0,
    ) -> int:
        """
        Calculates calibrated confidence score (0-100) with proof-level capping.

        The score is built up from evidence, then HARD CAPPED by the proof level.
        This prevents inflated scores on unverified theoretical findings.
        """
        score = base_confidence

        # 1. Impact weighting
        impact_lower = impact.lower()
        if impact_lower == "high":
            score = min(100, score + 10)
        elif impact_lower == "low":
            score = max(10, score - 15)
        elif impact_lower == "informational":
            score = max(5, score - 25)

        # 2. Detector heuristics
        detector_lower = detector_name.lower()
        if any(h in detector_lower for h in HIGH_PRIORITY_DETECTORS):
            score = min(100, score + 15)
        elif detector_lower in NOISY_DETECTORS:
            score = max(10, score - 25)

        # 3. Blue Team validation adjustment
        if blue_team_status:
            status_lower = blue_team_status.lower()
            if status_lower == "validated":
                score = min(100, score + 5)
            elif status_lower == "challenged":
                score = max(0, score - 15)
            elif status_lower == "rejected":
                score = max(0, score - 40)

        # 4. PoC and forge test bonuses
        if has_compilable_poc:
            score = min(100, score + 10)
        if forge_test_passed:
            score = min(100, score + 20)

        # 5. On-chain signal boost (only if TVL/balance is meaningful)
        if on_chain_tvl_usd > 100_000:
            score = min(100, score + 5)  # real money at stake = more credible
        elif on_chain_tvl_usd > 0 and on_chain_tvl_usd < 1_000:
            score = max(0, score - 10)   # tiny TVL = likely test contract

        # 6. HARD CAP by proof level — THIS IS THE KEY MECHANISM
        max_allowed = proof_level.max_confidence
        score = min(score, max_allowed)

        return max(0, min(100, score))

    def filter_and_rank(
        self,
        findings: List[Dict[str, Any]],
        max_items: int = 5,
        proof_level: ProofLevel = ProofLevel.THEORETICAL,
    ) -> List[Dict[str, Any]]:
        """Filters low-confidence findings, deduplicates, and sorts by composite risk score."""
        valid_findings = []
        self._seen_signatures.clear()

        for f in findings:
            if not self.should_process_detector(f):
                continue

            # Deduplicate
            sig = self._make_signature(f)
            if sig in self._seen_signatures:
                continue
            self._seen_signatures.add(sig)

            impact = f.get("impact", "Medium")
            conf_str = f.get("confidence", "Medium")
            base_conf = 85 if conf_str.lower() == "high" else (65 if conf_str.lower() == "medium" else 40)

            adjusted_conf = self.calculate_confidence_score(
                base_conf,
                impact,
                f.get("check", f.get("detector", "")),
                proof_level=proof_level,
            )

            # Apply minimum score threshold
            if adjusted_conf < self.min_score:
                continue

            f["_computed_confidence"] = adjusted_conf
            f["_proof_level"] = proof_level.value
            valid_findings.append(f)

        # Sort descending by computed confidence score
        valid_findings.sort(key=lambda x: x.get("_computed_confidence", 0), reverse=True)
        return valid_findings[:max_items]
