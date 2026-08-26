"""
Target Discovery Pipeline for ETH Hunter.
Discovers real bug bounty targets from Immunefi and fetches verified Solidity
source code from Etherscan for automated scanning.

v1.0: Immunefi program discovery + Etherscan verified contract fetching.
"""

import json
import logging
import os
import ssl
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parents[2] / "cache"
TARGETS_CACHE = CACHE_DIR / "discovered_targets.json"
CONTRACTS_CACHE = CACHE_DIR / "contracts"

# Known high-value Immunefi bounty programs with contract addresses
# These are real, active programs as of 2026 — update periodically
KNOWN_IMMUNEFI_TARGETS = [
    {
        "protocol": "Uniswap",
        "bounty_max": 3_000_000,
        "bounty_url": "https://immunefi.com/bounty/uniswap/",
        "chain_id": 1,
        "addresses": [
            "0x1F98431c8aD98523631AE4a59f267346ea31F984",  # UniswapV3Factory
        ],
    },
    {
        "protocol": "Aave V3",
        "bounty_max": 250_000,
        "bounty_url": "https://immunefi.com/bounty/aavev3/",
        "chain_id": 1,
        "addresses": [
            "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2",  # Pool
        ],
    },
    {
        "protocol": "Compound V3",
        "bounty_max": 150_000,
        "bounty_url": "https://immunefi.com/bounty/compoundv3/",
        "chain_id": 1,
        "addresses": [
            "0xc3d688B66703497DAA19211EEdff47f25384cdc3",  # cUSDCv3
        ],
    },
    {
        "protocol": "Lido",
        "bounty_max": 2_000_000,
        "bounty_url": "https://immunefi.com/bounty/lido/",
        "chain_id": 1,
        "addresses": [
            "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84",  # stETH
        ],
    },
    {
        "protocol": "MakerDAO",
        "bounty_max": 10_000_000,
        "bounty_url": "https://immunefi.com/bounty/makerdao/",
        "chain_id": 1,
        "addresses": [
            "0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2",  # MKR Token
        ],
    },
]


def _get_ssl_context():
    """Resilient SSL context for macOS."""
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    except Exception:
        return ssl._create_unverified_context()


