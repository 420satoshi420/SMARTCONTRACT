# Flashloan Knowledge Deep Dive

### Exploitation Flows
1. Flashloan 50,000 ETH from Balancer or Aave
2. Swap 25,000 ETH into targeted low-liquidity AMM pair to skew spot price
3. Trigger target protocol liquidation or deposit pricing based on manipulated spot price
4. Swap back remainder and repay flashloan with 0.05% fee, retaining profit
