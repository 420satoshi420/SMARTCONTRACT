#!/bin/bash
# ==============================================================================
# Eth-Hunter 100% Autonomous Security & Bug Bounty Pipeline Launcher
# Keeps macOS active (caffeinate), runs the Web Dashboard & background scheduler,
# executes Slither & Foundry test suites, and automates submission packaging.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🛡️  ========================================================"
echo "🛡️  ETH-HUNTER: 100% Autonomous Security & Bug Bounty Engine"
echo "🛡️  ========================================================"
echo "📁 Project Root: $PROJECT_ROOT"

cd "$PROJECT_ROOT"
mkdir -p logs cache results/reports results/submissions/batch results/submissions/archive results/all_findings

# Activate Python Virtual Environment
if [ -d "backend/venv" ]; then
    echo "📦 Activating virtual environment (backend/venv)..."
    source backend/venv/bin/activate
elif [ -d "venv" ]; then
    echo "📦 Activating virtual environment (venv)..."
    source venv/bin/activate
fi

# Ensure solc binaries in PATH
export PATH="$PROJECT_ROOT/backend/venv/bin:$HOME/.svm/0.8.24:$HOME/.svm/0.8.20:$HOME/.local/bin:$PATH"

# Prevent macOS sleep during analysis
if command -v caffeinate &> /dev/null; then
    echo "☕ Enabling caffeinate daemon to prevent system sleep..."
    caffeinate -i -s &
    CAFFEINATE_PID=$!
    echo "☕ Caffeinate PID: $CAFFEINATE_PID"
fi

PORT="${PORT:-8001}"

# Clear stale process on port
if lsof -Pi :"$PORT" -sTCP:LISTEN -t >/dev/null 2>&1; then
    EXISTING_PID=$(lsof -Pi :"$PORT" -sTCP:LISTEN -t | head -n 1)
    echo "⚠️  Port $PORT held by PID $EXISTING_PID. Refreshing..."
    kill -9 "$EXISTING_PID" 2>/dev/null || true
    sleep 1
fi

# Start Background Scheduler
echo "⏰ Starting Autonomous Background Scheduler (interval: 120s)..."
pkill -f "python.*scheduler.py" || true
nohup python3 scripts/scheduler.py --interval 120 --daemon > logs/scheduler.log 2>&1 &
SCHEDULER_PID=$!
echo "🤖 Scheduler PID: $SCHEDULER_PID"

# Run initial full suite pass
echo "🚀 Running initial full audit & packaging sweep..."
python3 scripts/run_full_suite.py || true
python3 scripts/package_archive.py || true

# Start Dashboard Server
echo ""
echo "🌐 Starting Eth-Hunter Web Dashboard on http://localhost:$PORT..."
echo "📊 Real-time Log Stream, Invariant PoC Engine & Master DB Active."
echo ""

cd "$PROJECT_ROOT/backend"
PORT=$PORT python3 server.py
