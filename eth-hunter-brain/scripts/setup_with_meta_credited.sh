#!/bin/bash
set -e
echo "🚀 Setting up ETH Hunter Brain - Written by Meta & Sirin (420satoshi420)"
echo "========================================================================"
BRAIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "Brain Directory: $BRAIN_DIR"

python3 "$BRAIN_DIR/mcp_server_unified_credited.py" --test
echo "✅ ETH Hunter Brain initialized with speed turbo optimizations!"
