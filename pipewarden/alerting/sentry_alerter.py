"""Sentry alerter for PipeWarden.

Sends pipeline failure alerts to Sentry as captured messages or events,
allowing teams already using Sentry for error tracking to consolidate
ETL health alerts in the same platform.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from pipewarden.alerting.base import AlertContext, BaseAlerter


@dataclass
class SentryAlerter(BaseAlerter):
    """Send pipeline health alerts to Sentry.

    Requires the ``sentry-sdk`` package to be installed::

        pip install sentry-sdk

    Attributes:
        dsn: Sentry Data Source Name (DSN) for your project.
        environment: Environment tag attached to each event (e.g. "production").
        release: Optional release/version string to attach to events.
        extra_tags: Additional key-value tags to include on every event.
        alert_on_warn: If True, WARN-level results also trigger an event.
            Defaults to False (only FAIL triggers an event).
    """

    dsn: str = ""
    environment: str = "production"
    release: Optional[str] = None
    extra_tags: dict = field(default_factory=dict)
    alert_on_warn: bool = False

    def __post_init__(self) -> None:
        if not self.dsn:
            raise ValueError("SentryAlerter requires a non-empty 'dsn'.")

        try:
            import sentry_sdk  # noqa: F401
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "sentry-sdk is required for SentryAlerter. "
                "Install it with: pip install sentry-sdk"
            ) from exc

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _init_sdk(self) -> None:  # pragma: no cover
        """Initialise the Sentry SDK with the configured DSN.

        Called lazily inside :meth:`send` so that the SDK is only
        initialised when an alert is actually dispatched.
        """
        import sentry_sdk

        sentry_sdk.init(
            dsn=self.dsn,
            environment=self.environment,
            release=self.release,
        )

    def _build_extra(self, ctx: AlertContext) -> dict:
        """Build the ``extra`` context dict attached to the Sentry event."""
        failed_names = [r.check_name for r in ctx.failures]
        warned_names = [r.check_name for r in ctx.warnings]
        return {
            "pipeline": ctx.pipeline_name,
            "total_checks": len(ctx.results),
            "failed_checks": failed_names,
            "warned_checks": warned_names,
        }

    # ------------------------------------------------------------------
    # BaseAlerter interface
    # ------------------------------------------------------------------

    def send(self, ctx: AlertContext) -> None:  # pragma: no cover
        """Capture a Sentry event when the pipeline is unhealthy.

        If the pipeline is healthy (no failures, no warnings that exceed
        the ``alert_on_warn`` threshold) this method is a no-op.

        Args:
            ctx: Alert context produced by the pipeline runner.
        """
        has_failures = bool(ctx.failures)
        has_warnings = self.alert_on_warn and bool(ctx.warnings)

        if not has_failures and not has_warnings:
            return

        import sentry_sdk

        self._init_sdk()

        status = "FAILED" if has_failures else "WARNED"
        message = (
            f"[PipeWarden] Pipeline '{ctx.pipeline_name}' {status}: "
            f"{len(ctx.failures)} failure(s), {len(ctx.warnings)} warning(s)."
        )

        tags = {"pipeline": ctx.pipeline_name, **self.extra_tags}
        extra = self._build_extra(ctx)

        with sentry_sdk.push_scope() as scope:
            scope.set_level("error" if has_failures else "warning")
            for key, value in tags.items():
                scope.set_tag(key, value)
            scope.set_extra("pipewarden", extra)
            sentry_sdk.capture_message(message)
