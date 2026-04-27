"""Tests for JiraAlerter."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from pipewarden.alerting.base import AlertContext
from pipewarden.alerting.jira_alerter import JiraAlerter
from pipewarden.checks.base import CheckResult, CheckStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(name: str, status: CheckStatus, detail: str = "") -> CheckResult:
    return CheckResult(check_name=name, status=status, detail=detail)


@pytest.fixture()
def default_alerter() -> JiraAlerter:
    return JiraAlerter(
        base_url="https://myorg.atlassian.net",
        email="user@example.com",
        api_token="secret-token",
        project_key="OPS",
    )


@pytest.fixture()
def failed_context() -> AlertContext:
    return AlertContext(
        pipeline_name="orders_pipeline",
        results=[
            _make_result("row_count", CheckStatus.FAILED, "too few rows"),
            _make_result("null_check", CheckStatus.PASSED),
            _make_result("freshness", CheckStatus.WARNED, "aging data"),
        ],
    )


@pytest.fixture()
def healthy_context() -> AlertContext:
    return AlertContext(
        pipeline_name="orders_pipeline",
        results=[
            _make_result("row_count", CheckStatus.PASSED),
            _make_result("null_check", CheckStatus.PASSED),
        ],
    )


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------

def test_raises_without_base_url():
    with pytest.raises(ValueError, match="base_url"):
        JiraAlerter(email="a@b.com", api_token="tok", project_key="OPS")


def test_raises_without_email():
    with pytest.raises(ValueError, match="email"):
        JiraAlerter(base_url="https://x.atlassian.net", api_token="tok", project_key="OPS")


def test_raises_without_api_token():
    with pytest.raises(ValueError, match="api_token"):
        JiraAlerter(base_url="https://x.atlassian.net", email="a@b.com", project_key="OPS")


def test_raises_without_project_key():
    with pytest.raises(ValueError, match="project_key"):
        JiraAlerter(base_url="https://x.atlassian.net", email="a@b.com", api_token="tok")


# ---------------------------------------------------------------------------
# Payload tests
# ---------------------------------------------------------------------------

def test_payload_summary_contains_pipeline_name(default_alerter, failed_context):
    payload = default_alerter._build_payload(failed_context)
    assert "orders_pipeline" in payload["fields"]["summary"]


def test_payload_marks_unhealthy(default_alerter, failed_context):
    payload = default_alerter._build_payload(failed_context)
    assert "UNHEALTHY" in payload["fields"]["summary"]


def test_payload_marks_healthy(default_alerter, healthy_context):
    payload = default_alerter._build_payload(healthy_context)
    assert "HEALTHY" in payload["fields"]["summary"]


def test_payload_includes_failed_check_name(default_alerter, failed_context):
    payload = default_alerter._build_payload(failed_context)
    doc_text = payload["fields"]["description"]["content"][0]["content"][0]["text"]
    assert "row_count" in doc_text


def test_payload_includes_priority_when_set(failed_context):
    alerter = JiraAlerter(
        base_url="https://myorg.atlassian.net",
        email="u@e.com",
        api_token="tok",
        project_key="OPS",
        priority="High",
    )
    payload = alerter._build_payload(failed_context)
    assert payload["fields"]["priority"] == {"name": "High"}


def test_payload_includes_labels_when_set(failed_context):
    alerter = JiraAlerter(
        base_url="https://myorg.atlassian.net",
        email="u@e.com",
        api_token="tok",
        project_key="OPS",
        labels=["etl", "monitoring"],
    )
    payload = alerter._build_payload(failed_context)
    assert payload["fields"]["labels"] == ["etl", "monitoring"]


# ---------------------------------------------------------------------------
# Send tests
# ---------------------------------------------------------------------------

def test_send_posts_to_correct_url(default_alerter, failed_context):
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {"key": "OPS-42"}
    mock_response.raise_for_status.return_value = None
    mock_session.post.return_value = mock_response
    default_alerter.session = mock_session

    default_alerter.send(failed_context)

    mock_session.post.assert_called_once()
    call_url = mock_session.post.call_args[0][0]
    assert call_url == "https://myorg.atlassian.net/rest/api/3/issue"


def test_send_skips_healthy_by_default(default_alerter, healthy_context):
    mock_session = MagicMock()
    default_alerter.session = mock_session

    default_alerter.send(healthy_context)

    mock_session.post.assert_not_called()


def test_send_healthy_when_alert_on_healthy_true(healthy_context):
    alerter = JiraAlerter(
        base_url="https://myorg.atlassian.net",
        email="u@e.com",
        api_token="tok",
        project_key="OPS",
        alert_on_healthy=True,
    )
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {"key": "OPS-1"}
    mock_response.raise_for_status.return_value = None
    mock_session.post.return_value = mock_response
    alerter.session = mock_session

    alerter.send(healthy_context)

    mock_session.post.assert_called_once()


def test_send_logs_error_on_request_exception(default_alerter, failed_context, caplog):
    mock_session = MagicMock()
    mock_session.post.side_effect = requests.RequestException("connection refused")
    default_alerter.session = mock_session

    import logging
    with caplog.at_level(logging.ERROR):
        default_alerter.send(failed_context)  # should not raise

    assert "connection refused" in caplog.text
