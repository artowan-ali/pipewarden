"""Tests for MSTeamsWebhookAlerter."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from pipewarden.alerting.base import AlertContext
from pipewarden.alerting.msteams_webhook_alerter import MSTeamsWebhookAlerter
from pipewarden.checks.base import CheckResult, CheckStatus


def _make_result(name: str, status: CheckStatus, detail: str = "") -> CheckResult:
    return CheckResult(check_name=name, status=status, detail=detail)


@pytest.fixture()
def default_alerter() -> MSTeamsWebhookAlerter:
    return MSTeamsWebhookAlerter(
        webhook_url="https://outlook.office.com/webhook/test",
        pipeline_name="Test Pipeline",
    )


@pytest.fixture()
def failed_context() -> AlertContext:
    return AlertContext(
        results=[
            _make_result("row_count", CheckStatus.FAILED, "too few rows"),
            _make_result("null_check", CheckStatus.PASSED),
        ]
    )


@pytest.fixture()
def healthy_context() -> AlertContext:
    return AlertContext(
        results=[
            _make_result("row_count", CheckStatus.PASSED),
            _make_result("null_check", CheckStatus.PASSED),
        ]
    )


def test_raises_without_webhook_url() -> None:
    with pytest.raises(ValueError, match="webhook_url"):
        MSTeamsWebhookAlerter(webhook_url=None)


def test_raises_with_empty_webhook_url() -> None:
    with pytest.raises(ValueError, match="webhook_url"):
        MSTeamsWebhookAlerter(webhook_url="")


def test_payload_structure_on_failure(
    default_alerter: MSTeamsWebhookAlerter, failed_context: AlertContext
) -> None:
    payload = default_alerter._build_payload(failed_context)
    assert payload["@type"] == "MessageCard"
    assert "Unhealthy" in payload["summary"]
    assert payload["themeColor"] == "FF0000"


def test_payload_structure_on_success(
    default_alerter: MSTeamsWebhookAlerter, healthy_context: AlertContext
) -> None:
    payload = default_alerter._build_payload(healthy_context)
    assert "Healthy" in payload["summary"]
    assert payload["themeColor"] == "00FF00"


def test_payload_includes_pipeline_name(
    default_alerter: MSTeamsWebhookAlerter, failed_context: AlertContext
) -> None:
    payload = default_alerter._build_payload(failed_context)
    assert "Test Pipeline" in payload["summary"]


def test_payload_lists_failed_checks(
    default_alerter: MSTeamsWebhookAlerter, failed_context: AlertContext
) -> None:
    payload = default_alerter._build_payload(failed_context)
    facts = payload["sections"][0]["facts"]
    fact_titles = {f["title"]: f["value"] for f in facts}
    assert "Failed Checks" in fact_titles
    assert "row_count" in fact_titles["Failed Checks"]


def test_send_posts_json(
    default_alerter: MSTeamsWebhookAlerter, failed_context: AlertContext
) -> None:
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_response) as mock_open:
        default_alerter.send(failed_context)
        mock_open.assert_called_once()
        req = mock_open.call_args[0][0]
        body = json.loads(req.data.decode())
        assert body["@type"] == "MessageCard"


def test_send_raises_on_bad_status(
    default_alerter: MSTeamsWebhookAlerter, failed_context: AlertContext
) -> None:
    mock_response = MagicMock()
    mock_response.status = 500
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_response):
        with pytest.raises(RuntimeError, match="unexpected status"):
            default_alerter.send(failed_context)
