import pytest
from pipewarden.checks.referential_integrity_check import ReferentialIntegrityCheck
from pipewarden.checks.base import CheckStatus


@pytest.fixture
def default_check():
    return ReferentialIntegrityCheck(
        column="user_id",
        reference_values=[1, 2, 3, 4, 5],
        allowed_violation_rate=0.0,
        warning_violation_rate=None,
    )


def make_rows(user_ids):
    return [{"user_id": uid} for uid in user_ids]


def test_passes_all_valid(default_check):
    rows = make_rows([1, 2, 3, 4, 5])
    result = default_check.run(rows)
    assert result.status == CheckStatus.PASSED


def test_fails_with_violations(default_check):
    rows = make_rows([1, 2, 99])
    result = default_check.run(rows)
    assert result.status == CheckStatus.FAILED
    assert "99" in result.message


def test_passes_within_allowed_rate():
    check = ReferentialIntegrityCheck(
        column="user_id",
        reference_values=[1, 2, 3, 4, 5],
        allowed_violation_rate=0.2,
    )
    rows = make_rows([1, 2, 3, 4, 99])
    result = check.run(rows)
    assert result.status == CheckStatus.PASSED


def test_fails_above_allowed_rate():
    check = ReferentialIntegrityCheck(
        column="user_id",
        reference_values=[1, 2, 3],
        allowed_violation_rate=0.1,
    )
    rows = make_rows([1, 99, 100])
    result = check.run(rows)
    assert result.status == CheckStatus.FAILED


def test_warns_within_warning_rate():
    check = ReferentialIntegrityCheck(
        column="user_id",
        reference_values=[1, 2, 3, 4, 5],
        allowed_violation_rate=0.3,
        warning_violation_rate=0.1,
    )
    rows = make_rows([1, 2, 3, 4, 99])
    result = check.run(rows)
    assert result.status == CheckStatus.WARNING


def test_passes_empty_rows(default_check):
    result = default_check.run([])
    assert result.status == CheckStatus.PASSED


def test_uses_reference_set_from_iterable():
    check = ReferentialIntegrityCheck(
        column="code",
        reference_values=(c for c in ["A", "B", "C"]),
    )
    rows = [{"code": "A"}, {"code": "B"}, {"code": "Z"}]
    result = check.run(rows)
    assert result.status == CheckStatus.FAILED
