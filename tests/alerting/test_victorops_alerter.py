from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from pipewarden.alerting.base import AlertContext
from pipewarden.alerting.victorops_alerter import VictorOpsAlerter
from pipewarden.checks.base import CheckResult, CheckStatus


def _make_result(name: str, status: CheckStatus) -> CheckResult:
    return CheckResult(check_name=name, status=status, details=f"{name} detail")


@pytest.fixture()
def default_alerter():
    return VictorOpsAlerter(api_key="test-api-key", routing_key="eng-team")


@pytest.fixture()
def failed_context():
    return AlertContext(
        pipeline_name="orders",
        results=[
            _make_result("row_count", CheckStatus.FAILED),
            _make_result("null_check", CheckStatus.PASSED),
        ],
    )


@pytest.fixture()
def healthy_context():
    return AlertContext(
        pipeline_name="orders",
        results=[
            _make_result("row_count", CheckStatus.PASSED),
            _make_result("null_check", CheckStatus.PASSED),
        ],
    )


def test_raises_without_api_key():
    with pytest.raises(ValueError, match="api_key"):
        VictorOpsAlerter(api_key="")


def test_payload_critical_on_failure(default_alerter, failed_context):
    payload = default_alerter._build_payload(failed_context)
    assert payload["message_type"] == "CRITICAL"
    assert "row_count" in payload["state_message"]
    assert payload["failed_checks"] == 1


def test_payload_recovery_on_healthy(default_alerter, healthy_context):
    payload = default_alerter._build_payload(healthy_context)
    assert payload["message_type"] == "RECOVERY"
    assert "recovered" in payload["state_message"]
    assert payload["failed_checks"] == 0


def test_payload_entity_id_contains_pipeline_name(default_alerter, failed_context):
    payload = default_alerter._build_payload(failed_context)
    assert "orders" in payload["entity_id"]
    assert "orders" in payload["entity_display_name"]


def test_send_posts_to_correct_url(default_alerter, failed_context):
    mock_session = MagicMock()
    mock_session.post.return_value.raise_for_status = MagicMock()
    default_alerter.session = mock_session

    default_alerter.send(failed_context)

    call_url = mock_session.post.call_args[0][0]
    assert "test-api-key" in call_url
    assert "eng-team" in call_url


def test_send_raises_on_http_error(default_alerter, failed_context):
    mock_session = MagicMock()
    mock_session.post.return_value.raise_for_status.side_effect = Exception("503")
    default_alerter.session = mock_session

    with pytest.raises(Exception, match="503"):
        default_alerter.send(failed_context)


def test_payload_monitoring_tool(default_alerter, failed_context):
    payload = default_alerter._build_payload(failed_context)
    assert payload["monitoring_tool"] == "pipewarden"
