import pytest
from pipewarden.checks.completeness_check import CompletenessCheck
from pipewarden.checks.base import CheckStatus


@pytest.fixture
def default_check():
    return CompletenessCheck(
        name="test_completeness",
        columns=["name", "email"],
        allowed_missing_rate=0.0,
    )


def make_rows(data):
    return data


def test_passes_all_present(default_check):
    rows = make_rows([{"name": "Alice", "email": "a@example.com"}, {"name": "Bob", "email": "b@example.com"}])
    result = default_check.run(rows)
    assert result.status == CheckStatus.PASSED


def test_fails_with_nulls(default_check):
    rows = make_rows([{"name": None, "email": "a@example.com"}, {"name": "Bob", "email": "b@example.com"}])
    result = default_check.run(rows)
    assert result.status == CheckStatus.FAILED
    assert result.details["missing_count"] == 1


def test_fails_with_empty_strings(default_check):
    rows = make_rows([{"name": "", "email": "a@example.com"}])
    result = default_check.run(rows)
    assert result.status == CheckStatus.FAILED


def test_passes_within_allowed_rate():
    check = CompletenessCheck(
        name="lenient_check",
        columns=["name", "email"],
        allowed_missing_rate=0.3,
    )
    rows = make_rows([
        {"name": None, "email": "a@example.com"},
        {"name": "Bob", "email": "b@example.com"},
        {"name": "Carol", "email": "c@example.com"},
        {"name": "Dave", "email": "d@example.com"},
    ])
    result = check.run(rows)
    assert result.status == CheckStatus.PASSED


def test_warning_threshold():
    check = CompletenessCheck(
        name="warn_check",
        columns=["name"],
        allowed_missing_rate=0.5,
        warning_missing_rate=0.1,
    )
    rows = make_rows([{"name": None}, {"name": "Bob"}, {"name": "Carol"}, {"name": "Dave"}, {"name": "Eve"}])
    result = check.run(rows)
    assert result.status == CheckStatus.WARNING


def test_fails_no_rows(default_check):
    result = default_check.run([])
    assert result.status == CheckStatus.FAILED


def test_fails_no_columns_specified():
    check = CompletenessCheck(name="empty_cols", columns=[])
    rows = [{"name": "Alice"}]
    result = check.run(rows)
    assert result.status == CheckStatus.FAILED


def test_result_details(default_check):
    rows = [{"name": "Alice", "email": None}]
    result = default_check.run(rows)
    assert "missing_rate" in result.details
    assert "columns_checked" in result.details
    assert result.details["missing_count"] == 1


def test_fails_exceeds_allowed_rate():
    """Verify that missing rate just above the allowed threshold causes a failure."""
    check = CompletenessCheck(
        name="strict_check",
        columns=["name"],
        allowed_missing_rate=0.2,
    )
    # 2 out of 5 rows are missing -> 0.4 missing rate, exceeds 0.2 threshold
    rows = make_rows([
        {"name": None},
        {"name": None},
        {"name": "Carol"},
        {"name": "Dave"},
        {"name": "Eve"},
    ])
    result = check.run(rows)
    assert result.status == CheckStatus.FAILED
    assert result.details["missing_count"] == 2
