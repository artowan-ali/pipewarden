import pytest

from pipewarden.checks.base import CheckStatus
from pipewarden.checks.row_count import RowCountCheck


@pytest.fixture
def default_check():
    return RowCountCheck(name="test_row_count", config={"min_rows": 10, "max_rows": 1000})


def test_passes_within_range(default_check):
    result = default_check.run(row_count=500)
    assert result.passed()
    assert result.status == CheckStatus.PASSED
    assert result.details["row_count"] == 500


def test_fails_below_minimum(default_check):
    result = default_check.run(row_count=5)
    assert result.failed()
    assert result.status == CheckStatus.FAILED
    assert "below minimum" in result.message


def test_fails_above_maximum(default_check):
    result = default_check.run(row_count=1500)
    assert result.failed()
    assert "exceeds maximum" in result.message


def test_warning_threshold():
    check = RowCountCheck(
        name="warn_check",
        config={"min_rows": 100, "warning_threshold": 0.2},
    )
    # 85 is within 20% of 100 → WARNING
    result = check.run(row_count=85)
    assert result.status == CheckStatus.WARNING

    # 70 is more than 20% below → FAILED
    result = check.run(row_count=70)
    assert result.status == CheckStatus.FAILED


def test_skipped_when_no_row_count():
    check = RowCountCheck(name="skip_check")
    result = check.run()
    assert result.status == CheckStatus.SKIPPED


def test_duration_recorded(default_check):
    result = default_check.run(row_count=100)
    assert result.duration_ms is not None
    assert result.duration_ms >= 0


def test_to_dict(default_check):
    result = default_check.run(row_count=50)
    d = result.to_dict()
    assert d["check_name"] == "test_row_count"
    assert d["status"] == CheckStatus.PASSED.value
    assert "timestamp" in d
