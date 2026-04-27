"""Tests for NewRelicAlerter."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from pipewarden.alerting.base import AlertContext
from pipewarden.alerting.newrelic_alerter import NewRelicAlerter, _EU_ENDPOINT, _US_ENDPOINT
from pipewarden.checks.base import CheckResult, CheckStatus


def _make_result(name: str, status: CheckStatus, detail: str = "") -> CheckResult:
    return CheckResult(
        check_name=name,
        status=status,
        detail=detail,
        checked_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


@pytest.fixture
def default_alerter() -> NewRelicAlerter:
    return NewRelicAlerter(api_key="insert-key-123", account_id="9876543")


@pytest.fixture
def failed_context() -> AlertContext:
    return AlertContext(
        pipeline_name="orders",
        results=[
            _make_result("row_count", CheckStatus.FAILED, "too few rows"),
            _make_result("null_check", CheckStatus.PASSED),
            _make_result("freshness", CheckStatus.WARNING, "aging data"),
        ],
    )


@pytest.fixture
def healthy_context() -> AlertContext:
    return AlertContext(
        pipeline_name="orders",
        results=[_make_result("row_count", CheckStatus.PASSED)],
    )


def test_raises_without_api_key():
    with pytest.raises(ValueError, match="api_key"):
        NewRelicAlerter(api_key="", account_id="123")


def test_raises_without_account_id():
    with pytest.raises(ValueError, match="account_id"):
        NewRelicAlerter(api_key="key", account_id="")


def test_us_endpoint(default_alerter):
    assert default_alerter._endpoint() == _US_ENDPOINT.format(account_id="9876543")


def test_eu_endpoint():
    alerter = NewRelicAlerter(api_key="key", account_id="111", eu_region=True)
    assert alerter._endpoint() == _EU_ENDPOINT.format(account_id="111")


def test_payload_structure(default_alerter, failed_context):
    payload = default_alerter._build_payload(failed_context)
    assert len(payload) == 1
    event = payload[0]
    assert event["eventType"] == "PipeWardenRun"
    assert event["pipeline"] == "orders"
    assert event["healthy"] is False
    assert event["total_checks"] == 3
    assert event["failed_checks"] == 1
    assert event["warned_checks"] == 1
    assert "row_count" in event["failed_check_names"]
    assert "freshness" in event["warned_check_names"]


def test_payload_healthy(default_alerter, healthy_context):
    event = default_alerter._build_payload(healthy_context)[0]
    assert event["healthy"] is True
    assert event["failed_checks"] == 0


def test_send_posts_to_correct_url(default_alerter, failed_context):
    mock_session = MagicMock()
    mock_session.post.return_value = MagicMock(status_code=200)
    default_alerter.session = mock_session

    default_alerter.send(failed_context)

    mock_session.post.assert_called_once()
    call_kwargs = mock_session.post.call_args
    assert "9876543" in call_kwargs[0][0]


def test_send_includes_insert_key_header(default_alerter, failed_context):
    mock_session = MagicMock()
    mock_session.post.return_value = MagicMock(status_code=200)
    default_alerter.session = mock_session

    default_alerter.send(failed_context)

    headers = mock_session.post.call_args[1]["headers"]
    assert headers["X-Insert-Key"] == "insert-key-123"


def test_send_raises_on_http_error(default_alerter, failed_context):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception("403 Forbidden")
    mock_session = MagicMock()
    mock_session.post.return_value = mock_response
    default_alerter.session = mock_session

    with pytest.raises(Exception, match="403"):
        default_alerter.send(failed_context)


def test_custom_event_type():
    alerter = NewRelicAlerter(api_key="k", account_id="1", event_type="MyPipelineEvent")
    ctx = AlertContext(pipeline_name="p", results=[_make_result("c", CheckStatus.PASSED)])
    assert alerter._build_payload(ctx)[0]["eventType"] == "MyPipelineEvent"
