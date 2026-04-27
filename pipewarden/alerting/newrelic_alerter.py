"""New Relic alerter — sends pipeline health events to New Relic Events API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import requests

from pipewarden.alerting.base import AlertContext, BaseAlerter

_US_ENDPOINT = "https://insights-collector.newrelic.com/v1/accounts/{account_id}/events"
_EU_ENDPOINT = "https://insights-collector.eu01.nr-data.net/v1/accounts/{account_id}/events"


@dataclass
class NewRelicAlerter(BaseAlerter):
    """Post a custom event to New Relic Insights when a pipeline run completes.

    Args:
        api_key: New Relic Insights insert key (required).
        account_id: New Relic account ID (required).
        event_type: Custom event type name recorded in NRDB.
        eu_region: When True, use the EU data centre endpoint.
        session: Optional pre-configured ``requests.Session`` for testing.
    """

    api_key: str = ""
    account_id: str = ""
    event_type: str = "PipeWardenRun"
    eu_region: bool = False
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

    def _build_payload(self, ctx: AlertContext) -> list[dict]:
        failed = [r.check_name for r in ctx.failures]
        warned = [r.check_name for r in ctx.warnings]
        return [
            {
                "eventType": self.event_type,
                "pipeline": ctx.pipeline_name,
                "healthy": ctx.is_healthy(),
                "total_checks": len(ctx.results),
                "failed_checks": len(failed),
                "warned_checks": len(warned),
                "failed_check_names": ", ".join(failed),
                "warned_check_names": ", ".join(warned),
            }
        ]

    def send(self, ctx: AlertContext) -> None:
        session = self._session_or_default()
        headers = {
            "X-Insert-Key": self.api_key,
            "Content-Type": "application/json",
        }
        payload = self._build_payload(ctx)
        response = session.post(self._endpoint(), json=payload, headers=headers)
        response.raise_for_status()
