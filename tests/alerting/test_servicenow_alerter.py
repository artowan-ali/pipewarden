"""Tests for ServiceNowAlerter."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from pipewarden.alerting.servicenow_alerter import ServiceNowAlerter
from pipewarden.alerting.base import AlertContext
from pipewarden.checks.base import CheckResult, CheckStatus


def _make_result(name: str, status: CheckStatus, detail: str = "") -> CheckResult:
    return CheckResult(check_name=name, status=status, detail=detail)


@pytest.fixture()
def default_alerter(mock_session):
    return ServiceNowAlerter(
        instance="dev99999",
        username="admin",
        password="secret",
        _session=mock_session,
    )


@pytest.fixture()
def mock_session():
    session = MagicMock()
    session.post.return_value = MagicMock(status_code=201, raise_for_status=MagicMock())
    return session


@pytest.fixture()
def failed_context():
    return AlertContext(
        pipeline_name="orders_pipeline",
        results=[
            _make_result("row_count", CheckStatus.FAILED, "too few rows"),
            _make_result("null_check", CheckStatus.PASSED),
        ],
    )


@pytest.fixture()
def healthy_context():
    return AlertContext(
        pipeline_name="orders_pipeline",
        results=[_make_result("row_count", CheckStatus.PASSED)],
    )


def test_raises_without_instance():
    with pytest.raises(ValueError, match="instance"):
        ServiceNowAlerter(instance="", username="u", password="p")


def test_raises_without_credentials():
    with pytest.raises(ValueError, match="username"):
        ServiceNowAlerter(instance="dev1", username="", password="")


def test_sends_on_failure(default_alerter, mock_session, failed_context):
    default_alerter.send(failed_context)
    mock_session.post.assert_called_once()
    url, kwargs = mock_session.post.call_args[0][0], mock_session.post.call_args[1]
    assert "incident" in url
    assert "dev99999" in url


def test_payload_contains_pipeline_name(default_alerter, mock_session, failed_context):
    default_alerter.send(failed_context)
    payload = mock_session.post.call_args[1]["json"]
    assert "orders_pipeline" in payload["short_description"]
    assert "orders_pipeline" in payload["description"]


def test_payload_lists_failed_checks(default_alerter, mock_session, failed_context):
    default_alerter.send(failed_context)
    payload = mock_session.post.call_args[1]["json"]
    assert "row_count" in payload["description"]


def test_skips_healthy_run_by_default(default_alerter, mock_session, healthy_context):
    default_alerter.send(healthy_context)
    mock_session.post.assert_not_called()


def test_sends_healthy_when_only_on_failure_false(mock_session, healthy_context):
    alerter = ServiceNowAlerter(
        instance="dev99999",
        username="admin",
        password="secret",
        only_on_failure=False,
        _session=mock_session,
    )
    alerter.send(healthy_context)
    mock_session.post.assert_called_once()


def test_assignment_group_included_when_set(mock_session, failed_context):
    alerter = ServiceNowAlerter(
        instance="dev99999",
        username="admin",
        password="secret",
        assignment_group="data-engineering",
        _session=mock_session,
    )
    alerter.send(failed_context)
    payload = mock_session.post.call_args[1]["json"]
    assert payload["assignment_group"] == "data-engineering"


def test_urgency_and_impact_defaults(default_alerter, mock_session, failed_context):
    default_alerter.send(failed_context)
    payload = mock_session.post.call_args[1]["json"]
    assert payload["urgency"] == "2"
    assert payload["impact"] == "2"


def test_raises_on_http_error(mock_session, failed_context):
    mock_session.post.return_value.raise_for_status.side_effect = Exception("401")
    alerter = ServiceNowAlerter(
        instance="dev99999", username="admin", password="secret", _session=mock_session
    )
    with pytest.raises(Exception, match="401"):
        alerter.send(failed_context)
