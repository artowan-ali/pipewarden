"""ServiceNow alerter — creates incidents via the ServiceNow Table API."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import requests

from pipewarden.alerting.base import AlertContext, BaseAlerter


@dataclass
class ServiceNowAlerter(BaseAlerter):
    """Post a ServiceNow incident when a pipeline run is unhealthy.

    Args:
        instance:        ServiceNow instance subdomain (e.g. ``dev12345``).
        username:        Basic-auth username.
        password:        Basic-auth password.
        assignment_group: Optional assignment group name to attach to the incident.
        urgency:         1 (High), 2 (Medium), 3 (Low).  Defaults to 2.
        impact:          1 (High), 2 (Medium), 3 (Low).  Defaults to 2.
        only_on_failure: When *True* (default) skip healthy runs.
    """

    instance: str = ""
    username: str = ""
    password: str = ""
    assignment_group: Optional[str] = None
    urgency: int = 2
    impact: int = 2
    only_on_failure: bool = True
    _session: Optional[requests.Session] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not self.instance:
            raise ValueError("ServiceNowAlerter requires 'instance'")
        if not self.username or not self.password:
            raise ValueError("ServiceNowAlerter requires 'username' and 'password'")

    # ------------------------------------------------------------------
    def _session_or_default(self) -> requests.Session:
        if self._session is not None:
            return self._session
        s = requests.Session()
        s.auth = (self.username, self.password)
        s.headers.update({"Content-Type": "application/json", "Accept": "application/json"})
        return s

    def _build_payload(self, ctx: AlertContext) -> dict:
        failed = [r.check_name for r in ctx.failures]
        warned = [r.check_name for r in ctx.warnings]
        lines = [f"Pipeline: {ctx.pipeline_name}"]
        if failed:
            lines.append(f"Failed checks: {', '.join(failed)}")
        if warned:
            lines.append(f"Warning checks: {', '.join(warned)}")
        status_label = "FAILED" if ctx.failures else "WARNING"
        payload: dict = {
            "short_description": f"[PipeWarden] {ctx.pipeline_name} — {status_label}",
            "description": "\n".join(lines),
            "urgency": str(self.urgency),
            "impact": str(self.impact),
        }
        if self.assignment_group:
            payload["assignment_group"] = self.assignment_group
        return payload

    def send(self, ctx: AlertContext) -> None:
        if self.only_on_failure and ctx.is_healthy:
            return
        url = f"https://{self.instance}.service-now.com/api/now/table/incident"
        response = self._session_or_default().post(url, json=self._build_payload(ctx))
        response.raise_for_status()
