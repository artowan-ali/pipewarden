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
    _session: Optional[requests.Session] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not self.api_key:
            raise ValueError("OpsGenieAlerter requires 'api_key'")
        valid_priorities = {"P1", "P2", "P3", "P4", "P5"}
        if self.priority not in valid_priorities:
            raise ValueError(
                f"Invalid priority '{self.priority}'. Must be one of {valid_priorities}"
            )

    def _session_or_default(self) -> requests.Session:
        if self._session is not None:
            return self._session
        s = requests.Session()
        s.headers["Authorization"] = f"GenieKey {self.api_key}"
        s.headers["Content-Type"] = "application/json"
        return s

    def _base_url(self) -> str:
        if self.region == "eu":
            return "https://api.eu.opsgenie.com/v2/alerts"
        return "https://api.opsgenie.com/v2/alerts"

    def _build_payload(self, context: AlertContext) -> dict:
        status_label = "HEALTHY" if context.is_healthy() else "UNHEALTHY"
        failed_names = [r.check_name for r in context.failed]
        warned_names = [r.check_name for r in context.warned]

        lines = [f"Pipeline '{context.pipeline_name}' is {status_label}."]
        if failed_names:
            lines.append(f"Failed checks: {', '.join(failed_names)}")
        if warned_names:
            lines.append(f"Warned checks: {', '.join(warned_names)}")

        payload: dict = {
            "message": f"[pipewarden] {context.pipeline_name} — {status_label}",
            "description": "\n".join(lines),
            "priority": self.priority,
            "tags": list(self.tags),
            "details": {
                "pipeline": context.pipeline_name,
                "total_checks": str(len(context.results)),
                "failed": str(len(context.failed)),
                "warned": str(len(context.warned)),
            },
        }
        if self.responders:
            payload["responders"] = self.responders
        return payload

    def send(self, context: AlertContext) -> None:
        session = self._session_or_default()
        payload = self._build_payload(context)
        response = session.post(self._base_url(), json=payload, timeout=10)
        response.raise_for_status()
