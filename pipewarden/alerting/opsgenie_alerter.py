from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import requests

from pipewarden.alerting.base import AlertContext, BaseAlerter


@dataclass
class OpsGenieAlerter(BaseAlerter):
    """Send alerts to OpsGenie when pipeline checks fail."""

    api_key: str = ""
    region: str = "us"  # "us" or "eu"
    responders: list = field(default_factory=list)
    tags: list = field(default_factory=list)
    priority: str = "P3"
    session: Optional[requests.Session] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not self.api_key:
            raise ValueError("OpsGenieAlerter requires 'api_key'")
        if self.priority not in {"P1", "P2", "P3", "P4", "P5"}:
            raise ValueError("priority must be one of P1-P5")

    def _session_or_default(self) -> requests.Session:
        return self.session if self.session is not None else requests.Session()

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

        description_parts = []
        for r in context.failures + context.warnings:
            description_parts.append(f"[{r.status.value}] {r.check_name}: {r.details}")

        payload: dict = {
            "message": f"[pipewarden] Pipeline '{context.pipeline_name}' alert — "
                       + "; ".join(lines),
            "description": "\n".join(description_parts),
            "priority": self.priority,
            "tags": list(self.tags),
            "details": {
                "pipeline": context.pipeline_name,
                "failed_checks": str(len(context.failures)),
                "warned_checks": str(len(context.warnings)),
            },
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
