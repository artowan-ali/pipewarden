from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from pipewarden.alerting.discord_alerter import DiscordAlerter
from pipewarden.alerting.base import AlertContext
from pipewarden.checks.base import CheckResult, CheckStatus


def _make_result(name: str, status: CheckStatus, details: str = "") -> CheckResult:
    return CheckResult(check_name=name, status=status, details=details)


@pytest.fixture
def default_alerter() -> DiscordAlerter:
    return DiscordAlerter(webhook_url="https://discord.com/api/webhooks/test/token")


@pytest.fixture
def failed_context() -> AlertContext:
    return AlertContext(
        pipeline_name="test_pipeline",
        results=[
            _make_result("row_count", CheckStatus.FAILED, "too few rows"),
            _make_result("null_check", CheckStatus.WARNING, "some nulls found"),
            _make_result("schema_check", CheckStatus.PASSED),
        ],
    )


@pytest.fixture
def healthy_context() -> AlertContext:
    return AlertContext(
        pipeline_name="test_pipeline",
        results=[_make_result("row_count", CheckStatus.PASSED)],
    )


def test_raises_without_webhook_url() -> None:
    with pytest.raises(ValueError, match="webhook_url"):
        DiscordAlerter(webhook_url=None)


def test_raises_with_empty_webhook_url() -> None:
    with pytest.raises(ValueError, match="webhook_url"):
        DiscordAlerter(webhook_url="")


def test_send_skipped_when_healthy_and_only_on_failure(
    default_alerter: DiscordAlerter, healthy_context: AlertContext
) -> None:
    with patch("urllib.request.urlopen") as mock_open:
        default_alerter.send(healthy_context)
        mock_open.assert_not_called()


def test_send_fires_when_unhealthy(
    default_alerter: DiscordAlerter, failed_context: AlertContext
) -> None:
    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.status = 204

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_open:
        default_alerter.send(failed_context)
        mock_open.assert_called_once()


def test_payload_contains_pipeline_name(
    default_alerter: DiscordAlerter, failed_context: AlertContext
) -> None:
    payload = default_alerter._build_payload(failed_context)
    assert "test_pipeline" in payload["content"]


def test_payload_contains_failed_check_name(
    default_alerter: DiscordAlerter, failed_context: AlertContext
) -> None:
    payload = default_alerter._build_payload(failed_context)
    assert "row_count" in payload["content"]


def test_payload_contains_warning(
    default_alerter: DiscordAlerter, failed_context: AlertContext
) -> None:
    payload = default_alerter._build_payload(failed_context)
    assert "null_check" in payload["content"]


def test_custom_username() -> None:
    alerter = DiscordAlerter(
        webhook_url="https://discord.com/api/webhooks/x/y",
        username="MyBot",
    )
    ctx = AlertContext(
        pipeline_name="p",
        results=[_make_result("c", CheckStatus.FAILED, "bad")],
    )
    payload = alerter._build_payload(ctx)
    assert payload["username"] == "MyBot"


def test_avatar_url_included_when_set() -> None:
    alerter = DiscordAlerter(
        webhook_url="https://discord.com/api/webhooks/x/y",
        avatar_url="https://example.com/avatar.png",
    )
    ctx = AlertContext(
        pipeline_name="p",
        results=[_make_result("c", CheckStatus.FAILED, "bad")],
    )
    payload = alerter._build_payload(ctx)
    assert payload["avatar_url"] == "https://example.com/avatar.png"


def test_send_fires_when_healthy_and_only_on_failure_false(
    healthy_context: AlertContext,
) -> None:
    alerter = DiscordAlerter(
        webhook_url="https://discord.com/api/webhooks/x/y",
        only_on_failure=False,
    )
    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.status = 204

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_open:
        alerter.send(healthy_context)
        mock_open.assert_called_once()
