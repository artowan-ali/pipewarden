from __future__ import annotations

import json
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

from pipewarden.alerting.base import AlertContext
from pipewarden.alerting.pagerduty_alerter import PagerDutyAlerter
from pipewarden.checks.base import CheckResult, CheckStatus


def _make_result(name: str, status: CheckStatus, detail: str = "") -> CheckResult:
    return CheckResult(check_name=name, status=status, detail=detail)


@pytest.fixture()
def default_alerter() -> PagerDutyAlerter:
    return PagerDutyAlerter(integration_key="test-key-123")


@pytest.fixture()
def failed_context() -> AlertContext:
    return AlertContext(
        results=[
            _make_result("row_count", CheckStatus.FAILED, "too few rows"),
            _make_result("null_check", CheckStatus.PASSED),
        ]
    )


@pytest.fixture()
def healthy_context() -> AlertContext:
    return AlertContext(
        results=[_make_result("row_count", CheckStatus.PASSED)]
    )


def test_raises_without_integration_key() -> None:
    with pytest.raises(ValueError, match="integration_key"):
        PagerDutyAlerter(integration_key="")


def test_raises_with_invalid_severity() -> None:
    with pytest.raises(ValueError, match="severity"):
        PagerDutyAlerter(integration_key="key", severity="fatal")


def test_no_request_when_healthy(
    default_alerter: PagerDutyAlerter, healthy_context: AlertContext
) -> None:
    with patch("urllib.request.urlopen") as mock_open:
        default_alerter.send(healthy_context)
        mock_open.assert_not_called()


def test_sends_request_when_unhealthy(
    default_alerter: PagerDutyAlerter, failed_context: AlertContext
) -> None:
    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.read.return_value = b"{\"status\": \"success\"}"

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_open:
        default_alerter.send(failed_context)
        mock_open.assert_called_once()


def test_payload_contains_failed_check_names(
    default_alerter: PagerDutyAlerter, failed_context: AlertContext
) -> None:
    payload = default_alerter._build_payload(failed_context)
    summary = payload["payload"]["summary"]
    assert "row_count" in summary


def test_payload_severity_is_configurable(
    failed_context: AlertContext,
) -> None:
    alerter = PagerDutyAlerter(integration_key="key", severity="critical")
    payload = alerter._build_payload(failed_context)
    assert payload["payload"]["severity"] == "critical"


def test_payload_includes_component_when_set(
    failed_context: AlertContext,
) -> None:
    alerter = PagerDutyAlerter(integration_key="key", component="my-pipeline")
    payload = alerter._build_payload(failed_context)
    assert payload["payload"]["component"] == "my-pipeline"


def test_payload_omits_component_when_not_set(
    default_alerter: PagerDutyAlerter, failed_context: AlertContext
) -> None:
    payload = default_alerter._build_payload(failed_context)
    assert "component" not in payload["payload"]


def test_custom_details_counts(
    default_alerter: PagerDutyAlerter, failed_context: AlertContext
) -> None:
    payload = default_alerter._build_payload(failed_context)
    details = payload["payload"]["custom_details"]
    assert details["total_checks"] == 2
    assert details["failed"] == 1
    assert details["passed"] == 1
