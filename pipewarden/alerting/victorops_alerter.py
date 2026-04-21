from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from pipewarden.alerting.base import AlertContext, BaseAlerter


@dataclass
class VictorOpsAlerter(BaseAlerter):
    """Send alerts to VictorOps (Splunk On-Call) via the REST endpoint."""

    routing_key: str = ""
    integration_url: str = "https://alert.victorops.com/integrations/generic/20131114/alert"
    api_key: str = ""
    only_on_failure: bool = True
    extra_fields: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.api_key:
            raise ValueError("VictorOpsAlerter requires 'api_key'")
        if not self.routing_key:
            raise ValueError("VictorOpsAlerter requires 'routing_key'")

    def _build_payload(self, context: AlertContext) -> dict[str, Any]:
        message_type = "CRITICAL" if not context.is_healthy() else "INFO"
        failed_names = [r.check_name for r in context.failed]
        warned_names = [r.check_name for r in context.warned]

        state_message_parts = []
        if failed_names:
            state_message_parts.append(f"Failed checks: {', '.join(failed_names)}")
        if warned_names:
            state_message_parts.append(f"Warnings: {', '.join(warned_names)}")
        state_message = "; ".join(state_message_parts) or "All checks passed."

        payload: dict[str, Any] = {
            "message_type": message_type,
            "entity_id": f"pipewarden/{context.pipeline_name}",
            "entity_display_name": f"PipeWarden: {context.pipeline_name}",
            "state_message": state_message,
            "monitoring_tool": "pipewarden",
            "pipeline": context.pipeline_name,
            "failed_count": len(context.failed),
            "warned_count": len(context.warned),
            "passed_count": len(context.passed),
        }
        payload.update(self.extra_fields)
        return payload

    def send(self, context: AlertContext) -> None:
        if self.only_on_failure and context.is_healthy():
            return

        url = f"{self.integration_url.rstrip('/')}/{self.api_key}/{self.routing_key}"
        payload = self._build_payload(context)
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:  # noqa: S310
            if resp.status >= 400:
                raise RuntimeError(
                    f"VictorOps alert failed with HTTP {resp.status}"
                )
