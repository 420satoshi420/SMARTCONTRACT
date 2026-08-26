# 📐 Formal Invariants & Solvency Rules

1. **Solvency Invariant:** `address(this).balance >= sum(userBalances)`
2. **Total Supply Invariant:** `vault.totalSupply() * vault.sharePrice() == vault.totalAssets()`
3. **Monotonic Non-Decreasing Asset Rate:** Vault `convertToAssets(1 ether)` must never decrease across state transitions.
4. **Debt Conservation Invariant:** `totalBorrowed + totalReserves == totalSupplied` in lending protocols.
5. **Fee Invariant:** `feeAmount <= grossAmount * maxFeeBps / 10000`
