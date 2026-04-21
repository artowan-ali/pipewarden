"""Pipeline check runner: executes a list of checks and aggregates results."""

from dataclasses import dataclass, field
from typing import Any

from pipewarden.checks.base import BaseCheck, CheckResult, CheckStatus


@dataclass
class PipelineRunResult:
    """Aggregated result of running all checks in a pipeline."""

    results: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> list[CheckResult]:
        return [r for r in self.results if r.status == CheckStatus.PASSED]

    @property
    def warned(self) -> list[CheckResult]:
        return [r for r in self.results if r.status == CheckStatus.WARNED]

    @property
    def failed(self) -> list[CheckResult]:
        return [r for r in self.results if r.status == CheckStatus.FAILED]

    @property
    def healthy(self) -> bool:
        return len(self.failed) == 0

    def summary(self) -> str:
        total = len(self.results)
        return (
            f"Pipeline run: {total} checks — "
            f"{len(self.passed)} passed, "
            f"{len(self.warned)} warned, "
            f"{len(self.failed)} failed."
        )


class PipelineRunner:
    """Runs a collection of checks against provided row data."""

    def __init__(self, checks: list[BaseCheck]) -> None:
        self.checks = checks

    def run(self, rows: list[dict[str, Any]]) -> PipelineRunResult:
        """Execute all checks and return an aggregated result."""
        results: list[CheckResult] = []
        for check in self.checks:
            try:
                result = check.run(rows)
            except Exception as exc:  # noqa: BLE001
                from pipewarden.checks.base import failed as make_failed

                result = make_failed(
                    getattr(check, "name", type(check).__name__),
                    f"Check raised an unexpected error: {exc}",
                )
            results.append(result)
        return PipelineRunResult(results=results)
