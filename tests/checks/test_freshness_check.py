import pytest
from datetime import datetime, timezone, timedelta
from pipewarden.checks.freshness_check import FreshnessCheck
from pipewarden.checks.base import CheckStatus


@pytest.fixture
def default_check():
    return FreshnessCheck(
        name="freshness",
        column="updated_at",
        max_age_seconds=3600,
        warning_age_seconds=1800,
    )


def make_rows(age_seconds: float) -> list[dict]:
    ts = datetime.now(tz=timezone.utc) - timedelta(seconds=age_seconds)
    return [{"updated_at": ts}]


def test_passes_fresh_data(default_check):
    result = default_check.run(make_rows(60))
    assert result.status == CheckStatus.PASSED


def test_warns_aging_data(default_check):
    result = default_check.run(make_rows(2000))
    assert result.status == CheckStatus.WARNING
    assert "aging" in result.message


def test_fails_stale_data(default_check):
    result = default_check.run(make_rows(7200))
    assert result.status == CheckStatus.FAILED
    assert "stale" in result.message


def test_fails_on_empty_rows(default_check):
    result = default_check.run([])
    assert result.status == CheckStatus.FAILED
    assert "No rows" in result.message


def test_fails_on_null_timestamp(default_check):
    result = default_check.run([{"updated_at": None}])
    assert result.status == CheckStatus.FAILED


def test_uses_latest_timestamp(default_check):
    now = datetime.now(tz=timezone.utc)
    rows = [
        {"updated_at": now - timedelta(seconds=7200)},
        {"updated_at": now - timedelta(seconds=60)},
    ]
    result = default_check.run(rows)
    assert result.status == CheckStatus.PASSED


def test_details_included(default_check):
    result = default_check.run(make_rows(100))
    assert "age_seconds" in result.details
    assert "latest_timestamp" in result.details
    assert "max_age_seconds" in result.details


def test_unix_timestamp_support():
    check = FreshnessCheck(name="ts_check", column="ts", max_age_seconds=3600)
    now_unix = datetime.now(tz=timezone.utc).timestamp() - 30
    result = check.run([{"ts": now_unix}])
    assert result.status == CheckStatus.PASSED
