from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from pipewarden.alerting.base import AlertContext
from pipewarden.alerting.rollbar_alerter import RollbarAlerter
from pipewarden.checks.base import CheckResult, CheckStatus


def _make_result(name: str, status: CheckStatus, detail: str = "") -> CheckResult:
    return CheckResult(check_name=name, status=status, detail=detail)


@pytest.fixture
def default_alerter() -> RollbarAlerter:
    return RollbarAlerter(access_token="test-token-abc", environment="staging")


@pytest.fixture
def failed_context() -> AlertContext:
    return AlertContext(
        pipeline_name="orders_pipeline",
        results=[
            _make_result("row_count", CheckStatus.FAILED, "too few rows"),
            _make_result("null_check", CheckStatus.PASSED),
            _make_result("freshness", CheckStatus.WARNING, "aging data"),
        ],
    )


@pytest.fixture
def healthy_context() -> AlertContext:
    return AlertContext(
        pipeline_name="orders_pipeline",
        results=[_make_result("row_count", CheckStatus.PASSED)],
    )


def test_raises_without_access_token() -> None:
    with pytest.raises(ValueError, match="access_token"):
        RollbarAlerter(access_token="")


def test_no_request_when_healthy(default_alerter, healthy_context) -> None:
    with patch("pipewarden.alerting.rollbar_alerter.requests.Session") as mock_cls:
        default_alerter.send(healthy_context)
        mock_cls.assert_not_called()


def test_sends_on_failure(default_alerter, failed_context) -> None:
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_session.post.return_value = mock_response
    default_alerter.session = mock_session

    default_alerter.send(failed_context)

    mock_session.post.assert_called_once()
    mock_response.raise_for_status.assert_called_once()


def test_payload_contains_access_token(default_alerter, failed_context) -> None:
    payload = default_alerter._build_payload(failed_context)
    assert payload["access_token"] == "test-token-abc"


def test_payload_level_is_error_on_failure(default_alerter, failed_context) -> None:
    payload = default_alerter._build_payload(failed_context)
    assert payload["data"]["level"] == "error"


def test_payload_level_is_warning_when_only_warnings() -> None:
    alerter = RollbarAlerter(access_token="tok")
    context = AlertContext(
        pipeline_name="pipe",
        results=[_make_result("check", CheckStatus.WARNING)],
    )
    payload = alerter._build_payload(context)
    assert payload["data"]["level"] == "warning"


def test_payload_includes_pipeline_name(default_alerter, failed_context) -> None:
    payload = default_alerter._build_payload(failed_context)
    assert payload["data"]["custom"]["pipeline"] == "orders_pipeline"


def test_payload_lists_failed_checks(default_alerter, failed_context) -> None:
    payload = default_alerter._build_payload(failed_context)
    assert "row_count" in payload["data"]["custom"]["failed_checks"]


def test_payload_environment(default_alerter, failed_context) -> None:
    payload = default_alerter._build_payload(failed_context)
    assert payload["data"]["environment"] == "staging"


def test_raises_on_http_error(default_alerter, failed_context) -> None:
    mock_session = MagicMock()
    mock_session.post.return_value.raise_for_status.side_effect = Exception("HTTP 401")
    default_alerter.session = mock_session

    with pytest.raises(Exception, match="HTTP 401"):
        default_alerter.send(failed_context)
