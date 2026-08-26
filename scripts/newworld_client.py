#!/usr/bin/env python3
"""
NewWorld Protocol CLI Client & Automation Toolkit
Interact with NewWorldToken (NEW) and NewWorldPool AMM/Staking Resource.
"""

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parents[1]
DEPLOYMENTS_FILE = BASE_DIR / "deployments.json"

DEFAULT_RPC = "http://127.0.0.1:8545"
DEFAULT_PK = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"


def load_deployments():
    if not DEPLOYMENTS_FILE.exists():
        print(f"Error: {DEPLOYMENTS_FILE} not found. Please deploy first.")
        sys.exit(1)
    with open(DEPLOYMENTS_FILE, "r") as f:
        return json.load(f)


def run_cast(cmd: str) -> str:
    import subprocess
    full_cmd = f"cast {cmd}"
    res = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Cast Error: {res.stderr.strip()}")
        return ""
    return res.stdout.strip()


def get_live_eth_price() -> float:
    # Try CMC from backend
    try:
        sys.path.insert(0, str(BASE_DIR))
        from backend.core.economic_evaluator import EconomicEvaluator
        res = EconomicEvaluator.fetch_live_eth_price()
        return res.get("eth_usd", 2464.0)
    except Exception:
        return 2464.0


def cmd_status(args):
    dep = load_deployments()
    token_addr = dep["contracts"]["NewWorldToken"]["address"]
    pool_addr = dep["contracts"]["NewWorldPool"]["address"]
    rpc = args.rpc or dep.get("rpcUrl", DEFAULT_RPC)

    eth_price = get_live_eth_price()

    # Query pool reserves
    res_eth_raw = run_cast(f"call {pool_addr} 'reserveEth()(uint256)' --rpc-url {rpc}")
    res_token_raw = run_cast(f"call {pool_addr} 'reserveToken()(uint256)' --rpc-url {rpc}")
    total_lp_raw = run_cast(f"call {pool_addr} 'totalLiquidity()(uint256)' --rpc-url {rpc}")

    eth_val = int(res_eth_raw.split()[0]) / 1e18 if res_eth_raw else 0.0
    token_val = int(res_token_raw.split()[0]) / 1e18 if res_token_raw else 0.0
    lp_val = int(total_lp_raw.split()[0]) / 1e18 if total_lp_raw else 0.0

    token_price_eth = (eth_val / token_val) if token_val > 0 else 0.0
    token_price_usd = token_price_eth * eth_price

    tvl_usd = (eth_val * eth_price) + (token_val * token_price_usd)

    print("=" * 60)
    print("🌐 NEWWORLD PROTOCOL LIVE STATUS")
    print("=" * 60)
    print(f"• Network RPC        : {rpc}")
    print(f"• Token Address      : {token_addr}")
    print(f"• Pool Address       : {pool_addr}")
    print("-" * 60)
    print(f"• ETH Market Price   : ${eth_price:,.2f} USD (Live CMC)")
    print(f"• NEW Token Price    : {token_price_eth:.6f} ETH (${token_price_usd:.4f} USD)")
    print(f"• Pool Reserves (ETH): {eth_val:,.4f} ETH")
    print(f"• Pool Reserves (NEW): {token_val:,.2f} NEW")
    print(f"• Total Staked LP    : {lp_val:,.4f} LP Shares")
    print(f"• Estimated TVL      : ${tvl_usd:,.2f} USD")
    print("=" * 60)


def cmd_swap_eth(args):
    dep = load_deployments()
    pool_addr = dep["contracts"]["NewWorldPool"]["address"]
    rpc = args.rpc or dep.get("rpcUrl", DEFAULT_RPC)
    pk = args.private_key or DEFAULT_PK

    amount_eth = float(args.amount)
    print(f"🔄 Swapping {amount_eth} ETH for NEWWORLD tokens...")
    out = run_cast(
        f"send {pool_addr} 'swapEthForToken(uint256)' 1 --value {amount_eth}ether --private-key {pk} --rpc-url {rpc}"
    )
    print("✅ Swap Transaction Executed!")
    print(out)


def cmd_swap_token(args):
    dep = load_deployments()
    token_addr = dep["contracts"]["NewWorldToken"]["address"]
    pool_addr = dep["contracts"]["NewWorldPool"]["address"]
    rpc = args.rpc or dep.get("rpcUrl", DEFAULT_RPC)
    pk = args.private_key or DEFAULT_PK

    amount_token = int(float(args.amount) * 1e18)
    print(f"🔄 Approving {args.amount} NEWWORLD tokens for pool...")
    run_cast(
        f"send {token_addr} 'approve(address,uint256)' {pool_addr} {amount_token} --private-key {pk} --rpc-url {rpc}"
    )
    print(f"🔄 Swapping {args.amount} NEWWORLD for ETH...")
    out = run_cast(
        f"send {pool_addr} 'swapTokenForEth(uint256,uint256)' {amount_token} 1 --private-key {pk} --rpc-url {rpc}"
    )
    print("✅ Swap Transaction Executed!")
    print(out)


def cmd_claim(args):
    dep = load_deployments()
    pool_addr = dep["contracts"]["NewWorldPool"]["address"]
    rpc = args.rpc or dep.get("rpcUrl", DEFAULT_RPC)
    pk = args.private_key or DEFAULT_PK

    print("🌾 Harvesting accumulated yield staking rewards...")
    out = run_cast(f"send {pool_addr} 'claimRewards()' --private-key {pk} --rpc-url {rpc}")
    print("✅ Rewards Claimed!")
    print(out)


def main():
    parser = argparse.ArgumentParser(description="NewWorld Protocol CLI Interaction Toolkit")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # status
    p_status = subparsers.add_parser("status", help="Inspect pool status, prices, and reserves")
    p_status.add_argument("--rpc", default=DEFAULT_RPC, help="EVM RPC endpoint")
    p_status.set_defaults(func=cmd_status)

    # swap-eth
    p_swap_eth = subparsers.add_parser("swap-eth", help="Swap ETH for NEWWORLD tokens")
    p_swap_eth.add_argument("--amount", required=True, help="Amount of ETH to swap (e.g. 0.1)")
    p_swap_eth.add_argument("--rpc", default=DEFAULT_RPC, help="EVM RPC endpoint")
    p_swap_eth.add_argument("--private-key", default=DEFAULT_PK, help="Sender private key")
    p_swap_eth.set_defaults(func=cmd_swap_eth)

    # swap-token
    p_swap_tok = subparsers.add_parser("swap-token", help="Swap NEWWORLD tokens for ETH")
    p_swap_tok.add_argument("--amount", required=True, help="Amount of NEW tokens to swap (e.g. 100)")
    p_swap_tok.add_argument("--rpc", default=DEFAULT_RPC, help="EVM RPC endpoint")
    p_swap_tok.add_argument("--private-key", default=DEFAULT_PK, help="Sender private key")
    p_swap_tok.set_defaults(func=cmd_swap_token)

    # claim
    p_claim = subparsers.add_parser("claim", help="Claim staking yield rewards")
    p_claim.add_argument("--rpc", default=DEFAULT_RPC, help="EVM RPC endpoint")
    p_claim.add_argument("--private-key", default=DEFAULT_PK, help="Sender private key")
    p_claim.set_defaults(func=cmd_claim)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
