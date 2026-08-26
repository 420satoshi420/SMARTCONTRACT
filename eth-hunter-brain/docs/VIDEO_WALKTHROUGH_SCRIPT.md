# 🎥 Loom Video Walkthrough Script
# ETH Hunter - From Zero to $2088 with Brain + Anti-Gravity + New Meta AI
# Duration: ~12-15 min total (split into 3 Looms if needed)
# For: MacBook Pro 2018, new laptop, full automation

---

## Loom 1: From Zero to Running (5 min) - Bootstrap

**Title:** "ETH Hunter - Bootstrap from Zero on New MacBook Pro 2018"

**What to show:** Terminal, Desktop

**Script:**

[0:00 - 0:30] Intro
"Hey, this is ETH Hunter autonomous bounty hunter. Goal $2088 = 1.09 ETH. I have new MacBook Pro 2018 with nothing installed. I'll show bootstrap from zero, brain integration, MCP for Anti-Gravity, and full automation."

[0:30 - 1:30] Download bootstrap
"First, download setup_full_with_brain.sh - this is complete package: brew, python, node, brain repo, automation."

Show:
```bash
cd ~/Desktop
ls -la setup_full_with_brain.sh
chmod +x setup_full_with_brain.sh
```

[1:30 - 3:00] Run bootstrap
"Run it - it asks for keys"

Show:
```bash
./setup_full_with_brain.sh

# Type when prompted:
META_AI_API_KEY: [paste - blur in video]
META_AI_URL: [default Enter]
ANTI-GRAVITY_KEY: [paste or Enter]
Telegram: [Enter]
```

Explain while it installs:
"It installs Xcode tools, Homebrew, Git, Python 3.11, Node, Rust, Tmux, then creates two folders: eth-hunter-brain with 5 rules + knowledge base, and eth-hunter-automated with backend + frontend."

[3:00 - 4:00] Show result
"Done - 15 min. Show structure:"

```bash
ls ~/Desktop/eth-hunter/
# eth-hunter-brain/  eth-hunter-automated/

ls eth-hunter-brain/rules/
# vulnerability_patterns.md, false_positive_filters.md, etc

ls eth-hunter-brain/knowledge/
# reentrancy, access_control, flashloan

cat eth-hunter-brain/config/thresholds.json
# Shows goal $2088 thresholds
```

[4:00 - 5:00] Start
"Start full auto + brain:"

```bash
cd ~/Desktop/eth-hunter/eth-hunter-automated
./start_all.sh

# Shows:
# Brain: 5 rules loaded
# Tmux hunter: backend + frontend
# Dashboard: http://localhost:5173
```

"Open http://localhost:5173 - shows brain loaded, $0 / $2088"

End Loom 1.

---

## Loom 2: Brain + Anti-Gravity Integration (5 min) - How to Send to Anti-Gravity

**Title:** "How to Send Brain to Anti-Gravity - @ Reference vs MCP Server"

**What to show:** Anti-Gravity / Cursor IDE, brain files, chat

**Script:**

[0:00 - 0:30] Intro
"Now I have brain repo. How to send to Anti-Gravity? 3 ways - easiest @ reference, best MCP server."

[0:30 - 2:00] Method 1: @ Reference (Easy, 30 sec)

Show in Cursor/Anti-Gravity:

"Open Cursor, new chat. Type @ and select files:"

```
@eth-hunter-brain/rules/vulnerability_patterns.md
@eth-hunter-brain/knowledge/reentrancy/patterns.md
@eth-hunter-brain/prompts/synthesis.md

Analyze: Slither found reentrancy-eth in Stargate withdraw(), no nonReentrant, TVL $2.3M
Estimate bounty, confidence, would_bet_2088? Generate Foundry PoC for $2088 goal
```

"Hit Enter. Anti-Gravity reads 3 files as context, reasons with brain knowledge, not pattern match."

Show AI response:
- Confidence 94%
- Bounty $25k
- Score 23500
- would_bet_2088 true
- PoC generated

"This is 30 sec setup, works on 8GB Mac 2018, no MCP."

[2:00 - 4:30] Method 2: MCP Server (Best, 10 min)

"Now best way - MCP server. Lets AI call brain as tools automatically."

Show terminal:

```bash
cd ~/Desktop/eth-hunter
chmod +x setup_mcp_antigravity.sh
./setup_mcp_antigravity.sh

# Installs mcp, copies mcp_server.py to brain, creates ~/.cursor/mcp.json
```

Show config:

```bash
cat ~/.cursor/mcp.json
# {
#   "mcpServers": {
#     "eth-hunter-brain": {
#       "command": "python3",
#       "args": ["/.../mcp_server.py"]
#     }
#   }
# }
```

"Restart Cursor / Anti-Gravity IDE - Cmd+Q then open again"

"Now in chat, no @ needed:"

```
Use eth-hunter-brain tools to list brain files
```

Show AI calls list_brain_files tool, returns list.

```
Use eth-hunter-brain to analyze reentrancy in Stargate for $2088 goal
```

Show AI calls get_knowledge("reentrancy") automatically, then reasons.

"Now fully automated - AI knows when to load brain. No copy-paste."

[4:30 - 5:00] Comparison

"Summary:
- Copy-paste: 0 min, manual, not scalable
- @ reference: 30 sec, easy, good for 2018 8GB
- MCP server: 10 min, best, auto-loads brain, recommended for 16GB + automation"

End Loom 2.

---

## Loom 3: Full Automation to $2088 (5 min) - Overnight Hunter

**Title:** "Full Automation - Scans at 2AM, Auto Draft, Alerts, Leaderboard Hits $2088"

