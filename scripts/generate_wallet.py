#!/usr/bin/env python3
"""
Ethereum Reward Wallet Generator & Manager for Eth-Hunter.
Generates an official EVM-compliant wallet (Address, Private Key, Mnemonic/Seed)
for receiving bug bounty rewards from Immunefi, Code4rena, and Sherlock.
"""
import os
import sys
import json
import secrets
from pathlib import Path
from eth_account import Account

Account.enable_unaudited_hdwallet_features()

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_ENV = BASE_DIR / ".env"
WALLET_FILE = BASE_DIR / "results" / "reward_wallet.json"
WALLET_FILE.parent.mkdir(parents=True, exist_ok=True)


def create_reward_wallet(force_new: bool = False):
    # If wallet already exists and not forcing new, load existing
    if WALLET_FILE.exists() and not force_new:
        try:
            data = json.loads(WALLET_FILE.read_text(encoding="utf-8"))
            if data.get("address"):
                return data
        except Exception:
            pass

    # Generate new wallet with 12-word mnemonic & private key
    acct, mnemonic = Account.create_with_mnemonic()
    
    wallet_data = {
        "address": acct.address,
        "private_key": acct.key.hex(),
        "mnemonic": mnemonic,
        "derivation_path": "m/44'/60'/0'/0/0",
        "created_at": str(os.popen("date").read().strip()),
        "security_notice": "CRITICAL: Keep your mnemonic & private key offline and secret. Never share them with anyone. Use the public address to receive bounty payouts."
    }

    # Save to local results/reward_wallet.json with strict 0600 permissions
    WALLET_FILE.write_text(json.dumps(wallet_data, indent=2), encoding="utf-8")
    os.chmod(WALLET_FILE, 0o600)

    # Update .env with ETH_REWARD_ADDRESS
    env_lines = []
    if CONFIG_ENV.exists():
        for line in CONFIG_ENV.read_text(encoding="utf-8").splitlines():
            if not line.startswith("ETH_REWARD_ADDRESS=") and not line.startswith("ETH_REWARD_PRIVATE_KEY="):
                env_lines.append(line)
    env_lines.append(f"ETH_REWARD_ADDRESS={acct.address}")
    env_lines.append(f"ETH_REWARD_PRIVATE_KEY={acct.key.hex()}")
    CONFIG_ENV.write_text("\n".join(env_lines) + "\n", encoding="utf-8")
    os.chmod(CONFIG_ENV, 0o600)

    return wallet_data


if __name__ == "__main__":
    force = "--force" in sys.argv or "--new" in sys.argv
    wallet = create_reward_wallet(force_new=force)
    
    print("=" * 60)
    print("💎 ETHEREUM BOUNTY REWARD WALLET CREATED")
    print("=" * 60)
    print(f"📍 Public Address (Submit for Rewards): {wallet['address']}")
    print(f"📁 Keystore File: {WALLET_FILE}")
    print(f"🔐 Configured in: {CONFIG_ENV}")
    print("=" * 60)
    print("⚠️  Security Note: Your private key and mnemonic have been saved")
    print("   locally with restricted permissions (chmod 0600).")
    print("=" * 60)
