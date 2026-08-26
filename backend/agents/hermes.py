"""
Hermes Agent: Deep Reasoning Adversarial Web3 & Invariant Synthesis Agent.
Powered by NVIDIA NIM Nemotron / Hermes Reasoning API with high reasoning token budget.
"""

import json
import logging
from typing import Any, Dict, List, Optional
try:
    from ..core.context import (
        ContractContext,
        RedTeamHypothesis,
        BlueTeamCritique,
        Severity,
        FindingStatus,
    )
except (ImportError, ValueError):
    from core.context import (
        ContractContext,
        RedTeamHypothesis,
        BlueTeamCritique,
        Severity,
        FindingStatus,
    )
from .base import BaseLLMClient, NvidiaNimBackend


logger = logging.getLogger(__name__)

HERMES_SYSTEM_PROMPT = """You are HERMES — an elite, deep-reasoning Web3 Security Specialist and Foundry Invariant Synthesizer.
Your objective is to systematically analyze smart contract code for critical attack vectors and generate concrete, compilable Foundry invariant assertions.

Focus areas:
1. Economic Exploits: Flash loan leverage, AMM spot price manipulation vs TWAP/Chainlink feeds.
2. Protocol Logic: ERC-4626 first depositor inflation, rounding truncation, slippage bypasses.
3. Advanced EVM: Transient storage (EIP-1153 TSTORE/TLOAD) state pollution, cross-function reentrancy, hook callbacks.
4. Access Controls: Uninitialized proxies, faulty initializer modifiers, arbitrary delegatecalls.

Return output strictly in valid JSON format:
{
  "hypotheses": [
    {
      "id": "HERMES-001",
      "title": "Title of vulnerability",
      "target_contract": "ContractName",
      "target_function": "functionName",
      "severity": "Critical|High|Medium|Low",
      "threat_vector": "Threat Category",
      "swc_id": "SWC-107",
      "description": "Detailed explanation of the attack mechanism",
      "attack_preconditions": ["Condition 1", "Condition 2"],
      "theoretical_attack_steps": ["Step 1", "Step 2", "Step 3"],
      "foundry_invariant_spec": "function invariant_X() public view { ... }",
      "impact": "Concrete financial or protocol impact",
      "confidence": 10
    }
  ]
}
"""


class HermesAgent:
    """
    Hermes Agent utilizes high-budget reasoning models to analyze smart contracts,
    uncover subtle adversarial paths, and synthesize formal Foundry invariant test cases.
    """

    def __init__(self, llm_client: Optional[BaseLLMClient] = None):
        self.llm = llm_client or NvidiaNimBackend(
            model="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
            reasoning_budget=16384,
        )

    def deep_audit(self, context: ContractContext) -> List[RedTeamHypothesis]:
        """Runs high-budget cognitive analysis on the contract context."""
        user_prompt = self._build_deep_audit_prompt(context)
        raw_response = self.llm.generate(
            system_prompt=HERMES_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.4,
        )
        return self._parse_hypotheses(raw_response)

    def synthesize_invariants(
        self,
        context: ContractContext,
        hypotheses: List[RedTeamHypothesis]
    ) -> Dict[str, str]:
        """Synthesizes formal Foundry invariant test cases for confirmed hypotheses."""
        prompt = (
            f"Generate compilable Foundry invariant test contract assertions for the following findings "
            f"in `{context.file_path}`:\n"
            f"{json.dumps([h.__dict__ for h in hypotheses if hasattr(h, '__dict__')], indent=2)}"
        )
        raw = self.llm.generate(
            system_prompt="You are a Foundry invariant test generator. Output valid Solidity invariant tests.",
            user_prompt=prompt,
            temperature=0.2,
        )
        return {"solidity_invariants": raw}

    def _build_deep_audit_prompt(self, context: ContractContext) -> str:
        parts = [
            f"### Target File: {context.file_path}",
            f"### Compiler: {context.pragma_version}",
            f"### Source Code:\n```solidity\n{context.raw_source}\n```",
        ]
        return "\n\n".join(parts)

    def _parse_hypotheses(self, raw_json: str) -> List[RedTeamHypothesis]:
        clean = raw_json.strip()
        if "```json" in clean:
            clean = clean.split("```json")[1].split("```")[0].strip()
        elif "```" in clean:
            clean = clean.split("```")[1].split("```")[0].strip()

        try:
            data = json.loads(clean)
            items = data.get("hypotheses", [])
            results = []
            for item in items:
                try:
                    sev = Severity(item.get("severity", "Medium"))
                except Exception:
                    sev = Severity.MEDIUM

                results.append(
                    RedTeamHypothesis(
                        id=item.get("id", "HERMES-001"),
                        title=item.get("title", "Hermes Finding"),
                        target_contract=item.get("target_contract", "Target"),
                        target_function=item.get("target_function", "all"),
                        severity=sev,
                        threat_vector=item.get("threat_vector", "DeFi Exploit"),
                        swc_id=item.get("swc_id", "SWC-101"),
                        description=item.get("description", ""),
                        attack_preconditions=item.get("attack_preconditions", []),
                        theoretical_attack_steps=item.get("theoretical_attack_steps", []),
                        impact=item.get("impact", ""),
                        confidence=int(item.get("confidence", 9)),
                    )
                )
            return results
        except Exception as e:
            logger.error(f"Hermes response JSON parsing failed: {e}")
            return []
