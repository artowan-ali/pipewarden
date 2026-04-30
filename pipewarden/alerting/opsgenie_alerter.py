from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import requests

from pipewarden.alerting.base import AlertContext, BaseAlerter


@dataclass
class OpsGenieAlerter(BaseAlerter):
    """Send alerts to OpsGenie via the Alert API."""

    api_key: str = ""
    region: str = "us"  # 'us' or 'eu'
    tags: list[str] = field(default_factory=list)
    priority: str = "P3"
    responders: list[dict] = field(default_factory=list)
    _session: Optional[requests.Session] = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.api_key:
            raise ValueError("OpsGenieAlerter requires 'api_key'")
        if self.priority not in {"P1", "P2", "P3", "P4", "P5"}:
            raise ValueError("priority must be one of P1-P5")

    def _session_or_default(self) -> requests.Session:
        if self._session is not None:
            return self._session
        s = requests.Session()
        s.headers.update(
            {"Authorization": f"GenieKey {self.api_key}", "Content-Type": "application/json"}
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

        description_lines = [f"Pipeline: {ctx.pipeline_name}", f"Status: {status_label}"]
        if failed_names:
            description_lines.append(f"Failed checks: {', '.join(failed_names)}")
        if warned_names:
            description_lines.append(f"Warned checks: {', '.join(warned_names)}")

        payload: dict = {
            "message": f"[pipewarden] {ctx.pipeline_name} — {status_label}",
            "description": "\n".join(description_lines),
            "priority": self.priority,
            "tags": self.tags,
            "details": {
                "pipeline": ctx.pipeline_name,
                "failed_checks": str(len(ctx.failed)),
                "warned_checks": str(len(ctx.warned)),
            },
        }
        if self.responders:
            payload["responders"] = self.responders
        return payload

    def send(self, ctx: AlertContext) -> None:
        if ctx.is_healthy() and not self.alert_on_recovery:
            return
        session = self._session_or_default()
        payload = self._build_payload(ctx)
        response = session.post(self._base_url(), json=payload, timeout=10)
        response.raise_for_status()
