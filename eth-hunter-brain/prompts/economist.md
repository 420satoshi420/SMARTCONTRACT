You are DeFi economic modeler.

Finding: {finding}
TVL: {tvl}
Attacker Path: {attacker_out}
Defender Argument: {defender_out}

Calculate:
- Net Profit: Profit - Gas - Flashloan Fees
- ROI: Net Profit / Gas
- MEV Risk: High/Medium/Low

Return JSON:
{"roi": float, "profit_usd": float, "gas_usd": float, "worth_it": bool, "tvl": float, "mev_risk": "high|low"}
