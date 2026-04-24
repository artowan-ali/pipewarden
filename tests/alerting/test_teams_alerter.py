from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from pipewarden.alerting.base import AlertContext
from pipewarden.alerting.teams_alerter import TeamsAlerter
from pipewarden.checks.base import CheckResult, CheckStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(name: str, status: CheckStatus, details: str = "") -> CheckResult:
    return CheckResult(check_name=name, status=status, details=details)


@pytest.fixture()
def default_alerter() -> TeamsAlerter:
    return TeamsAlerter(webhook_url="https://teams.example.com/webhook")


@pytest.fixture()
def failed_context() -> AlertContext:
    return AlertContext(
        pipeline_name="test_pipeline",
        results=[
            _make_result("row_count", CheckStatus.FAILED, "Too few rows"),
            _make_result("null_check", CheckStatus.PASSED),
        ],
    )


@pytest.fixture()
def healthy_context() -> AlertContext:
    return AlertContext(
        pipeline_name="test_pipeline",
        results=[
            _make_result("row_count", CheckStatus.PASSED),
            _make_result("null_check", CheckStatus.PASSED),
        ],
    )


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

def test_raises_without_webhook_url() -> None:
    with pytest.raises(ValueError, match="webhook_url"):
        TeamsAlerter(webhook_url="")


# ---------------------------------------------------------------------------
# Payload structure
# ---------------------------------------------------------------------------

def test_payload_contains_pipeline_name(default_alerter, failed_context) -> None:
    payload = default_alerter._build_payload(failed_context)
    assert "test_pipeline" in str(payload)


def test_payload_unhealthy_color(default_alerter, failed_context) -> None:
    payload = default_alerter._build_payload(failed_context)
    assert payload["themeColor"] == "d63b3b"


def test_payload_healthy_color(default_alerter, healthy_context) -> None:
    payload = default_alerter._build_payload(healthy_context)
    assert payload["themeColor"] == "00b300"


def test_payload_includes_failure_section(default_alerter, failed_context) -> None:
    payload = default_alerter._build_payload(failed_context)
    titles = [s.get("activityTitle", "") for s in payload["sections"]]
    assert "Failed checks" in titles


def test_payload_no_failure_section_when_healthy(default_alerter, healthy_context) -> None:
    payload = default_alerter._build_payload(healthy_context)
    titles = [s.get("activityTitle", "") for s in payload["sections"]]
    assert "Failed checks" not in titles


def test_extra_facts_appear_in_payload() -> None:
    alerter = TeamsAlerter(
        webhook_url="https://teams.example.com/webhook",
        extra_facts={"Environment": "staging"},
    )
    ctx = AlertContext(
        pipeline_name="p",
        results=[_make_result("c", CheckStatus.FAILED)],
    )
    payload = alerter._build_payload(ctx)
    facts = payload["sections"][0]["facts"]
    assert any(f["name"] == "Environment" and f["value"] == "staging" for f in facts)


# ---------------------------------------------------------------------------
# send() behaviour
# ---------------------------------------------------------------------------

def test_send_skipped_when_healthy_and_only_on_failure(
    default_alerter, healthy_context
) -> None:
    with patch("pipewarden.alerting.teams_alerter.requests") as mock_req:
        default_alerter.send(healthy_context)
        mock_req.post.assert_not_called()


def test_send_called_on_failure(default_alerter, failed_context) -> None:
    mock_response = MagicMock()
    with patch("pipewarden.alerting.teams_alerter.requests") as mock_req:
        mock_req.post.return_value = mock_response
        default_alerter.send(failed_context)
        mock_req.post.assert_called_once_with(
            default_alerter.webhook_url,
            json=default_alerter._build_payload(failed_context),
            timeout=10,
        )
        mock_response.raise_for_status.assert_called_once()


def test_send_healthy_when_only_on_failure_false(healthy_context) -> None:
    alerter = TeamsAlerter(
        webhook_url="https://teams.example.com/webhook",
        only_on_failure=False,
    )
    mock_response = MagicMock()
    with patch("pipewarden.alerting.teams_alerter.requests") as mock_req:
        mock_req.post.return_value = mock_response
        alerter.send(healthy_context)
        mock_req.post.assert_called_once()
