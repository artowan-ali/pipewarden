from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import requests

from pipewarden.alerting.base import BaseAlerter, AlertContext


@dataclass
class OpsGenieAlerter(BaseAlerter):
    """Send pipeline health alerts to OpsGenie."""

    api_key: str = ""
    region: str = "us"  # "us" or "eu"
    priority: str = "P3"
    tags: list[str] = field(default_factory=list)
    responders: list[dict] = field(default_factory=list)
    alias_prefix: str = "pipewarden"
    _session: Optional[requests.Session] = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.api_key:
            raise ValueError("OpsGenieAlerter requires 'api_key'")
        if self.region not in ("us", "eu"):
            raise ValueError("OpsGenieAlerter 'region' must be 'us' or 'eu'")

    def _session_or_default(self) -> requests.Session:
        if self._session is not None:
            return self._session
        session = requests.Session()
        session.headers.update(
            {
                "Authorization": f"GenieKey {self.api_key}",
                "Content-Type": "application/json",
            }
        )
        return session

    @property
    def _base_url(self) -> str:
        subdomain = "api.eu" if self.region == "eu" else "api"
        return f"https://{subdomain}.opsgenie.com/v2/alerts"

    def _build_payload(self, context: AlertContext) -> dict:
        status = "HEALTHY" if context.is_healthy else "UNHEALTHY"
        failed_names = [r.check_name for r in context.failures]
        warned_names = [r.check_name for r in context.warnings]

        lines = [f"Pipeline: {context.pipeline_name}  |  Status: {status}"]
        if failed_names:
            lines.append(f"Failed checks: {', '.join(failed_names)}")
        if warned_names:
            lines.append(f"Warned checks: {', '.join(warned_names)}")

        payload: dict = {
            "message": f"[pipewarden] {context.pipeline_name} — {status}",
            "alias": f"{self.alias_prefix}-{context.pipeline_name}",
            "description": "\n".join(lines),
            "priority": self.priority,
            "details": {
                "pipeline": context.pipeline_name,
                "status": status,
                "failed_checks": str(len(context.failures)),
                "warned_checks": str(len(context.warnings)),
            },
        }
        if self.tags:
            payload["tags"] = self.tags
        if self.responders:
            payload["responders"] = self.responders
        return payload

    def send(self, context: AlertContext) -> None:
        payload = self._build_payload(context)
        session = self._session_or_default()
        response = session.post(self._base_url, json=payload, timeout=10)
        response.raise_for_status()
