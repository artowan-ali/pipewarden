"""Grafana alerter — posts pipeline health annotations and alerts via the Grafana HTTP API.

Uses the Grafana Annotations API to record pipeline run results as dashboard
annotations, and optionally fires a Grafana alert via the Alerting API (requires
Grafana 9+ with the alerting feature enabled).

Reference:
  https://grafana.com/docs/grafana/latest/developers/http_api/annotations/
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

import requests

from pipewarden.alerting.base import AlertContext, BaseAlerter


@dataclass
class GrafanaAlerter(BaseAlerter):
    """Send pipeline run results to Grafana as annotations.

    Parameters
    ----------
    grafana_url:
        Base URL of the Grafana instance, e.g. ``https://grafana.example.com``.
    api_key:
        Grafana service-account token or legacy API key with *Editor* or
        *Admin* role so it can create annotations.
    dashboard_uid:
        Optional UID of the dashboard to tag the annotation on.  When omitted
        the annotation is created as a global (non-dashboard) annotation.
    panel_id:
        Optional numeric ID of the panel within the dashboard.
    tags:
        Extra string tags attached to every annotation (default: ``["pipewarden"]``).
    alert_on_failure:
        When ``True`` (default) an annotation with ``alertState=alerting`` is
        posted for failed runs; healthy runs use ``alertState=ok``.
    session:
        Optional :class:`requests.Session` — injected for testing.
    """

    grafana_url: str = ""
    api_key: str = ""
    dashboard_uid: Optional[str] = None
    panel_id: Optional[int] = None
    tags: list[str] = field(default_factory=lambda: ["pipewarden"])
    alert_on_failure: bool = True
    session: Optional[requests.Session] = None

    def __post_init__(self) -> None:
        if not self.grafana_url:
            raise ValueError("GrafanaAlerter requires 'grafana_url'")
        if not self.api_key:
            raise ValueError("GrafanaAlerter requires 'api_key'")
        # Normalise — strip trailing slash for clean URL construction.
        self.grafana_url = self.grafana_url.rstrip("/")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

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

    def _build_payload(self, context: AlertContext) -> dict:
        """Construct the Grafana annotation payload from *context*."""
        is_healthy = context.is_healthy()
        now_ms = int(time.time() * 1000)

        failed_names = [r.check_name for r in context.failed]
        warned_names = [r.check_name for r in context.warned]

        if is_healthy:
            text = (
                f"<b>pipewarden ✅ {context.pipeline_name}</b><br/>"
                f"All {len(context.all_results)} checks passed."
            )
            alert_state = "ok"
        else:
            parts: list[str] = []
            if failed_names:
                parts.append(f"Failed: {', '.join(failed_names)}")
            if warned_names:
                parts.append(f"Warned: {', '.join(warned_names)}")
            text = (
                f"<b>pipewarden ❌ {context.pipeline_name}</b><br/>"
                + "<br/>".join(parts)
            )
            alert_state = "alerting"

        payload: dict = {
            "time": now_ms,
            "isRegion": False,
            "tags": list(self.tags) + (["ok"] if is_healthy else ["alerting"]),
            "text": text,
        }

        if self.alert_on_failure:
            payload["alertState"] = alert_state

        if self.dashboard_uid:
            payload["dashboardUID"] = self.dashboard_uid
        if self.panel_id is not None:
            payload["panelId"] = self.panel_id

        return payload

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def send(self, context: AlertContext) -> None:
        """Post an annotation to Grafana for *context*.

        Raises
        ------
        requests.HTTPError
            If the Grafana API responds with a non-2xx status code.
        """
        payload = self._build_payload(context)
        session = self._session_or_default()
        url = f"{self.grafana_url}/api/annotations"
        response = session.post(url, json=payload)
        response.raise_for_status()
