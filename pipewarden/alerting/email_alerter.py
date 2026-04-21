from __future__ import annotations

import smtplib
import logging
from dataclasses import dataclass, field
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List

from pipewarden.alerting.base import BaseAlerter, AlertContext

logger = logging.getLogger(__name__)


@dataclass
class EmailAlerter(BaseAlerter):
    """Send pipeline alert notifications via SMTP email."""

    smtp_host: str = "localhost"
    smtp_port: int = 587
    username: str = ""
    password: str = ""
    sender: str = "pipewarden@localhost"
    recipients: List[str] = field(default_factory=list)
    use_tls: bool = True
    alert_on_warn: bool = False

    def __post_init__(self) -> None:
        if not self.recipients:
            raise ValueError("EmailAlerter requires at least one recipient.")

    def _build_subject(self, ctx: AlertContext) -> str:
        status = "UNHEALTHY" if not ctx.is_healthy() else "HEALTHY"
        return f"[PipeWarden] Pipeline {status} — {len(ctx.failed)} failed, {len(ctx.warned)} warned"

    def _build_body(self, ctx: AlertContext) -> str:
        lines = [f"Pipeline run completed.\n"]
        if ctx.failed:
            lines.append("FAILED checks:")
            for r in ctx.failed:
                lines.append(f"  ✗ {r.check_name}: {r.details}")
        if ctx.warned:
            lines.append("\nWARNING checks:")
            for r in ctx.warned:
                lines.append(f"  ⚠ {r.check_name}: {r.details}")
        if ctx.passed:
            lines.append(f"\nPassed: {len(ctx.passed)} check(s)")
        return "\n".join(lines)

    def send(self, ctx: AlertContext) -> None:
        should_alert = not ctx.is_healthy() or (self.alert_on_warn and ctx.warned)
        if not should_alert:
            logger.debug("EmailAlerter: pipeline healthy, skipping alert.")
            return

        subject = self._build_subject(ctx)
        body = self._build_body(ctx)

        msg = MIMEMultipart()
        msg["From"] = self.sender
        msg["To"] = ", ".join(self.recipients)
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.sendmail(self.sender, self.recipients, msg.as_string())
            logger.info("EmailAlerter: alert sent to %s", self.recipients)
        except smtplib.SMTPException as exc:
            logger.error("EmailAlerter: failed to send email — %s", exc)
