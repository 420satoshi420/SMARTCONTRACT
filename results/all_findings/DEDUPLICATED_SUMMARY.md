# 🛡️ ETH-Hunter: Deduplicated Vulnerability Intelligence Portfolio
**Date:** `2026-08-18 04:05:16 UTC`  
**Total Raw Scans Ingested:** `1151` | **Unique Vulnerability Archetypes:** `25`  
**Unique Bounty Portfolio Valuation:** `$431,500.00 USD` (Cumulative: `$17,817,000.00 USD`)

---

## 1. Vulnerability Severity Breakdown

| Severity Level | Unique Archetypes | Total Detected Instances | Representative Bounty Tier |
| :--- | :---: | :---: | :--- |
| 🚨 **Critical** | `15` | `534` | $25,000 - $50,000 USD |
| 🔴 **High** | `7` | `438` | $10,000 USD |
| 🟡 **Medium** | `3` | `179` | $3,000 USD |
| 🔵 **Low / Info** | `0` | `0` | Optimization / Quality |

---

## 2. Unique Vulnerability Master Index

| ID | Severity | Target Protocol / Contract | Threat Class & Title | Occurrences | Base Bounty ($) | Sample Report |
| :--- | :---: | :--- | :--- | :---: | :---: | :--- |
| **`VULN-001`** | 🚨 Critical | `sample_vulnerable_vault.sol` | **Cross-Function / State Reentrancy on Withdrawal**<br><small>State & Cross-Function Reentrancy (SWC-107)</small> | `175x` | $25,000 | [Preview](markdown/ETH-001_sample_vulnerable_vault.sol.md) |
| **`VULN-002`** | 🚨 Critical | `historical_defi_playground.sol` | **Cross-Function / State Reentrancy on Withdrawal**<br><small>State & Cross-Function Reentrancy (SWC-107)</small> | `87x` | $25,000 | [Preview](markdown/ETH-043_historical_defi_playground.sol.md) |
| **`VULN-003`** | 🚨 Critical | `sample_v4_hook_and_erc4626.sol` | **Uniswap V4 Hook Unauthorized Callback & Transient State Reentrancy**<br><small>State & Cross-Function Reentrancy (SWC-107)</small> | `87x` | $25,000 | [Preview](markdown/ETH-046_sample_v4_hook_and_erc4626.sol.md) |
| **`VULN-004`** | 🚨 Critical | `TestRepo` | **Reentrancy Exploit**<br><small>State & Cross-Function Reentrancy (SWC-107)</small> | `52x` | $25,000 | [Preview](markdown/ETH-051_TestRepo.md) |
| **`VULN-005`** | 🚨 Critical | `VulnerableVaultRepo` | **Unprotected Proxy Initializer**<br><small>Smart Contract Invariant & Logic Verification</small> | `50x` | $25,000 | [Preview](markdown/ETH-054_VulnerableVaultRepo.md) |
| **`VULN-006`** | 🚨 Critical | `InitializableVault` | **Unprotected Proxy Initializer**<br><small>Smart Contract Invariant & Logic Verification</small> | `50x` | $25,000 | [Preview](markdown/ETH-055_InitializableVault.md) |
| **`VULN-007`** | 🚨 Critical | `Target_0x68b346` | **Cross-Function / State Reentrancy on Withdrawal**<br><small>State & Cross-Function Reentrancy (SWC-107)</small> | `2x` | $25,000 | [Preview](markdown/ETH-1128_Target_0x68b346.md) |
| **`VULN-008`** | 🚨 Critical | `Target_0x794a61` | **Cross-Function / State Reentrancy on Withdrawal**<br><small>State & Cross-Function Reentrancy (SWC-107)</small> | `2x` | $25,000 | [Preview](markdown/ETH-1129_Target_0x794a61.md) |
| **`VULN-009`** | 🚨 Critical | `Target_0x420000` | **Cross-Function / State Reentrancy on Withdrawal**<br><small>State & Cross-Function Reentrancy (SWC-107)</small> | `2x` | $25,000 | [Preview](markdown/ETH-1130_Target_0x420000.md) |
| **`VULN-010`** | 🚨 Critical | `Target_0x490480` | **Cross-Function / State Reentrancy on Withdrawal**<br><small>State & Cross-Function Reentrancy (SWC-107)</small> | `2x` | $25,000 | [Preview](markdown/ETH-1131_Target_0x490480.md) |
| **`VULN-011`** | 🚨 Critical | `SampleVulnerableVault` | **General Vulnerability**<br><small>Smart Contract Invariant & Logic Verification</small> | `2x` | $25,000 | [Preview](markdown/ETH-1150_SampleVulnerableVault.md) |
| **`VULN-012`** | 🚨 Critical | `examples` | **Uniswap V4 Hook Unauthorized Callback & Transient State Reentrancy**<br><small>State & Cross-Function Reentrancy (SWC-107)</small> | `1x` | $25,000 | [Preview](markdown/ETH-662_examples.md) |
| **`VULN-013`** | 🚨 Critical | `examples` | **Cross-Function / State Reentrancy on Withdrawal**<br><small>State & Cross-Function Reentrancy (SWC-107)</small> | `1x` | $25,000 | [Preview](markdown/ETH-664_examples.md) |
| **`VULN-014`** | 🚨 Critical | `Contract_0x794a61.sol` | **Cross-Function / State Reentrancy on Withdrawal**<br><small>State & Cross-Function Reentrancy (SWC-107)</small> | `1x` | $25,000 | [Preview](markdown/ETH-1092_Contract_0x794a61.sol.md) |
| **`VULN-015`** | 🚨 Critical | `TestVault.sol` | **Reentrancy In Vault**<br><small>State & Cross-Function Reentrancy (SWC-107)</small> | `20x` | $2,500 | [Preview](markdown/ETH-265_TestVault.sol.md) |
| **`VULN-016`** | 🔴 High | `sample_vulnerable_vault.sol` | **Spot Price / Reserve Manipulation via Flash Loan**<br><small>Spot Reserve & Oracle Manipulation (SWC-120)</small> | `175x` | $10,000 | [Preview](markdown/ETH-002_sample_vulnerable_vault.sol.md) |
| **`VULN-017`** | 🔴 High | `historical_defi_playground.sol` | **Spot Price / Reserve Manipulation via Flash Loan**<br><small>Spot Reserve & Oracle Manipulation (SWC-120)</small> | `87x` | $10,000 | [Preview](markdown/ETH-044_historical_defi_playground.sol.md) |
| **`VULN-018`** | 🔴 High | `sample_v4_hook_and_erc4626.sol` | **ERC-4626 First Depositor Vault Share Inflation via Direct Donation**<br><small>ERC-4626 Share Inflation / Donation Attack</small> | `87x` | $10,000 | [Preview](markdown/ETH-045_sample_v4_hook_and_erc4626.sol.md) |
| **`VULN-019`** | 🔴 High | `sample_v4_hook_and_erc4626.sol` | **Signature Replay & Missing Zero-Address ecrecover Validation**<br><small>Smart Contract Invariant & Logic Verification</small> | `86x` | $10,000 | [Preview](markdown/ETH-047_sample_v4_hook_and_erc4626.sol.md) |
| **`VULN-020`** | 🔴 High | `examples` | **ERC-4626 First Depositor Vault Share Inflation via Direct Donation**<br><small>ERC-4626 Share Inflation / Donation Attack</small> | `1x` | $10,000 | [Preview](markdown/ETH-661_examples.md) |
| **`VULN-021`** | 🔴 High | `examples` | **Signature Replay & Missing Zero-Address ecrecover Validation**<br><small>Smart Contract Invariant & Logic Verification</small> | `1x` | $10,000 | [Preview](markdown/ETH-663_examples.md) |
| **`VULN-022`** | 🔴 High | `examples` | **Spot Price / Reserve Manipulation via Flash Loan**<br><small>Spot Reserve & Oracle Manipulation (SWC-120)</small> | `1x` | $10,000 | [Preview](markdown/ETH-665_examples.md) |
| **`VULN-023`** | 🟡 Medium | `sample_vulnerable_vault.sol` | **Unsafe ERC20 Transfer Missing Return Value Check**<br><small>Unsafe ERC20 Return Value Check (SWC-104)</small> | `175x` | $3,000 | [Preview](markdown/ETH-003_sample_vulnerable_vault.sol.md) |
| **`VULN-024`** | 🟡 Medium | `0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45.sol` | **General Smart Contract Logic & Invariant Audit**<br><small>Smart Contract Invariant & Logic Verification</small> | `3x` | $3,000 | [Preview](markdown/ETH-037_0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45.sol.md) |
| **`VULN-025`** | 🟡 Medium | `examples` | **Unsafe ERC20 Transfer Missing Return Value Check**<br><small>Unsafe ERC20 Return Value Check (SWC-104)</small> | `1x` | $3,000 | [Preview](markdown/ETH-666_examples.md) |

---
*Report compiled by Eth-Hunter Vulnerability Intelligence Suite.*