from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from pipewarden.checks.base import CheckResult, CheckStatus, failed, passed, warning


@dataclass
class NullCheck:
    """Check that null/None values in a column don't exceed a threshold."""

    name: str
    column: str
    max_null_rate: float = 0.0
    warning_null_rate: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def run(self, rows: List[Dict[str, Any]]) -> CheckResult:
        if not rows:
            return failed(
                self.name,
                "No rows provided to NullCheck",
                {"column": self.column},
            )

        total = len(rows)
        null_count = sum(1 for row in rows if row.get(self.column) is None)
        null_rate = null_count / total

        context = {
            "column": self.column,
            "total_rows": total,
            "null_count": null_count,
            "null_rate": round(null_rate, 4),
            "max_null_rate": self.max_null_rate,
        }

        return self._evaluate(null_rate, context)

    def _evaluate(self, null_rate: float, context: Dict[str, Any]) -> CheckResult:
        if null_rate > self.max_null_rate:
            return failed(
                self.name,
                f"Null rate {null_rate:.2%} exceeds maximum {self.max_null_rate:.2%}",
                context,
            )

        if self.warning_null_rate is not None and null_rate > self.warning_null_rate:
            return warning(
                self.name,
                f"Null rate {null_rate:.2%} exceeds warning threshold {self.warning_null_rate:.2%}",
                context,
            )

        return passed(
            self.name,
            f"Null rate {null_rate:.2%} is within acceptable range",
            context,
        )
