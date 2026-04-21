from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from pipewarden.alerting.email_alerter import EmailAlerter
from pipewarden.alerting.base import AlertContext
from pipewarden.checks.base import CheckResult, CheckStatus


def _make_result(name: str, status: CheckStatus, details: str = "") -> CheckResult:
    return CheckResult(check_name=name, status=status, details=details)


@pytest.fixture
def default_alerter() -> EmailAlerter:
    return EmailAlerter(
        smtp_host="smtp.example.com",
        smtp_port=587,
        sender="pw@example.com",
        recipients=["ops@example.com"],
    )


@pytest.fixture
def failed_context() -> AlertContext:
    return AlertContext(
        results=[
            _make_result("row_count", CheckStatus.FAILED, "too few rows"),
            _make_result("null_check", CheckStatus.PASSED),
        ]
    )


@pytest.fixture
def healthy_context() -> AlertContext:
    return AlertContext(
        results=[_make_result("row_count", CheckStatus.PASSED)]
    )


def test_raises_without_recipients() -> None:
    with pytest.raises(ValueError, match="recipient"):
        EmailAlerter(recipients=[])


def test_no_email_sent_when_healthy(default_alerter, healthy_context) -> None:
    with patch("smtplib.SMTP") as mock_smtp:
        default_alerter.send(healthy_context)
        mock_smtp.assert_not_called()


def test_email_sent_when_failed(default_alerter, failed_context) -> None:
    with patch("smtplib.SMTP") as mock_smtp:
        instance = MagicMock()
        mock_smtp.return_value.__enter__.return_value = instance
        default_alerter.send(failed_context)
        instance.sendmail.assert_called_once()


def test_subject_contains_unhealthy(default_alerter, failed_context) -> None:
    subject = default_alerter._build_subject(failed_context)
    assert "UNHEALTHY" in subject


def test_subject_contains_healthy(default_alerter, healthy_context) -> None:
    subject = default_alerter._build_subject(healthy_context)
    assert "HEALTHY" in subject


def test_body_lists_failed_checks(default_alerter, failed_context) -> None:
    body = default_alerter._build_body(failed_context)
    assert "row_count" in body
    assert "too few rows" in body


def test_alert_on_warn_sends_email_for_warning() -> None:
    alerter = EmailAlerter(
        recipients=["ops@example.com"],
        alert_on_warn=True,
    )
    ctx = AlertContext(
        results=[_make_result("freshness", CheckStatus.WARNED, "aging data")]
    )
    with patch("smtplib.SMTP") as mock_smtp:
        instance = MagicMock()
        mock_smtp.return_value.__enter__.return_value = instance
        alerter.send(ctx)
        instance.sendmail.assert_called_once()


def test_smtp_exception_is_logged_not_raised(default_alerter, failed_context) -> None:
    with patch("smtplib.SMTP", side_effect=Exception("connection refused")):
        # Should not raise
        default_alerter.send(failed_context)
