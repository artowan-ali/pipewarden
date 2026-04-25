"""Tests for SplunkAlerter."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from pipewarden.alerting.splunk_alerter import SplunkAlerter
from pipewarden.alerting.base import AlertContext
from pipewarden.checks.base import CheckResult, CheckStatus


def _make_result(name: str, status: CheckStatus, detail: str = "") -> CheckResult:
    return CheckResult(check_name=name, status=status, detail=detail)


@pytest.fixture()
def default_alerter(mock_session):
    return SplunkAlerter(
        hec_url="https://splunk.example.com:8088/services/collector/event",
        hec_token="test-hec-token",
        session=mock_session,
    )


@pytest.fixture()
def mock_session():
    session = MagicMock()
    session.post.return_value = MagicMock(status_code=200, raise_for_status=MagicMock())
    return session


@pytest.fixture()
def failed_context():
    return AlertContext(
        pipeline_name="test_pipeline",
        all_results=[
            _make_result("row_count", CheckStatus.FAILED, "Too few rows"),
            _make_result("null_check", CheckStatus.PASSED),
        ],
    )


@pytest.fixture()
def healthy_context():
    return AlertContext(
        pipeline_name="test_pipeline",
        all_results=[
            _make_result("row_count", CheckStatus.PASSED),
            _make_result("null_check", CheckStatus.PASSED),
        ],
    )


def test_raises_without_hec_url():
    with pytest.raises(ValueError, match="hec_url"):
        SplunkAlerter(hec_url="", hec_token="tok")


def test_raises_without_hec_token():
    with pytest.raises(ValueError, match="hec_token"):
        SplunkAlerter(hec_url="https://splunk.example.com", hec_token="")


def test_send_posts_to_hec(default_alerter, mock_session, failed_context):
    default_alerter.send(failed_context)
    mock_session.post.assert_called_once()
    call_kwargs = mock_session.post.call_args
    assert call_kwargs[0][0] == "https://splunk.example.com:8088/services/collector/event"


def test_authorization_header_uses_splunk_scheme(default_alerter, mock_session, failed_context):
    default_alerter.send(failed_context)
    headers = mock_session.post.call_args[1]["headers"]
    assert headers["Authorization"] == "Splunk test-hec-token"


def test_payload_contains_pipeline_name(default_alerter, mock_session, failed_context):
    default_alerter.send(failed_context)
    payload = mock_session.post.call_args[1]["json"]
    assert payload["event"]["pipeline"] == "test_pipeline"


def test_payload_status_unhealthy_on_failure(default_alerter, mock_session, failed_context):
    default_alerter.send(failed_context)
    payload = mock_session.post.call_args[1]["json"]
    assert payload["event"]["status"] == "unhealthy"


def test_payload_status_healthy(default_alerter, mock_session, healthy_context):
    default_alerter.send(healthy_context)
    payload = mock_session.post.call_args[1]["json"]
    assert payload["event"]["status"] == "healthy"


def test_payload_lists_failed_checks(default_alerter, mock_session, failed_context):
    default_alerter.send(failed_context)
    payload = mock_session.post.call_args[1]["json"]
    failures = payload["event"]["failures"]
    assert len(failures) == 1
    assert failures[0]["check"] == "row_count"
    assert failures[0]["detail"] == "Too few rows"


def test_custom_index_and_sourcetype(mock_session, failed_context):
    alerter = SplunkAlerter(
        hec_url="https://splunk.example.com:8088/services/collector/event",
        hec_token="tok",
        index="pipewarden",
        sourcetype="custom:pipewarden",
        session=mock_session,
    )
    alerter.send(failed_context)
    payload = mock_session.post.call_args[1]["json"]
    assert payload["index"] == "pipewarden"
    assert payload["sourcetype"] == "custom:pipewarden"


def test_raises_on_http_error(mock_session, failed_context):
    mock_session.post.return_value.raise_for_status.side_effect = Exception("HTTP 403")
    alerter = SplunkAlerter(
        hec_url="https://splunk.example.com:8088/services/collector/event",
        hec_token="tok",
        session=mock_session,
    )
    with pytest.raises(Exception, match="HTTP 403"):
        alerter.send(failed_context)
