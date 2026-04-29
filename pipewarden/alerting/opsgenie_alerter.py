from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import requests

from pipewarden.alerting.base import AlertContext, BaseAlerter


@dataclass
class OpsGenieAlerter(BaseAlerter):
    """Send alerts to OpsGenie via the Alert API."""

    api_key: str = ""
    region: str = "us"  # "us" or "eu"
    tags: list[str] = field(default_factory=list)
    priority: str = "P3"  # P1–P5
    responders: list[dict] = field(default_factory=list)
    session: Optional[requests.Session] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not self.api_key:
            raise ValueError("OpsGenieAlerter requires an api_key.")

    def _session_or_default(self) -> requests.Session:
        return self.session or requests.Session()

    def _base_url(self) -> str:
        if self.region == "eu":
            return "https://api.eu.opsgenie.com/v2/alerts"
        return "https://api.opsgenie.com/v2/alerts"

    def _build_payload(self, context: AlertContext) -> dict:
        failed = [r.check_name for r in context.failures]
        warned = [r.check_name for r in context.warnings]
        lines = []
        if failed:
            lines.append("FAILED: " + ", ".join(failed))
        if warned:
            lines.append("WARNED: " + ", ".join(warned))
        description = "\n".join(lines) or "All checks passed."
        status_label = "FAILED" if context.failures else "WARNED"
        message = f"[pipewarden] Pipeline {status_label} — {context.pipeline_name}"
        payload: dict = {
            "message": message,
            "description": description,
            "priority": self.priority,
            "tags": list(self.tags),
        }
        if self.responders:
            payload["responders"] = list(self.responders)
        return payload

    def send(self, context: AlertContext) -> None:
        if context.is_healthy():
            return
        session = self._session_or_default()
        payload = self._build_payload(context)
        response = session.post(
            self._base_url(),
            json=payload,
            headers={
                "Authorization": f"GenieKey {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        response.raise_for_status()
