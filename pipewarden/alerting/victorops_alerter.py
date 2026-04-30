from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import requests

from pipewarden.alerting.base import AlertContext, BaseAlerter


@dataclass
class VictorOpsAlerter(BaseAlerter):
    """Send pipeline alerts to VictorOps (Splunk On-Call) via the REST endpoint."""

    api_key: str = ""
    routing_key: str = "default"
    base_url: str = "https://alert.victorops.com/integrations/generic/20131114/alert"
    session: Optional[requests.Session] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not self.api_key:
            raise ValueError("VictorOpsAlerter requires 'api_key'")

    def _build_payload(self, ctx: AlertContext) -> dict:
        if ctx.is_healthy:
            message_type = "RECOVERY"
            state_message = f"Pipeline '{ctx.pipeline_name}' recovered — all checks passed."
        else:
            failed_names = ", ".join(r.check_name for r in ctx.failed)
            message_type = "CRITICAL"
            state_message = (
                f"Pipeline '{ctx.pipeline_name}' has {len(ctx.failed)} failed check(s): "
                f"{failed_names}"
            )

        return {
            "message_type": message_type,
            "entity_id": f"pipewarden.{ctx.pipeline_name}",
            "entity_display_name": f"PipeWarden — {ctx.pipeline_name}",
            "state_message": state_message,
            "monitoring_tool": "pipewarden",
            "failed_checks": len(ctx.failed),
            "warned_checks": len(ctx.warned),
            "passed_checks": len(ctx.passed),
        }

    def send(self, ctx: AlertContext) -> None:
        session = self.session or requests.Session()
        url = f"{self.base_url}/{self.api_key}/{self.routing_key}"
        payload = self._build_payload(ctx)
        response = session.post(url, json=payload, timeout=10)
        response.raise_for_status()
