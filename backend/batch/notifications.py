import os, httpx
from dotenv import load_dotenv

load_dotenv()
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID")
DISCORD_URL = os.getenv("DISCORD_WEBHOOK_URL")

async def send_telegram_alert(f):
    if not TG_TOKEN or TG_TOKEN in ("PUT_KEY_HERE", "PUT_GEMINI_KEY_HERE"):
        return {}
    msg = (
        f"🚨 ETH Hunter Alert: {f.get('repo')}\n"
        f"Confidence: {f.get('confidence')}%\n"
        f"Est. Bounty: ${f.get('bounty_estimate'):,}\n"
        f"Score: {f.get('score')}\n"
        f"Goal ($2088): {f.get('leaderboard', {}).get('goal_progress_percent', 0)}%"
    )
    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(
                f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                json={"chat_id": TG_CHAT, "text": msg}
            )
            return r.json()
        except Exception as e:
            return {"error": str(e)}

async def send_discord_alert(f):
    if not DISCORD_URL:
        return {}
    async with httpx.AsyncClient() as client:
        try:
            content = f"🚨 **ETH Hunter [Google AI]**: Finding in `{f.get('repo')}` (Score: {f.get('score')}, Confidence: {f.get('confidence')}%, Est: ${f.get('bounty_estimate'):,})"
            r = await client.post(DISCORD_URL, json={"content": content})
            return {"status": r.status_code}
        except Exception as e:
            return {"error": str(e)}

async def alert_if_high_value(f):
    if f.get('confidence', 0) >= 80 or f.get('score', 0) >= 4000:
        tg = await send_telegram_alert(f)
        dc = await send_discord_alert(f)
        return {"alerted": True, "telegram": tg, "discord": dc}
    return {"alerted": False}
