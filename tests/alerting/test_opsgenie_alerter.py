from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from pipewarden.alerting.base import AlertContext
from pipewarden.alerting.opsgenie_alerter import OpsGenieAlerter
from pipewarden.checks.base import CheckResult, CheckStatus


def _make_result(name: str, status: CheckStatus, detail: str = "") -> CheckResult:
    return CheckResult(check_name=name, status=status, detail=detail)


@pytest.fixture()
def default_alerter() -> OpsGenieAlerter:
    return OpsGenieAlerter(api_key="test-key-123")


@pytest.fixture()
def failed_context() -> AlertContext:
    return AlertContext(
        pipeline_name="test_pipeline",
        results=[
            _make_result("row_count", CheckStatus.FAILED, "too few rows"),
            _make_result("null_check", CheckStatus.WARNED, "some nulls"),
            _make_result("schema", CheckStatus.PASSED),
        ],
    )


@pytest.fixture()
def healthy_context() -> AlertContext:
    return AlertContext(
        pipeline_name="test_pipeline",
        results=[
            _make_result("row_count", CheckStatus.PASSED),
            _make_result("schema", CheckStatus.PASSED),
        ],
    )


def test_raises_without_api_key() -> None:
    with pytest.raises(ValueError, match="api_key"):
        OpsGenieAlerter(api_key="")


def test_raises_with_invalid_region() -> None:
    with pytest.raises(ValueError, match="region"):
        OpsGenieAlerter(api_key="key", region="ap")


def test_us_base_url(default_alerter: OpsGenieAlerter) -> None:
    assert "api.opsgenie.com" in default_alerter._base_url()
    assert "eu" not in default_alerter._base_url()


def test_eu_base_url() -> None:
    alerter = OpsGenieAlerter(api_key="key", region="eu")
    assert "api.eu.opsgenie.com" in alerter._base_url()


def test_payload_contains_pipeline_name(
    default_alerter: OpsGenieAlerter, failed_context: AlertContext
) -> None:
    payload = default_alerter._build_payload(failed_context)
    assert "test_pipeline" in payload["message"]
    assert payload["details"]["pipeline"] == "test_pipeline"


def test_payload_priority_default(
    default_alerter: OpsGenieAlerter, failed_context: AlertContext
) -> None:
    payload = default_alerter._build_payload(failed_context)
    assert payload["priority"] == "P3"


def test_payload_custom_priority(failed_context: AlertContext) -> None:
    alerter = OpsGenieAlerter(api_key="key", priority="P1")
    payload = alerter._build_payload(failed_context)
    assert payload["priority"] == "P1"


def test_payload_tags_included(failed_context: AlertContext) -> None:
    alerter = OpsGenieAlerter(api_key="key", tags=["etl", "critical"])
    payload = alerter._build_payload(failed_context)
    assert payload["tags"] == ["etl", "critical"]


def test_payload_no_tags_by_default(
    default_alerter: OpsGenieAlerter, failed_context: AlertContext
) -> None:
    payload = default_alerter._build_payload(failed_context)
    assert "tags" not in payload


def test_payload_failed_check_names_in_description(
    default_alerter: OpsGenieAlerter, failed_context: AlertContext
) -> None:
    payload = default_alerter._build_payload(failed_context)
    assert "row_count" in payload["description"]


def test_payload_healthy_status(
    default_alerter: OpsGenieAlerter, healthy_context: AlertContext
) -> None:
    payload = default_alerter._build_payload(healthy_context)
    assert "HEALTHY" in payload["message"]


def test_send_posts_to_opsgenie(
    default_alerter: OpsGenieAlerter, failed_context: AlertContext
) -> None:
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_session.post.return_value = mock_response
    default_alerter.session = mock_session

    default_alerter.send(failed_context)

    mock_session.post.assert_called_once()
    call_kwargs = mock_session.post.call_args
    assert "opsgenie.com" in call_kwargs[0][0]
    mock_response.raise_for_status.assert_called_once()


def test_send_skips_healthy_when_recovery_disabled(
    healthy_context: AlertContext,
) -> None:
    alerter = OpsGenieAlerter(api_key="key", alert_on_recovery=False)
    mock_session = MagicMock()
    alerter.session = mock_session

    alerter.send(healthy_context)

    mock_session.post.assert_not_called()


def test_send_healthy_when_recovery_enabled(
    default_alerter: OpsGenieAlerter, healthy_context: AlertContext
) -> None:
    mock_session = MagicMock()
    mock_session.post.return_value = MagicMock()
    default_alerter.session = mock_session

    default_alerter.send(healthy_context)

    mock_session.post.assert_called_once()
