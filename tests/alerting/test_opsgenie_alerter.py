from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from pipewarden.alerting.base import AlertContext
from pipewarden.alerting.opsgenie_alerter import OpsGenieAlerter
from pipewarden.checks.base import CheckResult, CheckStatus


def _make_result(name: str, status: CheckStatus, details: str = "") -> CheckResult:
    return CheckResult(check_name=name, status=status, details=details)


@pytest.fixture
def default_alerter():
    return OpsGenieAlerter(api_key="test-key", pipeline_name="my_pipeline")


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
        results=[_make_result("row_count", CheckStatus.PASSED)],
    )


def test_raises_without_api_key():
    with pytest.raises(ValueError, match="api_key"):
        OpsGenieAlerter(api_key="", pipeline_name="p")


def test_raises_with_invalid_priority():
    with pytest.raises(ValueError, match="priority"):
        OpsGenieAlerter(api_key="k", pipeline_name="p", priority="P9")


def test_us_base_url(default_alerter):
    assert "api.opsgenie.com" in default_alerter._base_url()


def test_eu_base_url():
    alerter = OpsGenieAlerter(api_key="k", pipeline_name="p", region="eu")
    assert "api.eu.opsgenie.com" in alerter._base_url()


def test_build_payload_contains_pipeline_name(default_alerter, failed_context):
    payload = default_alerter._build_payload(failed_context)
    assert "my_pipeline" in payload["message"]
    assert payload["details"]["pipeline"] == "my_pipeline"


def test_build_payload_lists_failed_checks(default_alerter, failed_context):
    payload = default_alerter._build_payload(failed_context)
    assert "row_count" in payload["message"]


def test_build_payload_includes_description(default_alerter, failed_context):
    payload = default_alerter._build_payload(failed_context)
    assert "too few rows" in payload["description"]
    assert "some nulls" in payload["description"]


def test_build_payload_responders_included():
    alerter = OpsGenieAlerter(
        api_key="k",
        pipeline_name="p",
        responders=[{"type": "team", "name": "data-eng"}],
    )
    ctx = AlertContext(
        pipeline_name="p",
        results=[_make_result("c", CheckStatus.FAILED)],
    )
    payload = alerter._build_payload(ctx)
    assert payload["responders"] == [{"type": "team", "name": "data-eng"}]


def test_send_skips_when_healthy(default_alerter, healthy_context):
    mock_session = MagicMock()
    default_alerter.session = mock_session
    default_alerter.send(healthy_context)
    mock_session.post.assert_not_called()


def test_send_posts_on_failure(default_alerter, failed_context):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_session = MagicMock()
    mock_session.post.return_value = mock_response
    default_alerter.session = mock_session

    default_alerter.send(failed_context)

    mock_session.post.assert_called_once()
    call_kwargs = mock_session.post.call_args
    assert call_kwargs.kwargs["headers"]["Authorization"] == "GenieKey test-key"


def test_send_raises_on_http_error(default_alerter, failed_context):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception("HTTP 429")
    mock_session = MagicMock()
    mock_session.post.return_value = mock_response
    default_alerter.session = mock_session

    with pytest.raises(Exception, match="HTTP 429"):
        default_alerter.send(failed_context)