def fetch_verified_source(
    address: str,
    chain_id: int = 1,
    api_key: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Fetches verified Solidity source code from Etherscan V2 API.
    Returns dict with source code, ABI, compiler version, etc.
    Returns None if contract is not verified or API fails.
    """
    key = api_key or os.getenv("ETHERSCAN_API_KEY", "")
    if not key:
        logger.warning("No ETHERSCAN_API_KEY configured. Cannot fetch source code.")
        return None

    url = (
        f"https://api.etherscan.io/v2/api"
        f"?chainid={chain_id}"
        f"&module=contract&action=getsourcecode"
        f"&address={address}"
        f"&apikey={key}"
    )

    try:
        ctx = _get_ssl_context()
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            data = json.loads(resp.read().decode())

        if data.get("status") != "1":
            logger.warning(f"Etherscan API error for {address}: {data.get('message', 'Unknown')}")
            return None

        results = data.get("result", [])
        if not results or not results[0].get("SourceCode"):
            logger.info(f"Contract {address} is not verified on chain {chain_id}")
            return None

        result = results[0]
        return {
            "address": address,
            "chain_id": chain_id,
            "contract_name": result.get("ContractName", "Unknown"),
            "source_code": result.get("SourceCode", ""),
            "abi": result.get("ABI", ""),
            "compiler_version": result.get("CompilerVersion", ""),
            "optimization_used": result.get("OptimizationUsed", "0"),
            "runs": result.get("Runs", "200"),
            "proxy": result.get("Proxy", "0"),
            "implementation": result.get("Implementation", ""),
        }
    except Exception as e:
        logger.warning(f"Failed to fetch source for {address}: {e}")
        return None


def save_contract_source(
    address: str,
    contract_name: str,
    source_code: str,
    chain_id: int = 1,
) -> Path:
    """
    Saves fetched Solidity source code to the local cache directory.
    Handles both single-file and multi-file (Standard JSON) sources.
    """
    target_dir = CONTRACTS_CACHE / f"{contract_name}_{address[:10]}"
    target_dir.mkdir(parents=True, exist_ok=True)

    # Check if source is Standard JSON format (multi-file)
    source = source_code.strip()
    if source.startswith("{{"):
        # Double-wrapped Standard JSON — unwrap
        source = source[1:-1]

    if source.startswith("{"):
        try:
            parsed = json.loads(source)
            sources = parsed.get("sources", {})
            if sources:
                for filename, file_data in sources.items():
                    content = file_data.get("content", "")
                    if content:
                        safe_name = filename.replace("/", "_").replace("\\", "_")
                        file_path = target_dir / safe_name
                        file_path.write_text(content, encoding="utf-8")
                # Return the main contract file or first file
                main_file = target_dir / f"{contract_name}.sol"
                if not main_file.exists():
                    # Find any .sol file
                    sol_files = list(target_dir.glob("*.sol"))
                    if sol_files:
                        main_file = sol_files[0]
                return main_file
        except json.JSONDecodeError:
            pass

    # Single-file source
    file_path = target_dir / f"{contract_name}.sol"
    file_path.write_text(source, encoding="utf-8")
    return file_path


def discover_targets(
    min_bounty: int = 5000,
    max_targets: int = 10,
    use_cache: bool = True,
) -> List[Dict[str, Any]]:
    """
    Discovers real bug bounty targets.

    Returns a list of target dicts with:
    - protocol: str
    - bounty_max: int (USD)
    - bounty_url: str
    - addresses: list of contract addresses
    - chain_id: int
    - source_path: str (local path to downloaded .sol, if fetched)
    """
    # Check cache first
    if use_cache and TARGETS_CACHE.exists():
        try:
            cached = json.loads(TARGETS_CACHE.read_text())
            cache_age = time.time() - cached.get("fetched_at", 0)
            if cache_age < 86400:  # 24 hours
                targets = cached.get("targets", [])
                logger.info(f"Using cached targets ({len(targets)} programs, {cache_age/3600:.1f}h old)")
                return targets[:max_targets]
        except Exception:
            pass

    # Build targets from known programs
    targets = []
    for program in KNOWN_IMMUNEFI_TARGETS:
        if program["bounty_max"] >= min_bounty:
            target = {
                "protocol": program["protocol"],
                "bounty_max": program["bounty_max"],
                "bounty_url": program["bounty_url"],
                "chain_id": program["chain_id"],
                "addresses": program["addresses"],
                "source_paths": [],
            }
            targets.append(target)

    # Try to fetch source code for each target
    api_key = os.getenv("ETHERSCAN_API_KEY", "")
    if api_key and api_key != "DEMO_KEY":
        for target in targets[:max_targets]:
            for addr in target["addresses"]:
                # Check if already cached locally
                cached_files = list(CONTRACTS_CACHE.glob(f"*_{addr[:10]}/*.sol"))
                if cached_files:
                    target["source_paths"].append(str(cached_files[0]))
                    continue

                result = fetch_verified_source(addr, target["chain_id"], api_key)
                if result and result["source_code"]:
                    path = save_contract_source(
                        addr, result["contract_name"],
                        result["source_code"], target["chain_id"]
                    )
                    target["source_paths"].append(str(path))
                    logger.info(f"Fetched source for {target['protocol']}: {result['contract_name']}")

                # Rate limit: Etherscan free tier = 5 req/s
                time.sleep(0.25)

    # Cache results
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_data = {
        "fetched_at": time.time(),
        "targets": targets,
    }
    TARGETS_CACHE.write_text(json.dumps(cache_data, indent=2))
    logger.info(f"Discovered {len(targets)} targets")

    return targets[:max_targets]


def get_local_targets(contracts_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """
    Scans local contracts directory for .sol files to audit.
    Useful when you've manually placed contracts to scan.
    """
    search_dir = contracts_dir or CONTRACTS_CACHE
    if not search_dir.exists():
        return []

    targets = []
    for sol_file in search_dir.rglob("*.sol"):
        # Skip test files, mocks, and libraries
        name_lower = sol_file.name.lower()
        if any(skip in name_lower for skip in ["test", "mock", "migration", "console"]):
            continue

        targets.append({
            "protocol": sol_file.stem,
            "bounty_max": 50_000,
            "bounty_url": "",
            "chain_id": 1,
            "addresses": [],
            "source_paths": [str(sol_file)],
        })

    return targets


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    targets = discover_targets()
    print(f"\n🎯 Discovered {len(targets)} bounty targets:\n")
    for t in targets:
        print(f"  • {t['protocol']}: Max ${t['bounty_max']:,} | {len(t['addresses'])} address(es)")
        for p in t.get("source_paths", []):
            print(f"    📄 {p}")
