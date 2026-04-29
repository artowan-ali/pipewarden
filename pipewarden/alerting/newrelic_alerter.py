from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import requests

from pipewarden.alerting.base import AlertContext, BaseAlerter

_US_ENDPOINT = "https://insights-collector.newrelic.com/v1/accounts/{account_id}/events"
_EU_ENDPOINT = "https://insights-collector.eu01.nr-data.net/v1/accounts/{account_id}/events"


@dataclass
class NewRelicAlerter(BaseAlerter):
    """Send pipeline run events to New Relic Insights."""

    api_key: str = ""
    account_id: str = ""
    eu_region: bool = False
    event_type: str = "PipeWardenCheck"
    session: Optional[requests.Session] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not self.api_key:
            raise ValueError("NewRelicAlerter requires 'api_key'")
        if not self.account_id:
            raise ValueError("NewRelicAlerter requires 'account_id'")

    def _session_or_default(self) -> requests.Session:
        return self.session or requests.Session()

    def _endpoint(self) -> str:
        template = _EU_ENDPOINT if self.eu_region else _US_ENDPOINT
        return template.format(account_id=self.account_id)

    def _build_payload(self, context: AlertContext) -> list[dict]:
        events = []
        for result in context.results:
            events.append({
                "eventType": self.event_type,
                "pipeline": context.pipeline_name,
                "checkName": result.check_name,
                "status": result.status.name,
                "details": result.details or "",
                "healthy": context.is_healthy(),
            })
        return events

    def send(self, context: AlertContext) -> None:
        session = self._session_or_default()
        headers = {
            "Api-Key": self.api_key,
            "Content-Type": "application/json",
        }
        payload = self._build_payload(context)
        response = session.post(
            self._endpoint(), json=payload, headers=headers, timeout=10
        )
        response.raise_for_status()
