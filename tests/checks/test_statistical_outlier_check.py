"""Tests for StatisticalOutlierCheck."""

import pytest

from pipewarden.checks.base import CheckStatus
from pipewarden.checks.statistical_outlier_check import StatisticalOutlierCheck


@pytest.fixture
def default_check():
    return StatisticalOutlierCheck(
        column="value",
        method="zscore",
        threshold=3.0,
        allowed_outlier_rate=0.0,
    )


def make_rows(values: list):
    return [{"value": v} for v in values]


def test_passes_no_outliers(default_check):
    rows = make_rows([10, 11, 10, 12, 11, 10, 11])
    result = default_check.run(rows)
    assert result.status == CheckStatus.PASSED


def test_fails_with_outliers(default_check):
    rows = make_rows([10, 11, 10, 12, 11, 1000])
    result = default_check.run(rows)
    assert result.status == CheckStatus.FAILED
    assert "outliers" in result.message


def test_passes_within_allowed_rate():
    check = StatisticalOutlierCheck(
        column="value",
        method="zscore",
        threshold=2.0,
        allowed_outlier_rate=0.2,
    )
    rows = make_rows([10, 10, 10, 10, 10, 1000])
    result = check.run(rows)
    assert result.status == CheckStatus.PASSED


def test_warns_within_warning_rate():
    check = StatisticalOutlierCheck(
        column="value",
        method="zscore",
        threshold=2.0,
        allowed_outlier_rate=0.5,
        warning_outlier_rate=0.1,
    )
    rows = make_rows([10, 10, 10, 10, 10, 1000])
    result = check.run(rows)
    assert result.status == CheckStatus.WARNED


def test_passes_empty_rows(default_check):
    result = default_check.run([])
    assert result.status == CheckStatus.PASSED


def test_fails_no_numeric_values(default_check):
    rows = [{"value": "abc"}, {"value": None}]
    result = default_check.run(rows)
    assert result.status == CheckStatus.FAILED


def test_iqr_method_passes_no_outliers():
    check = StatisticalOutlierCheck(
        column="score",
        method="iqr",
        threshold=1.5,
        allowed_outlier_rate=0.0,
    )
    rows = [{"score": v} for v in [10, 12, 11, 13, 10, 12]]
    result = check.run(rows)
    assert result.status == CheckStatus.PASSED


def test_iqr_method_fails_with_outliers():
    check = StatisticalOutlierCheck(
        column="score",
        method="iqr",
        threshold=1.5,
        allowed_outlier_rate=0.0,
    )
    rows = [{"score": v} for v in [10, 12, 11, 13, 10, 500]]
    result = check.run(rows)
    assert result.status == CheckStatus.FAILED
