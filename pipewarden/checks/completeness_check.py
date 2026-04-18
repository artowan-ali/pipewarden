from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pipewarden.checks.base import BaseCheck, CheckResult, passed, failed, warned


@dataclass
class CompletenessCheck(BaseCheck):
    """Check that required columns have no missing/empty values."""

    name: str = "completeness_check"
    columns: List[str] = field(default_factory=list)
    allowed_missing_rate: float = 0.0
    warning_missing_rate: Optional[float] = None

    def run(self, rows: List[Dict[str, Any]]) -> CheckResult:
        if not rows:
            return failed(self.name, "No rows provided", {"row_count": 0})

        if not self.columns:
            return failed(self.name, "No columns specified for completeness check", {})

        total_values = len(rows) * len(self.columns)
        missing_count = 0

        for row in rows:
            for col in self.columns:
                val = row.get(col)
                if val is None or val == "":
                    missing_count += 1

        missing_rate = missing_count / total_values
        details = {
            "row_count": len(rows),
            "columns_checked": self.columns,
            "missing_count": missing_count,
            "missing_rate": round(missing_rate, 4),
            "allowed_missing_rate": self.allowed_missing_rate,
        }

        if missing_rate > self.allowed_missing_rate:
            return failed(
                self.name,
                f"Missing rate {missing_rate:.2%} exceeds allowed {self.allowed_missing_rate:.2%}",
                details,
            )

        if self.warning_missing_rate is not None and missing_rate > self.warning_missing_rate:
            return warned(
                self.name,
                f"Missing rate {missing_rate:.2%} exceeds warning threshold {self.warning_missing_rate:.2%}",
                details,
            )

        return passed(self.name, f"Missing rate {missing_rate:.2%} within acceptable range", details)
