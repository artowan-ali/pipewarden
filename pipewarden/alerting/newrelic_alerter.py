from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import requests

from pipewarden.alerting.base import BaseAlerter, AlertContext

_US_ENDPOINT = "https://insights-collector.newrelic.com/v1/accounts/{account_id}/events"
_EU_ENDPOINT = "https://insights-collector.eu01.nr-data.net/v1/accounts/{account_id}/events"


@dataclass
class NewRelicAlerter(BaseAlerter):
    """Send pipeline health events to New Relic Insights."""

    api_key: str = ""
    account_id: str = ""
    region: str = "us"  # "us" or "eu"
    event_type: str = "PipeWardenCheck"
    _session: Optional[requests.Session] = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.api_key:
            raise ValueError("NewRelicAlerter requires 'api_key'")
        if not self.account_id:
            raise ValueError("NewRelicAlerter requires 'account_id'")
        if self.region not in ("us", "eu"):
            raise ValueError("NewRelicAlerter 'region' must be 'us' or 'eu'")

    def _session_or_default(self) -> requests.Session:
        if self._session is not None:
            return self._session
        session = requests.Session()
        session.headers.update(
            {
                "Api-Key": self.api_key,
                "Content-Type": "application/json",
            }
        )
        return session

    @property
    def _endpoint(self) -> str:
        template = _EU_ENDPOINT if self.region == "eu" else _US_ENDPOINT
        return template.format(account_id=self.account_id)

    def _build_payload(self, context: AlertContext) -> list[dict]:
        status = "healthy" if context.is_healthy else "unhealthy"
        events = []

        # One summary event for the whole pipeline run
        events.append(
            {
                "eventType": self.event_type,
                "pipeline": context.pipeline_name,
                "status": status,
                "failedChecks": len(context.failures),
                "warnedChecks": len(context.warnings),
                "passedChecks": len(context.passes),
            }
        )

        # Individual events for each failed or warned check
        for result in context.failures + context.warnings:
            events.append(
                {
                    "eventType": self.event_type,
                    "pipeline": context.pipeline_name,
                    "checkName": result.check_name,
                    "checkStatus": result.status.value,
                    "checkDetail": result.detail or "",
                }
            )

        return events

    def send(self, context: AlertContext) -> None:
        payload = self._build_payload(context)
        session = self._session_or_default()
        response = session.post(self._endpoint, json=payload, timeout=10)
        response.raise_for_status()
