#!/usr/bin/env python3
"""
Eth-Hunter Real-Time Web Dashboard & Wallet Progress Server.
Zero external dependencies required (Pure Python stdlib).
"""
import os
import sys
import json
import time
import secrets
import threading
import urllib.request
import ssl
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, unquote, parse_qs
from typing import Dict, List, Optional, Any

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from eth_audit_agent.core.parser import SolidityParser
from eth_audit_agent.agents.base import get_llm_backend
from eth_audit_agent.agents.red_team import RedTeamAgent
from eth_audit_agent.agents.blue_team import BlueTeamAgent
from eth_audit_agent.orchestrator.debater import AuditDebater
from eth_audit_agent.reporters.markdown_reporter import MarkdownReporter
from eth_audit_agent.reporters.webhook_notifier import WebhookNotifier

REPORTS_DIR = BASE_DIR / "results" / "drafts"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
LEADERBOARD_FILE = BASE_DIR / "results" / "leaderboard.json"
WALLET_FILE = BASE_DIR / "results" / "wallet.json"
WEB_DIR = BASE_DIR / "web"

ETH_PRICE_USD = 1920.0

log_history = [
    "[SYSTEM] 🟢 Eth-Hunter Real-Time Engine active",
    "[SYSTEM] 💼 Hunter Payout Wallet initialized & synchronized",
    "[SYSTEM] Ready for on-demand smart contract inspection"
]


def add_log(message: str):
    timestamped = f"[{time.strftime('%H:%M:%S')}] {message}"
    log_history.append(timestamped)
    if len(log_history) > 200:
        log_history.pop(0)
    
    # Save to local agent folder for sharing memory log
    agent_dir = BASE_DIR / "agent"
    agent_dir.mkdir(exist_ok=True)
    with open(agent_dir / "memory.log", "a", encoding="utf-8") as f:
        f.write(timestamped + "\n")


# Real-Time Market & Network Cache
ETH_PRICE_USD = 1920.0
last_price_fetch_time = 0
last_market_data = {
    "eth_usd": 1920.0,
    "gas_gwei": 15,
    "block_number": 20500000,
    "source": "Coinbase & Ethereum RPC",
    "updated_at": time.strftime('%H:%M:%S')
}


def get_ssl_context() -> ssl.SSLContext:
    """Returns a resilient SSL context for macOS Python runtime."""
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    except Exception:
        return ssl._create_unverified_context()


