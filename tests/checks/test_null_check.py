import pytest

from pipewarden.checks.base import CheckStatus
from pipewarden.checks.null_check import NullCheck


@pytest.fixture
def default_check():
    return NullCheck(name="test_nulls", column="email", max_null_rate=0.1)


def make_rows(total: int, null_count: int):
    rows = [{"email": f"user{i}@example.com"} for i in range(total - null_count)]
    rows += [{"email": None}] * null_count
    return rows


def test_passes_no_nulls(default_check):
    rows = make_rows(100, 0)
    result = default_check.run(rows)
    assert result.status == CheckStatus.PASSED


def test_passes_within_threshold(default_check):
    rows = make_rows(100, 5)
    result = default_check.run(rows)
    assert result.status == CheckStatus.PASSED


def test_fails_above_threshold(default_check):
    rows = make_rows(100, 20)
    result = default_check.run(rows)
    assert result.status == CheckStatus.FAILED
    assert "20.00%" in result.message


def test_warning_threshold():
    check = NullCheck(
        name="warn_nulls",
        column="email",
        max_null_rate=0.2,
        warning_null_rate=0.05,
    )
    rows = make_rows(100, 10)
    result = check.run(rows)
    assert result.status == CheckStatus.WARNING


def test_empty_rows(default_check):
    result = default_check.run([])
    assert result.status == CheckStatus.FAILED
    assert "No rows" in result.message


def test_context_contains_column(default_check):
    rows = make_rows(50, 2)
    result = default_check.run(rows)
    assert result.context["column"] == "email"
    assert result.context["total_rows"] == 50
