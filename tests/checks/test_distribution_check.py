import pytest
from pipewarden.checks.distribution_check import DistributionCheck
from pipewarden.checks.base import CheckStatus


@pytest.fixture
def default_check():
    return DistributionCheck(
        column="status",
        expected={"active": 0.5, "inactive": 0.5},
        tolerance=0.05,
        warning_tolerance=0.10,
    )


def make_rows(active: int, inactive: int):
    return [{"status": "active"}] * active + [{"status": "inactive"}] * inactive


def test_passes_exact_distribution(default_check):
    rows = make_rows(50, 50)
    result = default_check.run(rows)
    assert result.status == CheckStatus.PASSED


def test_passes_within_tolerance(default_check):
    rows = make_rows(52, 48)
    result = default_check.run(rows)
    assert result.status == CheckStatus.PASSED


def test_warns_within_warning_tolerance(default_check):
    rows = make_rows(58, 42)
    result = default_check.run(rows)
    assert result.status == CheckStatus.WARNING


def test_fails_beyond_warning_tolerance(default_check):
    rows = make_rows(70, 30)
    result = default_check.run(rows)
    assert result.status == CheckStatus.FAILED


def test_fails_no_rows(default_check):
    result = default_check.run([])
    assert result.status == CheckStatus.FAILED
    assert "No rows" in result.message


def test_details_contain_actual_distribution(default_check):
    rows = make_rows(60, 40)
    result = default_check.run(rows)
    assert "actual" in result.details
    assert "deviations" in result.details
    assert result.details["actual"]["active"] == pytest.approx(0.6, abs=0.01)


def test_missing_expected_value_counted_as_zero():
    check = DistributionCheck(
        column="tier",
        expected={"gold": 0.3, "silver": 0.3, "bronze": 0.4},
        tolerance=0.05,
    )
    rows = [{"tier": "gold"}] * 50 + [{"tier": "silver"}] * 50
    result = check.run(rows)
    assert result.status == CheckStatus.FAILED
    assert result.details["deviations"]["bronze"] == pytest.approx(0.4, abs=0.01)
