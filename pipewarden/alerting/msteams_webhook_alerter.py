"""Microsoft Teams alerter via Incoming Webhook (Adaptive Cards)."""
from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass, field
from typing import Optional

from pipewarden.alerting.base import AlertContext, BaseAlerter


@dataclass
class MSTeamsWebhookAlerter(BaseAlerter):
    """Send pipeline alerts to a Microsoft Teams channel via Incoming Webhook."""

    webhook_url: Optional[str] = field(default=None)
    pipeline_name: str = field(default="ETL Pipeline")
    mention_on_failure: bool = field(default=False)

    def __post_init__(self) -> None:
        if not self.webhook_url:
            raise ValueError("MSTeamsWebhookAlerter requires 'webhook_url'.")

    def _build_payload(self, context: AlertContext) -> dict:
        status_label = "✅ Healthy" if context.is_healthy() else "❌ Unhealthy"
        color = "Good" if context.is_healthy() else "Attention"

        facts = [
            {"title": "Pipeline", "value": self.pipeline_name},
            {"title": "Status", "value": status_label},
            {"title": "Total Checks", "value": str(len(context.results))},
            {"title": "Failed", "value": str(len(context.failures))},
            {"title": "Warnings", "value": str(len(context.warnings))},
        ]

        if context.failures:
            failed_names = ", ".join(r.check_name for r in context.failures)
            facts.append({"title": "Failed Checks", "value": failed_names})

        return {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "themeColor": "00FF00" if context.is_healthy() else "FF0000",
            "summary": f"{self.pipeline_name} — {status_label}",
            "sections": [
                {
                    "activityTitle": f"**{self.pipeline_name}** pipeline report",
                    "activitySubtitle": status_label,
                    "facts": facts,
                    "markdown": True,
                }
            ],
        }

    def send(self, context: AlertContext) -> None:
        payload = self._build_payload(context)
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status not in (200, 201, 202):
                raise RuntimeError(
                    f"MSTeamsWebhookAlerter: unexpected status {resp.status}"
                )
