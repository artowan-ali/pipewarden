"""Jira alerter — creates a Jira issue when a pipeline run is unhealthy."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import requests

from pipewarden.alerting.base import AlertContext, BaseAlerter

logger = logging.getLogger(__name__)


@dataclass
class JiraAlerter(BaseAlerter):
    """Creates a Jira issue via the REST API v3 when checks fail.

    Parameters
    ----------
    base_url:
        Root URL of your Jira instance, e.g. ``https://myorg.atlassian.net``.
    email:
        Atlassian account e-mail used for basic auth.
    api_token:
        Atlassian API token for the account.
    project_key:
        Jira project key where the issue will be created (e.g. ``OPS``).
    issue_type:
        Issue type name, defaults to ``"Bug"``.
    priority:
        Optional priority name, e.g. ``"High"``.
    labels:
        Optional list of labels to attach to the issue.
    alert_on_healthy:
        When *True* also create an issue for healthy runs (default ``False``).
    session:
        Optional :class:`requests.Session` for testing / connection reuse.
    """

    base_url: str = ""
    email: str = ""
    api_token: str = ""
    project_key: str = ""
    issue_type: str = "Bug"
    priority: Optional[str] = None
    labels: list[str] = field(default_factory=list)
    alert_on_healthy: bool = False
    session: Optional[requests.Session] = None

    def __post_init__(self) -> None:
        if not self.base_url:
            raise ValueError("JiraAlerter requires 'base_url'")
        if not self.email:
            raise ValueError("JiraAlerter requires 'email'")
        if not self.api_token:
            raise ValueError("JiraAlerter requires 'api_token'")
        if not self.project_key:
            raise ValueError("JiraAlerter requires 'project_key'")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _session_or_default(self) -> requests.Session:
        if self.session is not None:
            return self.session
        s = requests.Session()
        s.auth = (self.email, self.api_token)
        s.headers.update({"Content-Type": "application/json", "Accept": "application/json"})
        return s

    def _build_payload(self, ctx: AlertContext) -> dict:
        status_label = "HEALTHY" if ctx.is_healthy else "UNHEALTHY"
        failed_names = [r.check_name for r in ctx.failed]
        warned_names = [r.check_name for r in ctx.warned]

        summary = f"[PipeWarden] Pipeline {status_label}: {ctx.pipeline_name}"

        lines = [
            f"*Pipeline:* {ctx.pipeline_name}",
            f"*Status:* {status_label}",
            f"*Total checks:* {len(ctx.results)}",
        ]
        if failed_names:
            lines.append(f"*Failed checks:* {', '.join(failed_names)}")
        if warned_names:
            lines.append(f"*Warned checks:* {', '.join(warned_names)}")

        fields: dict = {
            "project": {"key": self.project_key},
            "summary": summary,
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "\n".join(lines)}],
                    }
                ],
            },
            "issuetype": {"name": self.issue_type},
        }

        if self.priority:
            fields["priority"] = {"name": self.priority}
        if self.labels:
            fields["labels"] = self.labels

        return {"fields": fields}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def send(self, ctx: AlertContext) -> None:
        if ctx.is_healthy and not self.alert_on_healthy:
            logger.debug("JiraAlerter: pipeline healthy, skipping issue creation.")
            return

        url = f"{self.base_url.rstrip('/')}/rest/api/3/issue"
        payload = self._build_payload(ctx)
        session = self._session_or_default()

        try:
            response = session.post(url, json=payload, timeout=10)
            response.raise_for_status()
            issue_key = response.json().get("key", "unknown")
            logger.info("JiraAlerter: created issue %s for pipeline '%s'.", issue_key, ctx.pipeline_name)
        except requests.RequestException as exc:
            logger.error("JiraAlerter: failed to create Jira issue — %s", exc)
