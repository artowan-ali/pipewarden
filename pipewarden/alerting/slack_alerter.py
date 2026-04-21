from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass, field
from typing import List, Optional

from pipewarden.alerting.base import BaseAlerter, AlertContext
from pipewarden.checks.base import CheckStatus


@dataclass
class SlackAlerter(BaseAlerter):
    """Send pipeline health alerts to a Slack channel via incoming webhook."""

    webhook_url: str = ""
    channel: Optional[str] = None
    username: str = "PipeWarden"
    icon_emoji: str = ":pipe:"
    notify_on_warn: bool = True
    timeout: int = 10

    def __post_init__(self) -> None:
        if not self.webhook_url:
            raise ValueError("SlackAlerter requires a non-empty webhook_url")

    def _build_text(self, context: AlertContext) -> str:
        if context.is_healthy():
            header = ":white_check_mark: *PipeWarden — Pipeline Healthy*"
        else:
            header = ":red_circle: *PipeWarden — Pipeline Unhealthy*"

        lines: List[str] = [header, ""]

        for result in context.failed_results:
            lines.append(f"  :x: `{result.check_name}` — {result.details}")

        if self.notify_on_warn:
            for result in context.warned_results:
                lines.append(f"  :warning: `{result.check_name}` — {result.details}")

        passed_count = len(context.passed_results)
        total = len(context.all_results)
        lines.append(f"\n{passed_count}/{total} checks passed.")

        return "\n".join(lines)

    def _build_payload(self, context: AlertContext) -> dict:
        payload: dict = {"text": self._build_text(context)}
        if self.channel:
            payload["channel"] = self.channel
        payload["username"] = self.username
        payload["icon_emoji"] = self.icon_emoji
        return payload

    def send(self, context: AlertContext) -> None:
        if context.is_healthy() and not self.notify_on_warn:
            return
        if context.is_healthy() and self.notify_on_warn and not context.warned_results:
            return

        payload = self._build_payload(context)
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            if resp.status not in (200, 204):
                raise RuntimeError(
                    f"Slack webhook returned unexpected status {resp.status}"
                )
