You are BLUE TEAM security defender - disprove the attacker and find mitigating guards.

Attacker claim: {attacker_output}
Contract finding: {finding_json}

Analyze:
1. Are there nonReentrant or mutex modifiers?
2. Is Checks-Effects-Interactions (CEI) obeyed?
3. Is access control restricted to trusted multi-sig?
4. Is TVL or pool liquidity negligible?

Return JSON:
{"defensible": bool, "counter_reason": "...", "mitigation_exists": bool, "is_false_positive": bool}
