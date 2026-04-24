from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from pipewarden.alerting.base import AlertContext
from pipewarden.alerting.datadog_alerter import DatadogAlerter
from pipewarden.checks.base import CheckResult, CheckStatus


def _make_result(name: str, status: CheckStatus, details: str = "") -> CheckResult:
    return CheckResult(check_name=name, status=status, details=details)


@pytest.fixture
def default_alerter() -> DatadogAlerter:
    return DatadogAlerter(api_key="test-api-key", tags=["env:test"])


@pytest.fixture
def failed_context() -> AlertContext:
    return AlertContext(
        results=[
            _make_result("row_count", CheckStatus.FAILED, "too few rows"),
            _make_result("null_check", CheckStatus.WARNED, "some nulls"),
            _make_result("schema_check", CheckStatus.PASSED),
        ]
    )


@pytest.fixture
def healthy_context() -> AlertContext:
    return AlertContext(
        results=[
            _make_result("row_count", CheckStatus.PASSED),
            _make_result("null_check", CheckStatus.PASSED),
        ]
    )


def test_raises_without_api_key() -> None:
    with pytest.raises(ValueError, match="api_key"):
        DatadogAlerter(api_key="")


def test_build_payload_unhealthy(default_alerter: DatadogAlerter, failed_context: AlertContext) -> None:
    payload = default_alerter._build_payload(failed_context)
    assert "unhealthy" in payload["title"]
    assert payload["alert_type"] == "error"
    assert "row_count" in payload["text"]
    assert "null_check" in payload["text"]
    assert "healthy:false" in payload["tags"]
    assert "env:test" in payload["tags"]


def test_build_payload_healthy(default_alerter: DatadogAlerter, healthy_context: AlertContext) -> None:
    payload = default_alerter._build_payload(healthy_context)
    assert "healthy" in payload["title"]
    assert payload["alert_type"] == "success"
    assert "healthy:true" in payload["tags"]


def test_send_posts_to_api(default_alerter: DatadogAlerter, failed_context: AlertContext) -> None:
    mock_response = MagicMock()
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)
    mock_response.status = 202

    with patch("urllib.request.urlopen", return_value=mock_response) as mock_open:
        default_alerter.send(failed_context)

    mock_open.assert_called_once()
    request = mock_open.call_args[0][0]
    assert "datadoghq.com" in request.full_url
    assert request.get_header("Dd-api-key") == "test-api-key"
    sent_body = json.loads(request.data.decode())
    assert "title" in sent_body
    assert "text" in sent_body


def test_send_includes_app_key_if_provided(failed_context: AlertContext) -> None:
    alerter = DatadogAlerter(api_key="key", app_key="app-key")
    mock_response = MagicMock()
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)
    mock_response.status = 202

    with patch("urllib.request.urlopen", return_value=mock_response) as mock_open:
        alerter.send(failed_context)

    request = mock_open.call_args[0][0]
    assert request.get_header("Dd-application-key") == "app-key"


def test_source_type_name_default(default_alerter: DatadogAlerter, healthy_context: AlertContext) -> None:
    payload = default_alerter._build_payload(healthy_context)
    assert payload["source_type_name"] == "pipewarden"
