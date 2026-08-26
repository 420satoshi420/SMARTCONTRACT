# Reentrancy Knowledge Deep Dive

### Mechanics
Reentrancy occurs when an external contract call hands over control flow to an untrusted recipient before the caller has synchronized internal accounting state.

### High-Value Bounty Patterns
- Stargate / LayerZero cross-chain payload receipt fallback
- Curve pool read-only reentrancy during `remove_liquidity`
- Uniswap V4 `afterSwap` or `beforeSwap` custom hook recursion
