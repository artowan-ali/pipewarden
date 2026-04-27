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
    return OpsGenieAlerter(api_key="test-key-123", pipeline_name="test_pipeline")


@pytest.fixture
def failed_context():
    return AlertContext(
        pipeline_name="test_pipeline",
        results=[
            _make_result("row_count", CheckStatus.FAILED, "too few rows"),
            _make_result("null_check", CheckStatus.PASSED),
            _make_result("freshness", CheckStatus.WARNING, "aging data"),
        ],
    )


@pytest.fixture
def healthy_context():
    return AlertContext(
        pipeline_name="test_pipeline",
        results=[
            _make_result("row_count", CheckStatus.PASSED),
            _make_result("null_check", CheckStatus.PASSED),
        ],
    )


def test_raises_without_api_key():
    with pytest.raises(ValueError, match="api_key"):
        OpsGenieAlerter(api_key="", pipeline_name="p")


def test_raises_with_invalid_region():
    with pytest.raises(ValueError, match="region"):
        OpsGenieAlerter(api_key="key", pipeline_name="p", region="ap")


def test_base_url_us(default_alerter):
    assert "api.opsgenie.com" in default_alerter._base_url()


def test_base_url_eu():
    alerter = OpsGenieAlerter(api_key="key", pipeline_name="p", region="eu")
    assert "api.eu.opsgenie.com" in alerter._base_url()


def test_payload_contains_pipeline_name(default_alerter, failed_context):
    payload = default_alerter._build_payload(failed_context)
    assert "test_pipeline" in payload["message"]
    assert payload["details"]["pipeline"] == "test_pipeline"


def test_payload_unhealthy_status(default_alerter, failed_context):
    payload = default_alerter._build_payload(failed_context)
    assert "UNHEALTHY" in payload["message"]
    assert "row_count" in payload["details"]["failed_checks"]


def test_payload_healthy_status(default_alerter, healthy_context):
    payload = default_alerter._build_payload(healthy_context)
    assert "HEALTHY" in payload["message"]
    assert payload["details"]["failed_checks"] == "none"


def test_payload_includes_priority(default_alerter, failed_context):
    payload = default_alerter._build_payload(failed_context)
    assert payload["priority"] == "P3"


def test_payload_includes_custom_priority(failed_context):
    alerter = OpsGenieAlerter(api_key="key", pipeline_name="p", priority="P1")
    payload = alerter._build_payload(failed_context)
    assert payload["priority"] == "P1"


def test_payload_includes_tags(failed_context):
    alerter = OpsGenieAlerter(api_key="key", pipeline_name="p", tags=["etl", "prod"])
    payload = alerter._build_payload(failed_context)
    assert "etl" in payload["tags"]
    assert "prod" in payload["tags"]


def test_payload_includes_responders(failed_context):
    responders = [{"type": "team", "name": "data-eng"}]
    alerter = OpsGenieAlerter(api_key="key", pipeline_name="p", responders=responders)
    payload = alerter._build_payload(failed_context)
    assert payload["responders"] == responders


def test_send_posts_to_api(default_alerter, failed_context):
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_session.post.return_value = mock_response
    default_alerter._session = mock_session

    default_alerter.send(failed_context)

    mock_session.post.assert_called_once()
    call_kwargs = mock_session.post.call_args
    assert "opsgenie.com" in call_kwargs[0][0]
    mock_response.raise_for_status.assert_called_once()
