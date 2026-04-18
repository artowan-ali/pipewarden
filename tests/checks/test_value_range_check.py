import pytest
from pipewarden.checks.value_range_check import ValueRangeCheck
from pipewarden.checks.base import CheckStatus


@pytest.fixture
def default_check():
    return ValueRangeCheck(column="amount", min_value=0.0, max_value=1000.0)


def make_rows(values):
    return [{"amount": v} for v in values]


def test_passes_within_range(default_check):
    rows = make_rows([0, 100, 500, 999.99])
    result = default_check.run(rows)
    assert result.status == CheckStatus.PASS


def test_fails_below_minimum(default_check):
    rows = make_rows([100, -5, 200])
    result = default_check.run(rows)
    assert result.status == CheckStatus.FAIL
    assert "out of range" in result.message


def test_fails_above_maximum(default_check):
    rows = make_rows([100, 1500, 200])
    result = default_check.run(rows)
    assert result.status == CheckStatus.FAIL


def test_passes_empty_rows(default_check):
    result = default_check.run([])
    assert result.status == CheckStatus.PASS


def test_fails_non_numeric():
    check = ValueRangeCheck(column="amount", min_value=0)
    rows = make_rows([10, "abc", 20])
    result = check.run(rows)
    assert result.status == CheckStatus.FAIL


def test_allows_nulls_by_default():
    check = ValueRangeCheck(column="amount", min_value=0, max_value=100)
    rows = make_rows([10, None, 50])
    result = check.run(rows)
    assert result.status == CheckStatus.PASS
    assert result.meta["null_count"] == 1


def test_fails_nulls_when_disallowed():
    check = ValueRangeCheck(column="amount", min_value=0, allow_nulls=False)
    rows = make_rows([10, None, 50])
    result = check.run(rows)
    assert result.status == CheckStatus.FAIL


def test_warning_threshold():
    check = ValueRangeCheck(
        column="amount",
        min_value=0,
        max_value=1000,
        warning_min=10,
        warning_max=900,
    )
    rows = make_rows([5, 500, 800])
    result = check.run(rows)
    assert result.status == CheckStatus.WARN
