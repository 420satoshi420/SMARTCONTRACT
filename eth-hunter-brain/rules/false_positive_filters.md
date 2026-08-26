# 🛡️ False Positive Elimination Rules

1. **Guardrails & Modifiers:** If `nonReentrant` modifier from OpenZeppelin exists, drop reentrancy findings unless reentrancy is cross-contract on unshared lock.
2. **Strict CEI:** If balance is updated BEFORE external call (`balances[msg.sender] = 0; msg.sender.call(...)`), it is NOT vulnerable.
3. **Multi-Sig & Timelock:** If privileged function is behind a 48h Timelock + 3/5 Multi-Sig, mark administrative risk as Low/Informational, not High.
4. **Liquidity / TVL Filter:** If target pool has TVL < $1,000 USD, economic incentive is non-viable. Drop finding.
5. **Economic ROI Rule:** Net profit must exceed $1,000 USD and ROI > 2.0x after subtracting Ethereum mainnet gas (0.05-0.2 ETH) and flashloan fees (0.05%).
6. **MEV Frontrunning Defense:** Vulnerability must be packageable in atomic transaction or flashbots bundle to avoid frontrun theft.
