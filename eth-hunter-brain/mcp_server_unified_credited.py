#!/usr/bin/env python3
"""
ETH Hunter & NewWorld Unified MCP Server
Written by Meta & Sirin (420satoshi420)
Provides tools for Antigravity IDE, Claude Desktop, and CLI agentic reasoning.
Automates Smart Contract Audits, AMM Operations, Yield Staking, and DEX Listing.
"""
import sys, json, os, glob, subprocess, urllib.request, ssl
from pathlib import Path

BRAIN_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BRAIN_DIR.parent
DEPLOYMENTS_FILE = PROJECT_DIR / "deployments.json"

def list_brain_files():
    files = []
    for p in BRAIN_DIR.rglob("*"):
        if p.is_file() and not p.name.startswith("."):
            files.append(str(p.relative_to(BRAIN_DIR)))
    return {"files": sorted(files), "total_count": len(files)}

def get_rules(rule_name="all"):
    rules_dir = BRAIN_DIR / "rules"
    if rule_name == "all":
        res = {}
        for f in rules_dir.glob("*.md"):
            res[f.stem] = f.read_text(encoding="utf-8")
        return res
    target = rules_dir / f"{rule_name}.md"
    if target.exists():
        return {rule_name: target.read_text(encoding="utf-8")}
    return {"error": f"Rule {rule_name} not found"}

def get_knowledge(category="all"):
    k_dir = BRAIN_DIR / "knowledge"
    res = {}
    for p in k_dir.rglob("*.md"):
        key = str(p.relative_to(k_dir))
        if category == "all" or category in key:
            res[key] = p.read_text(encoding="utf-8")
    return res

def get_poc_template(name="reentrancy"):
    template_file = BRAIN_DIR / "templates" / "FOUNDRY_POC_TEMPLATES.sol"
    if template_file.exists():
        return {"template": template_file.read_text(encoding="utf-8")}
    return {"error": "PoC template file not found"}

def get_thresholds():
    cfg = BRAIN_DIR / "config" / "thresholds.json"
    if cfg.exists():
        return json.loads(cfg.read_text(encoding="utf-8"))
    return {"goal_usd": 2088}

def get_live_market():
    cmc_key = "53cfff81437841029b74d436fbfd5f99"
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest?symbol=ETH"
        req = urllib.request.Request(url, headers={"X-CMC_PRO_API_KEY": cmc_key, "User-Agent": "EthHunter/1.0"})
        with urllib.request.urlopen(req, timeout=4, context=ctx) as resp:
            data = json.loads(resp.read().decode())
            quote = data.get("data", {}).get("ETH", {}).get("quote", {}).get("USD", {})
            return {
                "provider": "CoinMarketCap Pro API",
                "eth_price_usd": quote.get("price"),
                "change_24h_percent": quote.get("percent_change_24h"),
                "market_cap_usd": quote.get("market_cap"),
                "volume_24h_usd": quote.get("volume_24h")
            }
    except Exception as e:
        return {"error": str(e), "eth_price_usd": 2463.0}

def newworld_status(rpc="http://127.0.0.1:8545"):
    if not DEPLOYMENTS_FILE.exists():
        return {"error": "deployments.json not found. Please deploy first."}
    dep = json.loads(DEPLOYMENTS_FILE.read_text())
    pool_addr = dep["contracts"]["NewWorldPool"]["address"]
    token_addr = dep["contracts"]["NewWorldToken"]["address"]

    mkt = get_live_market()
    eth_price = mkt.get("eth_price_usd", 2463.0)

    def run_cast(cmd):
        res = subprocess.run(f"cast {cmd}", shell=True, capture_output=True, text=True)
        return res.stdout.strip()

    r_eth = run_cast(f"call {pool_addr} 'reserveEth()(uint256)' --rpc-url {rpc}")
    r_tok = run_cast(f"call {pool_addr} 'reserveToken()(uint256)' --rpc-url {rpc}")
    r_lp = run_cast(f"call {pool_addr} 'totalLiquidity()(uint256)' --rpc-url {rpc}")

    eth_val = int(r_eth.split()[0]) / 1e18 if r_eth else 0.0
    tok_val = int(r_tok.split()[0]) / 1e18 if r_tok else 0.0
    lp_val = int(r_lp.split()[0]) / 1e18 if r_lp else 0.0

    tok_price_eth = (eth_val / tok_val) if tok_val > 0 else 0.0
    tok_price_usd = tok_price_eth * eth_price
    tvl_usd = (eth_val * eth_price) + (tok_val * tok_price_usd)

    return {
        "status": "online",
        "network": dep.get("network", "Local EVM"),
        "rpc": rpc,
        "token_address": token_addr,
        "pool_address": pool_addr,
        "eth_market_price_usd": eth_price,
        "new_token_price_eth": round(tok_price_eth, 6),
        "new_token_price_usd": round(tok_price_usd, 4),
        "pool_reserves_eth": round(eth_val, 4),
        "pool_reserves_new": round(tok_val, 2),
        "total_staked_lp_shares": round(lp_val, 4),
        "estimated_tvl_usd": round(tvl_usd, 2)
    }

