"""
Alert Dispatcher for Discord and Telegram Webhooks.
Dispatches high-impact vulnerability alerts (Composite Score >= 5000 / Confidence >= 80% / Critical & High severity).
"""
import os
import json
import logging
from typing import Optional, List
from ..core.context import AuditSession, Severity, FindingStatus, TriagedFinding

logger = logging.getLogger(__name__)


class WebhookNotifier:
    """Dispatches real-time vulnerability alerts to Discord and Telegram."""

    def __init__(
        self,
        discord_webhook_url: Optional[str] = None,
        telegram_bot_token: Optional[str] = None,
        telegram_chat_id: Optional[str] = None,
    ):
        self.discord_url = discord_webhook_url or os.getenv("DISCORD_WEBHOOK_URL")
        self.tg_token = telegram_bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.tg_chat_id = telegram_chat_id or os.getenv("TELEGRAM_CHAT_ID")

    def _qualifies_for_alert(self, f: TriagedFinding) -> bool:
        """Determines if finding meets threshold: Score >= 5000 & Conf >= 80% or Validated Critical/High."""
        if f.status == FindingStatus.REJECTED or f.final_severity == Severity.FALSE_POSITIVE:
            return False
        
        comp_score = getattr(f, "composite_score", 0)
        conf_score = getattr(f, "confidence_score", 0)
        
        # High composite score + confidence threshold
        if comp_score >= 5000 and conf_score >= 80:
            return True
        
        # Validated Critical or High findings
        if f.status == FindingStatus.VALIDATED and f.final_severity in (Severity.CRITICAL, Severity.HIGH):
            return True
        
        # General Critical/High with non-rejected status
        if f.final_severity in (Severity.CRITICAL, Severity.HIGH):
            return True
            
        return False

    def notify_audit_completed(self, session: AuditSession) -> bool:
        """Checks findings against alert thresholds and dispatches webhook notifications."""
        qualifying = [f for f in session.triaged_findings if self._qualifies_for_alert(f)]
        
        criticals = [f for f in qualifying if f.final_severity == Severity.CRITICAL]
        highs = [f for f in qualifying if f.final_severity != Severity.CRITICAL]

        if not criticals and not highs:
            logger.info("No Critical or High / high-score vulnerabilities found. Skipping instant alert.")
            return False

        success = True
        dispatched_any = False
        
        if self.discord_url:
            res_discord = self._send_discord_alert(session, criticals, highs)
            success = res_discord and success
            dispatched_any = True
            
        if self.tg_token and self.tg_chat_id:
            res_tg = self._send_telegram_alert(session, criticals, highs)
            success = res_tg and success
            dispatched_any = True

        return success if dispatched_any else False

    def _send_discord_alert(self, session: AuditSession, criticals: list, highs: list) -> bool:
        import urllib.request

        if not self.discord_url:
            return False

        fields = []
        for f in criticals[:3]:
            fix_text = f.recommended_mitigation or "Implement defensive guard."
            fix_preview = (fix_text[:120] + "...") if len(fix_text) > 120 else fix_text
            bounty_val = getattr(f, "bounty_estimate_usd", 0.0)
            bounty_str = f" (${bounty_val:,.0f})" if bounty_val > 0 else ""
            fields.append({
                "name": f"🚨 [CRITICAL] {f.title}{bounty_str}",
                "value": f"**Target:** `{f.contract_name}`\n**Vector:** {f.threat_vector}\n**Fix:** {fix_preview}",
                "inline": False
            })
            
        for f in highs[:3]:
            fix_text = f.recommended_mitigation or "Implement defensive guard."
            fix_preview = (fix_text[:120] + "...") if len(fix_text) > 120 else fix_text
            bounty_val = getattr(f, "bounty_estimate_usd", 0.0)
            bounty_str = f" (${bounty_val:,.0f})" if bounty_val > 0 else ""
            fields.append({
                "name": f"⚠️ [HIGH] {f.title}{bounty_str}",
                "value": f"**Target:** `{f.contract_name}`\n**Vector:** {f.threat_vector}\n**Fix:** {fix_preview}",
                "inline": False
            })

        payload = {
            "username": "EthAudit Bug Hunter",
            "embeds": [{
                "title": f"🛡️ Bounty Alert: High-Impact Findings in `{os.path.basename(session.target_file)}`",
                "description": f"Audited `{session.target_file}`. Found **{len(criticals)} Critical** and **{len(highs)} High** severity bugs.",
                "color": 15158332 if criticals else 15105570,
                "fields": fields,
                "footer": {"text": "EthAudit-Agent Multi-Agent Simulation"}
            }]
        }

        try:
            req = urllib.request.Request(
                self.discord_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "User-Agent": "EthAuditAgent/1.0"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status in (200, 204)
        except Exception as e:
            logger.warning(f"Failed to dispatch Discord webhook: {e}")
            return False

    def _send_telegram_alert(self, session: AuditSession, criticals: list, highs: list) -> bool:
        import urllib.request

        if not self.tg_token or not self.tg_chat_id:
            return False

        text_lines = [
            "🚨 *EthAudit Alert: High-Impact Findings*",
            f"📁 Target: `{os.path.basename(session.target_file)}`",
            f"📊 Critical: *{len(criticals)}* | High: *{len(highs)}*\n"
        ]

        for f in criticals[:2]:
            bounty_val = getattr(f, "bounty_estimate_usd", 0.0)
            bounty_str = f" | Est. Bounty: `${bounty_val:,.0f}`" if bounty_val > 0 else ""
            text_lines.append(f"🔴 *[CRITICAL]* {f.title}\n• Contract: `{f.contract_name}`\n• Vector: {f.threat_vector}{bounty_str}")

        for f in highs[:2]:
            bounty_val = getattr(f, "bounty_estimate_usd", 0.0)
            bounty_str = f" | Est. Bounty: `${bounty_val:,.0f}`" if bounty_val > 0 else ""
            text_lines.append(f"🟠 *[HIGH]* {f.title}\n• Contract: `{f.contract_name}`\n• Vector: {f.threat_vector}{bounty_str}")

        url = f"https://api.telegram.org/bot{self.tg_token}/sendMessage"
        payload = {
            "chat_id": self.tg_chat_id,
            "text": "\n\n".join(text_lines),
            "parse_mode": "Markdown"
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception as e:
            logger.warning(f"Failed to dispatch Telegram alert: {e}")
            return False
