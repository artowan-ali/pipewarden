from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from pipewarden.alerting.base import AlertContext
from pipewarden.alerting.zendesk_alerter import ZendeskAlerter
from pipewarden.checks.base import CheckResult, CheckStatus


def _make_result(name: str, status: CheckStatus, details: str = "") -> CheckResult:
    return CheckResult(check_name=name, status=status, details=details)


@pytest.fixture
def default_alerter():
    return ZendeskAlerter(
        subdomain="mycompany",
        email="admin@example.com",
        api_token="secret-token",
    )


@pytest.fixture
def failed_context():
    return AlertContext(
        pipeline_name="orders_pipeline",
        results=[
            _make_result("RowCountCheck", CheckStatus.FAILED, "too few rows"),
            _make_result("NullCheck", CheckStatus.WARNING, "some nulls"),
            _make_result("SchemaCheck", CheckStatus.PASSED),
        ],
    )


@pytest.fixture
def healthy_context():
    return AlertContext(
        pipeline_name="orders_pipeline",
        results=[
            _make_result("RowCountCheck", CheckStatus.PASSED),
            _make_result("SchemaCheck", CheckStatus.PASSED),
        ],
    )


def test_raises_without_subdomain():
    with pytest.raises(ValueError, match="subdomain"):
        ZendeskAlerter(subdomain="", email="a@b.com", api_token="tok")


def test_raises_without_email():
    with pytest.raises(ValueError, match="email"):
        ZendeskAlerter(subdomain="co", email="", api_token="tok")


def test_raises_without_api_token():
    with pytest.raises(ValueError, match="api_token"):
        ZendeskAlerter(subdomain="co", email="a@b.com", api_token="")


def test_does_not_send_when_healthy(default_alerter, healthy_context):
    mock_session = MagicMock()
    default_alerter._session = mock_session
    default_alerter.send(healthy_context)
    mock_session.post.assert_not_called()


def test_sends_ticket_on_failure(default_alerter, failed_context):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_session = MagicMock()
    mock_session.post.return_value = mock_response
    default_alerter._session = mock_session

    default_alerter.send(failed_context)

    mock_session.post.assert_called_once()
    url, kwargs = mock_session.post.call_args[0][0], mock_session.post.call_args[1]
    assert "mycompany.zendesk.com" in url
    assert "tickets.json" in url


def test_payload_contains_pipeline_name(default_alerter, failed_context):
    payload = default_alerter._build_payload(failed_context)
    ticket = payload["ticket"]
    assert "orders_pipeline" in ticket["subject"]
    assert "orders_pipeline" in ticket["comment"]["body"]


def test_payload_contains_failed_checks(default_alerter, failed_context):
    payload = default_alerter._build_payload(failed_context)
    body = payload["ticket"]["comment"]["body"]
    assert "RowCountCheck" in body
    assert "too few rows" in body


def test_payload_tags_default(default_alerter, failed_context):
    payload = default_alerter._build_payload(failed_context)
    assert "pipewarden" in payload["ticket"]["tags"]


def test_payload_custom_priority_and_type(failed_context):
    alerter = ZendeskAlerter(
        subdomain="co",
        email="a@b.com",
        api_token="tok",
        priority="urgent",
        ticket_type="problem",
    )
    payload = alerter._build_payload(failed_context)
    assert payload["ticket"]["priority"] == "urgent"
    assert payload["ticket"]["type"] == "problem"


def test_payload_includes_assignee_email(failed_context):
    alerter = ZendeskAlerter(
        subdomain="co",
        email="a@b.com",
        api_token="tok",
        assignee_email="oncall@example.com",
    )
    payload = alerter._build_payload(failed_context)
    assert payload["ticket"]["assignee_email"] == "oncall@example.com"


def test_raises_on_http_error(default_alerter, failed_context):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception("403 Forbidden")
    mock_session = MagicMock()
    mock_session.post.return_value = mock_response
    default_alerter._session = mock_session

    with pytest.raises(Exception, match="403"):
        default_alerter.send(failed_context)