**What to show:** Dashboard, terminal, Telegram, Immunefi draft

**Script:**

[0:00 - 1:00] Start automation

"Now full automation - scans itself daily at 2AM + every 6h"

Show:

```bash
cd ~/Desktop/eth-hunter/eth-hunter-automated
./start_all.sh

# caffeinate prevents sleep
# tmux hunter session: backend, frontend

tmux attach -t hunter
# Show 2 windows: backend running, frontend running
# Ctrl+B then D to detach
```

"Open http://localhost:5173"

Show dashboard:
- Brain: ✅ 5 rules loaded
- $0 / $2088 (0%)
- Button: RUN WITH BRAIN

[1:00 - 2:30] Run batch

"Click RUN WITH BRAIN - simulates scan with brain"

Show:

```bash
# Or via API:
curl -X POST http://localhost:8000/api/batch
```

"Show ranking: Stargate Score 23500 Conf 94% Model llama-4-maverick PoC antigravity"

"Show leaderboard: $25000 / $2088 (100%) 🎉 GOAL HIT! 13 ETH"

"This is automation - Meta AI new (Llama 4) reasons, Anti-Gravity generates PoC, score = Conf x Bounty, ranks."

[2:30 - 3:30] Auto-draft + Brain API

"Show brain API: http://localhost:8000/api/brain/rules"

```bash
curl http://localhost:8000/api/brain/rules | head -n 20
# Returns vulnerability_patterns.md content
```

"Show drafts:"

```bash
ls ../results/immunefi_drafts/
# Stargate_20250513_0200.md

cat ../results/immunefi_drafts/Stargate*.md | head -n 30
# # Immunefi Report - Stargate - Auto-Generated
# Confidence 94% Est $25k Score 23500 Bet $2088? ✅ YES
# PoC auto-generated by antigravity...
```

"Draft ready to copy-paste to Immunefi: https://immunefi.com/explore -> Search Stargate -> Submit Report -> Paste"

[3:30 - 4:30] Alerts + Leaderboard

"Show leaderboard file:"

```bash
cat ../results/leaderboard.json
# {
#   "goal_usd": 2088,
#   "total_potential_usd": 25000,
#   "goal_progress_percent": 100,
#   "goal_hit": true,
#   "findings": [...]
# }
```

"Show Telegram alert (if configured):"

Show phone or Telegram Desktop:

```
🚨 FULL AUTO: Stargate Score 23500 Conf 94% Est $25,000 Model llama-4-maverick Goal $2088 🎉 HIT
Draft: .../Stargate_20250513_0200.md
```

"For overnight: close lid, Mac stays awake via caffeinate, scans at 2AM, phone buzzes at 3AM if high value."

[4:30 - 5:00] Summary + Goal

"Summary:

1. Bootstrap from zero: setup_full_with_brain.sh (15 min) -> brain + automation
2. Send to Anti-Gravity: @ reference (30 sec) or MCP server (10 min, best)
3. Full automation: ./start_all.sh -> scans 2AM daily + every 6h, brain reasoning, Anti-Gravity PoC, auto draft, alert, leaderboard
4. Goal: $2088 = 1.09 ETH, one 94% finding = $25k = 12x goal
5. Submit: Copy draft -> Immunefi -> Earn

All files in ~/Desktop/eth-hunter/

Links in description: brain zip, MacDowell 504 guide, bootstrap scripts"

End Loom 3.

---

## Loom Recording Checklist

- [ ] Blur API keys in video (META_AI_API_KEY, ANTI_GRAVITY_KEY, Telegram token)
- [ ] Show terminal with large font (Cmd + +)
- [ ] Show Desktop folder structure
- [ ] Show Cursor/Anti-Gravity chat with @ references
- [ ] Show dashboard http://localhost:5173
- [ ] Show brain API http://localhost:8000/api/brain/rules
- [ ] Show leaderboard $25000 / $2088 🎉
- [ ] Show draft file
- [ ] Show Telegram alert (if possible)
- [ ] Keep each Loom <6 min (attention span)
- [ ] Add captions: "Goal $2088", "Brain loaded", "MCP auto", "Full automation"

---

## Files to Include in Loom Description

```
🧠 Brain Repo: eth-hunter-brain.zip
📄 MacDowell 504 Guide: MacDowell_504_Explaining_and_Prompting.md
🚀 Bootstrap From Zero: bootstrap_from_zero_mac.sh
🍎 Mac 2018 Optimized: setup_mac_2018.sh
🤖 Full Automation: setup_automated_antigravity.sh
🧠🚀 FULL PACKAGE: setup_full_with_brain.sh (RECOMMENDED - from zero + brain)
🤖 MCP Server: mcp_server.py + mcp_config.json + setup_mcp_antigravity.sh
📄 How to Send to Anti-Gravity: HOW_TO_SEND_TO_ANTIGRAVITY.md

Goal: $2088 = 1.09 ETH
One high-confidence finding (94%) = $25k = 12x goal
```

---

## Quick Start for Viewer (Copy-paste in Loom description)

```bash
# For new MacBook with nothing:
cd ~/Desktop
chmod +x setup_full_with_brain.sh
./setup_full_with_brain.sh
# Paste keys when asked

cd eth-hunter/eth-hunter-automated
./start_all.sh
# Open http://localhost:5173
# Click RUN WITH BRAIN
# Goal: $2088 hit!

# For Anti-Gravity MCP:
chmod +x setup_mcp_antigravity.sh
./setup_mcp_antigravity.sh
# Restart Cursor / Anti-Gravity
# Chat: "Use eth-hunter-brain tools to analyze..."
```

---

## End of Loom Script
