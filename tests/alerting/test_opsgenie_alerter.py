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
        pipeline_name="my_pipeline",
        results=[
            _make_result("row_count", CheckStatus.FAILED, "too few rows"),
            _make_result("null_check", CheckStatus.WARNING, "some nulls"),
            _make_result("schema", CheckStatus.PASSED),
        ],
    )


@pytest.fixture
def healthy_context():
    return AlertContext(
        pipeline_name="my_pipeline",
        results=[
            _make_result("row_count", CheckStatus.PASSED),
            _make_result("schema", CheckStatus.PASSED),
        ],
    )


def test_raises_without_api_key():
    with pytest.raises(ValueError, match="api_key"):
        OpsGenieAlerter(api_key="")


def test_raises_with_invalid_region():
    with pytest.raises(ValueError, match="region"):
        OpsGenieAlerter(api_key="k", region="ap")


def test_base_url_us(default_alerter):
    assert "opsgenie.com" in default_alerter._base_url()
    assert "eu" not in default_alerter._base_url()


def test_base_url_eu():
    alerter = OpsGenieAlerter(api_key="k", region="eu")
    assert "eu.opsgenie.com" in alerter._base_url()


def test_payload_unhealthy(default_alerter, failed_context):
    payload = default_alerter._build_payload(failed_context)
    assert "UNHEALTHY" in payload["message"]
    assert "row_count" in payload["details"]["failed_checks"]
    assert "null_check" in payload["details"]["warned_checks"]


def test_payload_healthy(default_alerter, healthy_context):
    payload = default_alerter._build_payload(healthy_context)
    assert "HEALTHY" in payload["message"]
    assert payload["details"]["failed_checks"] == "none"


def test_payload_includes_priority(default_alerter, failed_context):
    payload = default_alerter._build_payload(failed_context)
    assert payload["priority"] == "P3"


def test_payload_includes_custom_tags(failed_context):
    alerter = OpsGenieAlerter(api_key="k", tags=["etl", "production"])
    payload = alerter._build_payload(failed_context)
    assert payload["tags"] == ["etl", "production"]


def test_payload_includes_responders(failed_context):
    responders = [{"type": "team", "name": "data-eng"}]
    alerter = OpsGenieAlerter(api_key="k", responders=responders)
    payload = alerter._build_payload(failed_context)
    assert payload["responders"] == responders


def test_send_posts_to_opsgenie(default_alerter, failed_context):
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_session.post.return_value = mock_response
    default_alerter.session = mock_session

    default_alerter.send(failed_context)

    mock_session.post.assert_called_once()
    call_kwargs = mock_session.post.call_args
    assert "opsgenie.com" in call_kwargs[0][0]
    assert call_kwargs[1]["json"]["message"] is not None


def test_send_raises_on_http_error(default_alerter, failed_context):
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception("403 Forbidden")
    mock_session.post.return_value = mock_response
    default_alerter.session = mock_session

    with pytest.raises(Exception, match="403"):
        default_alerter.send(failed_context)
