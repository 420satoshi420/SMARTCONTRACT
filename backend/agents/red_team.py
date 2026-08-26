"""
Red Team Persona Agent: Generates adversarial hypotheses and vulnerability threat models.
"""
import json
import logging
from typing import List, Optional
try:
    from ..core.context import ContractContext, RedTeamHypothesis, BlueTeamCritique, Severity
except (ImportError, ValueError):
    from core.context import ContractContext, RedTeamHypothesis, BlueTeamCritique, Severity
from .base import BaseLLMClient
from .prompts import RED_TEAM_SYSTEM_PROMPT


logger = logging.getLogger(__name__)


class RedTeamAgent:
    def __init__(self, llm_client: BaseLLMClient):
        self.llm = llm_client

    def analyze(self, context: ContractContext) -> List[RedTeamHypothesis]:
        """Analyzes the contract context and returns vulnerability hypotheses."""
        user_prompt = self._build_analysis_prompt(context)
        raw_response = self.llm.generate(
            system_prompt=RED_TEAM_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.3
        )
        return self._parse_response(raw_response, context=context)

    def refine(
        self,
        context: ContractContext,
        previous_hypotheses: List[RedTeamHypothesis],
        previous_critiques: List[BlueTeamCritique],
    ) -> List[RedTeamHypothesis]:
        """
        Multi-turn refinement: Refines hypotheses or provides counter-arguments in response
        to Blue Team defense critiques.
        """
        if not previous_hypotheses:
            return []

        user_prompt = self._build_refinement_prompt(context, previous_hypotheses, previous_critiques)
        raw_response = self.llm.generate(
            system_prompt=RED_TEAM_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.3
        )
        refined = self._parse_response(raw_response, context=context)
        return refined if refined else previous_hypotheses


    def _build_analysis_prompt(self, context: ContractContext) -> str:
        prompt_parts = [
            f"### Target Contract File: {context.file_path}",
            f"### Pragma Version: {context.pragma_version}",
            f"### Imports: {', '.join(context.imports) if context.imports else 'None'}",
            "\n### Discovered Contracts & Interfaces:"
        ]

        for contract in context.contracts:
            prompt_parts.append(
                f"\n- **{contract.kind.capitalize()}**: `{contract.name}` (Inherits: {', '.join(contract.inheritance) if contract.inheritance else 'None'})"
            )
            prompt_parts.append(f"  * State Variables ({len(contract.state_variables)}): {', '.join(contract.state_variables[:10])}")
            prompt_parts.append(f"  * Modifiers: {', '.join(contract.modifiers) if contract.modifiers else 'None'}")
            prompt_parts.append(f"  * Functions ({len(contract.functions)}): {', '.join(f.name for f in contract.functions)}")
            
            # Defense tags
            defenses = []
            if contract.has_checked_math:
                defenses.append("Solidity 0.8+ Checked Math")
            if contract.is_non_reentrant:
                defenses.append("nonReentrant Mutex Guard")
            if contract.is_ownable:
                defenses.append("Ownable Access Control")
            if contract.has_initializer_lock:
                defenses.append("Initializer Lock")
            if defenses:
                prompt_parts.append(f"  * Active Defenses Detected: {', '.join(defenses)}")

        if context.slither_findings:
            prompt_parts.append(f"\n### Static Analysis (Slither) Preliminary Findings: {len(context.slither_findings)} alerts detected.")

        prompt_parts.append("\n### Complete Source Code:")
        prompt_parts.append("```solidity")
        prompt_parts.append(context.full_source)
        prompt_parts.append("```")
        prompt_parts.append("\nGenerate adversarial hypotheses as specified in the schema.")

        return "\n".join(prompt_parts)

    def _build_refinement_prompt(
        self,
        context: ContractContext,
        hypotheses: List[RedTeamHypothesis],
        critiques: List[BlueTeamCritique]
    ) -> str:
        prompt_parts = [
            f"### Adversarial Debate Round 2 — Target Contract: {context.file_path}",
            "Review the Blue Team's defensive critiques and refine or defend your exploit hypotheses.\n"
        ]

        critique_map = {c.hypothesis_id: c for c in critiques}
        for hyp in hypotheses:
            c = critique_map.get(hyp.id)
            c_args = "; ".join(c.counter_arguments) if c and c.counter_arguments else "None"
            prompt_parts.append(
                f"- **Hypothesis {hyp.id} ({hyp.title})** [Severity: {hyp.severity.value}]\n"
                f"  * Blue Team Status: {c.status.value if c else 'Challenged'}\n"
                f"  * Blue Team Counters: {c_args}\n"
            )

        prompt_parts.append("Provide refined attack transaction steps, address defender counter-arguments, and update confidence.")
        return "\n".join(prompt_parts)

    def _parse_response(self, raw_response: str, context: Optional[ContractContext] = None) -> List[RedTeamHypothesis]:
        import re
        if not raw_response or not raw_response.strip():
            if context:
                from .base import MockLLMBackend
                raw_response = MockLLMBackend().generate("RED TEAM ADVERSARIAL", self._build_analysis_prompt(context))
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
                if isinstance(data, dict) and "hypotheses" in data:
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
        if not data and context:
            try:
                from .base import MockLLMBackend
                mock_out = MockLLMBackend().generate("RED TEAM ADVERSARIAL", self._build_analysis_prompt(context))
                data = json.loads(mock_out)
            except Exception:
                pass

        if not data or not isinstance(data, dict):
            logger.warning(f"Failed to parse Red Team JSON (falling back to empty/mock). Preview: {raw_response[:200]}")
            return []

        hypotheses_raw = data.get("hypotheses", [])
        results = []

        for item in hypotheses_raw:
            sev_str = str(item.get("severity", "Medium")).capitalize()
            try:
                severity = Severity(sev_str)
            except ValueError:
                severity = Severity.MEDIUM

            results.append(
                RedTeamHypothesis(
                    id=item.get("id", f"RED-{len(results)+1:03d}"),
                    title=item.get("title", "Untitled Vulnerability"),
                    target_contract=item.get("target_contract", "Unknown"),
                    target_function=item.get("target_function"),
                    severity=severity,
                    threat_vector=item.get("threat_vector", "Smart Contract Logic"),
                    swc_id=item.get("swc_id"),
                    description=item.get("description", ""),
                    attack_preconditions=item.get("attack_preconditions", []),
                    theoretical_attack_steps=item.get("theoretical_attack_steps", []),
                    impact=item.get("impact", ""),
                    confidence=int(item.get("confidence", 7)),
                )
            )
        return results

