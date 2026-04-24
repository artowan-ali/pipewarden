from __future__ import annotations

import json
import logging
import urllib.request
from dataclasses import dataclass, field
from typing import Optional

from pipewarden.alerting.base import AlertContext, BaseAlerter

logger = logging.getLogger(__name__)

_DEFAULT_API_URL = "https://api.datadoghq.com/api/v1/events"


@dataclass
class DatadogAlerter(BaseAlerter):
    """Send pipeline health alerts to Datadog as events."""

    api_key: str = ""
    app_key: str = ""
    api_url: str = _DEFAULT_API_URL
    tags: list[str] = field(default_factory=list)
    alert_type: str = "error"  # error | warning | info | success
    source_type_name: str = "pipewarden"

    def __post_init__(self) -> None:
        if not self.api_key:
            raise ValueError("DatadogAlerter requires a non-empty 'api_key'.")

    def _build_payload(self, context: AlertContext) -> dict:
        status_emoji = "\u2705" if context.is_healthy() else "\u274c"
        title = (
            f"{status_emoji} PipeWarden: pipeline {'healthy' if context.is_healthy() else 'unhealthy'}"
        )
        lines = [f"Pipeline run finished — {len(context.results)} check(s) executed."]
        for result in context.failed_results:
            lines.append(f"  FAIL  {result.check_name}: {result.details}")
        for result in context.warned_results:
            lines.append(f"  WARN  {result.check_name}: {result.details}")

        tags = list(self.tags)
        tags.append(f"healthy:{str(context.is_healthy()).lower()}")

        return {
            "title": title,
            "text": "\n".join(lines),
            "alert_type": self.alert_type if not context.is_healthy() else "success",
            "source_type_name": self.source_type_name,
            "tags": tags,
        }

    def send(self, context: AlertContext) -> None:
        payload = self._build_payload(context)
        body = json.dumps(payload).encode()
        headers = {
            "Content-Type": "application/json",
            "DD-API-KEY": self.api_key,
        }
        if self.app_key:
            headers["DD-APPLICATION-KEY"] = self.app_key

        req = urllib.request.Request(
            self.api_url, data=body, headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                logger.debug("Datadog event created, status=%s", resp.status)
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to send Datadog alert: %s", exc)
            raise
