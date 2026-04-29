from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from pipewarden.alerting.base import AlertContext
from pipewarden.alerting.opsgenie_alerter import OpsGenieAlerter
from pipewarden.checks.base import CheckResult, CheckStatus


def _make_result(name: str, status: CheckStatus, detail: str = "") -> CheckResult:
    return CheckResult(check_name=name, status=status, detail=detail)


@pytest.fixture
def default_alerter():
    return OpsGenieAlerter(api_key="test-key-123")


@pytest.fixture
def failed_context():
    return AlertContext(
        pipeline_name="orders_pipeline",
        results=[
            _make_result("row_count", CheckStatus.FAILED, "Too few rows"),
            _make_result("null_check", CheckStatus.PASSED),
            _make_result("freshness", CheckStatus.WARNED, "Aging data"),
        ],
    )


@pytest.fixture
def healthy_context():
    return AlertContext(
        pipeline_name="orders_pipeline",
        results=[
            _make_result("row_count", CheckStatus.PASSED),
            _make_result("null_check", CheckStatus.PASSED),
        ],
    )


def test_raises_without_api_key():
    with pytest.raises(ValueError, match="api_key"):
        OpsGenieAlerter(api_key="")


def test_raises_with_invalid_priority():
    with pytest.raises(ValueError, match="Invalid priority"):
        OpsGenieAlerter(api_key="key", priority="P9")


def test_base_url_us_region(default_alerter):
    assert "api.opsgenie.com" in default_alerter._base_url()


def test_base_url_eu_region():
    alerter = OpsGenieAlerter(api_key="key", region="eu")
    assert "api.eu.opsgenie.com" in alerter._base_url()


def test_payload_contains_pipeline_name(default_alerter, failed_context):
    payload = default_alerter._build_payload(failed_context)
    assert "orders_pipeline" in payload["message"]
    assert "orders_pipeline" in payload["details"]["pipeline"]


def test_payload_marks_unhealthy(default_alerter, failed_context):
    payload = default_alerter._build_payload(failed_context)
    assert "UNHEALTHY" in payload["message"]


def test_payload_marks_healthy(default_alerter, healthy_context):
    payload = default_alerter._build_payload(healthy_context)
    assert "HEALTHY" in payload["message"]


def test_payload_lists_failed_checks(default_alerter, failed_context):
    payload = default_alerter._build_payload(failed_context)
    assert "row_count" in payload["description"]


def test_payload_lists_warned_checks(default_alerter, failed_context):
    payload = default_alerter._build_payload(failed_context)
    assert "freshness" in payload["description"]


def test_payload_priority(default_alerter, failed_context):
    payload = default_alerter._build_payload(failed_context)
    assert payload["priority"] == "P3"


def test_payload_custom_priority(failed_context):
    alerter = OpsGenieAlerter(api_key="key", priority="P1")
    payload = alerter._build_payload(failed_context)
    assert payload["priority"] == "P1"


def test_payload_includes_tags(failed_context):
    alerter = OpsGenieAlerter(api_key="key", tags=["etl", "prod"])
    payload = alerter._build_payload(failed_context)
    assert "etl" in payload["tags"]
    assert "prod" in payload["tags"]


def test_payload_includes_responders(failed_context):
    responders = [{"type": "team", "name": "data-eng"}]
    alerter = OpsGenieAlerter(api_key="key", responders=responders)
    payload = alerter._build_payload(failed_context)
    assert payload["responders"] == responders


def test_send_posts_to_opsgenie(default_alerter, failed_context):
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_session.post.return_value = mock_response
    default_alerter._session = mock_session

    default_alerter.send(failed_context)

    mock_session.post.assert_called_once()
    call_kwargs = mock_session.post.call_args
    assert "opsgenie.com" in call_kwargs[0][0]
    mock_response.raise_for_status.assert_called_once()


def test_send_raises_on_http_error(default_alerter, failed_context):
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception("403 Forbidden")
    mock_session.post.return_value = mock_response
    default_alerter._session = mock_session

    with pytest.raises(Exception, match="403 Forbidden"):
        default_alerter.send(failed_context)
