"""
Blue Team Persona Agent: Evaluates Red Team hypotheses, prunes false positives, defines invariant properties, and formulates patches.
"""
import json
import logging
from typing import List, Dict, Optional
from ..core.context import (
    ContractContext,
    RedTeamHypothesis,
    BlueTeamCritique,
    FindingStatus,
    Severity,
)
from .base import BaseLLMClient
from .prompts import BLUE_TEAM_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class BlueTeamAgent:
    def __init__(self, llm_client: BaseLLMClient):
        self.llm = llm_client

    def critique(
        self,
        context: ContractContext,
        hypotheses: List[RedTeamHypothesis]
    ) -> List[BlueTeamCritique]:
        """Reviews Red Team hypotheses, evaluates contract defenses, and produces critiques."""
        if not hypotheses:
            return []

        user_prompt = self._build_critique_prompt(context, hypotheses)
        raw_response = self.llm.generate(
            system_prompt=BLUE_TEAM_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.2
        )
        return self._parse_response(raw_response, context=context, hypotheses=hypotheses)

    def re_evaluate(
        self,
        context: ContractContext,
        refined_hypotheses: List[RedTeamHypothesis],
        previous_critiques: List[BlueTeamCritique]
    ) -> List[BlueTeamCritique]:
        """
        Multi-turn defense review: Re-evaluates refined Red Team hypotheses
        against contract invariants and defensive modifiers.
        """
        if not refined_hypotheses:
            return []

        user_prompt = self._build_critique_prompt(context, refined_hypotheses)
        raw_response = self.llm.generate(
            system_prompt=BLUE_TEAM_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.2
        )
        updated = self._parse_response(raw_response, context=context, hypotheses=refined_hypotheses)
        return updated if updated else previous_critiques


    def _build_critique_prompt(
        self,
        context: ContractContext,
        hypotheses: List[RedTeamHypothesis]
    ) -> str:
        prompt_parts = [
            f"### Contract Under Defensive Audit: {context.file_path}",
            f"### Pragma: {context.pragma_version}",
            "\n### Discovered Contract Architecture & Defense Tags:"
        ]

        for contract in context.contracts:
            defenses = []
            if contract.has_checked_math:
                defenses.append("Solidity 0.8+ Checked Math")
            if contract.is_non_reentrant:
                defenses.append("nonReentrant Mutex Guard")
            if contract.is_ownable:
                defenses.append("Ownable Access Control")
            if contract.has_initializer_lock:
                defenses.append("Initializer Lock")

            prompt_parts.append(
                f"- **{contract.name}** ({contract.kind}): Modifiers: {', '.join(contract.modifiers) if contract.modifiers else 'None'} | Defenses: {', '.join(defenses) if defenses else 'None'}"
            )

        prompt_parts.append("\n### Red Team Hypotheses to Evaluate:")
        for hyp in hypotheses:
            prompt_parts.append(
                f"\n--- Hypothesis ID: {hyp.id} ---\n"
                f"- Title: {hyp.title}\n"
                f"- Target: {hyp.target_contract}.{hyp.target_function or 'all'}\n"
                f"- Claimed Severity: {hyp.severity.value}\n"
                f"- Threat Vector: {hyp.threat_vector}\n"
                f"- Preconditions: {json.dumps(hyp.attack_preconditions)}\n"
                f"- Attack Steps: {json.dumps(hyp.theoretical_attack_steps)}\n"
                f"- Impact Claimed: {hyp.impact}\n"
                f"- Description: {hyp.description}\n"
            )

        prompt_parts.append("\n### Complete Contract Source Code for Verification:")
        prompt_parts.append("```solidity")
        prompt_parts.append(context.full_source)
        prompt_parts.append("```")
        prompt_parts.append("\nEvaluate each hypothesis, challenge false assumptions, identify compiler/modifier protections, draft valid compiling Foundry invariants, and propose patches.")

        return "\n".join(prompt_parts)

    def _parse_response(
        self,
        raw_response: str,
        context: Optional[ContractContext] = None,
        hypotheses: Optional[List[RedTeamHypothesis]] = None
    ) -> List[BlueTeamCritique]:
        import re
        if not raw_response or not raw_response.strip():
            if context and hypotheses:
                from .base import MockLLMBackend
                raw_response = MockLLMBackend().generate("BLUE TEAM DEFENSE AUDITOR", self._build_critique_prompt(context, hypotheses))
            else:
                return []

        # 1. Clean reasoning tags
        cleaned = re.sub(r"<think>[\s\S]*?</think>", "", raw_response, flags=re.DOTALL).strip()

        # 2. Try parsing json code blocks
        data = None
        code_blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
        for cb in code_blocks:
            try:
                data = json.loads(cb.strip())
                if isinstance(data, dict) and "critiques" in data:
                    break
            except Exception:
                pass

        # 3. Try parsing full text
        if not data:
            try:
                data = json.loads(cleaned)
            except Exception:
                pass

        # 4. Try outermost curly braces
        if not data:
            first_brace = cleaned.find("{")
            last_brace = cleaned.rfind("}")
            if first_brace != -1 and last_brace > first_brace:
                sub = cleaned[first_brace:last_brace + 1]
                try:
                    data = json.loads(sub)
                except Exception:
                    sanitized = re.sub(r",\s*([\]}])", r"\1", sub)
                    try:
                        data = json.loads(sanitized)
                    except Exception:
                        pass

        # 5. Fallback to rule engine if LLM JSON failed
        if not data and context and hypotheses:
            try:
                from .base import MockLLMBackend
                mock_out = MockLLMBackend().generate("BLUE TEAM DEFENSE AUDITOR", self._build_critique_prompt(context, hypotheses))
                data = json.loads(mock_out)
            except Exception:
                pass

        if not data or not isinstance(data, dict):
            logger.warning(f"Failed to parse Blue Team JSON (falling back to empty/mock). Preview: {raw_response[:200]}")
            return []

        critiques_raw = data.get("critiques", [])
        results = []

        for item in critiques_raw:
            status_str = str(item.get("status", "Validated")).capitalize()
            try:
                status = FindingStatus(status_str)
            except ValueError:
                status = FindingStatus.VALIDATED

            sev_str = str(item.get("validated_severity", "Medium")).capitalize()
            try:
                severity = Severity(sev_str)
            except ValueError:
                severity = Severity.MEDIUM

            results.append(
                BlueTeamCritique(
                    hypothesis_id=item.get("hypothesis_id", "UNKNOWN"),
                    status=status,
                    counter_arguments=item.get("counter_arguments", []),
                    validated_severity=severity,
                    foundry_invariant_spec=item.get("foundry_invariant_spec"),
                    remediation_patch=item.get("remediation_patch"),
                    defense_mechanisms_present=item.get("defense_mechanisms_present", []),
                    notes=item.get("notes", ""),
                )
            )
        return results

