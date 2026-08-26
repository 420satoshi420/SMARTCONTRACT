#!/bin/bash
set -e

# ==============================================================================
# CyberDesk Kali Linux & Wireshark LLM Security Operations Setup
# Provisions offline LLM engine (Ollama), TShark/Wireshark packet capture tooling,
# and connects the Eth-Hunter network & smart contract analysis suite.
# ==============================================================================

echo "🦈 ========================================================"
echo "🦈  CYBERDESK: Kali Linux & Wireshark LLM Suite Setup"
echo "🦈 ========================================================"
echo ""

# 1. Check Root / Sudo
if [[ $EUID -ne 0 ]]; then
   echo "⚠️  This setup script will prompt for sudo privileges to install tools."
fi

# 2. Install Network Capture & Analysis Dependencies
echo "📦 [1/4] Installing Wireshark, TShark, and Python dependencies..."
if command -v apt-get &> /dev/null; then
    sudo apt-get update
    sudo apt-get install -y tshark wireshark python3-pip curl jq libpcap-dev
    
    # Configure non-root packet capture permissions
    echo "🛡️  Configuring dumpcap non-root capture permissions..."
    sudo groupadd -f wireshark
    sudo usermod -aG wireshark "$USER" || true
    sudo setcap cap_net_raw,cap_net_admin=eip /usr/bin/dumpcap || true
elif command -v brew &> /dev/null; then
    echo "🍎 macOS detected - Installing via Homebrew..."
    brew install wireshark jq || true
fi

# 3. Python Crypto & Packet Tools
echo "🐍 [2/4] Installing Python packet & LLM integration modules..."
pip install pyshark scapy eth-account ecdsa pycryptodome httpx websockets fastapi uvicorn 2>/dev/null || python3 -m pip install pyshark scapy eth-account ecdsa pycryptodome httpx websockets fastapi uvicorn

# 4. Install Ollama (Offline Local LLM Engine)
echo "🤖 [3/4] Checking Ollama (Local Offline AI)..."
if ! command -v ollama &> /dev/null; then
    echo "⬇️  Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "✅ Ollama already installed: $(ollama --version)"
fi

# Start Ollama service if not active
if ! pgrep -x "ollama" > /dev/null; then
    echo "🚀 Starting Ollama background service..."
    ollama serve &
    sleep 3
fi

# Pull high-performance security & reasoning model
echo "🧠 [4/4] Pulling security reasoning model (llama3.3 / qwen2.5-coder:7b)..."
ollama pull qwen2.5-coder:7b || ollama pull llama3.3 || echo "⚠️ Model pull queued."

echo ""
echo "========================================================"
echo "🎉 CYBERDESK KALI LINUX & WIRESHARK SETUP COMPLETE!"
echo "========================================================"
echo "📡 Run PCAP LLM Analysis:"
echo "   python3 scripts/pcap_llm_analyzer.py <path_to_pcap> --model qwen2.5-coder:7b"
echo ""
echo "🛡️  Start Eth-Hunter Dashboard & On-Chain Audit Engine:"
echo "   PORT=8001 python3 server.py"
echo "========================================================"
