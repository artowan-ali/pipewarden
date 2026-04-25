"""Tests for GrafanaAlerter."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from pipewarden.alerting.grafana_alerter import GrafanaAlerter
from pipewarden.alerting.base import AlertContext
from pipewarden.checks.base import CheckResult, CheckStatus


def _make_result(name: str, status: CheckStatus, details: str = "") -> CheckResult:
    return CheckResult(check_name=name, status=status, details=details)


@pytest.fixture()
def mock_session() -> MagicMock:
    session = MagicMock()
    response = MagicMock()
    response.raise_for_status.return_value = None
    session.post.return_value = response
    return session


@pytest.fixture()
def default_alerter(mock_session: MagicMock) -> GrafanaAlerter:
    return GrafanaAlerter(
        base_url="https://grafana.example.com",
        api_key="glsa_test_key",
        session=mock_session,
    )


@pytest.fixture()
def failed_context() -> AlertContext:
    return AlertContext(
        pipeline_name="orders_pipeline",
        results=[
            _make_result("RowCount", CheckStatus.FAILED, "too few rows"),
            _make_result("NullCheck", CheckStatus.PASSED),
        ],
    )


@pytest.fixture()
def healthy_context() -> AlertContext:
    return AlertContext(
        pipeline_name="orders_pipeline",
        results=[_make_result("RowCount", CheckStatus.PASSED)],
    )


# --- validation -----------------------------------------------------------

def test_raises_without_base_url() -> None:
    with pytest.raises(ValueError, match="base_url"):
        GrafanaAlerter(api_key="key")


def test_raises_without_api_key() -> None:
    with pytest.raises(ValueError, match="api_key"):
        GrafanaAlerter(base_url="https://grafana.example.com")


# --- send behaviour -------------------------------------------------------

def test_does_not_post_when_healthy(
    default_alerter: GrafanaAlerter,
    healthy_context: AlertContext,
    mock_session: MagicMock,
) -> None:
    default_alerter.send(healthy_context)
    mock_session.post.assert_not_called()


def test_posts_on_failure(
    default_alerter: GrafanaAlerter,
    failed_context: AlertContext,
    mock_session: MagicMock,
) -> None:
    default_alerter.send(failed_context)
    mock_session.post.assert_called_once()
    url, _ = mock_session.post.call_args[0][0], mock_session.post.call_args
    assert "/api/annotations" in mock_session.post.call_args[0][0]


def test_payload_contains_pipeline_name(
    default_alerter: GrafanaAlerter,
    failed_context: AlertContext,
    mock_session: MagicMock,
) -> None:
    default_alerter.send(failed_context)
    payload = mock_session.post.call_args[1]["json"]
    assert "orders_pipeline" in payload["text"]


def test_payload_tags_include_alerting_state(
    default_alerter: GrafanaAlerter,
    failed_context: AlertContext,
    mock_session: MagicMock,
) -> None:
    default_alerter.send(failed_context)
    payload = mock_session.post.call_args[1]["json"]
    assert "alerting" in payload["tags"]
    assert "pipewarden" in payload["tags"]


def test_payload_includes_dashboard_uid(
    mock_session: MagicMock,
    failed_context: AlertContext,
) -> None:
    alerter = GrafanaAlerter(
        base_url="https://grafana.example.com",
        api_key="key",
        dashboard_uid="abc123",
        session=mock_session,
    )
    alerter.send(failed_context)
    payload = mock_session.post.call_args[1]["json"]
    assert payload["dashboardUID"] == "abc123"


def test_warn_only_skipped_when_alert_on_warn_false(
    mock_session: MagicMock,
) -> None:
    warn_context = AlertContext(
        pipeline_name="p",
        results=[_make_result("NullCheck", CheckStatus.WARNED, "some nulls")],
    )
    alerter = GrafanaAlerter(
        base_url="https://grafana.example.com",
        api_key="key",
        alert_on_warn=False,
        session=mock_session,
    )
    alerter.send(warn_context)
    mock_session.post.assert_not_called()
