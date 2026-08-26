#!/bin/bash
# ==============================================================================
# Eth-Hunter Launcher: Starts Backend & Frontend, opens Browser
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "☕ Preventing system sleep..."
caffeinate -i -s &
CAFFE_PID=$!

mkdir -p logs results

echo "🚀 [1/2] Starting Eth-Hunter Backend on http://localhost:8000..."
cd "$SCRIPT_DIR/backend"
source venv/bin/activate
nohup python3 main.py > "$SCRIPT_DIR/logs/backend.log" 2>&1 &
BACKEND_PID=$!
echo "   ✅ Backend running (PID: $BACKEND_PID)"

echo "🌐 [2/2] Starting Eth-Hunter Frontend on http://localhost:5173..."
cd "$SCRIPT_DIR/frontend"
nohup npm run dev > "$SCRIPT_DIR/logs/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "   ✅ Frontend running (PID: $FRONTEND_PID)"

echo ""
echo "========================================================"
echo "🎉 ETH-HUNTER IS RUNNING!"
echo "========================================================"
echo "  - Backend API: http://localhost:8000"
echo "  - Web Dashboard: http://localhost:5173"
echo "  - Logs: tail -f logs/backend.log"
echo "========================================================"
echo ""

sleep 2
# Open default browser
if command -v open &> /dev/null; then
    open "http://localhost:5173" || true
fi

# Wait to keep terminal alive and cleanup on exit
trap "kill $BACKEND_PID $FRONTEND_PID $CAFFE_PID 2>/dev/null; echo 'Stopped all services.'; exit 0" INT TERM
echo "Press Ctrl+C in this window to stop Eth-Hunter."
wait $BACKEND_PID $FRONTEND_PID