def newworld_swap(amount_eth: float, rpc="http://127.0.0.1:8545", pk="0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"):
    if not DEPLOYMENTS_FILE.exists():
        return {"error": "deployments.json not found"}
    dep = json.loads(DEPLOYMENTS_FILE.read_text())
    pool_addr = dep["contracts"]["NewWorldPool"]["address"]

    cmd = f"cast send {pool_addr} 'swapEthForToken(uint256)' 1 --value {amount_eth}ether --private-key {pk} --rpc-url {rpc}"
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        return {"error": res.stderr.strip()}
    return {"status": "success", "swapped_eth": amount_eth, "tx_output": res.stdout.strip()[:300]}

def newworld_claim_rewards(rpc="http://127.0.0.1:8545", pk="0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"):
    if not DEPLOYMENTS_FILE.exists():
        return {"error": "deployments.json not found"}
    dep = json.loads(DEPLOYMENTS_FILE.read_text())
    pool_addr = dep["contracts"]["NewWorldPool"]["address"]

    cmd = f"cast send {pool_addr} 'claimRewards()' --private-key {pk} --rpc-url {rpc}"
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        return {"error": res.stderr.strip()}
    return {"status": "success", "tx_output": res.stdout.strip()[:300]}

def generate_listing_package():
    doc_path = PROJECT_DIR / "COINMARKETCAP_LISTING_PACKAGE.md"
    if doc_path.exists():
        return {"listing_dossier": doc_path.read_text(encoding="utf-8")}
    return {"error": "COINMARKETCAP_LISTING_PACKAGE.md not found"}

def handle_request(req):
    method = req.get("method")
    params = req.get("params", {})
    req_id = req.get("id")

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {"name": "list_brain_files", "description": "Lists all rules, knowledge, and templates in ETH Hunter Brain"},
                    {"name": "get_rules", "description": "Fetches security rules and false positive filters"},
                    {"name": "get_knowledge", "description": "Fetches domain knowledge for reentrancy, access control, flashloans"},
                    {"name": "get_poc_template", "description": "Returns verified Foundry PoC exploit templates"},
                    {"name": "get_thresholds", "description": "Returns speed mode and bounty threshold settings ($2088 target)"},
                    {"name": "get_live_market", "description": "Fetches real-time cryptocurrency quotes from CoinMarketCap Pro API"},
                    {"name": "newworld_status", "description": "Queries on-chain AMM pool reserves, prices, and TVL for NewWorld Protocol"},
                    {"name": "newworld_swap", "description": "Automates ETH to NEW token swap on NewWorldPool AMM"},
                    {"name": "newworld_claim_rewards", "description": "Automates harvesting accumulated staking yield rewards"},
                    {"name": "generate_listing_package", "description": "Returns complete structured submission dossier for CoinMarketCap & CoinGecko"}
                ]
            }
        }
    elif method == "tools/call":
        name = params.get("name")
        args = params.get("arguments", {})
        if name == "list_brain_files":
            res = list_brain_files()
        elif name == "get_rules":
            res = get_rules(args.get("rule_name", "all"))
        elif name == "get_knowledge":
            res = get_knowledge(args.get("category", "all"))
        elif name == "get_poc_template":
            res = get_poc_template(args.get("name", "reentrancy"))
        elif name == "get_thresholds":
            res = get_thresholds()
        elif name == "get_live_market":
            res = get_live_market()
        elif name == "newworld_status":
            res = newworld_status(args.get("rpc", "http://127.0.0.1:8545"))
        elif name == "newworld_swap":
            res = newworld_swap(float(args.get("amount_eth", 0.1)), args.get("rpc", "http://127.0.0.1:8545"), args.get("pk", "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"))
        elif name == "newworld_claim_rewards":
            res = newworld_claim_rewards(args.get("rpc", "http://127.0.0.1:8545"), args.get("pk", "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"))
        elif name == "generate_listing_package":
            res = generate_listing_package()
        else:
            res = {"error": f"Unknown tool {name}"}

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"content": [{"type": "text", "text": json.dumps(res, indent=2)}]}
        }
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": "Method not found"}}

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print(f"MCP Server Ready. Tools available: 10 | Files in brain: {len(list_brain_files()['files'])}")
        print("Testing get_live_market via CMC:", get_live_market())
        print("Testing newworld_status:", newworld_status())
        return
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            res = handle_request(req)
            sys.stdout.write(json.dumps(res) + "\n")
            sys.stdout.flush()
        except Exception as e:
            err = {"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": str(e)}}
            sys.stdout.write(json.dumps(err) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()
