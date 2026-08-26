#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Ensure venv is activated
if [ -d "backend/venv" ]; then
    source backend/venv/bin/activate
fi

TARGET="${1:-contracts/target-repo}"
PRESET="${2:-immunefi}"

echo "🛡️  ========================================================"
echo "🛡️  Eth-Hunter: Executing Static Analysis & Security Pipeline"
echo "🛡️  ========================================================"
echo "🎯 Target: $TARGET"
echo "📝 Preset: $PRESET"
echo ""

python3 scripts/audit_pipeline.py --target "$TARGET" --preset "$PRESET"
