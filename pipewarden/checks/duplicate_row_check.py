from dataclasses import dataclass, field
from typing import Any, List, Optional
from pipewarden.checks.base import BaseCheck, CheckResult, passed, failed, warned


@dataclass
class DuplicateRowCheck(BaseCheck):
    """Check that duplicate rows do not exceed an allowed rate."""

    columns: Optional[List[str]] = None  # None means all columns
    allowed_duplicate_rate: float = 0.0
    warning_duplicate_rate: Optional[float] = None
    name: str = "duplicate_row_check"

    def run(self, rows: List[dict]) -> CheckResult:
        if not rows:
            return passed(self.name, "No rows to check", {})

        total = len(rows)

        def row_key(row: dict) -> tuple:
            if self.columns:
                return tuple(row.get(c) for c in self.columns)
            return tuple(sorted(row.items()))

        seen = {}
        duplicate_count = 0
        for row in rows:
            key = row_key(row)
            if key in seen:
                duplicate_count += 1
            else:
                seen[key] = True

        duplicate_rate = duplicate_count / total
        details = {
            "total_rows": total,
            "duplicate_rows": duplicate_count,
            "duplicate_rate": round(duplicate_rate, 4),
            "allowed_duplicate_rate": self.allowed_duplicate_rate,
            "columns_checked": self.columns or "all",
        }

        if duplicate_rate > self.allowed_duplicate_rate:
            return failed(
                self.name,
                f"Duplicate rate {duplicate_rate:.2%} exceeds allowed {self.allowed_duplicate_rate:.2%}",
                details,
            )

        if self.warning_duplicate_rate is not None and duplicate_rate > self.warning_duplicate_rate:
            return warned(
                self.name,
                f"Duplicate rate {duplicate_rate:.2%} exceeds warning threshold {self.warning_duplicate_rate:.2%}",
                details,
            )

        return passed(
            self.name,
            f"Duplicate rate {duplicate_rate:.2%} within allowed {self.allowed_duplicate_rate:.2%}",
            details,
        )
