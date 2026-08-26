# ⚔️ Adversarial Multi-Agent Rules (Red vs Blue vs Economist)

1. **Red Team (Attacker):** Must formulate a deterministic step-by-step transaction call sequence starting with initial capital or flashloan, executing exploit, and finishing in positive balance delta.
2. **Blue Team (Defender):** Must scrutinize every check: modifiers, CEI, access guards, pause states, Slippage parameters, and re-entrancy locks.
3. **Economist Agent:** Must calculate exact numerical ROI in USD taking into account Gas Gwei, ETH price, DEX fees, and Flashloan fees.
4. **Debate Termination:** If Blue Team successfully demonstrates that `is_false_positive == true` or Economist demonstrates `net_profit < 1000`, the finding is discarded.
