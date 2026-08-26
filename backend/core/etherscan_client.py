"""
Etherscan V2 Universal Multichain Client.
Supports 12+ EVM chains, rate-limit backoff, multi-file JSON unpacking ({{...}} and {...}),
local contract caching, on-chain balance queries, and explorer URL parsing.
"""
import os
import re
import json
import time
import urllib.request
import urllib.parse
import urllib.error
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List, Union

logger = logging.getLogger("EtherscanClient")


class EtherscanAPIError(Exception):
    """Base exception for Etherscan API errors."""
    pass


class ContractNotVerifiedError(EtherscanAPIError):
    """Raised when the requested contract source code is not verified on Etherscan."""
    pass


class EtherscanRateLimitError(EtherscanAPIError):
    """Raised when Etherscan rate limit is exceeded after retries."""
    pass


class EtherscanAuthError(EtherscanAPIError):
    """Raised on invalid API key errors."""
    pass


class EtherscanNetworkError(EtherscanAPIError):
    """Raised when network connectivity fails and no cached copy is available."""
    pass


SUPPORTED_CHAINS: Dict[str, Dict[str, Any]] = {
    "1": {
        "name": "Ethereum Mainnet",
        "symbol": "ETH",
        "chain_id": 1,
        "explorer": "https://etherscan.io",
        "blockscan_name": "ethereum",
        "v1_api": "https://api.etherscan.io/api",
    },
    "42161": {
        "name": "Arbitrum One",
        "symbol": "ETH",
        "chain_id": 42161,
        "explorer": "https://arbiscan.io",
        "blockscan_name": "arbitrum",
        "v1_api": "https://api.arbiscan.io/api",
    },
    "8453": {
        "name": "Base Mainnet",
        "symbol": "ETH",
        "chain_id": 8453,
        "explorer": "https://basescan.org",
        "blockscan_name": "base",
        "v1_api": "https://api.basescan.org/api",
    },
    "10": {
        "name": "OP Mainnet",
        "symbol": "ETH",
        "chain_id": 10,
        "explorer": "https://optimistic.etherscan.io",
        "blockscan_name": "optimism",
        "v1_api": "https://api-optimistic.etherscan.io/api",
    },
    "137": {
        "name": "Polygon Mainnet",
        "symbol": "POL",
        "chain_id": 137,
        "explorer": "https://polygonscan.com",
        "blockscan_name": "polygon",
        "v1_api": "https://api.polygonscan.com/api",
    },
    "56": {
        "name": "BNB Smart Chain",
        "symbol": "BNB",
        "chain_id": 56,
        "explorer": "https://bscscan.com",
        "blockscan_name": "bsc",
        "v1_api": "https://api.bscscan.com/api",
    },
    "11155111": {
        "name": "Sepolia Testnet",
        "symbol": "SepoliaETH",
        "chain_id": 11155111,
        "explorer": "https://sepolia.etherscan.io",
        "blockscan_name": "sepolia",
        "v1_api": "https://api-sepolia.etherscan.io/api",
    },
    "59144": {
        "name": "Linea Mainnet",
        "symbol": "ETH",
        "chain_id": 59144,
        "explorer": "https://lineascan.build",
        "blockscan_name": "linea",
        "v1_api": "https://api.lineascan.build/api",
    },
    "81457": {
        "name": "Blast Mainnet",
        "symbol": "ETH",
        "chain_id": 81457,
        "explorer": "https://blastscan.io",
        "blockscan_name": "blast",
        "v1_api": "https://api.blastscan.io/api",
    },
    "146": {
        "name": "Sonic Mainnet",
        "symbol": "S",
        "chain_id": 146,
        "explorer": "https://sonicscan.org",
        "blockscan_name": "sonic",
        "v1_api": "https://api.sonicscan.org/api",
    },
    "80094": {
        "name": "Berachain Mainnet",
        "symbol": "BERA",
        "chain_id": 80094,
        "explorer": "https://berascan.com",
        "blockscan_name": "berachain",
        "v1_api": "https://api.berascan.com/api",
    },
    "100": {
        "name": "Gnosis",
        "symbol": "xDAI",
        "chain_id": 100,
        "explorer": "https://gnosisscan.io",
        "blockscan_name": "gnosis",
        "v1_api": "https://api.gnosisscan.io/api",
    },
    "43114": {
        "name": "Avalanche C-Chain",
        "symbol": "AVAX",
        "chain_id": 43114,
        "explorer": "https://snowtrace.io",
        "blockscan_name": "avalanche",
        "v1_api": "https://api.snowtrace.io/api",
    },
    "250": {
        "name": "Fantom Opera",
        "symbol": "FTM",
        "chain_id": 250,
        "explorer": "https://ftmscan.com",
        "blockscan_name": "fantom",
        "v1_api": "https://api.ftmscan.com/api",
    },
    "534352": {
        "name": "Scroll",
        "symbol": "ETH",
        "chain_id": 534352,
        "explorer": "https://scrollscan.com",
        "blockscan_name": "scroll",
        "v1_api": "https://api.scrollscan.com/api",
    },
    "324": {
        "name": "ZKsync Era",
        "symbol": "ETH",
        "chain_id": 324,
        "explorer": "https://era.zksync.network",
        "blockscan_name": "zksync",
        "v1_api": "https://api-era.zksync.network/api",
    },
}

