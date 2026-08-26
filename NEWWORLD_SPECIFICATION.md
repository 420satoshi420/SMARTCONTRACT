# 🌐 NewWorld Protocol Technical Specification & Whitepaper

**Version:** 1.0.0  
**EVM Target:** Ethereum Mainnet / Arbitrum / Base / Local EVM (Cancun)  
**Compiler:** Solidity `^0.8.20`  

---

## 1. Executive Summary

**NewWorld Protocol** is a decentralized liquidity AMM and staking yield ecosystem designed for fair liquidity provisioning, decentralized trading, and automated yield rewards.

```mermaid
graph TD
    User["👤 User / Liquidity Provider"]
    Deployer["🔑 Admin / Deployer"]
    
    subgraph NewWorld_Protocol ["NewWorld Protocol Ecosystem"]
        Token["🪙 NewWorldToken (NEWWORLD)\nERC-20 + EIP-2612 Permit"]
        Pool["🏊 NewWorldPool\nAMM (x * y = k) + Staking Vault"]
    end
    
    Deployer -->|Mint / Burn / Pause| Token
    User -->|Swap ETH ↔ NEWWORLD| Pool
    User -->|Deposit ETH + NEW| Pool
    User -->|Harvest Yield| Pool
    Pool -->|Distribute Rewards| User
```

---

## 2. Core Architecture

### A. NewWorldToken (`NEWWORLD`)
* **Standard:** ERC-20 with EIP-2612 gasless permits and EIP-712 typed structured data hashing.
* **Decimals:** `18`
* **Total Supply:** `1,000,000 NEW`
* **Security Defenses:**
  * 2-Step Ownership Transfer (`transferOwnership` + `acceptOwnership`) preventing accidental ownership loss.
  * Pausable emergency circuit breaker.
  * Overflow/Underflow safe unchecked operations.

### B. NewWorldPool (AMM & Staking Resource)
* **Standard:** Automated Market Maker with Constant Product Formula:
  $$(x + \Delta x \cdot 0.997) \cdot (y - \Delta y) \ge k$$
* **Fee Structure:** $0.30\%$ ($30\text{ bps}$) retained in liquidity reserves.
* **Yield Engine:** Accumulative reward per share index:
  $$\text{accRewardPerShare}_{t} = \text{accRewardPerShare}_{t_0} + \frac{(t - t_0) \cdot \text{RewardRate} \cdot 10^{12}}{\text{TotalLiquidity}}$$

---

## 3. On-Chain Deployment Registry

| Parameter | Value |
| :--- | :--- |
| **Network** | Anvil / Local EVM (Chain ID: `31337`) |
| **RPC URL** | `http://127.0.0.1:8545` |
| **NewWorldToken Address** | `0x5FbDB2315678afecb367f032d93F642f64180aa3` |
| **NewWorldPool Address** | `0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512` |
| **Initial Pool Reserves** | $1.0\text{ ETH} + 10,000.0\text{ NEW}$ |
| **Staking Reward Reserves** | $50,000.0\text{ NEW}$ |

---

## 4. Verification & Testing Matrix

Foundry test suite in [`contracts/test/NewWorld.t.sol`](file:///Users/wakeup/Desktop/eth-hunter/contracts/test/NewWorld.t.sol) passed 100% of test cases:

```
[PASS] test_InitialState() (gas: 25980)
[PASS] test_AddLiquidity() (gas: 146826)
[PASS] test_SwapEthForToken() (gas: 165408)
[PASS] test_SwapTokenForEth() (gas: 173145)
[PASS] test_StakingRewardsAccrual() (gas: 206221)
[PASS] test_RemoveLiquidity() (gas: 148011)
Suite result: ok. 6 passed; 0 failed; 0 skipped
```

---

## 5. Tooling & Interaction

* **Python CLI Toolkit:** [`scripts/newworld_client.py`](file:///Users/wakeup/Desktop/eth-hunter/scripts/newworld_client.py)
* **DApp Dashboard:** [`frontend/newworld_dapp.html`](file:///Users/wakeup/Desktop/eth-hunter/frontend/newworld_dapp.html)
* **ABI Exports:**
  * [`contracts/abis/NewWorldToken.json`](file:///Users/wakeup/Desktop/eth-hunter/contracts/abis/NewWorldToken.json)
  * [`contracts/abis/NewWorldPool.json`](file:///Users/wakeup/Desktop/eth-hunter/contracts/abis/NewWorldPool.json)
