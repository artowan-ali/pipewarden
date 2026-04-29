from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import requests

from pipewarden.alerting.base import AlertContext, BaseAlerter

_EU_BASE_URL = "https://api.eu.opsgenie.com"
_DEFAULT_BASE_URL = "https://api.opsgenie.com"


@dataclass
class OpsGenieAlerter(BaseAlerter):
    """Send pipeline alerts to OpsGenie."""

    api_key: str = ""
    eu_region: bool = False
    tags: list = field(default_factory=list)
    session: Optional[requests.Session] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not self.api_key:
            raise ValueError("OpsGenieAlerter requires 'api_key'")

    def _session_or_default(self) -> requests.Session:
        return self.session or requests.Session()

    def _base_url(self) -> str:
        return _EU_BASE_URL if self.eu_region else _DEFAULT_BASE_URL

    def _build_payload(self, context: AlertContext) -> dict:
        if context.is_healthy():
            message = f"[RECOVERY] Pipeline '{context.pipeline_name}' is healthy"
            priority = "P5"
        elif context.failed:
            failed_names = ", ".join(r.check_name for r in context.failed)
            message = f"[CRITICAL] Pipeline '{context.pipeline_name}' failures: {failed_names}"
            priority = "P1"
        else:
            warned_names = ", ".join(r.check_name for r in context.warned)
            message = f"[WARNING] Pipeline '{context.pipeline_name}' warnings: {warned_names}"
            priority = "P3"

        return {
            "message": message,
            "alias": f"pipewarden-{context.pipeline_name}",
            "priority": priority,
            "tags": self.tags or ["pipewarden"],
            "details": {
                "pipeline": context.pipeline_name,
                "failed": str([r.check_name for r in context.failed]),
                "warned": str([r.check_name for r in context.warned]),
            },
        }

    def send(self, context: AlertContext) -> None:
        session = self._session_or_default()
        url = f"{self._base_url()}/v2/alerts"
        headers = {
            "Authorization": f"GenieKey {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = self._build_payload(context)
        response = session.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
