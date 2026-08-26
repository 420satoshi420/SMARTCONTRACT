#!/usr/bin/env python3
"""
Headless Browser and Task Automation Worker.
Supports Playwright when installed, with resilient urllib fallback for automated monitoring.
"""
import sys
import json
import logging
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("BrowserAutomation")


def load_rules():
    rules_file = Path(__file__).resolve().parent.parent / "config" / "rules.json"
    if rules_file.exists():
        try:
            with open(rules_file, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"browser_rules": {"timeout_ms": 30000}}


async def run_playwright_task(url: str = "https://immunefi.com/explore/"):
    from playwright.async_api import async_playwright
    rules = load_rules()
    b_rules = rules.get("browser_rules", {})
    timeout = b_rules.get("timeout_ms", 30000)

    logger.info(f"Launching Playwright Chromium for target: {url}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=b_rules.get("headless", True))
        context = await browser.new_context(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)")
        page = await context.new_page()

        try:
            await page.goto(url, timeout=timeout)
            title = await page.title()
            logger.info(f"Page loaded: {title}")
        except Exception as e:
            logger.warning(f"Playwright navigation warning: {e}")
        finally:
            await browser.close()


def run_fallback_task(url: str = "https://api.github.com/orgs/code-423n4/repos"):
    import urllib.request
    logger.info(f"Running lightweight HTTP monitor against: {url}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "EthAudit-Agent/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read().decode("utf-8")
            logger.info(f"Successfully fetched {len(data)} bytes from {url}")
    except Exception as e:
        logger.warning(f"HTTP monitor warning: {e}")


def main():
    target_url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    try:
        import asyncio
        import playwright
        asyncio.run(run_playwright_task(target_url))
    except ImportError:
        logger.info("Playwright not installed in current environment. Using lightweight HTTP automation worker.")
        run_fallback_task()


if __name__ == "__main__":
    main()
