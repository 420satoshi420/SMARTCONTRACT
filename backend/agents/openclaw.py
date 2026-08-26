"""
OpenClaw Agent: Automated Smart Contract Clawing, Multi-Chain Source Extractor & On-Chain AST Ingestion Agent.
"""

import json
import logging
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

CHAIN_ID_MAP = {
    "ethereum": 1,
    "mainnet": 1,
    "arbitrum": 42161,
    "optimism": 10,
    "base": 8453,
    "polygon": 137,
    "bsc": 56,
    "sepolia": 11155111,
}


class OpenClawAgent:
    """
    OpenClaw Agent crawls EVM on-chain state, decompresses multi-source verified contracts,
    fetches raw bytecode, and formats smart contract targets directly for the Eth-Hunter debater pipeline.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = (
            api_key
            or os.getenv("ETHERSCAN_API_KEY")
            or "DEMO_KEY"
        )
        self.base_url = "https://api.etherscan.io/v2/api"

    def claw_contract(
        self,
        address: str,
        chain: str = "ethereum",
        output_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Claws smart contract verified source code, ABI, and compiler metadata
        from Etherscan v2 endpoint for any EVM chain.
        """
        chain_id = (
            CHAIN_ID_MAP.get(chain.lower(), int(chain))
            if str(chain).isdigit() or chain.lower() in CHAIN_ID_MAP
            else 1
        )
        
        # Clean address
        addr_match = re.search(r"0x[a-fA-F0-9]{40}", address)
        if not addr_match:
            raise ValueError(f"Invalid Ethereum address: {address}")
        target_addr = addr_match.group(0)

        params = {
            "chainid": chain_id,
            "module": "contract",
            "action": "getsourcecode",
            "address": target_addr,
            "apikey": self.api_key,
        }

        query_str = urllib.parse.urlencode(params)
        req_url = f"{self.base_url}?{query_str}"
        req = urllib.request.Request(req_url, headers={"User-Agent": "OpenClaw/1.0-Web3Agent"})

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            logger.error(f"OpenClaw clawing request failed: {e}")
            return {
                "success": False,
                "address": target_addr,
                "chain_id": chain_id,
                "error": str(e),
            }

        if data.get("status") != "1" or not data.get("result"):
            return {
                "success": False,
                "address": target_addr,
                "chain_id": chain_id,
                "message": data.get("message", "Contract not verified or unknown"),
                "result": data.get("result"),
            }

        item = data["result"][0]
        contract_name = item.get("ContractName", "UnknownContract")
        raw_source = item.get("SourceCode", "")
        compiler_version = item.get("CompilerVersion", "")
        optimization_used = item.get("OptimizationUsed", "0")
        runs = item.get("Runs", "200")
        abi = item.get("ABI", "")

        extracted_sources = {}
        # Multi-file Standard JSON format handling
        if raw_source.startswith("{{") and raw_source.endswith("}}"):
            clean_json = raw_source[1:-1]
            try:
                parsed = json.loads(clean_json)
                sources = parsed.get("sources", {})
                for path, content in sources.items():
                    extracted_sources[path] = content.get("content", "")
            except Exception:
                extracted_sources[f"{contract_name}.sol"] = raw_source
        elif raw_source.startswith("{") and raw_source.endswith("}"):
            try:
                parsed = json.loads(raw_source)
                for path, content in parsed.items():
                    if isinstance(content, dict):
                        extracted_sources[path] = content.get("content", "")
                    else:
                        extracted_sources[path] = str(content)
            except Exception:
                extracted_sources[f"{contract_name}.sol"] = raw_source
        else:
            extracted_sources[f"{contract_name}.sol"] = raw_source

        # Write to output directory if specified
        saved_files = []
        if output_dir:
            out_path = Path(output_dir)
            out_path.mkdir(parents=True, exist_ok=True)
            for filename, src in extracted_sources.items():
                safe_name = filename.split("/")[-1]
                target_file = out_path / safe_name
                with open(target_file, "w", encoding="utf-8") as f:
                    f.write(src)
                saved_files.append(str(target_file))

        return {
            "success": True,
            "address": target_addr,
            "chain_id": chain_id,
            "contract_name": contract_name,
            "compiler_version": compiler_version,
            "optimization_used": optimization_used,
            "runs": runs,
            "files_count": len(extracted_sources),
            "sources": extracted_sources,
            "saved_files": saved_files,
            "has_abi": bool(abi and abi != "Contract source code not verified"),
        }

    async def crawl_url_playwright(self, url: str) -> Dict[str, Any]:
        """
        Crawls a dynamic web page, bounty program brief (e.g. Immunefi/Code4rena),
        or DeFi app frontend using Playwright browser automation with httpx fallback.
        """
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url, timeout=20000, wait_until="domcontentloaded")
                title = await page.title()
                content = await page.content()
                
                # Extract text content
                text = await page.evaluate("() => document.body.innerText")
                await browser.close()
                return {
                    "success": True,
                    "engine": "Playwright Chromium",
                    "url": url,
                    "title": title,
                    "text_length": len(text),
                    "summary": text[:500] if text else "",
                    "html_length": len(content)
                }
        except Exception as e:
            # Fallback to fast httpx async
            try:
                import httpx
                async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                    resp = await client.get(url, headers={"User-Agent": "EthHunter-OpenClaw/1.0"})
                    return {
                        "success": True,
                        "engine": "HTTPX Fast Crawler",
                        "url": url,
                        "title": url,
                        "text_length": len(resp.text),
                        "summary": resp.text[:500],
                        "html_length": len(resp.content)
                    }
            except Exception as e2:
                return {
                    "success": False,
                    "engine": "Failed",
                    "url": url,
                    "error": f"Playwright error: {e} | HTTPX error: {e2}"
                }
