from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore

from pipewarden.alerting.base import BaseAlerter, AlertContext


@dataclass
class TeamsAlerter(BaseAlerter):
    """Send pipeline health alerts to a Microsoft Teams channel via
    an Incoming Webhook connector URL."""

    webhook_url: str = ""
    only_on_failure: bool = True
    mention_on_failure: str = ""  # e.g. "<at>Channel</at>"
    extra_facts: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.webhook_url:
            raise ValueError("TeamsAlerter requires a non-empty 'webhook_url'.")
        if requests is None:  # pragma: no cover
            raise ImportError(
                "'requests' is required for TeamsAlerter. "
                "Install it with: pip install requests"
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_payload(self, ctx: AlertContext) -> dict[str, Any]:
        status_label = "✅ Healthy" if ctx.is_healthy else "🚨 Unhealthy"
        color = "00b300" if ctx.is_healthy else "d63b3b"

        facts = [
            {"name": "Pipeline", "value": ctx.pipeline_name},
            {"name": "Status", "value": status_label},
            {"name": "Total checks", "value": str(len(ctx.results))},
            {"name": "Failed", "value": str(len(ctx.failures))},
            {"name": "Warnings", "value": str(len(ctx.warnings))},
        ]
        for key, value in self.extra_facts.items():
            facts.append({"name": key, "value": value})

        sections: list[dict[str, Any]] = [
            {
                "activityTitle": f"PipeWarden — {ctx.pipeline_name}",
                "activitySubtitle": status_label,
                "facts": facts,
                "markdown": True,
            }
        ]

        if not ctx.is_healthy and ctx.failures:
            failure_lines = "\n".join(
                f"- **{r.check_name}**: {r.details}" for r in ctx.failures
            )
            if self.mention_on_failure:
                failure_lines = f"{self.mention_on_failure}\n{failure_lines}"
            sections.append(
                {
                    "activityTitle": "Failed checks",
                    "text": failure_lines,
                    "markdown": True,
                }
            )

        return {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "themeColor": color,
            "summary": f"PipeWarden: {ctx.pipeline_name} — {status_label}",
            "sections": sections,
        }

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def send(self, ctx: AlertContext) -> None:  # type: ignore[override]
        if self.only_on_failure and ctx.is_healthy:
            return

        payload = self._build_payload(ctx)
        response = requests.post(self.webhook_url, json=payload, timeout=10)
        response.raise_for_status()
