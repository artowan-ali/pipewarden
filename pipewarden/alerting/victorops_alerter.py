from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import requests

from pipewarden.alerting.base import AlertContext, BaseAlerter


@dataclass
class VictorOpsAlerter(BaseAlerter):
    """Send pipeline alerts to VictorOps (Splunk On-Call) via REST endpoint."""

    api_key: str = ""
    routing_key: str = "default"
    base_url: str = "https://alert.victorops.com/integrations/generic/20131114/alert"
    session: Optional[requests.Session] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not self.api_key:
            raise ValueError("VictorOpsAlerter requires 'api_key'")

    def _build_payload(self, context: AlertContext) -> dict:
        if context.is_healthy():
            message_type = "RECOVERY"
            state_message = f"Pipeline '{context.pipeline_name}' is healthy."
        elif any(r.status.name == "FAILED" for r in context.failed):
            message_type = "CRITICAL"
            failed_names = ", ".join(r.check_name for r in context.failed)
            state_message = f"Pipeline '{context.pipeline_name}' has failures: {failed_names}"
        else:
            message_type = "WARNING"
            warned_names = ", ".join(r.check_name for r in context.warned)
            state_message = f"Pipeline '{context.pipeline_name}' has warnings: {warned_names}"

        return {
            "message_type": message_type,
            "entity_id": f"pipewarden.{context.pipeline_name}",
            "entity_display_name": f"PipeWarden: {context.pipeline_name}",
            "state_message": state_message,
            "monitoring_tool": "pipewarden",
            "failed_checks": [r.check_name for r in context.failed],
            "warned_checks": [r.check_name for r in context.warned],
        }

    def send(self, context: AlertContext) -> None:
        session = self.session or requests.Session()
        url = f"{self.base_url}/{self.api_key}/{self.routing_key}"
        payload = self._build_payload(context)
        response = session.post(url, json=payload, timeout=10)
        response.raise_for_status()
