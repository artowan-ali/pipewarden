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
    return OpsGenieAlerter(api_key="test-key-123", priority="P2")


@pytest.fixture()
def failed_context() -> AlertContext:
    return AlertContext(
        pipeline_name="test-pipeline",
        results=[
            _make_result("row_count", CheckStatus.FAILED, "too few rows"),
            _make_result("null_check", CheckStatus.PASSED),
            _make_result("schema", CheckStatus.WARNED, "extra column"),
        ],
    )


@pytest.fixture()
def healthy_context() -> AlertContext:
    return AlertContext(
        pipeline_name="test-pipeline",
        results=[
            _make_result("row_count", CheckStatus.PASSED),
            _make_result("null_check", CheckStatus.PASSED),
        ],
    )


def test_raises_without_api_key() -> None:
    with pytest.raises(ValueError, match="api_key"):
        OpsGenieAlerter(api_key="")


def test_raises_with_invalid_priority() -> None:
    with pytest.raises(ValueError, match="priority"):
        OpsGenieAlerter(api_key="key", priority="P9")


def test_base_url_us_region(default_alerter: OpsGenieAlerter) -> None:
    assert "api.opsgenie.com" in default_alerter._base_url()


def test_base_url_eu_region() -> None:
    alerter = OpsGenieAlerter(api_key="key", region="eu")
    assert "api.eu.opsgenie.com" in alerter._base_url()


def test_payload_contains_pipeline_name(
    default_alerter: OpsGenieAlerter, failed_context: AlertContext
) -> None:
    payload = default_alerter._build_payload(failed_context)
    assert "test-pipeline" in payload["message"]
    assert "test-pipeline" in payload["description"]


def test_payload_marks_unhealthy(
    default_alerter: OpsGenieAlerter, failed_context: AlertContext
) -> None:
    payload = default_alerter._build_payload(failed_context)
    assert "UNHEALTHY" in payload["message"]


def test_payload_marks_healthy(
    default_alerter: OpsGenieAlerter, healthy_context: AlertContext
) -> None:
    payload = default_alerter._build_payload(healthy_context)
    assert "HEALTHY" in payload["message"]


def test_payload_lists_failed_checks(
    default_alerter: OpsGenieAlerter, failed_context: AlertContext
) -> None:
    payload = default_alerter._build_payload(failed_context)
    assert "row_count" in payload["description"]


def test_payload_priority(
    default_alerter: OpsGenieAlerter, failed_context: AlertContext
) -> None:
    payload = default_alerter._build_payload(failed_context)
    assert payload["priority"] == "P2"


def test_payload_responders_included() -> None:
    alerter = OpsGenieAlerter(
        api_key="key",
        responders=[{"type": "team", "name": "ops-team"}],
    )
    ctx = AlertContext(
        pipeline_name="pipe",
        results=[_make_result("c", CheckStatus.FAILED)],
    )
    payload = alerter._build_payload(ctx)
    assert payload["responders"] == [{"type": "team", "name": "ops-team"}]


def test_send_posts_to_api(
    default_alerter: OpsGenieAlerter, failed_context: AlertContext
) -> None:
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_session.post.return_value = mock_response
    default_alerter.session = mock_session

    default_alerter.send(failed_context)

    mock_session.post.assert_called_once()
    call_kwargs = mock_session.post.call_args
    assert "opsgenie.com" in call_kwargs[0][0]


def test_send_raises_on_http_error(
    default_alerter: OpsGenieAlerter, failed_context: AlertContext
) -> None:
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception("403 Forbidden")
    mock_session.post.return_value = mock_response
    default_alerter.session = mock_session

    with pytest.raises(Exception, match="403"):
        default_alerter.send(failed_context)
