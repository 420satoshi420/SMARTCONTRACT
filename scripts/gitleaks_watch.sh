#!/usr/bin/env bash
# ==============================================================================
# Continuous Gitleaks Secret Scanner Daemon
# Runs non-stop in background / interval to prevent credential leaks.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
GITLEAKS_BIN="$ROOT_DIR/scripts/bin/gitleaks"

if [ ! -f "$GITLEAKS_BIN" ]; then
    echo "❌ Gitleaks binary not found at $GITLEAKS_BIN"
    exit 1
fi

echo "🛡️ Starting Continuous Gitleaks Secret Scanner Daemon..."
echo "📂 Monitoring repository at $ROOT_DIR"
echo "Press [Ctrl+C] to stop."

while true; do
    TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
    echo -n "[$TIMESTAMP] 🔍 Scanning workspace for secrets... "
    
    if "$GITLEAKS_BIN" detect -s "$ROOT_DIR" --no-git -c "$ROOT_DIR/.gitleaks.toml" > /dev/null 2>&1; then
        echo "✅ CLEAN (0 leaks detected)"
    else
        echo "🚨 ALERT: Secret leak detected!"
        "$GITLEAKS_BIN" detect -s "$ROOT_DIR" --no-git -c "$ROOT_DIR/.gitleaks.toml" -v || true
    fi
    
    sleep 30
done