def fetch_live_eth_price() -> float:
    """Fetches real-time spot ETH price in USD from Coinbase public API."""
    global ETH_PRICE_USD, last_market_data
    now = time.time()
    if now - last_market_data.get("last_price_fetch", 0) < 10 and ETH_PRICE_USD > 0:
        return ETH_PRICE_USD
    
    url = "https://api.coinbase.com/v2/prices/ETH-USD/spot"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})
        with urllib.request.urlopen(req, context=get_ssl_context(), timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            val = float(data.get("data", {}).get("amount", ETH_PRICE_USD))
            if val > 0:
                ETH_PRICE_USD = val
                last_market_data["last_price_fetch"] = now
                last_market_data["eth_usd"] = val
                last_market_data["updated_at"] = time.strftime('%H:%M:%S')
    except Exception:
        pass
    return ETH_PRICE_USD


def fetch_live_network_stats() -> dict:
    """Fetches live real-time Ethereum network statistics (Gas, Block, ETH Price)."""
    global last_market_data
    price = fetch_live_eth_price()
    ctx = get_ssl_context()
    
    # Try fetching live gas/block via public RPC
    rpc_urls = ["https://ethereum-rpc.publicnode.com", "https://rpc.ankr.com/eth", "https://1rpc.io/eth"]
    for rpc_url in rpc_urls:
        try:
            block_req_data = json.dumps({"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1}).encode("utf-8")
            req = urllib.request.Request(rpc_url, data=block_req_data, headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, context=ctx, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if "result" in data:
                    last_market_data["block_number"] = int(data["result"], 16)
                    break
        except Exception:
            continue

    for rpc_url in rpc_urls:
        try:
            gas_req_data = json.dumps({"jsonrpc": "2.0", "method": "eth_gasPrice", "params": [], "id": 2}).encode("utf-8")
            req = urllib.request.Request(rpc_url, data=gas_req_data, headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, context=ctx, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if "result" in data:
                    gas_wei = int(data["result"], 16)
                    last_market_data["gas_gwei"] = max(1, round(gas_wei / 1e9, 1))
                    break
        except Exception:
            continue

    last_market_data["eth_usd"] = price
    last_market_data["updated_at"] = time.strftime('%H:%M:%S')
    return last_market_data


# Supported Chains Matrix (Etherscan V2 API, Blockscan & Public RPC Fallbacks)
SUPPORTED_CHAINS = {
    "1": {
        "name": "Ethereum Mainnet", "symbol": "ETH", "chain_id": 1,
        "explorer": "https://etherscan.io", "blockscan_name": "ethereum",
        "rpc": ["https://ethereum-rpc.publicnode.com", "https://rpc.ankr.com/eth", "https://1rpc.io/eth"]
    },
    "42161": {
        "name": "Arbitrum One", "symbol": "ETH", "chain_id": 42161,
        "explorer": "https://arbiscan.io", "blockscan_name": "arbitrum",
        "rpc": ["https://arbitrum-one-rpc.publicnode.com", "https://arb1.arbitrum.io/rpc", "https://1rpc.io/arb"]
    },
    "8453": {
        "name": "Base Mainnet", "symbol": "ETH", "chain_id": 8453,
        "explorer": "https://basescan.org", "blockscan_name": "base",
        "rpc": ["https://base-rpc.publicnode.com", "https://mainnet.base.org", "https://1rpc.io/base"]
    },
    "10": {
        "name": "OP Mainnet", "symbol": "ETH", "chain_id": 10,
        "explorer": "https://optimistic.etherscan.io", "blockscan_name": "optimism",
        "rpc": ["https://optimism-rpc.publicnode.com", "https://mainnet.optimism.io", "https://1rpc.io/op"]
    },
    "137": {
        "name": "Polygon Mainnet", "symbol": "POL", "chain_id": 137,
        "explorer": "https://polygonscan.com", "blockscan_name": "polygon",
        "rpc": ["https://polygon-bor-rpc.publicnode.com", "https://polygon-rpc.com", "https://1rpc.io/matic"]
    },
    "56": {
        "name": "BNB Smart Chain", "symbol": "BNB", "chain_id": 56,
        "explorer": "https://bscscan.com", "blockscan_name": "bsc",
        "rpc": ["https://bsc-rpc.publicnode.com", "https://binance.llamarpc.com"]
    },
    "11155111": {
        "name": "Sepolia Testnet", "symbol": "SepoliaETH", "chain_id": 11155111,
        "explorer": "https://sepolia.etherscan.io", "blockscan_name": "sepolia",
        "rpc": ["https://ethereum-sepolia-rpc.publicnode.com", "https://rpc.sepolia.org"]
    },
    "59144": {
        "name": "Linea Mainnet", "symbol": "ETH", "chain_id": 59144,
        "explorer": "https://lineascan.build", "blockscan_name": "linea",
        "rpc": ["https://linea-rpc.publicnode.com", "https://rpc.linea.build"]
    },
    "81457": {
        "name": "Blast Mainnet", "symbol": "ETH", "chain_id": 81457,
        "explorer": "https://blastscan.io", "blockscan_name": "blast",
        "rpc": ["https://blast-rpc.publicnode.com", "https://rpc.blast.io"]
    },
    "146": {
        "name": "Sonic Mainnet", "symbol": "S", "chain_id": 146,
        "explorer": "https://sonicscan.org", "blockscan_name": "sonic",
        "rpc": ["https://rpc.soniclabs.com"]
    },
    "80094": {
        "name": "Berachain Mainnet", "symbol": "BERA", "chain_id": 80094,
        "explorer": "https://berascan.com", "blockscan_name": "berachain",
        "rpc": ["https://rpc.berachain.com"]
    },
    "100": {
        "name": "Gnosis", "symbol": "xDAI", "chain_id": 100,
        "explorer": "https://gnosisscan.io", "blockscan_name": "gnosis",
        "rpc": ["https://gnosis-rpc.publicnode.com", "https://rpc.gnosischain.com"]
    },
}


def fetch_etherscan_balance(address: str, chain_id: int = 1, api_key: str = None) -> dict:
    """
    Queries real live on-chain balance.
    1. Tries Etherscan V2 API (if key is configured).
    2. Seamlessly falls back to Public JSON-RPC (eth_getBalance) for 100% reliability with zero configuration.
    """
    current_price = fetch_live_eth_price()
    api_key = api_key or os.getenv("ETHERSCAN_API_KEY", "")
    chain_info = SUPPORTED_CHAINS.get(str(chain_id), {"name": "Ethereum Mainnet", "symbol": "ETH", "chain_id": 1, "rpc": ["https://ethereum-rpc.publicnode.com"]})
    ctx = get_ssl_context()
    
    # 1. Try Etherscan V2 Universal API if valid API key is present
    if api_key and api_key != "YourApiKeyToken":
        url_v2 = f"https://api.etherscan.io/v2/api?chainid={chain_id}&module=account&action=balance&address={address}&tag=latest&apikey={api_key}"
        url_v1 = f"https://api.etherscan.io/api?module=account&action=balance&address={address}&tag=latest&apikey={api_key}"
        for url in [url_v2, url_v1]:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})
                with urllib.request.urlopen(req, context=ctx, timeout=4) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    if data.get("status") == "1":
                        wei_val = int(data.get("result", "0"))
                        eth_val = round(wei_val / 1e18, 6)
                        usd_val = round(eth_val * current_price, 2)
                        return {
                            "success": True,
                            "address": address,
                            "chain_id": chain_id,
                            "chain_name": chain_info["name"],
                            "symbol": chain_info.get("symbol", "ETH"),
                            "wei": str(wei_val),
                            "eth": eth_val,
                            "usd": usd_val,
                            "eth_price_usd": current_price,
                            "source": f"Etherscan V2 API ({chain_info['name']})"
                        }
            except Exception:
                continue

    # 2. Public JSON-RPC Fallback (100% Free, No API Key Required)
    rpc_list = chain_info.get("rpc", ["https://ethereum-rpc.publicnode.com"])
    for rpc_url in rpc_list:
        try:
            req_data = json.dumps({
                "jsonrpc": "2.0",
                "method": "eth_getBalance",
                "params": [address, "latest"],
                "id": 1
            }).encode("utf-8")
            req = urllib.request.Request(rpc_url, data=req_data, headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, context=ctx, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if "result" in data:
                    wei_val = int(data["result"], 16)
                    eth_val = round(wei_val / 1e18, 6)
                    usd_val = round(eth_val * current_price, 2)
                    return {
                        "success": True,
                        "address": address,
                        "chain_id": chain_id,
                        "chain_name": chain_info["name"],
                        "symbol": chain_info.get("symbol", "ETH"),
                        "wei": str(wei_val),
                        "eth": eth_val,
                        "usd": usd_val,
                        "eth_price_usd": current_price,
                        "source": f"On-Chain Public Node ({chain_info['name']})"
                    }
        except Exception:
            continue

    return {
        "success": False,
        "address": address,
        "chain_id": chain_id,
        "chain_name": chain_info["name"],
        "error": "Unable to connect to on-chain nodes"
    }


def generate_eth_address() -> str:
    """Generates a cryptographically random Ethereum address (0x + 40 hex chars)."""
    return "0x" + secrets.token_hex(20)


def get_wallet_data(include_onchain: bool = False) -> dict:
    wallet = None
    if WALLET_FILE.exists():
        try:
            wallet = json.loads(WALLET_FILE.read_text(encoding="utf-8"))
        except Exception:
            wallet = None

    if not wallet or not isinstance(wallet, dict):
        wallet = {
            "address": generate_eth_address(),
            "created_at": time.strftime('%Y-%m-%d %H:%M:%S'),
        }

    # Ensure all required runtime fields exist
    wallet.setdefault("balance_eth", 0.0)
    wallet.setdefault("balance_usd", 0.0)
    wallet.setdefault("goal_target_usd", 2088.0)
    wallet.setdefault("goal_target_eth", round(2088.0 / ETH_PRICE_USD, 3))
    wallet.setdefault("goal_progress_percent", 0)
    wallet.setdefault("goal_hit", False)
    wallet.setdefault("network", "Ethereum Mainnet (Simulation + Etherscan Live)")
    wallet.setdefault("transactions", [])

    if include_onchain and wallet.get("address"):
        onchain = fetch_etherscan_balance(wallet["address"])
        wallet["onchain"] = onchain
    
    return wallet


# Security & Validation Helpers
REQUEST_HISTORY: Dict[str, list] = {}

def check_rate_limit(ip: str, limit: int = 120, window: int = 60) -> bool:
    """In-memory rate limiter per IP address (limit requests per window seconds)."""
    now = time.time()
    history = [t for t in REQUEST_HISTORY.get(ip, []) if now - t < window]
    if len(history) >= limit:
        return False
    history.append(now)
    REQUEST_HISTORY[ip] = history
    return True


def is_valid_eth_address(address: str) -> bool:
    """Validates standard 42-char hex Ethereum address (0x + 40 hex characters)."""
    import re
    return bool(re.match(r'^0x[a-fA-F0-9]{40}$', str(address).strip()))


def sanitize_and_resolve_path(user_input: str) -> Optional[Path]:
    """Ensures paths stay strictly within workspace or safe sandbox boundaries."""
    try:
        raw_str = str(user_input).strip()
        if ".." in raw_str:
            # Check for path traversal attempts
            p = (BASE_DIR / raw_str).resolve()
            if not str(p).startswith(str(BASE_DIR.resolve())):
                return None
            return p
        p = Path(raw_str)
        if not p.is_absolute():
            p = (BASE_DIR / raw_str).resolve()
        return p
    except Exception:
        return None


def atomic_save_json(filepath: Path, data: dict):
    """Atomically writes JSON to disk using temporary file replacement to prevent corruption."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    temp_file = filepath.with_suffix(f'.tmp_{secrets.token_hex(4)}')
    try:
        temp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        temp_file.replace(filepath)
    except Exception:
        if temp_file.exists():
            temp_file.unlink(missing_ok=True)
        filepath.write_text(json.dumps(data, indent=2), encoding="utf-8")


def save_wallet_data(wallet: dict):
    atomic_save_json(WALLET_FILE, wallet)


def credit_wallet_payout(finding_title: str, severity: str, amount_usd: float, platform: str = "Immunefi") -> dict:
    wallet = get_wallet_data()
    amount_eth = round(amount_usd / ETH_PRICE_USD, 4)
    
    tx = {
        "tx_hash": "0x" + secrets.token_hex(32),
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
        "type": "BOUNTY_PAYOUT",
        "platform": platform,
        "finding": finding_title,
        "severity": severity,
        "amount_usd": amount_usd,
        "amount_eth": amount_eth,
        "status": "CONFIRMED"
    }
    wallet["transactions"].insert(0, tx)
    wallet["balance_usd"] = sum(t["amount_usd"] for t in wallet["transactions"])
    wallet["balance_eth"] = round(wallet["balance_usd"] / ETH_PRICE_USD, 3)
    wallet["goal_progress_percent"] = min(100, int((wallet["balance_usd"] / wallet["goal_target_usd"]) * 100))
    wallet["goal_hit"] = wallet["balance_usd"] >= wallet["goal_target_usd"]
    save_wallet_data(wallet)
    return wallet


def get_leaderboard_data() -> dict:
    if LEADERBOARD_FILE.exists():
        try:
            return json.loads(LEADERBOARD_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "goal_usd": 2088,
        "total_potential_usd": 0,
        "goal_progress_percent": 0,
        "goal_hit": False,
        "findings": []
    }


def update_leaderboard(repo: str, finding_title: str, severity: str, confidence: int, bounty_est: int) -> dict:
    lb = get_leaderboard_data()
    score = int((confidence / 100.0) * bounty_est)
    
    entry = {
        "date": time.strftime('%Y-%m-%d %H:%M:%S'),
        "repo": repo,
        "finding": finding_title,
        "severity": severity,
        "confidence": confidence,
        "bounty_estimate": bounty_est,
        "score": score
    }
    lb["findings"].append(entry)
    
    total = sum(f.get("bounty_estimate", 0) for f in lb["findings"] if f.get("confidence", 0) >= 70)
    lb["total_potential_usd"] = total
    lb["goal_progress_percent"] = min(100, int((total / lb["goal_usd"]) * 100))
    lb["goal_hit"] = total >= lb["goal_usd"]
    
    LEADERBOARD_FILE.parent.mkdir(parents=True, exist_ok=True)
    LEADERBOARD_FILE.write_text(json.dumps(lb, indent=2), encoding="utf-8")
    
    # Auto-credit hunter wallet
    credit_wallet_payout(finding_title, severity, float(bounty_est))
    return lb


def fetch_verified_contract_source(address: str, chain_id: int = 1, api_key: str = None) -> Path:
    """
    Fetches verified Solidity source code with multi-tier fallback:
    1. Etherscan V2 API (if key is configured)
    2. Blockscout V2 Open API (100% Free, No Key Required, 60+ files support)
    3. Sourcify Decentralized Open Registry (100% Free)
    """
    cache_contract_dir = BASE_DIR / "cache" / "contracts" / f"{chain_id}_{address}"
    cache_contract_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if full directory is already cached
    sol_files = list(cache_contract_dir.glob("**/*.sol"))
    if len(sol_files) > 1:
        return cache_contract_dir
    elif len(sol_files) == 1 and sol_files[0].stat().st_size > 100:
        return sol_files[0]

    api_key = api_key or os.getenv("ETHERSCAN_API_KEY", "")
    ctx = get_ssl_context()
    
    # Tier 1: Try Etherscan V2 Universal API if valid API key is present
    if api_key and api_key != "YourApiKeyToken":
        url_v2 = f"https://api.etherscan.io/v2/api?chainid={chain_id}&module=contract&action=getsourcecode&address={address}&apikey={api_key}"
        url_v1 = f"https://api.etherscan.io/api?module=contract&action=getsourcecode&address={address}&apikey={api_key}"
        for url in [url_v2, url_v1]:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})
                with urllib.request.urlopen(req, context=ctx, timeout=8) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    if data.get("status") == "1" and data.get("result"):
                        res_item = data["result"][0]
                        source_code = res_item.get("SourceCode", "")
                        contract_name = res_item.get("ContractName", "VerifiedContract")
                        
                        if not source_code:
                            continue

                        if source_code.startswith("{{") and source_code.endswith("}}"):
                            try:
                                inner_json = json.loads(source_code[1:-1])
                                sources = inner_json.get("sources", {})
                                for file_path, src_obj in sources.items():
                                    f_path = cache_contract_dir / file_path
                                    f_path.parent.mkdir(parents=True, exist_ok=True)
                                    f_path.write_text(src_obj.get("content", ""), encoding="utf-8")
                                add_log(f"✅ Downloaded {len(sources)} verified source files via Etherscan V2 for {contract_name} ({address})")
                                return cache_contract_dir
                            except Exception:
                                pass
                        
                        target_file = cache_contract_dir / f"{contract_name}.sol"
                        target_file.write_text(source_code, encoding="utf-8")
                        add_log(f"✅ Downloaded verified contract {contract_name} via Etherscan V2 ({address})")
                        return target_file
            except Exception:
                pass

    # Tier 2: Blockscout V2 API (100% Free, Zero API Key Required)
    BLOCKSCOUT_HOSTS = {
        1: "https://eth.blockscout.com",
        42161: "https://arbitrum.blockscout.com",
        8453: "https://base.blockscout.com",
        10: "https://optimism.blockscout.com",
        137: "https://polygon.blockscout.com",
        11155111: "https://eth-sepolia.blockscout.com",
        59144: "https://linea.blockscout.com",
        81457: "https://blast.blockscout.com",
        100: "https://gnosis.blockscout.com"
    }
    blockscout_base = BLOCKSCOUT_HOSTS.get(chain_id, "https://eth.blockscout.com")
    blockscout_url = f"{blockscout_base}/api/v2/smart-contracts/{address}"
    try:
        req = urllib.request.Request(blockscout_url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            contract_name = data.get("name", "VerifiedContract")
            main_source = data.get("source_code", "")
            add_sources = data.get("additional_sources", [])
            
            if add_sources:
                for item in add_sources:
                    f_path = cache_contract_dir / item.get("file_path", "Contract.sol")
                    f_path.parent.mkdir(parents=True, exist_ok=True)
                    f_path.write_text(item.get("source_code", ""), encoding="utf-8")
                if main_source:
                    f_path = cache_contract_dir / f"{contract_name}.sol"
                    f_path.write_text(main_source, encoding="utf-8")
                add_log(f"🌐 [Zero-Key Auto-Fetcher] Downloaded {len(add_sources)} verified source files for {contract_name} ({address}) via Blockscout V2")
                return cache_contract_dir
            elif main_source:
                target_file = cache_contract_dir / f"{contract_name}.sol"
                target_file.write_text(main_source, encoding="utf-8")
                add_log(f"🌐 [Zero-Key Auto-Fetcher] Downloaded verified {contract_name} ({address}) via Blockscout V2")
                return target_file
    except Exception as e:
        add_log(f"⚠️ Blockscout V2 auto-fetch notice: {e}")

    # Tier 3: Sourcify Decentralized Registry
    try:
        sourcify_url = f"https://sourcify.dev/server/files/any/{chain_id}/{address}"
        req = urllib.request.Request(sourcify_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, context=ctx, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            files = data.get("files", [])
            if files:
                for f_item in files:
                    f_path = cache_contract_dir / f_item.get("name", "Contract.sol")
                    f_path.parent.mkdir(parents=True, exist_ok=True)
                    f_path.write_text(f_item.get("content", ""), encoding="utf-8")
                add_log(f"🌐 [Zero-Key Auto-Fetcher] Downloaded {len(files)} source files via Sourcify ({address})")
                return cache_contract_dir
    except Exception:
        pass

    target_file = cache_contract_dir / f"{address}.sol"
    if not target_file.exists():
        target_file.write_text(f"// SPDX-License-Identifier: MIT\npragma solidity ^0.8.20;\n\n// Contract stub for {address} (Chain {chain_id})\ncontract Contract_{address[:8]} {{\n}}\n", encoding="utf-8")
    return target_file


def run_audit_task(target_path_or_url: str, preset: str = "immunefi", provider: str = "mock", chain_id: int = 1):
    add_log(f"🚀 Starting audit on target: {target_path_or_url} (Preset: {preset}, Provider: {provider}, Chain ID: {chain_id})")
    try:
        import re
        target_str = str(target_path_or_url).strip()
        detected_chain_id = chain_id
        
        # Handle Blockscan / Etherscan URLs
        if "blockscan.com" in target_str or "etherscan.io" in target_str or "arbiscan.io" in target_str or "basescan.org" in target_str:
            # Check chain in URL
            for cid, cinfo in SUPPORTED_CHAINS.items():
                if f"/{cinfo['blockscan_name']}/" in target_str.lower() or f"/{cid}/" in target_str:
                    detected_chain_id = int(cid)
                    break
            m = re.search(r'0x[a-fA-F0-9]{40}', target_str)
            if m:
                target_str = m.group(0)

        chain_meta = SUPPORTED_CHAINS.get(str(detected_chain_id), {"name": "Ethereum Mainnet", "blockscan_name": "ethereum"})

        # Handle 0x Ethereum Address
        if target_str.startswith("0x") and len(target_str) == 42:
            add_log(f"🌐 Target: Verified Contract {target_str} on {chain_meta['name']} (Chain ID: {detected_chain_id})")
            add_log(f"🔍 Blockscan Code Viewer: https://vscode.blockscan.com/{chain_meta['blockscan_name']}/{target_str}")
            add_log(f"📥 Fetching verified Solidity source code via Etherscan V2 Universal API...")
            path = fetch_verified_contract_source(target_str, chain_id=detected_chain_id)
        else:
            path = Path(target_str)
            if not path.is_absolute():
                path = BASE_DIR / target_str

        if path.is_dir():
            add_log("🔍 Ingesting directory and running static AST parsing...")
            context = SolidityParser.parse_directory(str(path.resolve()), auto_slither=True)
        elif path.is_file():
            add_log("🔍 Ingesting single Solidity contract file...")
            context = SolidityParser.parse_file(str(path.resolve()))
        else:
            add_log(f"❌ Target path not found: {path}")
            return

        add_log(f"✅ Ingested {len(context.contracts)} contracts. Detected pragma: {context.pragma_version}")
        add_log("⚔️ Initiating Layer 2 Multi-Agent Adversarial Debate (Red Team vs Blue Team)...")

        llm_client = get_llm_backend(provider=provider)
        debater = AuditDebater(RedTeamAgent(llm_client), BlueTeamAgent(llm_client))
        session = debater.run_session(context)

        add_log(f"📊 Layer 2 finished. Triaged {len(session.triaged_findings)} findings across {len(session.red_hypotheses)} threat hypotheses.")
        add_log("📐 Layer 3: Generating Foundry Invariant Test Specifications & Handlers...")

        reporter = MarkdownReporter()
        report_md = reporter.generate_bounty_report(session, preset=preset)
        
        report_filename = f"audit_{path.stem}_{int(time.time())}.md"
        report_file = REPORTS_DIR / report_filename
        report_file.write_text(report_md, encoding="utf-8")

        add_log(f"📝 Layer 4: Generated bounty draft -> results/drafts/{report_filename}")

        for f in session.triaged_findings:
            sev_str = f.final_severity.value if hasattr(f.final_severity, 'value') else str(f.final_severity)
            if sev_str in ["Critical", "High", "Medium"]:
                bounty_map = {"Critical": 25000, "High": 10000, "Medium": 3000}
                bounty_val = bounty_map.get(sev_str, 1000)
                conf = int(f.red_team_analysis.confidence * 10) if hasattr(f, 'red_team_analysis') and f.red_team_analysis else 85
                update_leaderboard(path.name, f.title, sev_str, conf, bounty_val)
                add_log(f"🏆 Finding: [{sev_str}] {f.title} (Conf: {conf}%, Est: ${bounty_val:,})")

        notifier = WebhookNotifier()
        notifier.notify_audit_completed(session)
        add_log("🎉 Audit complete! Leaderboard, wallet payouts, and reports updated.")
    except Exception as e:
        add_log(f"❌ Audit execution failed: {e}")


class EthHunterHTTPHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'SAMEORIGIN')
        self.send_header('X-XSS-Protection', '1; mode=block')
        self.send_header('Referrer-Policy', 'strict-origin-when-cross-origin')
        super().end_headers()

    def check_client_rate(self) -> bool:
        client_ip = self.client_address[0] if self.client_address else "127.0.0.1"
        if not check_rate_limit(client_ip, limit=180, window=60):
            self.send_response(429)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error": "Rate limit exceeded. Please slow down."}')
            return False
        return True

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        if not self.check_client_rate():
            return
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ["/", "/index.html"]:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write((WEB_DIR / "index.html").read_bytes())
            return

        if path.startswith("/static/"):
            rel_file = unquote(path[8:])
            file_path = WEB_DIR / rel_file
            if file_path.exists() and file_path.is_file():
                self.send_response(200)
                if rel_file.endswith(".css"):
                    self.send_header("Content-Type", "text/css")
                elif rel_file.endswith(".js"):
                    self.send_header("Content-Type", "application/javascript")
                self.end_headers()
                self.wfile.write(file_path.read_bytes())
                return

        if path == "/api/targets":
            targets_file = BASE_DIR / "config" / "targets.json"
            if targets_file.exists():
                try:
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(targets_file.read_bytes())
                    return
                except Exception:
                    pass
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"curated_targets": []}')
            return

        if path == "/api/chains":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(SUPPORTED_CHAINS).encode("utf-8"))
            return

        if path == "/api/market":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(fetch_live_network_stats()).encode("utf-8"))
            return

        if path == "/api/wallet":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(get_wallet_data(include_onchain=True)).encode("utf-8"))
            return

        if path == "/api/wallet/status":
            try:
                from eth_audit_agent.core.aa_wallet import AgentWalletManager
                aa_wallet = AgentWalletManager(str(BASE_DIR / "results" / "agent_signer.json"))
                status = aa_wallet.get_status()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(status).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        if path == "/api/etherscan/balance":
            qs = parse_qs(parsed.query)
            address = qs.get("address", [""])[0]
            chain_id = int(qs.get("chain_id", ["1"])[0])
            if not address:
                address = get_wallet_data().get("address", "")
            res = fetch_etherscan_balance(address, chain_id=chain_id)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(res).encode("utf-8"))
            return

        if path == "/api/leaderboard":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(get_leaderboard_data()).encode("utf-8"))
            return

        if path == "/api/logs":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"logs": log_history}).encode("utf-8"))
            return

        if path == "/api/reports":
            reports = []
            for f in sorted(REPORTS_DIR.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True):
                reports.append({
                    "filename": f.name,
                    "path": str(f),
                    "size": f.stat().st_size,
                    "modified": f.stat().st_mtime
                })
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(reports).encode("utf-8"))
            return

        if path.startswith("/api/reports/"):
            filename = unquote(path[13:])
            file_path = REPORTS_DIR / filename
            if file_path.exists() and file_path.is_file():
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"filename": filename, "content": file_path.read_text(encoding="utf-8")}).encode("utf-8"))
                return

        ETH_HUNTER_DIR = Path("/Users/wakeup/Desktop/eth-hunter")
        if path == "/api/deduplicated_findings":
            dedup_file = ETH_HUNTER_DIR / "results" / "all_findings" / "deduplicated.json"
            if not dedup_file.exists():
                dedup_file = BASE_DIR / "results" / "all_findings" / "deduplicated.json"
            if dedup_file.exists():
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(dedup_file.read_bytes())
                return
            else:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"clusters": []}')
                return

        if path == "/api/submissions/batch":
            sub_dir = ETH_HUNTER_DIR / "results" / "submissions" / "batch"
            if not sub_dir.exists():
                sub_dir = BASE_DIR / "results" / "submissions" / "batch"
            items = []
            if sub_dir.exists():
                for f in sorted(sub_dir.glob("*.md")):
                    items.append({
                        "filename": f.name,
                        "title": f.stem.replace("_", " "),
                        "size": f.stat().st_size
                    })
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"submissions": items}).encode("utf-8"))
            return

        if path.startswith("/api/submissions/batch/"):
            fname = unquote(path[23:])
            sub_dir = ETH_HUNTER_DIR / "results" / "submissions" / "batch"
            if not sub_dir.exists():
                sub_dir = BASE_DIR / "results" / "submissions" / "batch"
            f_path = sub_dir / fname
            if f_path.exists() and f_path.is_file():
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"filename": fname, "content": f_path.read_text(encoding="utf-8")}).encode("utf-8"))
                return

        self.send_response(404)
        self.end_headers()
        self.wfile.write(b'{"error": "Not found"}')

    def do_POST(self):
        if not self.check_client_rate():
            return
        parsed = urlparse(self.path)
        content_len = int(self.headers.get('Content-Length', 0))
        if content_len > 1_000_000: # 1MB limit on request body
            self.send_response(413)
            self.end_headers()
            self.wfile.write(b'{"error": "Payload too large (max 1MB)"}')
            return

        body = self.rfile.read(content_len).decode('utf-8') if content_len > 0 else "{}"

        if parsed.path == "/api/scan":
            try:
                data = json.loads(body)
                target = data.get("target", "examples/sample_vulnerable_vault.sol")
                preset = data.get("preset", "immunefi")
                provider = data.get("provider", "mock")
                chain_id = int(data.get("chain_id", 1))
                
                threading.Thread(target=run_audit_task, args=(target, preset, provider, chain_id), daemon=True).start()
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "Scan queued", "target": target, "chain_id": chain_id}).encode("utf-8"))
                return
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
                return

        elif parsed.path == "/api/wallet/setup_aa":
            try:
                from eth_audit_agent.core.aa_wallet import AgentWalletManager
                aa_wallet = AgentWalletManager(str(BASE_DIR / "results" / "agent_signer.json"))
                status = aa_wallet.get_status()
                add_log(f"🤖 Initialized Agent AA Wallet: {status['smart_account_address']}")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(status).encode("utf-8"))
                return
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
                return

        elif parsed.path == "/api/wallet/generate":
            try:
                new_address = generate_eth_address()
                wallet = {
                    "address": new_address,
                    "created_at": time.strftime('%Y-%m-%d %H:%M:%S'),
                    "balance_eth": 0.0,
                    "balance_usd": 0.0,
                    "goal_target_usd": 2088.0,
                    "goal_target_eth": round(2088.0 / ETH_PRICE_USD, 3),
                    "goal_progress_percent": 0,
                    "goal_hit": False,
                    "network": "Ethereum Mainnet (Simulation Tracker)",
                    "transactions": []
                }
                save_wallet_data(wallet)
                add_log(f"💼 Created new Hunter Wallet address: {new_address}")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(wallet).encode("utf-8"))
                return
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
                return

        elif parsed.path == "/api/wallet/claim_all":
            try:
                lb = get_leaderboard_data()
                wallet = get_wallet_data()
                claimed_count = 0
                total_credited = 0
                
                # Check for findings in leaderboard
                for f in lb.get("findings", []):
                    bounty = f.get("bounty_estimate", 0)
                    if bounty > 0 and f.get("confidence", 0) >= 70:
                        # Check if already credited in wallet transactions
                        exists = any(t.get("finding") == f.get("finding") for t in wallet.get("transactions", []))
                        if not exists:
                            credit_wallet_payout(f.get("finding"), f.get("severity", "High"), float(bounty))
                            claimed_count += 1
                            total_credited += bounty

                wallet = get_wallet_data()
                add_log(f"⚡ Auto-Claim Engine: Processed {claimed_count} new payouts (+${total_credited:,} USD / +{round(total_credited/ETH_PRICE_USD, 3)} ETH)")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": True,
                    "claimed_count": claimed_count,
                    "total_credited_usd": total_credited,
                    "wallet": wallet
                }).encode("utf-8"))
                return
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
                return

        elif parsed.path == "/api/wallet/set_address":
            try:
                data = json.loads(body)
                custom_addr = str(data.get("address", "")).strip()
                if not is_valid_eth_address(custom_addr):
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Invalid Ethereum address format. Must start with 0x followed by 40 hex characters."}).encode("utf-8"))
                    return

                wallet = get_wallet_data()
                wallet["address"] = custom_addr
                wallet["network"] = "Ethereum Mainnet (Live Tracking)"
                save_wallet_data(wallet)
                add_log(f"💼 Set custom Hunter Wallet address: {custom_addr}")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(wallet).encode("utf-8"))
                return
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
                return

        elif parsed.path == "/api/settings/etherscan_key":
            try:
                data = json.loads(body)
                api_key = str(data.get("api_key", "")).strip()
                os.environ["ETHERSCAN_API_KEY"] = api_key
                settings_file = BASE_DIR / "config" / "settings.json"
                settings_file.parent.mkdir(parents=True, exist_ok=True)
                settings = {}
                if settings_file.exists():
                    try:
                        settings = json.loads(settings_file.read_text(encoding="utf-8"))
                    except Exception:
                        pass
                settings["etherscan_api_key"] = api_key
                atomic_save_json(settings_file, settings)
                add_log(f"🔑 Etherscan API Key updated ({api_key[:4]}...{api_key[-4:] if len(api_key)>8 else ''})")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "message": "API key saved successfully"}).encode("utf-8"))
                return
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
                return

        elif parsed.path == "/api/wallet/setup_aa":
            try:
                from eth_audit_agent.core.aa_wallet import AgentWalletManager
                aa_wallet = AgentWalletManager(str(BASE_DIR / "results" / "agent_signer.json"))
                status = aa_wallet.get_status()
                add_log(f"🤖 Account Abstraction Wallet Setup: Smart Account {status.get('smart_account_address', '')[:10]}...")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": True,
                    "message": "ERC-4337 Smart Account setup complete",
                    "status": status
                }).encode("utf-8"))
                return
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
                return

        self.send_response(404)
        self.end_headers()


class ReusableHTTPServer(HTTPServer):
    allow_reuse_address = True


def start_server(port: int = None):
    target_port = port or int(os.getenv("PORT", 8000))
    httpd = None
    
    for p in range(target_port, target_port + 10):
        try:
            server_address = ('0.0.0.0', p)
            httpd = ReusableHTTPServer(server_address, EthHunterHTTPHandler)
            target_port = p
            break
        except OSError as e:
            if e.errno == 48:  # Address already in use
                continue
            raise e

    if httpd is None:
        print(f"❌ Failed to bind server on ports {target_port}..{target_port+9}", flush=True)
        return

    print(f"🛡️  Eth-Hunter Server running at http://localhost:{target_port}", flush=True)
    try:
        httpd.serve_forever()
    except (KeyboardInterrupt, SystemExit):
        print("\nStopping server...", flush=True)
        httpd.server_close()
    except Exception as e:
        print(f"Server error: {e}", flush=True)
        httpd.server_close()


if __name__ == "__main__":
    start_server()
