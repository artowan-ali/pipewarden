from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import requests

from pipewarden.alerting.base import AlertContext, BaseAlerter


@dataclass
class OpsGenieAlerter(BaseAlerter):
    """Send alerts to OpsGenie via the Alerts API."""

    api_key: str = ""
    region: str = "us"  # "us" or "eu"
    tags: list[str] = field(default_factory=list)
    priority: str = "P3"  # P1–P5
    responders: list[dict] = field(default_factory=list)
    session: Optional[requests.Session] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not self.api_key:
            raise ValueError("OpsGenieAlerter requires 'api_key'")
        valid_priorities = {"P1", "P2", "P3", "P4", "P5"}
        if self.priority not in valid_priorities:
            raise ValueError(
                f"OpsGenieAlerter 'priority' must be one of {valid_priorities}"
            )

    def _session_or_default(self) -> requests.Session:
        return self.session or requests.Session()

    def _base_url(self) -> str:
        host = "api.eu.opsgenie.com" if self.region == "eu" else "api.opsgenie.com"
        return f"https://{host}/v2/alerts"

    def _build_payload(self, context: AlertContext) -> dict:
        status_label = "HEALTHY" if context.is_healthy() else "UNHEALTHY"
        failed_names = [r.check_name for r in context.failures]
        warned_names = [r.check_name for r in context.warnings]

        lines = [f"Pipeline: {context.pipeline_name} | Status: {status_label}"]
        if failed_names:
            lines.append("Failed checks: " + ", ".join(failed_names))
        if warned_names:
            lines.append("Warnings: " + ", ".join(warned_names))

        payload: dict = {
            "message": f"[pipewarden] {context.pipeline_name} — {status_label}",
            "description": "\n".join(lines),
            "priority": self.priority,
            "source": "pipewarden",
            "tags": self.tags,
        }
        if self.responders:
            payload["responders"] = self.responders
        return payload

    def send(self, context: AlertContext) -> None:
        if context.is_healthy():
            return

        session = self._session_or_default()
        payload = self._build_payload(context)
        headers = {
            "Authorization": f"GenieKey {self.api_key}",
            "Content-Type": "application/json",
        }
        response = session.post(self._base_url(), json=payload, headers=headers)
        response.raise_for_status()
