#!/usr/bin/env bash
# ==============================================================================
# Helper Script: Configure GitHub Secrets & Local .env for Google Cloud Free Tier
# ==============================================================================

set -euo pipefail

echo "============================================================"
echo "🔐 Web3 & Google Cloud Free Tier Secret Setup"
echo "============================================================"

if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ Created .env from .env.example"
    else
        touch .env
    fi
fi

echo ""
echo "📋 Required Secrets for Google Cloud Free Tier & CI/CD:"
echo "------------------------------------------------------------"
echo "1. GEMINI_API_KEY           - Google Gemini API Free Tier Key"
echo "2. GCP_PROJECT_ID           - Google Cloud Project ID"
echo "3. GCP_SA_KEY               - Google Service Account JSON Key (Base64 or Raw)"
echo "4. FIREBASE_TOKEN           - Firebase CLI Token (via npx firebase login:ci)"
echo "5. ETHERSCAN_API_KEY        - Etherscan Free Tier API Key"
echo "6. PRIVATE_KEY              - Deployer Wallet Private Key (Optional for testnet)"
echo "------------------------------------------------------------"
echo ""

if command -v gh >/dev/null 2>&1; then
    echo "💡 GitHub CLI (gh) detected. You can set repository secrets directly:"
    echo "   gh secret set GEMINI_API_KEY"
    echo "   gh secret set GCP_SA_KEY"
    echo "   gh secret set FIREBASE_TOKEN"
    echo "   gh secret set ETHERSCAN_API_KEY"
else
    echo "💡 To set repository secrets on GitHub manually:"
    echo "   Navigate to: Settings -> Secrets and variables -> Actions -> New repository secret"
fi

echo ""
echo "============================================================"
