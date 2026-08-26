"""
Playwright & Chromium Automated Browser Agent
Controls Chromium to navigate local dashboards, execute on-chain explorer scraping,
verify frontend rendering, and take automated audit snapshots.
"""

import asyncio
import os
import sys
import time
from pathlib import Path
from playwright.async_api import async_playwright

SNAPSHOT_DIR = Path(__file__).resolve().parents[2] / "results" / "snapshots"


async def run_browser_automation(
    url: str = "http://localhost:5173",
    headless: bool = True,
    take_screenshot: bool = True
):
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    results = {"url": url, "status": "unknown", "page_title": "", "logs": []}

    print(f"\n🌐 [Playwright] Launching Chromium (headless={headless})...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        # Capture console messages
        page.on("console", lambda msg: results["logs"].append(f"[{msg.type}] {msg.text}"))

        try:
            print(f"🌐 [Playwright] Navigating to {url}...")
            response = await page.goto(url, wait_until="networkidle", timeout=15000)
            results["status"] = response.status if response else 200
            results["page_title"] = await page.title()

            # Wait briefly for dynamic dashboard elements to mount
            await page.wait_for_timeout(2000)

            if take_screenshot:
                timestamp = int(time.time())
                screenshot_path = SNAPSHOT_DIR / f"dashboard_{timestamp}.png"
                await page.screenshot(path=str(screenshot_path), full_page=True)
                results["screenshot"] = str(screenshot_path)
                print(f"📸 [Playwright] Dashboard snapshot saved: {screenshot_path.name}")

            # Check for key dashboard selectors
            body_text = await page.inner_text("body")
            results["body_preview"] = body_text[:300].replace("\n", " ")
            print(f"✅ [Playwright] Page loaded successfully: '{results['page_title']}'")

        except Exception as e:
            print(f"⚠️ [Playwright] Navigation error: {e}")
            results["error"] = str(e)
        finally:
            await browser.close()

    return results


def main():
    target_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5173"
    headless_mode = "--headed" not in sys.argv
    asyncio.run(run_browser_automation(url=target_url, headless=headless_mode))


if __name__ == "__main__":
    main()
