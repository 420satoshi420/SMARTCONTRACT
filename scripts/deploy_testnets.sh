#!/usr/bin/env bash
# ==============================================================================
# Automated Testnet Deployer for Arbitrum Sepolia & Ethereum Sepolia
# ==============================================================================

ADDRESS="0x44489dC714CB4F7c95e817C2B3C5E0cDb696B1F6"
PRIVATE_KEY="0x53378b951a76ae12f62bd0ceaf9ad06cd4ad640b22333b07e513375a57689d05"

ARB_RPC="https://sepolia-rollup.arbitrum.io/rpc"
ETH_RPC="https://ethereum-sepolia-rpc.publicnode.com"

echo "=================================================="
echo "🚀 NEWWORLD TESTNET DEPLOYMENT CHECK"
echo "Wallet Address: $ADDRESS"
echo "=================================================="

# Check Arbitrum Sepolia
echo -n "Checking Arbitrum Sepolia Balance... "
ARB_BAL=$(cast balance $ADDRESS --rpc-url $ARB_RPC 2>/dev/null || echo "0")
echo "$ARB_BAL wei"

if [ "$ARB_BAL" != "0" ]; then
    echo "⚡ Deploying to Arbitrum Sepolia..."
    forge script contracts/script/DeployNewWorld.s.sol \
        --rpc-url $ARB_RPC \
        --private-key $PRIVATE_KEY \
        --broadcast -vvv
else
    echo "⚠️  Arbitrum Sepolia balance is 0. Claim free ETH from QuickNode faucet."
fi

echo "--------------------------------------------------"

# Check Ethereum Sepolia
echo -n "Checking Ethereum Sepolia Balance... "
ETH_BAL=$(cast balance $ADDRESS --rpc-url $ETH_RPC 2>/dev/null || echo "0")
echo "$ETH_BAL wei"

if [ "$ETH_BAL" != "0" ]; then
    echo "⚡ Deploying to Ethereum Sepolia..."
    forge script contracts/script/DeployNewWorld.s.sol \
        --rpc-url $ETH_RPC \
        --private-key $PRIVATE_KEY \
        --broadcast -vvv
else
    echo "⚠️  Ethereum Sepolia balance is 0. Claim free ETH from Google Cloud / Sepolia faucet."
fi

echo "=================================================="
