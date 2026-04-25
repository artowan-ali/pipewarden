from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import requests

from pipewarden.alerting.base import AlertContext, BaseAlerter


@dataclass
class GoogleChatAlerter(BaseAlerter):
    """Send pipeline health alerts to a Google Chat webhook."""

    webhook_url: str = ""
    timeout: int = 10
    only_on_failure: bool = False
    session: Optional[requests.Session] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not self.webhook_url:
            raise ValueError("GoogleChatAlerter requires a 'webhook_url'.")

    def _session_or_default(self) -> requests.Session:
        return self.session if self.session is not None else requests.Session()

    def _status_emoji(self, context: AlertContext) -> str:
        return "\u2705" if context.is_healthy() else "\u274c"

    def _build_payload(self, context: AlertContext) -> dict:
        emoji = self._status_emoji(context)
        status_label = "HEALTHY" if context.is_healthy() else "UNHEALTHY"
        lines = [
            f"{emoji} *Pipeline: {context.pipeline_name}* — {status_label}",
            f"Ran {context.total} check(s): "
            f"{context.passed_count} passed, "
            f"{context.warned_count} warned, "
            f"{context.failed_count} failed.",
        ]
        for result in context.failures:
            lines.append(f"  \u2022 FAIL `{result.check_name}`: {result.detail}")
        for result in context.warnings:
            lines.append(f"  \u2022 WARN `{result.check_name}`: {result.detail}")
        return {"text": "\n".join(lines)}

    def send(self, context: AlertContext) -> None:
        if self.only_on_failure and context.is_healthy():
            return
        payload = self._build_payload(context)
        session = self._session_or_default()
        response = session.post(self.webhook_url, json=payload, timeout=self.timeout)
        response.raise_for_status()
