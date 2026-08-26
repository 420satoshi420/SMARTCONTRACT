# MacDowell 504 - ETH Hunter Automation
## Explaining and Prompting Guide
### Anti-Gravity + New Meta AI - Full Automation to $2088

---

## 1. Overview - What This Is

**Project:** Autonomous ETH Smart Contract Bounty Hunter for MacBook Pro 2018
**Goal:** $2088 (1.09 ETH) via Immunefi/Cantina bounties
**Stack:** Anti-Gravity (code gen) + New Meta AI (critical reasoning) + Full Automation

**MacDowell 504 Format:** This document explains the system and provides copy-paste prompts for each layer.

---

## 2. Architecture - 4 Layers + Automation

```
[Smart Contract Input]
        ↓
Layer 1 - Perception: Slither + Filter (false positive <30% dropped)
        ↓
Layer 2 - Adversarial Reasoning (Anti-Gravity + Meta AI New):
  - Attacker Agent: How to exploit? Flashloan? Profit?
  - Defender Agent: Why NOT exploitable? Guard exists?
  - Economist Agent: ROI? TVL? MEV front-run?
  -> Debate Loop 2-3 rounds
        ↓
Layer 3 - Formal Reasoning:
  - Invariants: totalSupply == sum(balances)?
  - Assumptions: owner trusted? oracle is Chainlink?
  - Edge Cases: amount=0, max uint, reentrant same tx
  - Economic: gas vs profit
        ↓
Layer 4 - Meta AI Synthesis (New Models):
  - Synthesizes all layers
  - Confidence 0-100%
  - Bounty estimate
  - Would you bet $2088?
        ↓
Automation:
  - Anti-Gravity: Auto-generates Foundry PoC
  - Auto-generates Immunefi draft
  - Telegram/Discord alert if Score>=5000 or Conf>=85%
  - Leaderboard tracks $/2088
  - Scheduler: Daily 2AM + Every 6h
```

---

## 3. Anti-Gravity Prompts (Your Subscription)

### 3.1 Anti-Gravity Config
File: `.antigravity/config.json`
```json
{
  "subscription": "anti-gravity-pro",
  "auto_mode": true,
  "agents": {
    "code_generator": {"enabled": true, "model": "antigravity-code-v2"},
    "security_auditor": {"enabled": true, "uses_meta_ai": true},
    "poc_builder": {"enabled": true, "auto_generate_exploit": true}
  }
}
```

### 3.2 Prompt - Auto PoC Generation
**Use in:** `automation/antigravity_agent.py` -> `generate_poc_with_antigravity()`

```
You are Anti-Gravity code generator with Pro subscription.

Task: Generate Foundry PoC for smart contract vulnerability.

Input:
- Repo: {repo_name}
- Finding: {finding_check} - {finding_details}
- Slither output: {slither_json_short}

Requirements:
1. Generate Solidity Foundry test (forge test)
2. Use vm.startPrank(attacker), vm.deal, etc.
3. Steps:
   - Deploy attacker contract if needed
   - For reentrancy: deposit then reenter via fallback
   - For access control: prank as attacker
   - Assert profit > 0 or state change
4. Include comments for each step
5. Return ONLY Solidity code, no explanation
6. Use 0.8.20 syntax

Example output:
```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "forge-std/Test.sol";
contract ExploitTest is Test {
    function testExploit() public {
        // 1. Setup
        vm.startPrank(attacker);
        // 2. Exploit
        vulnerable.withdraw();
        // 3. Assert
        assertGt(attacker.balance, 0);
    }
}
```

Return code only.
```

### 3.3 Prompt - Auto Fix Suggestion
```
You are Anti-Gravity security fix generator.

Finding: {finding}
Repo: {repo_name}

Generate fixed version:

Before (vulnerable):
{original_code}

After (fixed):
- Add nonReentrant if reentrancy
- Add checks-effects-interactions
- Add access control if needed
- Use OpenZeppelin

Return diff only.
```

---

## 4. New Meta AI Prompts (Your New Implementation)

### 4.1 Model Priority (New -> Old)
```python
models_to_try = [
    "llama-4-maverick",  # New - try first
    "llama-4-scout",     # New - second
    "llama-3-70b",       # Fallback
    "llama-3-8b"         # Cheap for debate
]
```

### 4.2 Prompt - Attacker Agent (Critical Thinking)
**File:** `layers/layer2_attacker.py`

```
You are BLACK HAT smart contract attacker with 10 years DeFi exploit experience.

Finding: {finding_json}
Repo: {repo_name} | Bounty Max: ${bounty_max}

Critical thinking - answer step-by-step:

1. Flashloan: Can I use flashloan (Aave, Balancer) to get capital? Cost? 0.05% fee?
2. Cross-function: Is there cross-function reentrancy? (deposit() calls withdraw() in fallback?)
3. Front-run: Can I front-run initialize()? Is owner changeable?
4. Profit: Pool TVL? If TVL $2M and I can drain 100%, profit $2M. Gas cost 0.01-0.5 ETH.
5. ROI: (profit - gas - flashloan_fee) / (gas + fee). If ROI <2x, not worth.

Write exploit path:
- Step 1: ...
- Step 2: ...
- Profit: X ETH, Gas: Y ETH, ROI: Z

Return JSON ONLY:
{"exploitable": bool, "attack_path": "step1...", "profit_eth": float, "gas_cost_eth": float, "needs_flashloan": bool, "roi": float}
```

