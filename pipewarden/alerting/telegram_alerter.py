from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import requests

from pipewarden.alerting.base import AlertContext, BaseAlerter


@dataclass
class TelegramAlerter(BaseAlerter):
    """Send pipeline alerts to a Telegram chat via the Bot API."""

    bot_token: str = ""
    chat_id: str = ""
    base_url: str = "https://api.telegram.org"
    timeout: int = 10
    alert_on_healthy: bool = False
    _session: Optional[requests.Session] = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.bot_token:
            raise ValueError("TelegramAlerter requires a 'bot_token'.")
        if not self.chat_id:
            raise ValueError("TelegramAlerter requires a 'chat_id'.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _session_or_default(self) -> requests.Session:
        return self._session or requests.Session()

    def _build_text(self, ctx: AlertContext) -> str:
        status = "\u2705 HEALTHY" if ctx.is_healthy() else "\u274c UNHEALTHY"
        lines = [
            f"*PipeWarden — {status}*",
            f"Pipeline: `{ctx.pipeline_name}`",
            "",
        ]
        if ctx.failures:
            lines.append("*Failed checks:*")
            for r in ctx.failures:
                lines.append(f"  \u2022 {r.check_name}: {r.message}")
            lines.append("")
        if ctx.warnings:
            lines.append("*Warnings:*")
            for r in ctx.warnings:
                lines.append(f"  \u2022 {r.check_name}: {r.message}")
        return "\n".join(lines).strip()

    def _build_payload(self, ctx: AlertContext) -> dict:
        return {
            "chat_id": self.chat_id,
            "text": self._build_text(ctx),
            "parse_mode": "Markdown",
        }

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def send(self, ctx: AlertContext) -> None:
        if ctx.is_healthy() and not self.alert_on_healthy:
            return

        url = f"{self.base_url}/bot{self.bot_token}/sendMessage"
        payload = self._build_payload(ctx)
        session = self._session_or_default()
        response = session.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()
