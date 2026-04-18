import pytest

from pipewarden.checks.base import CheckStatus
from pipewarden.checks.uniqueness_check import UniquenessCheck


@pytest.fixture
def default_check():
    return UniquenessCheck(name="test_unique", column="id", max_duplicate_rate=0.0)


def make_rows(total: int, duplicate_count: int):
    rows = [{"id": i} for i in range(total - duplicate_count)]
    rows += [{"id": 0}] * duplicate_count  # duplicate of id=0
    return rows


def test_passes_all_unique(default_check):
    rows = [{"id": i} for i in range(50)]
    result = default_check.run(rows)
    assert result.status == CheckStatus.PASSED


def test_fails_with_duplicates(default_check):
    rows = make_rows(100, 5)
    result = default_check.run(rows)
    assert result.status == CheckStatus.FAILED


def test_passes_within_allowed_rate():
    check = UniquenessCheck(name="allow_some", column="id", max_duplicate_rate=0.1)
    rows = make_rows(100, 5)
    result = check.run(rows)
    assert result.status == CheckStatus.PASSED


def test_warning_threshold():
    check = UniquenessCheck(
        name="warn_dupes",
        column="id",
        max_duplicate_rate=0.2,
        warning_duplicate_rate=0.03,
    )
    rows = make_rows(100, 10)
    result = check.run(rows)
    assert result.status == CheckStatus.WARNING


def test_empty_rows(default_check):
    result = default_check.run([])
    assert result.status == CheckStatus.FAILED


def test_context_fields(default_check):
    rows = [{"id": i} for i in range(20)]
    result = default_check.run(rows)
    assert result.context["unique_count"] == 20
    assert result.context["duplicate_count"] == 0
