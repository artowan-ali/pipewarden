from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from pipewarden.alerting.base import AlertContext
from pipewarden.alerting.sns_alerter import SNSAlerter
from pipewarden.checks.base import CheckResult, CheckStatus


def _make_result(name: str, status: CheckStatus, message: str = "") -> CheckResult:
    return CheckResult(check_name=name, status=status, message=message)


@pytest.fixture()
def mock_client():
    return MagicMock()


@pytest.fixture()
default_alerter = None  # defined inline per test for clarity


@pytest.fixture()
def failed_context():
    return AlertContext(
        results=[
            _make_result("row_count", CheckStatus.FAILED, "Too few rows"),
            _make_result("null_check", CheckStatus.PASSED),
        ]
    )


@pytest.fixture()
def healthy_context():
    return AlertContext(
        results=[
            _make_result("row_count", CheckStatus.PASSED),
            _make_result("null_check", CheckStatus.PASSED),
        ]
    )


def test_raises_without_topic_arn():
    with pytest.raises(ValueError, match="topic_arn"):
        SNSAlerter(topic_arn="")


def test_no_publish_when_healthy(healthy_context, mock_client):
    alerter = SNSAlerter(topic_arn="arn:aws:sns:us-east-1:123:test", _client=mock_client)
    alerter.send(healthy_context)
    mock_client.publish.assert_not_called()


def test_publishes_on_failure(failed_context, mock_client):
    alerter = SNSAlerter(topic_arn="arn:aws:sns:us-east-1:123:test", _client=mock_client)
    alerter.send(failed_context)
    mock_client.publish.assert_called_once()
    call_kwargs = mock_client.publish.call_args.kwargs
    assert call_kwargs["TopicArn"] == "arn:aws:sns:us-east-1:123:test"
    assert "UNHEALTHY" in call_kwargs["Message"]
    assert "row_count" in call_kwargs["Message"]


def test_custom_subject_is_used(failed_context, mock_client):
    alerter = SNSAlerter(
        topic_arn="arn:aws:sns:us-east-1:123:test",
        subject="Custom Subject",
        _client=mock_client,
    )
    alerter.send(failed_context)
    call_kwargs = mock_client.publish.call_args.kwargs
    assert call_kwargs["Subject"] == "Custom Subject"


def test_message_includes_failed_check_details(failed_context, mock_client):
    alerter = SNSAlerter(topic_arn="arn:aws:sns:us-east-1:123:test", _client=mock_client)
    alerter.send(failed_context)
    message = mock_client.publish.call_args.kwargs["Message"]
    assert "Too few rows" in message
    assert "FAILED" in message.upper()


def test_warned_checks_included_in_message(mock_client):
    context = AlertContext(
        results=[
            _make_result("freshness", CheckStatus.WARNING, "Data aging"),
            _make_result("row_count", CheckStatus.PASSED),
        ]
    )
    alerter = SNSAlerter(topic_arn="arn:aws:sns:us-east-1:123:test", _client=mock_client)
    alerter.send(context)
    message = mock_client.publish.call_args.kwargs["Message"]
    assert "freshness" in message
    assert "Data aging" in message
