from __future__ import annotations

from unittest.mock import MagicMock, patch
import json
import pytest

from pipewarden.alerting.opsgenie_alerter import OpsGenieAlerter
from pipewarden.alerting.base import AlertContext
from pipewarden.checks.base import CheckResult, CheckStatus


def _make_result(name: str, status: CheckStatus, detail: str = "") -> CheckResult:
    return CheckResult(check_name=name, status=status, detail=detail)


@pytest.fixture
def default_alerter() -> OpsGenieAlerter:
    return OpsGenieAlerter(api_key="test-key-123", priority="P2", tags=["etl", "prod"])


@pytest.fixture
def failed_context() -> AlertContext:
    return AlertContext(
        pipeline_name="orders_pipeline",
        results=[
            _make_result("row_count", CheckStatus.FAILED, "Too few rows"),
            _make_result("null_check", CheckStatus.WARNED, "High null rate"),
            _make_result("schema_check", CheckStatus.PASSED),
        ],
    )


@pytest.fixture
def healthy_context() -> AlertContext:
    return AlertContext(
        pipeline_name="orders_pipeline",
        results=[
            _make_result("row_count", CheckStatus.PASSED),
            _make_result("schema_check", CheckStatus.PASSED),
        ],
    )


def test_raises_without_api_key() -> None:
    with pytest.raises(ValueError, match="api_key"):
        OpsGenieAlerter(api_key="")


def test_raises_with_invalid_priority() -> None:
    with pytest.raises(ValueError, match="priority"):
        OpsGenieAlerter(api_key="key", priority="P9")


def test_no_request_when_healthy(
    default_alerter: OpsGenieAlerter, healthy_context: AlertContext
) -> None:
    with patch("urllib.request.urlopen") as mock_open:
        default_alerter.send(healthy_context)
        mock_open.assert_not_called()


def test_sends_request_on_failure(
    default_alerter: OpsGenieAlerter, failed_context: AlertContext
) -> None:
    mock_resp = MagicMock()
    mock_resp.status = 202
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_open:
        default_alerter.send(failed_context)
        mock_open.assert_called_once()


def test_payload_contains_pipeline_name(
    default_alerter: OpsGenieAlerter, failed_context: AlertContext
) -> None:
    payload = default_alerter._build_payload(failed_context)
    assert "orders_pipeline" in payload["message"]
    assert "orders_pipeline" in payload["alias"]


def test_payload_lists_failed_checks(
    default_alerter: OpsGenieAlerter, failed_context: AlertContext
) -> None:
    payload = default_alerter._build_payload(failed_context)
    assert "row_count" in payload["description"]


def test_payload_includes_priority_and_tags(
    default_alerter: OpsGenieAlerter, failed_context: AlertContext
) -> None:
    payload = default_alerter._build_payload(failed_context)
    assert payload["priority"] == "P2"
    assert "etl" in payload["tags"]


def test_payload_details_counts(
    default_alerter: OpsGenieAlerter, failed_context: AlertContext
) -> None:
    payload = default_alerter._build_payload(failed_context)
    assert payload["details"]["failed_count"] == "1"
    assert payload["details"]["warning_count"] == "1"


def test_raises_on_http_error(
    default_alerter: OpsGenieAlerter, failed_context: AlertContext
) -> None:
    import urllib.error

    with patch(
        "urllib.request.urlopen",
        side_effect=urllib.error.HTTPError(
            url="", code=403, msg="Forbidden", hdrs=None, fp=None  # type: ignore[arg-type]
        ),
    ):
        with pytest.raises(urllib.error.HTTPError):
            default_alerter.send(failed_context)
