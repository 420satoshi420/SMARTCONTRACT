"""
Economic & MEV Feasibility Evaluator for Ethereum Smart Contract Vulnerabilities.
Implements skin-in-the-game profitability gating, flashloan fee modeling (Balancer 0 bps, Aave 9 bps, Uniswap 30 bps),
spot gas deductions, TVL-scaled dynamic caps, live price fetching, and composite triage scoring.

v2.0: Added live ETH price fetching and on-chain balance queries.
"""

import os
import json
import logging
import urllib.request
import urllib.error
import ssl
import time
from typing import Dict, Any, Optional, List
from pathlib import Path
from .context import Severity

logger = logging.getLogger(__name__)

# Ensure .env is loaded if present
try:
    from dotenv import load_dotenv
    _env_backend = Path(__file__).resolve().parents[1] / ".env"
    _env_root = Path(__file__).resolve().parents[2] / ".env"
    if _env_backend.exists():
        load_dotenv(_env_backend)
    elif _env_root.exists():
        load_dotenv(_env_root)
    else:
        load_dotenv()
except ImportError:
    # Manual fallback parser if python-dotenv is not installed
    for p in [Path(__file__).resolve().parents[1] / ".env", Path(__file__).resolve().parents[2] / ".env"]:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k, v = k.strip(), v.strip().strip("'\"")
                            if k and k not in os.environ:
                                os.environ[k] = v
            except Exception:
                pass

# Cache for live price data (avoid hitting API every call)
_price_cache = {"eth_usd": 1920.0, "gas_gwei": 15.0, "fetched_at": 0, "tokens": {}}
_PRICE_CACHE_TTL = 300  # 5 minutes


