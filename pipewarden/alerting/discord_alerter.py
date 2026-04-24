from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional

import urllib.request
import urllib.error

from pipewarden.alerting.base import BaseAlerter, AlertContext


@dataclass
class DiscordAlerter(BaseAlerter):
    """Send pipeline alerts to a Discord channel via an incoming webhook."""

    webhook_url: Optional[str] = None
    username: str = "PipeWarden"
    avatar_url: Optional[str] = None
    # Only fire when the pipeline is unhealthy
    only_on_failure: bool = True

    def __post_init__(self) -> None:
        if not self.webhook_url:
            raise ValueError("DiscordAlerter requires a 'webhook_url'.")

    def _status_emoji(self, context: AlertContext) -> str:
        if context.is_healthy():
            return "✅"
        failed = len(context.failed)
        warned = len(context.warned)
        if failed:
            return "🔴"
        if warned:
            return "🟡"
        return "✅"

    def _build_payload(self, context: AlertContext) -> dict:
        emoji = self._status_emoji(context)
        status_label = "HEALTHY" if context.is_healthy() else "UNHEALTHY"
        lines = [
            f"{emoji} **PipeWarden Pipeline Alert — {status_label}**",
            f"Pipeline: `{context.pipeline_name}`",
        ]

        if context.failed:
            lines.append("\n**Failed checks:**")
            for r in context.failed:
                lines.append(f"  • `{r.check_name}` — {r.details}")

        if context.warned:
            lines.append("\n**Warnings:**")
            for r in context.warned:
                lines.append(f"  • `{r.check_name}` — {r.details}")

        payload: dict = {"content": "\n".join(lines), "username": self.username}
        if self.avatar_url:
            payload["avatar_url"] = self.avatar_url
        return payload

    def send(self, context: AlertContext) -> None:
        if self.only_on_failure and context.is_healthy():
            return

        payload = self._build_payload(context)
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req) as resp:
                if resp.status not in (200, 204):
                    raise RuntimeError(
                        f"Discord webhook returned unexpected status {resp.status}"
                    )
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Discord webhook request failed: {exc}") from exc
