"""
Adversarial debate orchestrator: manages the multi-turn interaction loop between Red Team and Blue Team,
integrates MEV economic math, Bayesian confidence updates, and composite triage scoring.
"""
import logging
from typing import List, Dict, Optional
from ..core.context import (
    ContractContext,
    AuditSession,
    RedTeamHypothesis,
    BlueTeamCritique,
    TriagedFinding,
    FindingStatus,
    Severity,
)
from ..core.economic_evaluator import EconomicEvaluator
from ..agents.red_team import RedTeamAgent
from ..agents.blue_team import BlueTeamAgent

logger = logging.getLogger(__name__)


class AuditDebater:
    """Coordinates the 4-Layer adversarial debate between Red and Blue teams."""

    def __init__(
        self,
        red_team: RedTeamAgent,
        blue_team: BlueTeamAgent,
        rounds: int = 1,
        min_confidence_score: int = 5,
        protocol_tvl_usd: Optional[float] = None,
        gas_price_gwei: float = 20.0,
        eth_price_usd: float = 1920.0,
        flashloan_fee_bps: int = 9,
        flashloan_provider: Optional[str] = None,
    ):
        self.red_team = red_team
        self.blue_team = blue_team
        self.rounds = max(1, rounds)
        self.min_confidence = min_confidence_score
        self.protocol_tvl_usd = protocol_tvl_usd
        self.gas_price_gwei = gas_price_gwei
        self.eth_price_usd = eth_price_usd
        self.flashloan_fee_bps = flashloan_fee_bps
        self.flashloan_provider = flashloan_provider

    def run_session(self, context: ContractContext) -> AuditSession:
        """Executes the full 4-layer adversarial cognitive triage loop on the target contract context."""
        logger.info(f"Initiating Layer 2 Red Team adversarial analysis on {context.file_path}...")

        # Round 1: Red Team creates initial threat hypotheses
        red_hypotheses = self.red_team.analyze(context)
        # Filter by initial confidence threshold
        filtered_hypotheses = [h for h in red_hypotheses if h.confidence >= self.min_confidence]

        logger.info(f"Red Team generated {len(filtered_hypotheses)} hypotheses.")

        # Round 1: Blue Team evaluates, verifies, and challenges
        logger.info("Initiating Layer 2 Blue Team defensive review and false-positive triage...")
        blue_critiques = self.blue_team.critique(context, filtered_hypotheses)
        logger.info(f"Blue Team completed {len(blue_critiques)} critiques.")

        # Iterative Multi-Round Debate (if rounds > 1)
        if self.rounds > 1 and filtered_hypotheses:
            for round_idx in range(2, self.rounds + 1):
                logger.info(f"Initiating Adversarial Debate Round {round_idx}/{self.rounds}...")
                filtered_hypotheses = self.red_team.refine(context, filtered_hypotheses, blue_critiques)
                blue_critiques = self.blue_team.re_evaluate(context, filtered_hypotheses, blue_critiques)

        # Layer 3 (Economic & MEV Feasibility) + Layer 4 (Socratic Synthesis & Bayesian Scoring)
        triaged_findings = self._synthesize(filtered_hypotheses, blue_critiques, context)

        session = AuditSession(
            target_file=context.file_path,
            context=context,
            red_hypotheses=filtered_hypotheses,
            blue_critiques=blue_critiques,
            triaged_findings=triaged_findings,
            summary=f"Audit completed: {len(triaged_findings)} findings triaged across {len(context.contracts)} contract definitions."
        )

        return session

    def _calculate_bayesian_confidence(
        self,
        hypothesis: RedTeamHypothesis,
        critique: BlueTeamCritique,
        context: Optional[ContractContext] = None
    ) -> int:
        """
        Calculates calibrated Bayesian confidence score (0-100%) incorporating
        prior confidence, defense critique status, and false-positive penalties (Rule 4).
        """
        # 1. Base Prior Confidence (scale 1-10 or 1-100 to percentage)
        if hypothesis.confidence <= 10:
            confidence = hypothesis.confidence * 10
        else:
            confidence = min(100, hypothesis.confidence)

        # 2. Blue Team Defensive Verification Update
        if critique.status == FindingStatus.VALIDATED:
            confidence = min(100, confidence + 5)
        elif critique.status == FindingStatus.CHALLENGED:
            confidence = max(0, confidence - 20)
        elif critique.status == FindingStatus.REJECTED:
            confidence = min(20, max(0, confidence - 50))

        # 3. Rule 4 False Positive & Speculation Penalties
        lower_desc = (hypothesis.description + " " + hypothesis.title + " " + " ".join(hypothesis.attack_preconditions)).lower()
        
        # -30% if the exploit assumes the contract owner / multisig behaves maliciously
        if "malicious owner" in lower_desc or "compromised owner" in lower_desc or "rogue admin" in lower_desc:
            confidence = max(0, confidence - 30)

        # -40% if compiler version >= 0.8.0 and finding claims integer overflow without unchecked blocks
        if "overflow" in lower_desc or "underflow" in lower_desc:
            has_checked = True
            if context:
                # Check pragma or contracts
                has_checked = context.pragma_version.startswith("^0.8") or "0.8" in context.pragma_version
            if has_checked and "unchecked" not in lower_desc:
                confidence = max(0, confidence - 40)

        # -50% if a nonReentrant modifier or mutex is present on the execution call graph
        if "reentrancy" in lower_desc or "reentrant" in lower_desc:
            has_mutex = False
            if context:
                for c in context.contracts:
                    if c.name == hypothesis.target_contract:
                        if c.is_non_reentrant:
                            has_mutex = True
                        for f in c.functions:
                            if f.name == hypothesis.target_function and (f.is_non_reentrant or f.is_guarded):
                                has_mutex = True
            if has_mutex and critique.status == FindingStatus.REJECTED:
                confidence = max(0, confidence - 50)

        return max(0, min(100, confidence))

    def _synthesize(
        self,
        hypotheses: List[RedTeamHypothesis],
        critiques: List[BlueTeamCritique],
        context: Optional[ContractContext] = None
    ) -> List[TriagedFinding]:
        critique_map: Dict[str, BlueTeamCritique] = {c.hypothesis_id: c for c in critiques}
        findings: List[TriagedFinding] = []

        for hyp in hypotheses:
            critique = critique_map.get(hyp.id)
            if not critique:
                # Default fallback critique if missing
                critique = BlueTeamCritique(
                    hypothesis_id=hyp.id,
                    status=FindingStatus.CHALLENGED,
                    counter_arguments=["Automated verification inconclusive."],
                    validated_severity=hyp.severity,
                    remediation_patch="Review state access and consider defensive modifiers.",
                    notes="Requires manual confirmation by auditor."
                )

            # 1. Compute Bayesian Confidence Score
            confidence_score = self._calculate_bayesian_confidence(hyp, critique, context)

            # 2. Determine Final Status and Severity
            if confidence_score < 70 and critique.status == FindingStatus.REJECTED:
                final_status = FindingStatus.REJECTED
                final_severity = Severity.FALSE_POSITIVE
            elif confidence_score < 70 and critique.status == FindingStatus.CHALLENGED:
                final_status = FindingStatus.CHALLENGED
                final_severity = critique.validated_severity if critique.validated_severity != Severity.FALSE_POSITIVE else hyp.severity
            else:
                final_status = critique.status
                final_severity = critique.validated_severity if critique.validated_severity != Severity.FALSE_POSITIVE else hyp.severity

            # 3. Layer 3 Economic & MEV Feasibility Evaluation
            # Assign representative capital/extraction baselines for economic modeling
            if final_severity == Severity.CRITICAL:
                gross_est = 50_000.0
                capital_est = 10_000.0
            elif final_severity == Severity.HIGH:
                gross_est = 20_000.0
                capital_est = 5_000.0
            elif final_severity == Severity.MEDIUM:
                gross_est = 4_000.0
                capital_est = 1_000.0
            elif final_severity in (Severity.LOW, Severity.INFORMATIONAL):
                gross_est = 500.0
                capital_est = 0.0
            else:
                gross_est = 0.0
                capital_est = 0.0

            economic_eval = EconomicEvaluator.evaluate_exploit_profitability(
                gross_extractable_usd=gross_est,
                gas_price_gwei=self.gas_price_gwei,
                eth_price_usd=self.eth_price_usd,
                required_capital_usd=capital_est,
                protocol_tvl_usd=self.protocol_tvl_usd,
                flashloan_fee_bps=self.flashloan_fee_bps,
                flashloan_provider=self.flashloan_provider
            )

            # Rule 3: Economic Feasibility Gate
            if final_severity in (Severity.CRITICAL, Severity.HIGH):
                if not economic_eval["meets_skin_in_game_threshold"] and gross_est > 0:
                    # Downgrade to Low / Griefing if net profit < $1k or ROI < 2.0x
                    final_severity = Severity.LOW

            # 4. Calculate Bounty Valuation & Composite Score (Layer 4)
            bounty_estimate = EconomicEvaluator.calculate_bounty_estimate(final_severity, self.protocol_tvl_usd)
            composite_score = EconomicEvaluator.calculate_composite_score(confidence_score, bounty_estimate)

            # 5. Build Proof of Concept Logic Summary
            poc_summary = ""
            if hyp.theoretical_attack_steps:
                poc_summary = "Theoretical Attack Sequence:\n" + "\n".join(
                    f"{i+1}. {step}" for i, step in enumerate(hyp.theoretical_attack_steps)
                )

            findings.append(
                TriagedFinding(
                    id=hyp.id,
                    title=hyp.title,
                    contract_name=hyp.target_contract,
                    function_name=hyp.target_function,
                    threat_vector=hyp.threat_vector,
                    final_severity=final_severity,
                    status=final_status,
                    red_team_analysis=hyp,
                    blue_team_defense=critique,
                    proof_of_concept_logic=poc_summary,
                    recommended_mitigation=critique.remediation_patch or "Apply defensive Checks-Effects-Interactions pattern.",
                    mitigation_diff=None,
                    confidence_score=confidence_score,
                    composite_score=composite_score,
                    bounty_estimate_usd=bounty_estimate,
                    economic_feasibility=economic_eval,
                )
            )

        return findings