ADDRESS_REGEX = re.compile(r"^0[xX][a-fA-F0-9]{40}$")


@dataclass
class EtherscanContractResult:
    """Represents the fetched and unpacked contract source information."""
    address: str
    chain_id: int
    contract_name: str
    compiler_version: str
    optimization_used: bool
    runs: int
    constructor_arguments: str
    evm_version: str
    library_addresses: Dict[str, str] = field(default_factory=dict)
    is_multi_file: bool = False
    files: Dict[str, str] = field(default_factory=dict)  # relative file path -> content
    main_source_file: str = ""
    local_path: Optional[Path] = None
    raw_source: str = ""
    abi: Optional[str] = None
    is_proxy: bool = False
    implementation_address: Optional[str] = None


class EtherscanClient:
    """Universal Etherscan V2 Multichain Client supporting 12+ EVM chains."""

    SUPPORTED_CHAINS: Dict[str, Dict[str, Any]] = SUPPORTED_CHAINS

    def __init__(
        self,
        api_key: Optional[str] = None,
        cache_root: Optional[Union[str, Path]] = None,
        max_retries: int = 3,
        backoff_factor: float = 1.0,
    ):
        self.api_key = api_key or os.getenv("ETHERSCAN_API_KEY", "YourApiKeyToken")
        self.cache_root = Path(cache_root).resolve() if cache_root else Path("cache/contracts").resolve()
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    @classmethod
    def validate_address(cls, address: str) -> str:
        """Validates that address is a valid 42-character hex Ethereum address."""
        if not address or not isinstance(address, str):
            raise ValueError("Invalid 42-character Ethereum address format")
        addr = address.strip()
        if not ADDRESS_REGEX.match(addr):
            raise ValueError(f"Invalid 42-character Ethereum address format: '{address}'")
        return addr

    @classmethod
    def parse_target_url(cls, url_or_address: str, default_chain_id: int = 1) -> Tuple[str, int]:
        """
        Parses explorer URLs (e.g. https://basescan.org/address/0x... or https://vscode.blockscan.com/base/0x...)
        or raw 0x address into a tuple of (address, chain_id).
        """
        target_str = str(url_or_address).strip()
        detected_chain_id = default_chain_id

        # Search for 42-char address anywhere in string
        match = re.search(r"0[xX][a-fA-F0-9]{40}", target_str)
        if not match:
            raise ValueError(f"No valid 42-character Ethereum address found in: '{url_or_address}'")
        extracted_address = match.group(0)

        # Domain / blockscan detection
        target_lower = target_str.lower()
        parsed_url = urllib.parse.urlparse(target_str if "://" in target_str else f"https://{target_str}")
        target_netloc = parsed_url.netloc.lower()

        # Sort chains by descending length of explorer domain to prevent subdomain collisions (e.g. optimistic.etherscan.io vs etherscan.io)
        sorted_chains = sorted(
            cls.SUPPORTED_CHAINS.items(),
            key=lambda item: len(urllib.parse.urlparse(item[1].get("explorer", "")).netloc),
            reverse=True,
        )

        matched = False
        # 1. Exact netloc match check
        for cid_str, info in sorted_chains:
            exp_url = info.get("explorer", "").lower()
            exp_domain = urllib.parse.urlparse(exp_url).netloc.lower()
            if exp_domain and (target_netloc == exp_domain or target_netloc == f"www.{exp_domain}"):
                detected_chain_id = int(cid_str)
                matched = True
                break

        if not matched:
            # 2. Explorer domain substring (sorted descending length), blockscan alias, or explicit chain_id query parameter
            for cid_str, info in sorted_chains:
                b_name = info.get("blockscan_name", "")
                exp_url = info.get("explorer", "").lower()
                exp_domain = urllib.parse.urlparse(exp_url).netloc.lower()

                if exp_domain and exp_domain in target_lower:
                    detected_chain_id = int(cid_str)
                    matched = True
                    break
                if b_name and (f"/{b_name}/" in target_lower or f"/{b_name}scan" in target_lower):
                    detected_chain_id = int(cid_str)
                    matched = True
                    break
                if f"chainid={cid_str}" in target_lower or f"chain_id={cid_str}" in target_lower:
                    detected_chain_id = int(cid_str)
                    matched = True
                    break

        return extracted_address, detected_chain_id

    def get_chain_metadata(self, chain_id: int) -> Dict[str, Any]:
        """Returns metadata for the specified chain ID."""
        return self.SUPPORTED_CHAINS.get(
            str(chain_id),
            {
                "name": f"EVM Chain {chain_id}",
                "symbol": "ETH",
                "chain_id": chain_id,
                "explorer": "https://etherscan.io",
                "blockscan_name": "unknown",
                "v1_api": "https://api.etherscan.io/api",
            },
        )

    def unpack_source_json(
        self,
        source_code_raw: str,
        contract_name: str,
        target_dir: Path,
    ) -> Path:
        """
        Unpacks Etherscan Standard-JSON format ({{ ... }} or { ... }) into target_dir.
        If standard flat single file, writes {contract_name}.sol into target_dir.
        """
        target_dir.mkdir(parents=True, exist_ok=True)
        raw_trimmed = source_code_raw.strip()

        # Check for double-brace wrapping: {{ ... }}
        parsed_json = None
        if raw_trimmed.startswith("{{") and raw_trimmed.endswith("}}"):
            try:
                parsed_json = json.loads(raw_trimmed[1:-1])
            except Exception:
                pass
        elif raw_trimmed.startswith("{") and raw_trimmed.endswith("}"):
            try:
                parsed_json = json.loads(raw_trimmed)
            except Exception:
                pass

        if parsed_json and isinstance(parsed_json, dict) and "sources" in parsed_json:
            sources = parsed_json.get("sources", {})
            written_files = 0
            for rel_path, src_obj in sources.items():
                if not isinstance(src_obj, dict):
                    continue
                content = src_obj.get("content", "")
                
                # Sanitize rel_path against path traversal
                clean_parts = [p for p in Path(rel_path).parts if p not in ("..", "/", "\\")]
                if not clean_parts:
                    continue
                dest_file = target_dir.joinpath(*clean_parts)
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                dest_file.write_text(content, encoding="utf-8")
                written_files += 1

            if written_files > 0:
                return target_dir

        # Flat single source file fallback
        dest_file = target_dir / f"{contract_name}.sol"
        dest_file.write_text(source_code_raw, encoding="utf-8")
        return dest_file

    def _http_get_json(self, url: str) -> Dict[str, Any]:
        """Performs HTTP GET with rate-limit detection and exponential backoff retry."""
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": "EthAuditAgent/2.0 (Autonomous Smart Contract Auditor)",
                        "Accept": "application/json",
                    },
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    resp_bytes = resp.read()
                    data = json.loads(resp_bytes.decode("utf-8"))

                    # Check for Etherscan rate limit or error response in JSON body
                    status = str(data.get("status", ""))
                    result = data.get("result", "")
                    message = data.get("message", "")

                    if isinstance(result, str) and ("Max rate limit reached" in result or "rate limit" in result.lower()):
                        backoff = self.backoff_factor * (2 ** attempt)
                        logger.warning(f"Rate limit encountered on attempt {attempt + 1}. Backing off {backoff:.1f}s...")
                        time.sleep(backoff)
                        continue

                    if status == "0" and isinstance(result, str) and "Invalid API Key" in result:
                        raise EtherscanAuthError("Invalid Etherscan API key supplied.")

                    return data
            except EtherscanAuthError:
                raise
            except urllib.error.HTTPError as he:
                if he.code == 429:
                    backoff = self.backoff_factor * (2 ** attempt)
                    logger.warning(f"HTTP 429 Too Many Requests. Backing off {backoff:.1f}s...")
                    time.sleep(backoff)
                    last_exception = he
                    continue
                last_exception = he
            except Exception as e:
                last_exception = e
                backoff = self.backoff_factor * (2 ** attempt)
                time.sleep(backoff)

        raise EtherscanNetworkError(f"Etherscan request failed after {self.max_retries} attempts: {last_exception}")

    def fetch_contract(
        self,
        address: str,
        chain_id: int = 1,
        force_refresh: bool = False,
    ) -> EtherscanContractResult:
        """
        Fetches verified contract source code across 12+ EVM chains via Etherscan V2 Universal API.
        Unpacks multi-file structures and caches artifacts into cache_root/{chain_id}_{address}/.
        """
        valid_addr = self.validate_address(address)
        cache_dir = self.cache_root / f"{chain_id}_{valid_addr}"
        metadata_file = cache_dir / "metadata.json"

        # Check Cache Hit
        if not force_refresh and cache_dir.exists() and metadata_file.exists():
            try:
                meta = json.loads(metadata_file.read_text(encoding="utf-8"))
                files_dict = {}
                for sol_file in cache_dir.rglob("*.sol"):
                    rel_p = str(sol_file.relative_to(cache_dir))
                    files_dict[rel_p] = sol_file.read_text(encoding="utf-8")

                local_path = cache_dir if meta.get("is_multi_file") else (cache_dir / f"{meta.get('contract_name', 'Contract')}.sol")
                if not local_path.exists():
                    sol_candidates = list(cache_dir.glob("*.sol"))
                    local_path = sol_candidates[0] if sol_candidates else cache_dir

                return EtherscanContractResult(
                    address=valid_addr,
                    chain_id=chain_id,
                    contract_name=meta.get("contract_name", "CachedContract"),
                    compiler_version=meta.get("compiler_version", "^0.8.20"),
                    optimization_used=meta.get("optimization_used", False),
                    runs=meta.get("runs", 200),
                    constructor_arguments=meta.get("constructor_arguments", ""),
                    evm_version=meta.get("evm_version", "default"),
                    library_addresses=meta.get("library_addresses", {}),
                    is_multi_file=meta.get("is_multi_file", False),
                    files=files_dict,
                    main_source_file=meta.get("main_source_file", ""),
                    local_path=local_path,
                    raw_source=meta.get("raw_source", ""),
                    abi=meta.get("abi"),
                    is_proxy=meta.get("is_proxy", False),
                    implementation_address=meta.get("implementation_address"),
                )
            except Exception as e:
                logger.debug(f"Cache read failed for {valid_addr}, querying API anew: {e}")

        # Construct API endpoints: V2 Universal first, then chain V1 fallback
        chain_info = self.get_chain_metadata(chain_id)
        api_key_param = f"&apikey={self.api_key}" if self.api_key else ""
        url_v2 = (
            f"https://api.etherscan.io/v2/api?chainid={chain_id}"
            f"&module=contract&action=getsourcecode&address={valid_addr}{api_key_param}"
        )
        url_v1 = (
            f"{chain_info.get('v1_api', 'https://api.etherscan.io/api')}"
            f"?module=contract&action=getsourcecode&address={valid_addr}{api_key_param}"
        )

        response_data = None
        for endpoint in [url_v2, url_v1]:
            try:
                response_data = self._http_get_json(endpoint)
                if response_data.get("status") == "1" and response_data.get("result"):
                    break
            except EtherscanAuthError:
                raise
            except Exception as e:
                logger.debug(f"Endpoint {endpoint} error: {e}")
                continue

        if not response_data or not response_data.get("result"):
            # Check if contract is unverified
            if response_data and response_data.get("status") == "0":
                res_str = str(response_data.get("result", ""))
                if "not verified" in res_str.lower():
                    raise ContractNotVerifiedError(f"Contract {valid_addr} on chain {chain_id} is not verified on Etherscan.")
            # If network failed completely and cache dir exists with .sol
            existing_sols = list(cache_dir.glob("*.sol")) if cache_dir.exists() else []
            if existing_sols:
                return EtherscanContractResult(
                    address=valid_addr,
                    chain_id=chain_id,
                    contract_name=existing_sols[0].stem,
                    compiler_version="^0.8.20",
                    optimization_used=False,
                    runs=200,
                    constructor_arguments="",
                    evm_version="default",
                    local_path=existing_sols[0],
                    raw_source=existing_sols[0].read_text(encoding="utf-8"),
                )
            raise EtherscanAPIError(f"Unable to fetch contract source for {valid_addr} (Chain {chain_id})")

        result_items = response_data["result"]
        if not isinstance(result_items, list) or len(result_items) == 0:
            raise ContractNotVerifiedError(f"No source code entries returned for {valid_addr}.")

        item = result_items[0]
        raw_source = item.get("SourceCode", "")
        contract_name = item.get("ContractName", "VerifiedContract")
        compiler_version = item.get("CompilerVersion", "^0.8.20")
        optimization_used = bool(int(item.get("OptimizationUsed", "0") or "0"))
        runs = int(item.get("Runs", "200") or "200")
        constructor_args = item.get("ConstructorArguments", "")
        evm_version = item.get("EVMVersion", "default")
        abi = item.get("ABI")
        is_proxy = bool(int(item.get("Proxy", "0") or "0"))
        impl_addr = item.get("Implementation")

        if not raw_source or raw_source.strip() == "":
            raise ContractNotVerifiedError(f"Source code empty or unverified for {valid_addr} on chain {chain_id}.")

        # Unpack sources
        local_path = self.unpack_source_json(raw_source, contract_name, cache_dir)
        is_multi_file = local_path.is_dir()

        # Collect files dictionary
        files_dict = {}
        if is_multi_file:
            for sol_p in local_path.rglob("*.sol"):
                rel = str(sol_p.relative_to(local_path))
                files_dict[rel] = sol_p.read_text(encoding="utf-8")
        else:
            files_dict[f"{contract_name}.sol"] = raw_source

        # Save metadata.json
        meta_payload = {
            "address": valid_addr,
            "chain_id": chain_id,
            "chain_name": chain_info.get("name", "Unknown"),
            "contract_name": contract_name,
            "compiler_version": compiler_version,
            "optimization_used": optimization_used,
            "runs": runs,
            "constructor_arguments": constructor_args,
            "evm_version": evm_version,
            "is_multi_file": is_multi_file,
            "main_source_file": f"{contract_name}.sol",
            "abi": abi,
            "is_proxy": is_proxy,
            "implementation_address": impl_addr,
            "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        try:
            (cache_dir / "metadata.json").write_text(json.dumps(meta_payload, indent=2), encoding="utf-8")
        except Exception:
            pass

        return EtherscanContractResult(
            address=valid_addr,
            chain_id=chain_id,
            contract_name=contract_name,
            compiler_version=compiler_version,
            optimization_used=optimization_used,
            runs=runs,
            constructor_arguments=constructor_args,
            evm_version=evm_version,
            is_multi_file=is_multi_file,
            files=files_dict,
            main_source_file=f"{contract_name}.sol",
            local_path=local_path,
            raw_source=raw_source,
            abi=abi,
            is_proxy=is_proxy,
            implementation_address=impl_addr,
        )

    def fetch_contract_source(
        self,
        address: str,
        chain_id: int = 1,
        force_refresh: bool = False,
    ) -> Path:
        """
        Fetches verified Solidity source code and returns Path to directory or .sol file.
        Matches interface contract specified in PROJECT.md.
        """
        result = self.fetch_contract(address, chain_id=chain_id, force_refresh=force_refresh)
        return result.local_path

    def fetch_native_balance(
        self,
        address: str,
        chain_id: int = 1,
        eth_price_usd: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Queries native on-chain balance via Etherscan V2."""
        valid_addr = self.validate_address(address)
        chain_info = self.get_chain_metadata(chain_id)
        api_key_param = f"&apikey={self.api_key}" if self.api_key else ""

        url_v2 = (
            f"https://api.etherscan.io/v2/api?chainid={chain_id}"
            f"&module=account&action=balance&address={valid_addr}&tag=latest{api_key_param}"
        )
        url_v1 = (
            f"{chain_info.get('v1_api', 'https://api.etherscan.io/api')}"
            f"?module=account&action=balance&address={valid_addr}&tag=latest{api_key_param}"
        )

        current_eth_price = eth_price_usd or 2000.0

        for endpoint in [url_v2, url_v1]:
            try:
                data = self._http_get_json(endpoint)
                if data.get("status") == "1":
                    wei_val = int(data.get("result", "0"))
                    eth_val = round(wei_val / 1e18, 6)
                    usd_val = round(eth_val * current_eth_price, 2)
                    return {
                        "success": True,
                        "address": valid_addr,
                        "chain_id": chain_id,
                        "chain_name": chain_info["name"],
                        "symbol": chain_info.get("symbol", "ETH"),
                        "wei": str(wei_val),
                        "eth": eth_val,
                        "usd": usd_val,
                        "eth_price_usd": current_eth_price,
                        "source": f"Etherscan V2 API ({chain_info['name']})",
                    }
            except Exception:
                continue

        return {
            "success": False,
            "address": valid_addr,
            "chain_id": chain_id,
            "chain_name": chain_info["name"],
            "error": "Balance query timed out or API key required",
        }

    def fetch_balance(self, address: str, chain_id: int = 1) -> Dict[str, Any]:
        """Alias for fetch_native_balance."""
        return self.fetch_native_balance(address, chain_id)
