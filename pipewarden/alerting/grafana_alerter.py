"""Grafana alerter — posts pipeline run results as Grafana annotations."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

import requests

from pipewarden.alerting.base import AlertContext, BaseAlerter
from pipewarden.checks.base import CheckStatus


@dataclass
class GrafanaAlerter(BaseAlerter):
    """Send pipeline health results to Grafana as dashboard annotations.

    Args:
        base_url:        Grafana instance base URL, e.g. ``https://grafana.example.com``.
        api_key:         Grafana API key (Bearer token).
        dashboard_uid:   Optional dashboard UID to scope the annotation.
        panel_id:        Optional panel ID to scope the annotation.
        tags:            Extra tags to attach to the annotation.
        alert_on_warn:   Whether to post annotations for WARN-only runs.
        session:         Optional ``requests.Session`` (injected for testing).
    """

    base_url: str = ""
    api_key: str = ""
    dashboard_uid: Optional[str] = None
    panel_id: Optional[int] = None
    tags: list[str] = field(default_factory=list)
    alert_on_warn: bool = True
    session: Optional[requests.Session] = None

    def __post_init__(self) -> None:
        if not self.base_url:
            raise ValueError("GrafanaAlerter requires 'base_url'")
        if not self.api_key:
            raise ValueError("GrafanaAlerter requires 'api_key'")

    def _session_or_default(self) -> requests.Session:
        if self.session is not None:
            return self.session
        s = requests.Session()
        s.headers.update(
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
        )
        return s

    def _build_payload(self, ctx: AlertContext) -> dict:
        if ctx.is_healthy:
            text = f"✅ Pipeline <b>{ctx.pipeline_name}</b> passed all checks."
            tag_state = "ok"
        elif any(r.status == CheckStatus.FAILED for r in ctx.failures):
            lines = [f"❌ Pipeline <b>{ctx.pipeline_name}</b> has failures:"]
            for r in ctx.failures:
                lines.append(f"• {r.check_name}: {r.details}")
            text = "\n".join(lines)
            tag_state = "alerting"
        else:
            lines = [f"⚠️ Pipeline <b>{ctx.pipeline_name}</b> has warnings:"]
            for r in ctx.warnings:
                lines.append(f"• {r.check_name}: {r.details}")
            text = "\n".join(lines)
            tag_state = "warning"

        payload: dict = {
            "time": int(time.time() * 1000),
            "isRegion": False,
            "text": text,
            "tags": ["pipewarden", tag_state, ctx.pipeline_name] + self.tags,
        }
        if self.dashboard_uid:
            payload["dashboardUID"] = self.dashboard_uid
        if self.panel_id is not None:
            payload["panelId"] = self.panel_id
        return payload

    def send(self, ctx: AlertContext) -> None:
        """Post an annotation to Grafana unless the run is healthy and quiet."""
        if ctx.is_healthy:
            return
        if not ctx.failures and not self.alert_on_warn:
            return

        session = self._session_or_default()
        url = f"{self.base_url.rstrip('/')}/api/annotations"
        payload = self._build_payload(ctx)
        response = session.post(url, json=payload, timeout=10)
        response.raise_for_status()
