from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import requests

from pipewarden.alerting.base import BaseAlerter, AlertContext


@dataclass
class OpsGenieAlerter(BaseAlerter):
    """Send alerts to OpsGenie via the Alert API."""

    api_key: str = ""
    region: str = "us"  # "us" or "eu"
    priority: str = "P3"
    tags: list[str] = field(default_factory=list)
    responders: list[dict] = field(default_factory=list)
    session: Optional[requests.Session] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not self.api_key:
            raise ValueError("OpsGenieAlerter requires 'api_key'")
        if self.region not in ("us", "eu"):
            raise ValueError("OpsGenieAlerter 'region' must be 'us' or 'eu'")

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

    def _build_payload(self, context: AlertContext) -> dict:
        status = "HEALTHY" if context.is_healthy() else "UNHEALTHY"
        failed_names = [r.check_name for r in context.failures]
        warned_names = [r.check_name for r in context.warnings]

        lines = [f"Pipeline: {context.pipeline_name} — {status}"]
        if failed_names:
            lines.append("Failed: " + ", ".join(failed_names))
        if warned_names:
            lines.append("Warnings: " + ", ".join(warned_names))

        payload: dict = {
            "message": f"[pipewarden] {context.pipeline_name} is {status}",
            "description": "\n".join(lines),
            "priority": self.priority,
            "source": "pipewarden",
            "details": {
                "pipeline": context.pipeline_name,
                "status": status,
                "failed_checks": ", ".join(failed_names) or "none",
                "warned_checks": ", ".join(warned_names) or "none",
            },
        }
        if self.tags:
            payload["tags"] = self.tags
        if self.responders:
            payload["responders"] = self.responders
        return payload

    def send(self, context: AlertContext) -> None:
        session = self._session_or_default()
        payload = self._build_payload(context)
        response = session.post(self._base_url(), json=payload, timeout=10)
        response.raise_for_status()