### 4.3 Prompt - Defender Agent
```
You are BLUE TEAM auditor - try to prove Attacker WRONG.

Attacker claims: {attacker_output}
Finding: {finding_json}

Counter-argue critically:

1. Guard: Is there nonReentrant? Check modifier exists?
2. CEI: Is checks-effects-interactions actually done? (balance set to 0 BEFORE call?)
3. Trust: Is owner trusted multisig? Can owner mitigate?
4. Liquidity: Is pool empty? TVL < $1000 = not worth?
5. MEV: Will MEV bot front-run and take profit?

If you can defend, mark as false positive.

Return JSON:
{"defensible": bool, "counter_reason": "...", "mitigation_exists": bool, "is_false_positive": bool}
```

### 4.4 Prompt - Economist Agent
```
You are DeFi economist.

Finding: {finding}
Attacker: {attacker_out}
Defender: {defender_out}
Repo TVL: {tvl_estimate}

Calculate:
- Profit USD: If pool $2.3M, profit $2.3M
- Gas: 0.01-0.5 ETH ($20-$1000)
- Flashloan fee: 0.05% of profit
- Net profit: profit - gas - fee
- ROI: net / (gas+fee)
- MEV risk: High if profit > $10k (bots will front-run)

If ROI <2.0 or net profit < $1000, mark not worth it (false positive filter).

Return JSON:
{"roi": float, "profit_usd": float, "gas_usd": float, "worth_it": bool, "tvl": float, "mev_risk": "high|low"}
```

### 4.5 Prompt - Final Synthesis (New Meta AI - Llama 4)
**File:** `layers/layer4_synthesis.py` - This is the brain

```
You are final auditor synthesizing 3 adversarial agents + formal checks. You have Anti-Gravity PoC.

Attacker Agent: {attacker}
Defender Agent: {defender}
Economist Agent: {economist}
Formal Checks: {formal} - Invariants, Assumptions, Edge Cases
Anti-Gravity PoC: {poc_code}
Original Finding: {finding}
Repo: {repo_name} | Max Bounty: ${bounty_max}

Socratic critical thinking - ask yourself:

1. What assumption might be false? (Is owner really trusted? Is oracle manipulable?)
2. What did attacker miss that defender caught?
3. What did defender miss that attacker found?
4. Would you bet $2088 of your OWN money this is real and exploitable and will be paid by Immunefi?
5. Confidence 0-100% - how sure are you?
6. If confidence <70%, it's likely false positive - mark is_real false

Return JSON ONLY, no extra text:
{
  "is_real": bool,
  "severity": "Critical|High|Medium|Low",
  "bounty_estimate": "$25000",
  "confidence": 94,
  "reasoning": "Cross-function reentrancy via deposit() fallback, no guard, ROI 23000x...",
  "exploit_poc": "Solidity code...",
  "fix": "Add nonReentrant and CEI pattern...",
  "would_bet_2088": true,
  "model_used": "llama-4-maverick"
}

Rules:
- is_real true only if confidence >=70 and would_bet_2088 true
- bounty_estimate based on severity + TVL
- exploit_poc must be concrete, not "exists"
```

---

## 5. Automation Prompts

### 5.1 Scheduler Prompt (APScheduler)
File: `automation/scheduler.py`

```python
# Daily at 2AM Bangkok + Every 6h
scheduler.add_job(lambda: asyncio.run(automated_scan_job()), 'cron', hour=2, minute=0)
scheduler.add_job(lambda: asyncio.run(automated_scan_job()), 'cron', hour='*/6')

# Job does:
# 1. git pull top repos
# 2. fast_scan (Slither, cached)
# 3. Meta AI new critical reasoning
# 4. Anti-Gravity PoC generation
# 5. Immunefi draft auto-generation
# 6. Leaderboard update
# 7. Alert if high value
```

### 5.2 Mac Launchd Prompt
File: `com.ethhunter.automation.plist`

```xml
<!-- Runs daily at 2AM even after reboot -->
<key>StartCalendarInterval</key>
<dict>
  <key>Hour</key><integer>2</integer>
  <key>Minute</key><integer>0</integer>
</dict>
```

Enable:
```bash
cp com.ethhunter.automation.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.ethhunter.automation.plist
```

### 5.3 Notification Prompt
```
IF confidence >=85 OR score >=5000 OR would_bet_2088 == true:
  SEND Telegram:
    🚨 {repo} Score {score} Conf {confidence}% Est ${bounty_estimate}
    Draft: {draft_path}
    Goal $2088: {progress}%

  SEND Discord:
    Embed with fields: Bounty Max, Est, Confidence, Would bet?
```

