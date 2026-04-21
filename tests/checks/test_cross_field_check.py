import pytest
from pipewarden.checks.cross_field_check import CrossFieldCheck
from pipewarden.checks.base import CheckStatus


@pytest.fixture
def default_check():
    return CrossFieldCheck(
        predicate=lambda row: row["end"] >= row["start"],
        allowed_failure_rate=0.0,
    )


def test_passes_all_valid(default_check):
    rows = [{"start": 1, "end": 5}, {"start": 3, "end": 3}]
    result = default_check.run(rows)
    assert result.status == CheckStatus.PASSED


def test_fails_with_invalid_rows(default_check):
    rows = [{"start": 5, "end": 1}]
    result = default_check.run(rows)
    assert result.status == CheckStatus.FAILED


def test_passes_within_allowed_rate():
    check = CrossFieldCheck(
        predicate=lambda row: row["qty"] > 0,
        allowed_failure_rate=0.25,
    )
    rows = [{"qty": 1}, {"qty": 2}, {"qty": 3}, {"qty": -1}]
    result = check.run(rows)
    assert result.status == CheckStatus.PASSED


def test_fails_above_allowed_rate():
    check = CrossFieldCheck(
        predicate=lambda row: row["qty"] > 0,
        allowed_failure_rate=0.1,
    )
    rows = [{"qty": 1}, {"qty": -1}, {"qty": -2}]
    result = check.run(rows)
    assert result.status == CheckStatus.FAILED


def test_warns_within_warning_rate():
    check = CrossFieldCheck(
        predicate=lambda row: row["a"] != row["b"],
        allowed_failure_rate=0.4,
        warning_failure_rate=0.1,
    )
    rows = [{"a": 1, "b": 1}, {"a": 2, "b": 3}, {"a": 4, "b": 4}, {"a": 5, "b": 6}]
    result = check.run(rows)
    assert result.status == CheckStatus.WARNING


def test_passes_empty_rows(default_check):
    result = default_check.run([])
    assert result.status == CheckStatus.PASSED


def test_custom_name():
    check = CrossFieldCheck(
        predicate=lambda row: True,
        name="MyCustomCrossFieldCheck",
    )
    result = check.run([{"x": 1}])
    assert result.check_name == "MyCustomCrossFieldCheck"
