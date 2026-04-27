from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import requests

from pipewarden.alerting.base import BaseAlerter, AlertContext


@dataclass
class ZendeskAlerter(BaseAlerter):
    """Create a Zendesk support ticket when pipeline checks fail."""

    subdomain: str = ""
    email: str = ""
    api_token: str = ""
    ticket_tags: list[str] = field(default_factory=lambda: ["pipewarden"])
    priority: str = "normal"  # low | normal | high | urgent
    ticket_type: str = "incident"  # problem | incident | question | task
    assignee_email: Optional[str] = None
    group_id: Optional[int] = None
    _session: Optional[requests.Session] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not self.subdomain:
            raise ValueError("ZendeskAlerter requires a 'subdomain'")
        if not self.email:
            raise ValueError("ZendeskAlerter requires an 'email'")
        if not self.api_token:
            raise ValueError("ZendeskAlerter requires an 'api_token'")

    def _session_or_default(self) -> requests.Session:
        if self._session is not None:
            return self._session
        session = requests.Session()
        session.auth = (f"{self.email}/token", self.api_token)
        session.headers.update({"Content-Type": "application/json"})
        return session

    def _build_subject(self, ctx: AlertContext) -> str:
        status = "UNHEALTHY" if not ctx.is_healthy() else "HEALTHY"
        return f"[PipeWarden] Pipeline {status}: {ctx.pipeline_name}"

    def _build_body(self, ctx: AlertContext) -> str:
        lines = [f"Pipeline: {ctx.pipeline_name}"]
        if ctx.failed:
            lines.append(f"\nFailed checks ({len(ctx.failed)}):")
            for r in ctx.failed:
                lines.append(f"  ✗ {r.check_name}: {r.details}")
        if ctx.warned:
            lines.append(f"\nWarning checks ({len(ctx.warned)}):")
            for r in ctx.warned:
                lines.append(f"  ⚠ {r.check_name}: {r.details}")
        lines.append(f"\nPassed: {len(ctx.passed)}")
        return "\n".join(lines)

    def _build_payload(self, ctx: AlertContext) -> dict:
        ticket: dict = {
            "subject": self._build_subject(ctx),
            "comment": {"body": self._build_body(ctx)},
            "tags": self.ticket_tags,
            "priority": self.priority,
            "type": self.ticket_type,
        }
        if self.assignee_email:
            ticket["assignee_email"] = self.assignee_email
        if self.group_id is not None:
            ticket["group_id"] = self.group_id
        return {"ticket": ticket}

    def send(self, ctx: AlertContext) -> None:
        if ctx.is_healthy():
            return
        url = f"https://{self.subdomain}.zendesk.com/api/v2/tickets.json"
        session = self._session_or_default()
        response = session.post(url, json=self._build_payload(ctx))
        response.raise_for_status()
