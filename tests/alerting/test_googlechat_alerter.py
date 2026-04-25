from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from pipewarden.alerting.base import AlertContext
from pipewarden.alerting.googlechat_alerter import GoogleChatAlerter
from pipewarden.checks.base import CheckResult, CheckStatus


def _make_result(name: str, status: CheckStatus, detail: str = "") -> CheckResult:
    return CheckResult(check_name=name, status=status, detail=detail)


@pytest.fixture
def default_alerter():
    return GoogleChatAlerter(webhook_url="https://chat.googleapis.com/v1/spaces/XXX/messages?key=abc")


@pytest.fixture
def failed_context():
    return AlertContext(
        pipeline_name="orders",
        results=[
            _make_result("row_count", CheckStatus.FAILED, "too few rows"),
            _make_result("null_check", CheckStatus.PASSED),
            _make_result("freshness", CheckStatus.WARNED, "aging data"),
        ],
    )


@pytest.fixture
def healthy_context():
    return AlertContext(
        pipeline_name="orders",
        results=[
            _make_result("row_count", CheckStatus.PASSED),
            _make_result("null_check", CheckStatus.PASSED),
        ],
    )


def test_raises_without_webhook_url():
    with pytest.raises(ValueError, match="webhook_url"):
        GoogleChatAlerter(webhook_url="")


def test_send_posts_to_webhook(default_alerter, failed_context):
    mock_session = MagicMock()
    mock_session.post.return_value = MagicMock(status_code=200)
    default_alerter.session = mock_session
    default_alerter.send(failed_context)
    mock_session.post.assert_called_once()
    _, kwargs = mock_session.post.call_args
    assert "text" in kwargs["json"]


def test_payload_contains_pipeline_name(default_alerter, failed_context):
    payload = default_alerter._build_payload(failed_context)
    assert "orders" in payload["text"]


def test_payload_marks_unhealthy(default_alerter, failed_context):
    payload = default_alerter._build_payload(failed_context)
    assert "UNHEALTHY" in payload["text"]


def test_payload_marks_healthy(default_alerter, healthy_context):
    payload = default_alerter._build_payload(healthy_context)
    assert "HEALTHY" in payload["text"]


def test_payload_includes_failure_detail(default_alerter, failed_context):
    payload = default_alerter._build_payload(failed_context)
    assert "too few rows" in payload["text"]


def test_only_on_failure_skips_healthy(default_alerter, healthy_context):
    default_alerter.only_on_failure = True
    mock_session = MagicMock()
    default_alerter.session = mock_session
    default_alerter.send(healthy_context)
    mock_session.post.assert_not_called()


def test_only_on_failure_sends_when_unhealthy(default_alerter, failed_context):
    default_alerter.only_on_failure = True
    mock_session = MagicMock()
    mock_session.post.return_value = MagicMock(status_code=200)
    default_alerter.session = mock_session
    default_alerter.send(failed_context)
    mock_session.post.assert_called_once()


def test_raises_on_http_error(default_alerter, failed_context):
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.HTTPError("403")
    mock_session.post.return_value = mock_response
    default_alerter.session = mock_session
    with pytest.raises(requests.HTTPError):
        default_alerter.send(failed_context)
