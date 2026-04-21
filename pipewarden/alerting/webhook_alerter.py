"""Alerter that posts a JSON payload to an HTTP webhook endpoint."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Dict, Optional

from pipewarden.alerting.base import AlertContext, BaseAlerter


@dataclass
class WebhookAlerter(BaseAlerter):
    """Sends a JSON alert payload to the configured URL."""

    url: str
    timeout: int = 10
    extra_headers: Dict[str, str] = field(default_factory=dict)

    def _build_payload(self, context: AlertContext) -> Dict:
        return {
            "pipeline": context.pipeline_name,
            "healthy": context.is_healthy,
            "failed": [
                {"check": r.check_name, "details": r.details}
                for r in context.failed
            ],
            "warned": [
                {"check": r.check_name, "details": r.details}
                for r in context.warned
            ],
        }

    def send(self, context: AlertContext) -> None:
        payload = json.dumps(self._build_payload(context)).encode()
        headers = {"Content-Type": "application/json", **self.extra_headers}
        req = urllib.request.Request(
            self.url, data=payload, headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout):
                pass
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"WebhookAlerter failed to reach '{self.url}': {exc.reason}"
            ) from exc
