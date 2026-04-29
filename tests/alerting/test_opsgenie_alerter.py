from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from pipewarden.alerting.base import AlertContext
from pipewarden.alerting.opsgenie_alerter import OpsGenieAlerter
from pipewarden.checks.base import CheckResult, CheckStatus


def _make_result(name: str, status: CheckStatus, detail: str = "") -> CheckResult:
    return CheckResult(check_name=name, status=status, detail=detail)


@pytest.fixture
def default_alerter() -> OpsGenieAlerter:
    return OpsGenieAlerter(api_key="test-key-123", pipeline_name="test_pipeline")


@pytest.fixture
def failed_context() -> AlertContext:
    return AlertContext(
        pipeline_name="test_pipeline",
        results=[
            _make_result("row_count", CheckStatus.FAILED, "too few rows"),
            _make_result("null_check", CheckStatus.PASSED),
            _make_result("freshness", CheckStatus.WARNING, "aging data"),
        ],
    )


@pytest.fixture
def healthy_context() -> AlertContext:
    return AlertContext(
        pipeline_name="test_pipeline",
        results=[
            _make_result("row_count", CheckStatus.PASSED),
            _make_result("null_check", CheckStatus.PASSED),
        ],
    )


def test_raises_without_api_key() -> None:
    with pytest.raises(ValueError, match="api_key"):
        OpsGenieAlerter(api_key="", pipeline_name="p")


def test_raises_with_invalid_priority() -> None:
    with pytest.raises(ValueError, match="priority"):
        OpsGenieAlerter(api_key="k", pipeline_name="p", priority="P9")


def test_us_base_url(default_alerter: OpsGenieAlerter) -> None:
    assert "api.opsgenie.com" in default_alerter._base_url()


def test_eu_base_url() -> None:
    alerter = OpsGenieAlerter(api_key="k", pipeline_name="p", region="eu")
    assert "api.eu.opsgenie.com" in alerter._base_url()


def test_payload_contains_pipeline_name(
    default_alerter: OpsGenieAlerter, failed_context: AlertContext
) -> None:
    payload = default_alerter._build_payload(failed_context)
    assert "test_pipeline" in payload["message"]


def test_payload_contains_failed_check_names(
    default_alerter: OpsGenieAlerter, failed_context: AlertContext
) -> None:
    payload = default_alerter._build_payload(failed_context)
    assert "row_count" in payload["description"]


def test_payload_contains_warning_names(
    default_alerter: OpsGenieAlerter, failed_context: AlertContext
) -> None:
    payload = default_alerter._build_payload(failed_context)
    assert "freshness" in payload["description"]


def test_payload_includes_custom_tags() -> None:
    alerter = OpsGenieAlerter(
        api_key="k", pipeline_name="p", tags=["etl", "production"]
    )
    ctx = AlertContext(
        pipeline_name="p",
        results=[_make_result("c", CheckStatus.FAILED)],
    )
    payload = alerter._build_payload(ctx)
    assert payload["tags"] == ["etl", "production"]


def test_payload_includes_responders() -> None:
    responders = [{"type": "team", "name": "data-eng"}]
    alerter = OpsGenieAlerter(
        api_key="k", pipeline_name="p", responders=responders
    )
    ctx = AlertContext(
        pipeline_name="p",
        results=[_make_result("c", CheckStatus.FAILED)],
    )
    payload = alerter._build_payload(ctx)
    assert payload["responders"] == responders


def test_send_skipped_for_healthy_pipeline(
    default_alerter: OpsGenieAlerter, healthy_context: AlertContext
) -> None:
    mock_session = MagicMock()
    default_alerter.session = mock_session
    default_alerter.send(healthy_context)
    mock_session.post.assert_not_called()


def test_send_posts_for_failed_pipeline(
    default_alerter: OpsGenieAlerter, failed_context: AlertContext
) -> None:
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_session = MagicMock()
    mock_session.post.return_value = mock_response
    default_alerter.session = mock_session

    default_alerter.send(failed_context)

    mock_session.post.assert_called_once()
    call_kwargs = mock_session.post.call_args
    assert "GenieKey test-key-123" in call_kwargs.kwargs["headers"]["Authorization"]


def test_send_raises_on_http_error(
    default_alerter: OpsGenieAlerter, failed_context: AlertContext
) -> None:
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception("403 Forbidden")
    mock_session = MagicMock()
    mock_session.post.return_value = mock_response
    default_alerter.session = mock_session

    with pytest.raises(Exception, match="403"):
        default_alerter.send(failed_context)