class EconomicEvaluator:
    """Evaluates the atomic economic feasibility of flashloan & MEV exploit hypotheses."""

    # Protocol-specific flashloan fee baselines (in basis points: 1 bps = 0.01%)
    FLASHLOAN_FEES_BPS = {
        "balancer": 0,    # Balancer V2 / V3: 0 bps (0.00% fee)
        "aave": 9,        # Aave V3: 9 bps (0.09% fee)
        "uniswap": 30,    # Uniswap V3: 30 bps (0.30% fee)
    }

    DEFAULT_FLASHLOAN_FEE_BPS = 9  # Aave V3 default: 9 bps
    ESTIMATED_EXPLOIT_GAS = 350_000  # Standard multi-hop exploit execution gas

    # Severity baseline bounty valuations (Immunefi V2.2 standard benchmarks)
    SEVERITY_BENCHMARKS = {
        Severity.CRITICAL: 50_000.0,      # Benchmark $25,000 - $1,000,000+ (default $50k)
        Severity.HIGH: 15_000.0,          # Benchmark $10,000 - $50,000 (default $15k)
        Severity.MEDIUM: 3_000.0,         # Benchmark $2,500 - $10,000 (default $3k)
        Severity.LOW: 500.0,              # Benchmark $0 - $1,000 (default $500)
        Severity.INFORMATIONAL: 0.0,
        Severity.FALSE_POSITIVE: 0.0,
    }

    @classmethod
    def fetch_live_eth_price(cls) -> Dict[str, float]:
        """
        Fetches live ETH/USD price.
        Prioritizes CoinMarketCap Pro API (if CMC_PRO_API_KEY / COINMARKETCAP_API_KEY set),
        falls back to CoinGecko, and then to cached/default value ($1920).
        """
        global _price_cache
        now = time.time()

        # Return cached if fresh enough
        if now - _price_cache["fetched_at"] < _PRICE_CACHE_TTL and _price_cache.get("eth_usd", 0) > 0:
            return {"eth_usd": _price_cache["eth_usd"], "gas_gwei": _price_cache["gas_gwei"]}

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        # 1. Try CoinMarketCap API first if key is available
        cmc_key = os.getenv("COINMARKETCAP_API_KEY") or os.getenv("CMC_PRO_API_KEY") or os.getenv("CMC_API_KEY")
        if cmc_key and cmc_key not in ("DEMO_KEY", "YOUR_KEY_HERE"):
            try:
                cmc_url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest?symbol=ETH"
                req = urllib.request.Request(
                    cmc_url,
                    headers={
                        "Accept": "application/json",
                        "X-CMC_PRO_API_KEY": cmc_key.strip()
                    }
                )
                with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                    data = json.loads(resp.read().decode())
                    eth_price = float(data["data"]["ETH"]["quote"]["USD"]["price"])
                    _price_cache["eth_usd"] = eth_price
                    _price_cache["fetched_at"] = now
                    logger.info(f"Live ETH price from CoinMarketCap: ${eth_price:,.2f}")
                    return {"eth_usd": eth_price, "gas_gwei": _price_cache["gas_gwei"]}
            except Exception as e:
                logger.debug(f"CoinMarketCap price fetch failed, trying fallback: {e}")

        # 2. Fallback to CoinGecko (free tier)
        try:
            url = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                data = json.loads(resp.read().decode())
                eth_price = float(data.get("ethereum", {}).get("usd", 1920.0))
                _price_cache["eth_usd"] = eth_price
                _price_cache["fetched_at"] = now
                logger.info(f"Live ETH price from CoinGecko: ${eth_price:,.2f}")
                return {"eth_usd": eth_price, "gas_gwei": _price_cache["gas_gwei"]}
        except Exception as e:
            logger.debug(f"CoinGecko price fetch failed (using cached): {e}")
            return {"eth_usd": _price_cache["eth_usd"], "gas_gwei": _price_cache["gas_gwei"]}

    @classmethod
    def fetch_token_prices(cls, symbols: List[str]) -> Dict[str, float]:
        """
        Fetches live USD prices for a list of token symbols (e.g. ['ETH', 'UNI', 'AAVE', 'LINK']).
        Uses CoinMarketCap Pro API with batch query support.
        """
        if not symbols:
            return {}

        symbols_clean = [s.upper().strip() for s in symbols if s.strip()]
        cmc_key = os.getenv("COINMARKETCAP_API_KEY") or os.getenv("CMC_PRO_API_KEY") or os.getenv("CMC_API_KEY")
        if not cmc_key or cmc_key in ("DEMO_KEY", "YOUR_KEY_HERE"):
            return {s: 0.0 for s in symbols_clean}

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        try:
            symbols_str = ",".join(symbols_clean)
            url = f"https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest?symbol={symbols_str}"
            req = urllib.request.Request(
                url,
                headers={
                    "Accept": "application/json",
                    "X-CMC_PRO_API_KEY": cmc_key.strip()
                }
            )
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                data = json.loads(resp.read().decode())
                results = {}
                for sym in symbols_clean:
                    coin_data = data.get("data", {}).get(sym)
                    if coin_data:
                        results[sym] = float(coin_data["quote"]["USD"]["price"])
                return results
        except Exception as e:
            logger.debug(f"Failed to fetch batch token prices from CoinMarketCap: {e}")
            return {}

    @classmethod
    def fetch_contract_balance(cls, address: str, chain_id: int = 1) -> float:

        """
        Fetches ETH balance of a contract address via Etherscan API.
        Returns balance in ETH. Returns 0.0 on failure.
        """
        api_key = os.getenv("ETHERSCAN_API_KEY", "")
        if not api_key or api_key == "DEMO_KEY":
            return 0.0

        try:
            url = (
                f"https://api.etherscan.io/v2/api"
                f"?chainid={chain_id}"
                f"&module=account&action=balance"
                f"&address={address}&tag=latest"
                f"&apikey={api_key}"
            )
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                data = json.loads(resp.read().decode())
                if data.get("status") == "1":
                    balance_wei = int(data.get("result", "0"))
                    return balance_wei / 1e18
        except Exception as e:
            logger.debug(f"Balance fetch failed for {address}: {e}")

        return 0.0

    @classmethod
    def get_provider_fee_bps(cls, provider: Optional[str] = None) -> int:
        """Returns the fee in basis points for a given flashloan provider name."""
        if not provider:
            return cls.DEFAULT_FLASHLOAN_FEE_BPS
        clean_name = provider.lower().strip()
        return cls.FLASHLOAN_FEES_BPS.get(clean_name, cls.DEFAULT_FLASHLOAN_FEE_BPS)

    @classmethod
    def evaluate_exploit_profitability(
        cls,
        gross_extractable_usd: float,
        gas_price_gwei: float = 20.0,
        eth_price_usd: float = 0.0,
        required_capital_usd: float = 0.0,
        protocol_tvl_usd: Optional[float] = None,
        flashloan_fee_bps: Optional[int] = None,
        flashloan_provider: Optional[str] = None,
        estimated_gas_units: int = 350_000,
        use_live_price: bool = True,
    ) -> Dict[str, Any]:
        """
        Calculates net extractable profit after flashloan fees and mainnet gas costs.
        Applies dynamic TVL caps (max 10% TVL) and skin-in-the-game gating (net profit >= $1,000, ROI >= 2.0x).

        v2: Uses live ETH price if available and use_live_price=True.
        """
        # Fetch live price if not provided
        if eth_price_usd <= 0 and use_live_price:
            live = cls.fetch_live_eth_price()
            eth_price_usd = live["eth_usd"]
            gas_price_gwei = live.get("gas_gwei", gas_price_gwei)
        elif eth_price_usd <= 0:
            eth_price_usd = 1920.0

        # 1. TVL Dynamic Capping (Maximum 10% of total pool TVL)
        effective_gross_usd = max(0.0, float(gross_extractable_usd))
        if protocol_tvl_usd and protocol_tvl_usd > 0:
            max_tvl_drain = protocol_tvl_usd * 0.10
            effective_gross_usd = min(effective_gross_usd, max_tvl_drain)

        # 2. Flashloan Fee Calculation
        if flashloan_fee_bps is not None:
            fee_bps = int(flashloan_fee_bps)
        elif flashloan_provider:
            fee_bps = cls.get_provider_fee_bps(flashloan_provider)
        else:
            fee_bps = cls.DEFAULT_FLASHLOAN_FEE_BPS

        flashloan_fee_usd = 0.0
        if required_capital_usd > 0:
            flashloan_fee_usd = round(required_capital_usd * (fee_bps / 10_000.0), 2)

        # 3. Gas Cost Spot Calculation
        gas_units = max(0, estimated_gas_units)
        gas_eth = (gas_units * max(0.0, gas_price_gwei)) / 1e9
        gas_cost_usd = round(gas_eth * max(0.0, eth_price_usd), 2)

        # 4. Total Costs, Net Profit & ROI Gating
        total_costs_usd = round(flashloan_fee_usd + gas_cost_usd, 2)
        net_profit_usd = round(effective_gross_usd - total_costs_usd, 2)

        is_economically_feasible = net_profit_usd >= 1000.0
        if total_costs_usd > 0:
            roi_multiplier = round(net_profit_usd / total_costs_usd, 2)
        else:
            roi_multiplier = 999.0 if net_profit_usd > 0 else 0.0

        meets_skin_in_game_threshold = is_economically_feasible and roi_multiplier >= 2.0

        return {
            "gross_extractable_usd": effective_gross_usd,
            "required_capital_usd": required_capital_usd,
            "flashloan_fee_bps": fee_bps,
            "flashloan_fee_usd": flashloan_fee_usd,
            "gas_units": gas_units,
            "gas_cost_usd": gas_cost_usd,
            "total_costs_usd": total_costs_usd,
            "net_profit_usd": net_profit_usd,
            "is_economically_feasible": is_economically_feasible,
            "roi_multiplier": roi_multiplier,
            "meets_skin_in_game_threshold": meets_skin_in_game_threshold,
            "eth_price_usd": eth_price_usd,
        }

    @classmethod
    def calculate_bounty_estimate(
        cls,
        severity: Severity,
        protocol_tvl_usd: Optional[float] = None,
    ) -> float:
        """
        Calculates estimated bug bounty valuation in USD according to Immunefi V2.2 benchmarks
        and TVL-scaled dynamic caps (Rule 2).
        """
        baseline = cls.SEVERITY_BENCHMARKS.get(severity, 0.0)
        if not protocol_tvl_usd or protocol_tvl_usd <= 0:
            return baseline

        if severity == Severity.CRITICAL:
            # Up to 10% of TVL
            return round(min(baseline, 0.10 * protocol_tvl_usd), 2)
        elif severity == Severity.HIGH:
            # Up to 5% of TVL
            return round(min(baseline, 0.05 * protocol_tvl_usd), 2)
        else:
            return baseline

    @classmethod
    def calculate_composite_score(
        cls,
        confidence_percent: int,
        bounty_estimate_usd: float,
    ) -> int:
        """
        Calculates Composite Triage Score = (Confidence % / 100) * Estimated Bounty (USD).
        Used for prioritization and automated alert gating (Score >= 5,000, Confidence >= 80%).
        """
        conf_clamped = max(0, min(100, confidence_percent))
        bounty_clamped = max(0.0, float(bounty_estimate_usd))
        return int(round((conf_clamped / 100.0) * bounty_clamped))
