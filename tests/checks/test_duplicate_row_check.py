import pytest
from pipewarden.checks.duplicate_row_check import DuplicateRowCheck
from pipewarden.checks.base import CheckStatus


@pytest.fixture
def default_check():
    return DuplicateRowCheck(allowed_duplicate_rate=0.1)


def make_rows(*dicts):
    return list(dicts)


def test_passes_all_unique(default_check):
    rows = make_rows({"id": 1}, {"id": 2}, {"id": 3})
    result = default_check.run(rows)
    assert result.status == CheckStatus.PASSED


def test_fails_with_duplicates_above_threshold(default_check):
    rows = make_rows({"id": 1}, {"id": 1}, {"id": 1}, {"id": 2}, {"id": 3})
    result = default_check.run(rows)
    assert result.status == CheckStatus.FAILED
    assert result.details["duplicate_rows"] == 2


def test_passes_within_allowed_rate():
    check = DuplicateRowCheck(allowed_duplicate_rate=0.5)
    rows = make_rows({"id": 1}, {"id": 1}, {"id": 2}, {"id": 3})
    result = check.run(rows)
    assert result.status == CheckStatus.PASSED


def test_warns_within_warning_threshold():
    check = DuplicateRowCheck(allowed_duplicate_rate=0.5, warning_duplicate_rate=0.1)
    rows = make_rows({"id": 1}, {"id": 1}, {"id": 2}, {"id": 3})
    result = check.run(rows)
    assert result.status == CheckStatus.WARNING


def test_passes_empty_rows(default_check):
    result = default_check.run([])
    assert result.status == CheckStatus.PASSED


def test_checks_specific_columns():
    check = DuplicateRowCheck(columns=["name"], allowed_duplicate_rate=0.0)
    rows = make_rows(
        {"id": 1, "name": "alice"},
        {"id": 2, "name": "alice"},
        {"id": 3, "name": "bob"},
    )
    result = check.run(rows)
    assert result.status == CheckStatus.FAILED
    assert result.details["columns_checked"] == ["name"]


def test_details_contain_expected_keys(default_check):
    rows = make_rows({"id": 1}, {"id": 2})
    result = default_check.run(rows)
    for key in ("total_rows", "duplicate_rows", "duplicate_rate", "allowed_duplicate_rate"):
        assert key in result.details
