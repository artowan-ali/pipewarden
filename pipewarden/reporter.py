"""Reporting utilities for pipeline run results."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from pipewarden.checks.base import CheckStatus
from pipewarden.runner import PipelineRunResult


def _status_icon(status: CheckStatus) -> str:
    return {
        CheckStatus.PASSED: "✅",
        CheckStatus.WARNED: "⚠️",
        CheckStatus.FAILED: "❌",
    }.get(status, "❓")


def format_text_report(result: PipelineRunResult) -> str:
    """Return a human-readable text summary of a pipeline run."""
    lines: list[str] = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines.append(f"PipeWarden Report — {now}")
    lines.append("=" * 50)

    for check_result in result.results:
        icon = _status_icon(check_result.status)
        lines.append(f"{icon}  [{check_result.status.value.upper()}] {check_result.check_name}")
        if check_result.message:
            lines.append(f"     {check_result.message}")
        if check_result.details:
            for key, value in check_result.details.items():
                lines.append(f"     {key}: {value}")

    lines.append("-" * 50)
    lines.append(result.summary)
    return "\n".join(lines)


def format_json_report(result: PipelineRunResult) -> str:
    """Return a JSON-serialisable string representation of a pipeline run."""
    payload: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "healthy": result.healthy,
        "summary": result.summary,
        "results": [
            {
                "check_name": r.check_name,
                "status": r.status.value,
                "message": r.message,
                "details": r.details or {},
            }
            for r in result.results
        ],
    }
    return json.dumps(payload, indent=2)


def write_report(result: PipelineRunResult, path: str, fmt: str = "text") -> None:
    """Write a report to *path* in the requested format ('text' or 'json')."""
    if fmt == "json":
        content = format_json_report(result)
    else:
        content = format_text_report(result)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
