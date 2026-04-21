from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from pipewarden.alerting.base import AlertContext
from pipewarden.alerting.slack_alerter import SlackAlerter
from pipewarden.checks.base import CheckResult, CheckStatus


WEBHOOK = "https://hooks.slack.com/services/TEST/FAKE/URL"


def _make_result(name: str, status: CheckStatus, details: str = "") -> CheckResult:
    return CheckResult(check_name=name, status=status, details=details)


@pytest.fixture
def default_alerter() -> SlackAlerter:
    return SlackAlerter(webhook_url=WEBHOOK)


@pytest.fixture
def failed_context() -> AlertContext:
    return AlertContext(
        all_results=[
            _make_result("row_count", CheckStatus.FAILED, "Too few rows"),
            _make_result("null_check", CheckStatus.PASSED),
        ]
    )


@pytest.fixture
def healthy_context() -> AlertContext:
    return AlertContext(
        all_results=[
            _make_result("row_count", CheckStatus.PASSED),
            _make_result("null_check", CheckStatus.PASSED),
        ]
    )


def test_raises_without_webhook_url() -> None:
    with pytest.raises(ValueError, match="webhook_url"):
        SlackAlerter(webhook_url="")


def test_payload_contains_check_name(default_alerter, failed_context) -> None:
    payload = default_alerter._build_payload(failed_context)
    assert "row_count" in payload["text"]


def test_payload_contains_failure_details(default_alerter, failed_context) -> None:
    payload = default_alerter._build_payload(failed_context)
    assert "Too few rows" in payload["text"]


def test_payload_includes_channel_when_set(failed_context) -> None:
    alerter = SlackAlerter(webhook_url=WEBHOOK, channel="#alerts")
    payload = alerter._build_payload(failed_context)
    assert payload["channel"] == "#alerts"


def test_payload_omits_channel_when_unset(default_alerter, failed_context) -> None:
    payload = default_alerter._build_payload(failed_context)
    assert "channel" not in payload


def test_send_posts_json_to_webhook(default_alerter, failed_context) -> None:
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_response) as mock_open:
        default_alerter.send(failed_context)
        mock_open.assert_called_once()
        req = mock_open.call_args[0][0]
        body = json.loads(req.data.decode())
        assert "text" in body


def test_send_skips_healthy_pipeline_with_no_warnings(
    default_alerter, healthy_context
) -> None:
    with patch("urllib.request.urlopen") as mock_open:
        default_alerter.send(healthy_context)
        mock_open.assert_not_called()


def test_send_raises_on_bad_status(default_alerter, failed_context) -> None:
    mock_response = MagicMock()
    mock_response.status = 500
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_response):
        with pytest.raises(RuntimeError, match="500"):
            default_alerter.send(failed_context)


def test_warned_results_included_in_text(failed_context) -> None:
    alerter = SlackAlerter(webhook_url=WEBHOOK, notify_on_warn=True)
    context = AlertContext(
        all_results=[
            _make_result("freshness", CheckStatus.WARNED, "Data aging"),
            _make_result("row_count", CheckStatus.PASSED),
        ]
    )
    payload = alerter._build_payload(context)
    assert "freshness" in payload["text"]
    assert "Data aging" in payload["text"]
