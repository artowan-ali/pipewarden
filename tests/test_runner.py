"""Tests for PipelineRunner."""

import pytest

from pipewarden.checks.base import CheckStatus
from pipewarden.checks.null_check import NullCheck
from pipewarden.checks.row_count import RowCountCheck
from pipewarden.checks.statistical_outlier_check import StatisticalOutlierCheck
from pipewarden.runner import PipelineRunner


def make_rows(n: int = 10):
    return [{"id": i, "score": 50 + (i % 5)} for i in range(n)]


def test_all_checks_pass():
    checks = [
        RowCountCheck(min_count=5, max_count=20),
        NullCheck(column="id", allowed_null_rate=0.0),
    ]
    runner = PipelineRunner(checks)
    result = runner.run(make_rows(10))
    assert result.healthy
    assert len(result.passed) == 2
    assert len(result.failed) == 0


def test_failed_check_marks_unhealthy():
    checks = [
        RowCountCheck(min_count=100, max_count=200),
    ]
    runner = PipelineRunner(checks)
    result = runner.run(make_rows(10))
    assert not result.healthy
    assert len(result.failed) == 1


def test_summary_string():
    checks = [
        RowCountCheck(min_count=5, max_count=20),
        RowCountCheck(min_count=100, max_count=200),
    ]
    runner = PipelineRunner(checks)
    result = runner.run(make_rows(10))
    summary = result.summary()
    assert "2 checks" in summary
    assert "1 passed" in summary
    assert "1 failed" in summary


def test_exception_in_check_is_caught():
    class BrokenCheck:
        name = "broken"

        def run(self, rows):
            raise RuntimeError("Simulated failure")

    runner = PipelineRunner([BrokenCheck()])
    result = runner.run(make_rows())
    assert not result.healthy
    assert "unexpected error" in result.failed[0].message


def test_mixed_statuses():
    checks = [
        RowCountCheck(min_count=5, max_count=20),
        StatisticalOutlierCheck(
            column="score",
            method="zscore",
            threshold=2.0,
            allowed_outlier_rate=0.5,
            warning_outlier_rate=0.0,
        ),
    ]
    runner = PipelineRunner(checks)
    rows = [{"id": i, "score": 50 if i < 9 else 9999} for i in range(10)]
    result = runner.run(rows)
    assert len(result.warned) >= 1
    assert result.healthy
