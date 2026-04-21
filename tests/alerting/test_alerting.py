"""Tests for the alerting sub-system."""

from __future__ import annotations

import json
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from typing import List
from unittest.mock import MagicMock, patch

import pytest

from pipewarden.alerting.base import AlertContext, BaseAlerter
from pipewarden.alerting.log_alerter import LogAlerter
from pipewarden.alerting.webhook_alerter import WebhookAlerter
from pipewarden.checks.base import CheckResult, CheckStatus


def _make_result(name: str, status: CheckStatus, details: str = "") -> CheckResult:
    return CheckResult(check_name=name, status=status, details=details)


@pytest.fixture()
def failed_context() -> AlertContext:
    return AlertContext(
        pipeline_name="test_pipeline",
        results=[
            _make_result("row_count", CheckStatus.FAILED, "too few rows"),
            _make_result("null_check", CheckStatus.WARNING, "5% nulls"),
            _make_result("schema_check", CheckStatus.PASSED),
        ],
    )


@pytest.fixture()
def healthy_context() -> AlertContext:
    return AlertContext(
        pipeline_name="test_pipeline",
        results=[_make_result("row_count", CheckStatus.PASSED)],
    )


# ---------------------------------------------------------------------------
# AlertContext
# ---------------------------------------------------------------------------

def test_context_partitions_results(failed_context: AlertContext) -> None:
    assert len(failed_context.failed) == 1
    assert len(failed_context.warned) == 1
    assert not failed_context.is_healthy


def test_healthy_context_is_healthy(healthy_context: AlertContext) -> None:
    assert healthy_context.is_healthy
    assert healthy_context.failed == []


# ---------------------------------------------------------------------------
# BaseAlerter.notify gating
# ---------------------------------------------------------------------------

def test_notify_calls_send_when_unhealthy(failed_context: AlertContext) -> None:
    alerter = MagicMock(spec=BaseAlerter)
    alerter.should_alert.return_value = True
    BaseAlerter.notify(alerter, failed_context)
    alerter.send.assert_called_once_with(failed_context)


def test_notify_skips_send_when_healthy(healthy_context: AlertContext) -> None:
    alerter = MagicMock(spec=BaseAlerter)
    alerter.should_alert.return_value = False
    BaseAlerter.notify(alerter, healthy_context)
    alerter.send.assert_not_called()


# ---------------------------------------------------------------------------
# LogAlerter
# ---------------------------------------------------------------------------

def test_log_alerter_emits_messages(failed_context: AlertContext, caplog) -> None:
    alerter = LogAlerter(logger_name="pipewarden.alerts", level=logging.ERROR)
    with caplog.at_level(logging.WARNING, logger="pipewarden.alerts"):
        alerter.send(failed_context)
    messages = caplog.text
    assert "test_pipeline" in messages
    assert "row_count" in messages
    assert "null_check" in messages


# ---------------------------------------------------------------------------
# WebhookAlerter
# ---------------------------------------------------------------------------

def test_webhook_alerter_posts_json(failed_context: AlertContext) -> None:
    received: List[bytes] = []

    class _Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers["Content-Length"])
            received.append(self.rfile.read(length))
            self.send_response(200)
            self.end_headers()

        def log_message(self, *args):  # silence server output
            pass

    server = HTTPServer(("127.0.0.1", 0), _Handler)
    port = server.server_address[1]
    thread = Thread(target=server.handle_request, daemon=True)
    thread.start()

    alerter = WebhookAlerter(url=f"http://127.0.0.1:{port}/alert")
    alerter.send(failed_context)
    thread.join(timeout=2)
    server.server_close()

    assert len(received) == 1
    payload = json.loads(received[0])
    assert payload["pipeline"] == "test_pipeline"
    assert len(payload["failed"]) == 1
    assert payload["healthy"] is False


def test_webhook_alerter_raises_on_connection_error(failed_context: AlertContext) -> None:
    alerter = WebhookAlerter(url="http://127.0.0.1:1/unreachable", timeout=1)
    with pytest.raises(RuntimeError, match="WebhookAlerter failed"):
        alerter.send(failed_context)
