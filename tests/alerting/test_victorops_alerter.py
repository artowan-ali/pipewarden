from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from pipewarden.alerting.base import AlertContext
from pipewarden.alerting.victorops_alerter import VictorOpsAlerter
from pipewarden.checks.base import CheckResult, CheckStatus


def _make_result(name: str, status: CheckStatus) -> CheckResult:
    return CheckResult(check_name=name, status=status, details=f"{name} detail")


@pytest.fixture()
def default_alerter() -> VictorOpsAlerter:
    return VictorOpsAlerter(api_key="test-api-key", routing_key="test-routing")


@pytest.fixture()
def failed_context() -> AlertContext:
    return AlertContext(
        pipeline_name="my_pipeline",
        results=[
            _make_result("check_a", CheckStatus.FAILED),
            _make_result("check_b", CheckStatus.PASSED),
        ],
    )


@pytest.fixture()
def healthy_context() -> AlertContext:
    return AlertContext(
        pipeline_name="my_pipeline",
        results=[_make_result("check_a", CheckStatus.PASSED)],
    )


def test_raises_without_api_key() -> None:
    with pytest.raises(ValueError, match="api_key"):
        VictorOpsAlerter(api_key="", routing_key="key")


def test_raises_without_routing_key() -> None:
    with pytest.raises(ValueError, match="routing_key"):
        VictorOpsAlerter(api_key="key", routing_key="")


def test_payload_message_type_critical_on_failure(
    default_alerter: VictorOpsAlerter, failed_context: AlertContext
) -> None:
    payload = default_alerter._build_payload(failed_context)
    assert payload["message_type"] == "CRITICAL"


def test_payload_message_type_info_on_healthy(
    default_alerter: VictorOpsAlerter, healthy_context: AlertContext
) -> None:
    payload = default_alerter._build_payload(healthy_context)
    assert payload["message_type"] == "INFO"


def test_payload_contains_pipeline_name(
    default_alerter: VictorOpsAlerter, failed_context: AlertContext
) -> None:
    payload = default_alerter._build_payload(failed_context)
    assert payload["pipeline"] == "my_pipeline"
    assert "my_pipeline" in payload["entity_id"]


def test_payload_lists_failed_check_names(
    default_alerter: VictorOpsAlerter, failed_context: AlertContext
) -> None:
    payload = default_alerter._build_payload(failed_context)
    assert "check_a" in payload["state_message"]


def test_no_alert_sent_when_healthy_and_only_on_failure(
    default_alerter: VictorOpsAlerter, healthy_context: AlertContext
) -> None:
    with patch("urllib.request.urlopen") as mock_open:
        default_alerter.send(healthy_context)
        mock_open.assert_not_called()


def test_alert_sent_when_healthy_and_not_only_on_failure(
    healthy_context: AlertContext,
) -> None:
    alerter = VictorOpsAlerter(
        api_key="key", routing_key="route", only_on_failure=False
    )
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_open:
        alerter.send(healthy_context)
        mock_open.assert_called_once()


def test_send_posts_correct_url_and_json(
    default_alerter: VictorOpsAlerter, failed_context: AlertContext
) -> None:
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=mock_resp):
        with patch("urllib.request.Request") as mock_req_cls:
            default_alerter.send(failed_context)
            call_args = mock_req_cls.call_args
            url = call_args[0][0]
            assert "test-api-key" in url
            assert "test-routing" in url
            body = json.loads(call_args[1]["data"])
            assert body["message_type"] == "CRITICAL"


def test_extra_fields_included_in_payload(
    failed_context: AlertContext,
) -> None:
    alerter = VictorOpsAlerter(
        api_key="key",
        routing_key="route",
        extra_fields={"team": "data-eng", "env": "prod"},
    )
    payload = alerter._build_payload(failed_context)
    assert payload["team"] == "data-eng"
    assert payload["env"] == "prod"
