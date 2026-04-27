import pytest
from pipewarden.checks.trend_check import TrendCheck
from pipewarden.checks.base import CheckStatus


@pytest.fixture
def default_check():
    return TrendCheck(
        column="value",
        baseline=100.0,
        warning_threshold=0.10,
        failure_threshold=0.25,
    )


def make_rows(values: list[float], col: str = "value") -> list[dict]:
    return [{col: v} for v in values]


def test_passes_within_range(default_check):
    rows = make_rows([98, 100, 102, 99, 101])  # avg ≈ 100 → 0 % change
    result = default_check.run(rows)
    assert result.status == CheckStatus.PASSED


def test_warns_moderate_deviation(default_check):
    # avg = 115 → 15 % above baseline; > 10 % warning, < 25 % failure
    rows = make_rows([113, 115, 117])
    result = default_check.run(rows)
    assert result.status == CheckStatus.WARNED
    assert "warning threshold" in result.message


def test_fails_large_deviation(default_check):
    # avg = 140 → 40 % above baseline; > 25 % failure
    rows = make_rows([138, 140, 142])
    result = default_check.run(rows)
    assert result.status == CheckStatus.FAILED
    assert "failure threshold" in result.message


def test_fails_on_empty_rows(default_check):
    result = default_check.run([])
    assert result.status == CheckStatus.FAILED
    assert "No rows" in result.message


def test_fails_on_non_numeric_values(default_check):
    rows = [{"value": "not-a-number"}]
    result = default_check.run(rows)
    assert result.status == CheckStatus.FAILED
    assert "Non-numeric" in result.message


def test_skips_null_values():
    check = TrendCheck(column="value", baseline=50.0, warning_threshold=0.1, failure_threshold=0.2)
    rows = [{"value": None}, {"value": 50}, {"value": 50}]
    result = check.run(rows)
    assert result.status == CheckStatus.PASSED


def test_fails_when_all_values_null(default_check):
    rows = [{"value": None}, {"value": None}]
    result = default_check.run(rows)
    assert result.status == CheckStatus.FAILED
    assert "no usable numeric" in result.message


def test_custom_aggregator_uses_max():
    check = TrendCheck(
        column="value",
        baseline=100.0,
        warning_threshold=0.10,
        failure_threshold=0.25,
        aggregator=max,
    )
    rows = make_rows([80, 90, 130])  # max=130 → 30 % → fail
    result = check.run(rows)
    assert result.status == CheckStatus.FAILED


def test_negative_deviation_warns(default_check):
    """A drop below baseline should also trigger warning/failure thresholds."""
    # avg = 85 → 15 % below baseline; > 10 % warning, < 25 % failure
    rows = make_rows([83, 85, 87])
    result = default_check.run(rows)
    assert result.status == CheckStatus.WARNED
    assert "warning threshold" in result.message


def test_negative_deviation_fails(default_check):
    """A large drop below baseline should trigger the failure threshold."""
    # avg = 60 → 40 % below baseline; > 25 % failure
    rows = make_rows([58, 60, 62])
    result = default_check.run(rows)
    assert result.status == CheckStatus.FAILED
    assert "failure threshold" in result.message
