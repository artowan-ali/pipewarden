from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from pipewarden.alerting.base import AlertContext
from pipewarden.alerting.opsgenie_alerter import OpsGenieAlerter
from pipewarden.checks.base import CheckResult, CheckStatus


def _make_result(name: str, status: CheckStatus, detail: str = "") -> CheckResult:
    return CheckResult(check_name=name, status=status, detail=detail)


@pytest.fixture()
def default_alerter():
    session = MagicMock()
    session.post.return_value = MagicMock(status_code=202)
    return OpsGenieAlerter(api_key="test-key", _session=session)


@pytest.fixture()
def failed_context():
    return AlertContext(
        pipeline_name="test_pipeline",
        results=[
            _make_result("row_count", CheckStatus.FAILED, "too few rows"),
            _make_result("null_check", CheckStatus.PASSED),
        ],
    )


@pytest.fixture()
def healthy_context():
    return AlertContext(
        pipeline_name="test_pipeline",
        results=[_make_result("row_count", CheckStatus.PASSED)],
    )


def test_raises_without_api_key():
    with pytest.raises(ValueError, match="api_key"):
        OpsGenieAlerter(api_key="")


def test_raises_with_invalid_priority():
    with pytest.raises(ValueError, match="priority"):
        OpsGenieAlerter(api_key="key", priority="P9")


def test_us_base_url():
    alerter = OpsGenieAlerter(api_key="key", region="us")
    assert "api.opsgenie.com" in alerter._base_url()


def test_eu_base_url():
    alerter = OpsGenieAlerter(api_key="key", region="eu")
    assert "api.eu.opsgenie.com" in alerter._base_url()


def test_payload_contains_pipeline_name(default_alerter, failed_context):
    payload = default_alerter._build_payload(failed_context)
    assert "test_pipeline" in payload["message"]
    assert "test_pipeline" in payload["description"]


def test_payload_marks_unhealthy(default_alerter, failed_context):
    payload = default_alerter._build_payload(failed_context)
    assert "UNHEALTHY" in payload["message"]


def test_payload_marks_healthy(default_alerter, healthy_context):
    payload = default_alerter._build_payload(healthy_context)
    assert "HEALTHY" in payload["message"]


def test_payload_lists_failed_checks(default_alerter, failed_context):
    payload = default_alerter._build_payload(failed_context)
    assert "row_count" in payload["description"]


def test_payload_includes_priority(default_alerter, failed_context):
    payload = default_alerter._build_payload(failed_context)
    assert payload["priority"] == "P3"


def test_payload_includes_responders():
    session = MagicMock()
    session.post.return_value = MagicMock(status_code=202)
    alerter = OpsGenieAlerter(
        api_key="key",
        responders=[{"type": "team", "name": "ops"}],
        _session=session,
    )
    ctx = AlertContext(
        pipeline_name="p",
        results=[_make_result("c", CheckStatus.FAILED)],
    )
    payload = alerter._build_payload(ctx)
    assert payload["responders"] == [{"type": "team", "name": "ops"}]


def test_send_posts_on_failure(default_alerter, failed_context):
    default_alerter.send(failed_context)
    assert default_alerter._session.post.called


def test_send_skips_healthy_by_default(default_alerter, healthy_context):
    default_alerter.send(healthy_context)
    default_alerter._session.post.assert_not_called()


def test_send_posts_healthy_when_recovery_enabled(healthy_context):
    session = MagicMock()
    session.post.return_value = MagicMock(status_code=202)
    alerter = OpsGenieAlerter(api_key="key", alert_on_recovery=True, _session=session)
    alerter.send(healthy_context)
    session.post.assert_called_once()
