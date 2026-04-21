from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass, field
from typing import Optional

from pipewarden.alerting.base import AlertContext, BaseAlerter

_EVENTS_API = "https://events.pagerduty.com/v2/enqueue"


@dataclass
class PagerDutyAlerter(BaseAlerter):
    """Send PagerDuty Events API v2 alerts when a pipeline is unhealthy."""

    integration_key: str = ""
    severity: str = "error"  # critical | error | warning | info
    source: str = "pipewarden"
    component: Optional[str] = None
    _api_url: str = field(default=_EVENTS_API, repr=False)

    def __post_init__(self) -> None:
        if not self.integration_key:
            raise ValueError("PagerDutyAlerter requires an 'integration_key'.")
        if self.severity not in {"critical", "error", "warning", "info"}:
            raise ValueError(
                f"Invalid severity '{self.severity}'. "
                "Must be one of: critical, error, warning, info."
            )

    def _build_payload(self, ctx: AlertContext) -> dict:
        failed_names = [r.check_name for r in ctx.failures]
        summary = (
            f"Pipeline unhealthy — {len(failed_names)} check(s) failed: "
            + ", ".join(failed_names)
        )
        payload: dict = {
            "routing_key": self.integration_key,
            "event_action": "trigger",
            "payload": {
                "summary": summary,
                "severity": self.severity,
                "source": self.source,
                "custom_details": {
                    "total_checks": len(ctx.results),
                    "failed": len(ctx.failures),
                    "warnings": len(ctx.warnings),
                    "passed": len(ctx.passed),
                },
            },
        }
        if self.component:
            payload["payload"]["component"] = self.component
        return payload

    def send(self, ctx: AlertContext) -> None:
        if ctx.is_healthy:
            return
        body = json.dumps(self._build_payload(ctx)).encode()
        req = urllib.request.Request(
            self._api_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:  # noqa: S310
            resp.read()
