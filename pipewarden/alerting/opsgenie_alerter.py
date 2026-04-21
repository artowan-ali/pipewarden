from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import urllib.request
import urllib.error
import json
import logging

from pipewarden.alerting.base import BaseAlerter, AlertContext

logger = logging.getLogger(__name__)


@dataclass
class OpsGenieAlerter(BaseAlerter):
    """Send alerts to OpsGenie when pipeline checks fail."""

    api_key: str = ""
    priority: str = "P3"  # P1–P5
    tags: list[str] = field(default_factory=list)
    alias_prefix: str = "pipewarden"
    api_url: str = "https://api.opsgenie.com/v2/alerts"

    def __post_init__(self) -> None:
        if not self.api_key:
            raise ValueError("OpsGenieAlerter requires 'api_key' to be set.")
        valid_priorities = {"P1", "P2", "P3", "P4", "P5"}
        if self.priority not in valid_priorities:
            raise ValueError(
                f"Invalid priority '{self.priority}'. Must be one of {valid_priorities}."
            )

    def _build_payload(self, context: AlertContext) -> dict[str, Any]:
        failed_names = [r.check_name for r in context.failures]
        warned_names = [r.check_name for r in context.warnings]

        lines = [f"Pipeline: {context.pipeline_name}"]
        if failed_names:
            lines.append(f"Failed checks: {', '.join(failed_names)}")
        if warned_names:
            lines.append(f"Warning checks: {', '.join(warned_names)}")

        description = "\n".join(lines)
        alias = f"{self.alias_prefix}-{context.pipeline_name}".replace(" ", "-").lower()

        return {
            "message": f"[PipeWarden] Pipeline '{context.pipeline_name}' has issues",
            "alias": alias,
            "description": description,
            "priority": self.priority,
            "tags": self.tags,
            "details": {
                "failed_count": str(len(context.failures)),
                "warning_count": str(len(context.warnings)),
            },
        }

    def send(self, context: AlertContext) -> None:
        if context.is_healthy:
            logger.debug(
                "OpsGenieAlerter: pipeline '%s' is healthy, skipping alert.",
                context.pipeline_name,
            )
            return

        payload = self._build_payload(context)
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.api_url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"GenieKey {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req) as resp:
                logger.info(
                    "OpsGenieAlerter: alert sent for pipeline '%s' (HTTP %s).",
                    context.pipeline_name,
                    resp.status,
                )
        except urllib.error.HTTPError as exc:
            logger.error(
                "OpsGenieAlerter: failed to send alert (HTTP %s): %s",
                exc.code,
                exc.reason,
            )
            raise
