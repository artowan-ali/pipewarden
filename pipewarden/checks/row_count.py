import time
from typing import Any, Dict, Optional

from pipewarden.checks.base import BaseCheck, CheckResult, CheckStatus


class RowCountCheck(BaseCheck):
    """
    Validates that a data source row count falls within expected bounds.

    Config keys:
        min_rows (int): minimum acceptable row count (default 1)
        max_rows (int | None): maximum acceptable row count (default None = unlimited)
        warning_threshold (float): fraction below min_rows that triggers WARNING instead of FAILED (default 0.0)
    """

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        super().__init__(name, config)
        self.min_rows: int = self.config.get("min_rows", 1)
        self.max_rows: Optional[int] = self.config.get("max_rows", None)
        self.warning_threshold: float = self.config.get("warning_threshold", 0.0)

    def run(self, row_count: Optional[int] = None) -> CheckResult:  # type: ignore[override]
        if row_count is None:
            row_count = self.config.get("row_count")
        if row_count is None:
            return self._make_result(
                CheckStatus.SKIPPED,
                "No row count provided; check skipped.",
            )

        start = time.monotonic()
        result = self._evaluate(row_count)
        result.duration_ms = (time.monotonic() - start) * 1000
        return result

    def _evaluate(self, row_count: int) -> CheckResult:
        details = {
            "row_count": row_count,
            "min_rows": self.min_rows,
            "max_rows": self.max_rows,
        }

        if self.max_rows is not None and row_count > self.max_rows:
            return self._make_result(
                CheckStatus.FAILED,
                f"Row count {row_count} exceeds maximum {self.max_rows}.",
                details,
            )

        if row_count < self.min_rows:
            warn_floor = int(self.min_rows * (1 - self.warning_threshold))
            status = CheckStatus.WARNING if row_count >= warn_floor else CheckStatus.FAILED
            return self._make_result(
                status,
                f"Row count {row_count} is below minimum {self.min_rows}.",
                details,
            )

        return self._make_result(
            CheckStatus.PASSED,
            f"Row count {row_count} is within acceptable range.",
            details,
        )
