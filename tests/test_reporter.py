"""Tests for pipewarden.reporter."""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from pipewarden.checks.base import CheckResult, CheckStatus
from pipewarden.reporter import format_json_report, format_text_report, write_report
from pipewarden.runner import PipelineRunResult


def _make_result(healthy: bool, results: list[CheckResult]) -> PipelineRunResult:
    return PipelineRunResult(healthy=healthy, results=results)


@pytest.fixture()
def mixed_run() -> PipelineRunResult:
    return _make_result(
        healthy=False,
        results=[
            CheckResult(check_name="row_count", status=CheckStatus.PASSED, message="OK"),
            CheckResult(
                check_name="null_check",
                status=CheckStatus.FAILED,
                message="Too many nulls",
                details={"null_rate": 0.25},
            ),
            CheckResult(check_name="freshness", status=CheckStatus.WARNED, message="Aging data"),
        ],
    )


def test_text_report_contains_check_names(mixed_run: PipelineRunResult) -> None:
    report = format_text_report(mixed_run)
    assert "row_count" in report
    assert "null_check" in report
    assert "freshness" in report


def test_text_report_contains_status_labels(mixed_run: PipelineRunResult) -> None:
    report = format_text_report(mixed_run)
    assert "PASSED" in report
    assert "FAILED" in report
    assert "WARNED" in report


def test_text_report_contains_details(mixed_run: PipelineRunResult) -> None:
    report = format_text_report(mixed_run)
    assert "null_rate" in report
    assert "0.25" in report


def test_json_report_is_valid_json(mixed_run: PipelineRunResult) -> None:
    raw = format_json_report(mixed_run)
    data = json.loads(raw)
    assert "results" in data
    assert len(data["results"]) == 3


def test_json_report_healthy_flag(mixed_run: PipelineRunResult) -> None:
    data = json.loads(format_json_report(mixed_run))
    assert data["healthy"] is False


def test_json_report_statuses(mixed_run: PipelineRunResult) -> None:
    data = json.loads(format_json_report(mixed_run))
    statuses = {r["check_name"]: r["status"] for r in data["results"]}
    assert statuses["row_count"] == "passed"
    assert statuses["null_check"] == "failed"
    assert statuses["freshness"] == "warned"


def test_write_text_report(mixed_run: PipelineRunResult) -> None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        path = tmp.name
    try:
        write_report(mixed_run, path, fmt="text")
        content = open(path).read()
        assert "PipeWarden Report" in content
    finally:
        os.unlink(path)


def test_write_json_report(mixed_run: PipelineRunResult) -> None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
        path = tmp.name
    try:
        write_report(mixed_run, path, fmt="json")
        data = json.loads(open(path).read())
        assert "timestamp" in data
    finally:
        os.unlink(path)
