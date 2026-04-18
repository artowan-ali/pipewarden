import pytest
from pipewarden.checks.regex_check import RegexCheck
from pipewarden.checks.base import CheckStatus


@pytest.fixture
def default_check():
    return RegexCheck(column="email", pattern=r"[^@]+@[^@]+\.[^@]+", max_failure_rate=0.0)


def make_rows(values: list[str]) -> list[dict]:
    return [{"email": v} for v in values]


def test_passes_all_match(default_check):
    rows = make_rows(["a@b.com", "user@example.org", "x@y.io"])
    result = default_check.run(rows)
    assert result.status == CheckStatus.PASSED


def test_fails_with_non_matching_values(default_check):
    rows = make_rows(["not-an-email", "also-bad"])
    result = default_check.run(rows)
    assert result.status == CheckStatus.FAILED
    assert result.metadata["failures"] == 2


def test_passes_within_allowed_failure_rate():
    check = RegexCheck(column="code", pattern=r"[A-Z]{3}\d{3}", max_failure_rate=0.5)
    rows = [{"code": "ABC123"}, {"code": "invalid"}, {"code": "XYZ999"}]
    result = check.run(rows)
    assert result.status == CheckStatus.PASSED


def test_fails_above_allowed_failure_rate():
    check = RegexCheck(column="code", pattern=r"[A-Z]{3}\d{3}", max_failure_rate=0.2)
    rows = [{"code": "ABC123"}, {"code": "bad"}, {"code": "worse"}]
    result = check.run(rows)
    assert result.status == CheckStatus.FAILED


def test_warning_threshold():
    check = RegexCheck(
        column="phone",
        pattern=r"\d{10}",
        max_failure_rate=0.5,
        warning_threshold=0.1,
    )
    rows = [{"phone": "1234567890"}, {"phone": "bad"}, {"phone": "9876543210"}]
    result = check.run(rows)
    assert result.status == CheckStatus.WARNING


def test_empty_rows(default_check):
    result = default_check.run([])
    assert result.status == CheckStatus.PASSED
    assert result.metadata["total"] == 0


def test_null_values_treated_as_empty_string():
    check = RegexCheck(column="val", pattern=r"\d+", max_failure_rate=0.0)
    rows = [{"val": None}, {"val": "123"}]
    result = check.run(rows)
    assert result.status == CheckStatus.FAILED
    assert result.metadata["failures"] == 1
