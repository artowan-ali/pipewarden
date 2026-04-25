"""Splunk HTTP Event Collector (HEC) alerter for PipeWarden."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

import requests

from pipewarden.alerting.base import AlertContext, BaseAlerter


@dataclass
class SplunkAlerter(BaseAlerter):
    """Send pipeline health alerts to a Splunk HTTP Event Collector endpoint.

    Args:
        hec_url:     Full URL to the Splunk HEC endpoint, e.g.
                     ``https://splunk.example.com:8088/services/collector/event``.
        hec_token:   HEC authentication token (Bearer).
        index:       Splunk index to write events into.  Defaults to ``"main"``.
        source:      Event source field.  Defaults to ``"pipewarden"``.
        sourcetype:  Event sourcetype field.  Defaults to ``"pipewarden:alert"``.
        session:     Optional :class:`requests.Session` (injected for testing).
    """

    hec_url: str = ""
    hec_token: str = ""
    index: str = "main"
    source: str = "pipewarden"
    sourcetype: str = "pipewarden:alert"
    session: Optional[requests.Session] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not self.hec_url:
            raise ValueError("SplunkAlerter requires 'hec_url'.")
        if not self.hec_token:
            raise ValueError("SplunkAlerter requires 'hec_token'.")

    def _session_or_default(self) -> requests.Session:
        return self.session if self.session is not None else requests.Session()

    def _build_payload(self, ctx: AlertContext) -> dict:
        status = "healthy" if ctx.is_healthy() else "unhealthy"
        failed = [
            {"check": r.check_name, "detail": r.detail}
            for r in ctx.failed_results
        ]
        warned = [
            {"check": r.check_name, "detail": r.detail}
            for r in ctx.warned_results
        ]
        return {
            "time": time.time(),
            "index": self.index,
            "source": self.source,
            "sourcetype": self.sourcetype,
            "event": {
                "pipeline": ctx.pipeline_name,
                "status": status,
                "total_checks": len(ctx.all_results),
                "failed_checks": len(failed),
                "warned_checks": len(warned),
                "failures": failed,
                "warnings": warned,
            },
        }

    def send(self, ctx: AlertContext) -> None:
        """POST an HEC event to Splunk."""
        payload = self._build_payload(ctx)
        session = self._session_or_default()
        headers = {
            "Authorization": f"Splunk {self.hec_token}",
            "Content-Type": "application/json",
        }
        resp = session.post(self.hec_url, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
