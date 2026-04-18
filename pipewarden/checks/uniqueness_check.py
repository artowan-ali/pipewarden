from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from pipewarden.checks.base import CheckResult, failed, passed, warning


@dataclass
class UniquenessCheck:
    """Check that duplicate values in a column don't exceed a threshold."""

    name: str
    column: str
    max_duplicate_rate: float = 0.0
    warning_duplicate_rate: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def run(self, rows: List[Dict[str, Any]]) -> CheckResult:
        if not rows:
            return failed(
                self.name,
                "No rows provided to UniquenessCheck",
                {"column": self.column},
            )

        total = len(rows)
        values = [row.get(self.column) for row in rows]
        unique_count = len(set(v for v in values if v is not None))
        non_null_count = sum(1 for v in values if v is not None)
        duplicate_count = max(non_null_count - unique_count, 0)
        duplicate_rate = duplicate_count / total if total else 0.0

        context = {
            "column": self.column,
            "total_rows": total,
            "unique_count": unique_count,
            "duplicate_count": duplicate_count,
            "duplicate_rate": round(duplicate_rate, 4),
            "max_duplicate_rate": self.max_duplicate_rate,
        }

        if duplicate_rate > self.max_duplicate_rate:
            return failed(
                self.name,
                f"Duplicate rate {duplicate_rate:.2%} exceeds maximum {self.max_duplicate_rate:.2%}",
                context,
            )

        if (
            self.warning_duplicate_rate is not None
            and duplicate_rate > self.warning_duplicate_rate
        ):
            return warning(
                self.name,
                f"Duplicate rate {duplicate_rate:.2%} exceeds warning threshold {self.warning_duplicate_rate:.2%}",
                context,
            )

        return passed(
            self.name,
            f"Duplicate rate {duplicate_rate:.2%} is within acceptable range",
            context,
        )