---

## 6. How To Setup - From Zero to Automated

### 6.1 One-Command Bootstrap (New Laptop)
```bash
chmod +x bootstrap_from_zero_mac.sh
./bootstrap_from_zero_mac.sh
# Installs brew, python, node, git, rust, solc, project, asks for keys
```

### 6.2 Full Automation Setup (Anti-Gravity + New Meta AI)
```bash
chmod +x setup_automated_antigravity.sh
./setup_automated_antigravity.sh
# Asks:
# META_AI_API_KEY: [your new Meta AI key]
# META_AI_URL: [your new endpoint - Llama 4]
# ANTI_GRAVITY_KEY: [from anti-gravity dashboard]
# Telegram/Discord: optional

cd eth-hunter-automated/backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt && pip install slither-analyzer solc-select
solc-select install 0.8.20 && solc-select use 0.8.20

# Start full automation
cd ..
./start_automated.sh
# - caffeinate (prevents sleep)
# - tmux (keeps running)
# - scheduler (2AM + every 6h)
# - backend + frontend

# Open http://localhost:5173
# Click RUN AUTOMATED SCAN NOW to test
# Then close lid, go sleep - it runs itself
```

### 6.3 MacBook Pro 2018 Specific
```bash
chmod +x setup_mac_2018.sh
./setup_mac_2018.sh
# Optimized: only 3 repos, 1 finding each, cheap 8b model, no Aderyn
# Less RAM, no thermal throttle
```

---

## 7. Leaderboard - Tracking $2088

File: `results/leaderboard.json`

```json
{
  "goal_usd": 2088,
  "total_potential_usd": 32500,
  "total_potential_eth": 16.92,
  "goal_progress_percent": 100,
  "goal_hit": true,
  "goal_hit_date": "2026-05-13T03:42:11",
  "findings": [
    {
      "repo": "Stargate",
      "bounty_estimate": 25000,
      "confidence": 94,
      "score": 23500,
      "would_bet_2088": true,
      "model": "llama-4-maverick",
      "poc_source": "antigravity"
    }
  ]
}
```

Dashboard shows:
```
$32500 / $2088 (100%) 🎉 GOAL HIT! 16.92 ETH potential
```

---

## 8. Immunefi Auto-Draft Template

File: `results/immunefi_drafts/{repo}_{date}.md`

Auto-generated from Meta AI + Anti-Gravity PoC:

```markdown
# Immunefi Report - Stargate - Auto-Generated

Automation: Anti-Gravity + New Meta AI (llama-4-maverick) + PoC via antigravity
Confidence: 94% | Est: $25,000 | Score: 23500 | Bet $2088? ✅ YES

## Finding: reentrancy in withdraw()

## PoC (Auto-Generated):
```solidity
// Generated by Anti-Gravity
function testExploit() public { ... }
```

## Impact: $25,000 - Max $1,000,000
## Fix: Add nonReentrant

Submit: https://immunefi.com/explore
Goal $2088 = 1.087 ETH
```

Copy-paste to Immunefi -> Submit.

---

## 9. Troubleshooting - MacDowell 504 Checklist

- [ ] Xcode tools installed? `xcode-select -p`
- [ ] Homebrew installed? `brew --version`
- [ ] Python 3.11? `python3 --version`
- [ ] Node 18+? `node --version`
- [ ] Slither works? `slither --version`
- [ ] Solc 0.8.20? `solc-select use 0.8.20`
- [ ] .env has META_AI_API_KEY?
- [ ] Backend runs? `http://localhost:8000` -> {"status":"Ready"}
- [ ] Frontend runs? `http://localhost:5173`
- [ ] Test alert? `POST /api/test-alert` -> Telegram/Discord message?
- [ ] Batch works? `POST /api/batch` -> ranking?
- [ ] Automation? `tmux attach -t hunter` shows 3 windows?
- [ ] Launchd? `launchctl list | grep ethhunter`
- [ ] Caffeinate? `ps aux | grep caffeinate`

---

## 10. Final Command - Everything Automated

```bash
# From zero to autonomous hunter in 1 command:
./bootstrap_from_zero_mac.sh && cd ~/Desktop/eth-hunter && ./start_automated.sh

# Then:
# 1. Open http://localhost:5173
# 2. Click RUN AUTOMATED SCAN NOW
# 3. Close lid, sleep
# 4. Wake up to $/2088 goal hit + drafts + Telegram alert
# 5. Copy draft -> Immunefi -> Submit -> Earn

# Goal: $2088 = 1.09 ETH
# One high-confidence finding (94%) = $10k-$25k = 5x-12x goal
```

---

**MacDowell 504 - END**

*This document explains the system and provides all prompts for Anti-Gravity + New Meta AI full automation.*

*For MacBook Pro 2018, use setup_mac_2018.sh or bootstrap_from_zero_mac.sh*

*For full automation, use setup_automated_antigravity.sh*

*Goal: $2088 - One finding is enough.*
