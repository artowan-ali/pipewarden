from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from pipewarden.alerting.base import AlertContext
from pipewarden.alerting.telegram_alerter import TelegramAlerter
from pipewarden.checks.base import CheckResult, CheckStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(name: str, status: CheckStatus, message: str = "") -> CheckResult:
    return CheckResult(check_name=name, status=status, message=message)


@pytest.fixture()
def default_alerter():
    return TelegramAlerter(bot_token="test-token", chat_id="123456")


@pytest.fixture()
def failed_context():
    return AlertContext(
        pipeline_name="my_pipeline",
        results=[
            _make_result("row_count", CheckStatus.FAILED, "Too few rows"),
            _make_result("null_check", CheckStatus.WARNING, "5% nulls"),
            _make_result("schema_check", CheckStatus.PASSED),
        ],
    )


@pytest.fixture()
def healthy_context():
    return AlertContext(
        pipeline_name="my_pipeline",
        results=[_make_result("row_count", CheckStatus.PASSED)],
    )


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

def test_raises_without_bot_token():
    with pytest.raises(ValueError, match="bot_token"):
        TelegramAlerter(bot_token="", chat_id="123")


def test_raises_without_chat_id():
    with pytest.raises(ValueError, match="chat_id"):
        TelegramAlerter(bot_token="tok", chat_id="")


# ---------------------------------------------------------------------------
# Payload construction
# ---------------------------------------------------------------------------

def test_payload_contains_chat_id(default_alerter, failed_context):
    payload = default_alerter._build_payload(failed_context)
    assert payload["chat_id"] == "123456"


def test_payload_parse_mode_is_markdown(default_alerter, failed_context):
    payload = default_alerter._build_payload(failed_context)
    assert payload["parse_mode"] == "Markdown"


def test_text_contains_pipeline_name(default_alerter, failed_context):
    text = default_alerter._build_text(failed_context)
    assert "my_pipeline" in text


def test_text_contains_failed_check(default_alerter, failed_context):
    text = default_alerter._build_text(failed_context)
    assert "row_count" in text
    assert "Too few rows" in text


def test_text_contains_warning(default_alerter, failed_context):
    text = default_alerter._build_text(failed_context)
    assert "null_check" in text


def test_healthy_text_shows_healthy_status(default_alerter, healthy_context):
    text = default_alerter._build_text(healthy_context)
    assert "HEALTHY" in text


# ---------------------------------------------------------------------------
# send() behaviour
# ---------------------------------------------------------------------------

def test_send_posts_to_telegram_api(default_alerter, failed_context):
    mock_session = MagicMock()
    mock_session.post.return_value.raise_for_status = MagicMock()
    default_alerter._session = mock_session

    default_alerter.send(failed_context)

    mock_session.post.assert_called_once()
    call_url = mock_session.post.call_args[0][0]
    assert "sendMessage" in call_url
    assert "test-token" in call_url


def test_send_skips_healthy_by_default(default_alerter, healthy_context):
    mock_session = MagicMock()
    default_alerter._session = mock_session

    default_alerter.send(healthy_context)

    mock_session.post.assert_not_called()


def test_send_healthy_when_flag_set(healthy_context):
    alerter = TelegramAlerter(
        bot_token="tok", chat_id="999", alert_on_healthy=True
    )
    mock_session = MagicMock()
    mock_session.post.return_value.raise_for_status = MagicMock()
    alerter._session = mock_session

    alerter.send(healthy_context)

    mock_session.post.assert_called_once()
