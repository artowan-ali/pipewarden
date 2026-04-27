from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import requests

from pipewarden.alerting.base import AlertContext, BaseAlerter

_DEFAULT_ENDPOINT = "https://api.rollbar.com/api/1/item/"


@dataclass
class RollbarAlerter(BaseAlerter):
    """Send pipeline failure alerts to Rollbar as error items."""

    access_token: str = ""
    environment: str = "production"
    endpoint: str = _DEFAULT_ENDPOINT
    session: Optional[requests.Session] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not self.access_token:
            raise ValueError("RollbarAlerter requires 'access_token'")

    def _session_or_default(self) -> requests.Session:
        return self.session or requests.Session()

    def _build_payload(self, context: AlertContext) -> dict:
        failed = [r.check_name for r in context.failures]
        warned = [r.check_name for r in context.warnings]

        body_message = (
            f"Pipeline '{context.pipeline_name}' is unhealthy. "
            f"Failures: {failed}. Warnings: {warned}."
        )

        return {
            "access_token": self.access_token,
            "data": {
                "environment": self.environment,
                "body": {
                    "message": {
                        "body": body_message,
                    }
                },
                "level": "error" if context.failures else "warning",
                "title": f"PipeWarden: {context.pipeline_name} check failure",
                "custom": {
                    "pipeline": context.pipeline_name,
                    "failed_checks": failed,
                    "warned_checks": warned,
                    "total_checks": context.total_checks,
                },
            },
        }

    def send(self, context: AlertContext) -> None:
        if context.is_healthy():
            return

        payload = self._build_payload(context)
        session = self._session_or_default()
        response = session.post(self.endpoint, json=payload, timeout=10)
        response.raise_for_status()
