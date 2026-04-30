from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import requests

from pipewarden.alerting.base import AlertContext, BaseAlerter


@dataclass
class OpsGenieAlerter(BaseAlerter):
    """Send alerts to OpsGenie via the Alerts API."""

    api_key: str = ""
    region: str = "us"  # 'us' or 'eu'
    priority: str = "P3"
    tags: list[str] = field(default_factory=list)
    responders: list[dict] = field(default_factory=list)
    session: Optional[requests.Session] = field(default=None, repr=False)
    alert_on_recovery: bool = True

    def __post_init__(self) -> None:
        if not self.api_key:
            raise ValueError("OpsGenieAlerter requires 'api_key'")
        if self.region not in ("us", "eu"):
            raise ValueError("region must be 'us' or 'eu'")

    def _session_or_default(self) -> requests.Session:
        if self.session is not None:
            return self.session
        s = requests.Session()
        s.headers.update(
            {
                "Authorization": f"GenieKey {self.api_key}",
                "Content-Type": "application/json",
            }
        )
        return s

    def _base_url(self) -> str:
        if self.region == "eu":
            return "https://api.eu.opsgenie.com/v2/alerts"
        return "https://api.opsgenie.com/v2/alerts"

    def _build_payload(self, ctx: AlertContext) -> dict:
        status_label = "HEALTHY" if ctx.is_healthy() else "UNHEALTHY"
        failed_names = [r.check_name for r in ctx.failed]
        warned_names = [r.check_name for r in ctx.warned]

        lines = [f"Pipeline '{ctx.pipeline_name}' is {status_label}."]
        if failed_names:
            lines.append(f"Failed checks: {', '.join(failed_names)}")
        if warned_names:
            lines.append(f"Warned checks: {', '.join(warned_names)}")

        payload: dict = {
            "message": f"[PipeWarden] {ctx.pipeline_name} — {status_label}",
            "description": "\n".join(lines),
            "priority": self.priority,
            "source": "pipewarden",
            "details": {
                "pipeline": ctx.pipeline_name,
                "total_checks": str(ctx.total),
                "failed": str(len(ctx.failed)),
                "warned": str(len(ctx.warned)),
            },
        }
        if self.tags:
            payload["tags"] = self.tags
        if self.responders:
            payload["responders"] = self.responders
        return payload

    def send(self, ctx: AlertContext) -> None:
        if ctx.is_healthy() and not self.alert_on_recovery:
            return

        payload = self._build_payload(ctx)
        session = self._session_or_default()
        response = session.post(self._base_url(), json=payload, timeout=10)
        response.raise_for_status()
