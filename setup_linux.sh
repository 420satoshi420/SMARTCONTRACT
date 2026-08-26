#!/usr/bin/env bash
# ==============================================================================
# Eth-Hunter: 1-Click Linux Setup & Launcher Script
# Automatically installs Foundry (forge), Slither, solc-select, Python dependencies,
# and generates a Linux Desktop application shortcut.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================================"
echo "🚀 ETH-HUNTER: Automated Linux Environment Setup"
echo "========================================================"
echo "📁 Working Directory: $SCRIPT_DIR"
echo ""

# 1. Detect Package Manager & Install System Packages
echo "📦 [1/5] Installing core build tools & libraries..."
if command -v apt-get &> /dev/null; then
    sudo apt-get update
    sudo apt-get install -y git curl python3 python3-pip python3-venv build-essential tmux jq libpcap-dev
elif command -v pacman &> /dev/null; then
    sudo pacman -Sy --noconfirm git curl python python-pip base-devel tmux jq
elif command -v dnf &> /dev/null; then
    sudo dnf install -y git curl python3 python3-pip make gcc tmux jq
fi

# 2. Install Foundry (forge, cast, anvil)
echo ""
echo "⚒️  [2/5] Installing Foundry (forge, cast, anvil)..."
if ! command -v forge &> /dev/null; then
    curl -L https://foundry.paradigm.xyz | bash
    export PATH="$HOME/.foundry/bin:$PATH"
    "$HOME/.foundry/bin/foundryup" || true
else
    echo "✅ Foundry already installed: $(forge --version 2>/dev/null || echo 'installed')"
fi

# 3. Setup Python Virtual Environment & Install Modules
echo ""
echo "🐍 [3/5] Setting up Python virtual environment..."
if [ ! -d "backend/venv" ]; then
    python3 -m venv backend/venv
fi

source backend/venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt
pip install slither-analyzer solc-select

# 4. Configure Solidity Compilers (solc-select)
echo ""
echo "⚙️  [4/5] Installing Solidity compilers via solc-select..."
export PATH="$HOME/.local/bin:$PATH"
solc-select install 0.8.20 || true
solc-select install 0.8.24 || true
solc-select use 0.8.20 || true

# 5. Create Desktop Launcher on Linux Desktop
echo ""
echo "🖥️  [5/5] Creating Linux Desktop shortcut..."
DESKTOP_DIR="$HOME/Desktop"
if [ -d "$DESKTOP_DIR" ]; then
    cat << DESK_EOF > "$DESKTOP_DIR/Eth-Hunter.desktop"
[Desktop Entry]
Version=1.0
Type=Application
Name=Eth-Hunter
Comment=Autonomous Smart Contract Security & Bug Bounty Engine
Exec=bash -c "cd '$SCRIPT_DIR' && ./start_all.sh; read -p 'Press enter to exit'"
Icon=utilities-terminal
Terminal=true
Categories=Development;Security;
DESK_EOF
    chmod +x "$DESKTOP_DIR/Eth-Hunter.desktop"
    echo "✅ Desktop launcher created at: $DESKTOP_DIR/Eth-Hunter.desktop"
fi

echo ""
echo "========================================================"
echo "🎉 SETUP COMPLETE! Eth-Hunter is ready in Linux."
echo "========================================================"
echo "To start Eth-Hunter now, run:"
echo "   ./start_all.sh"
echo "Or double-click the 'Eth-Hunter' icon on your Linux Desktop!"
echo "========================================================"
