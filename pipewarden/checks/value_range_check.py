from typing import Any, Dict, List, Optional
from pipewarden.checks.base import BaseCheck, CheckResult, passed, failed, warned


class ValueRangeCheck(BaseCheck):
    """Check that numeric values in a column fall within an expected range."""

    def __init__(
        self,
        column: str,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        warning_min: Optional[float] = None,
        warning_max: Optional[float] = None,
        allow_nulls: bool = True,
        name: Optional[str] = None,
    ):
        super().__init__(name or f"value_range:{column}")
        self.column = column
        self.min_value = min_value
        self.max_value = max_value
        self.warning_min = warning_min
        self.warning_max = warning_max
        self.allow_nulls = allow_nulls

    def run(self, rows: List[Dict[str, Any]]) -> CheckResult:
        if not rows:
            return passed(self.name, "No rows to check", {})

        violations = []
        null_count = 0

        for i, row in enumerate(rows):
            value = row.get(self.column)
            if value is None:
                null_count += 1
                if not self.allow_nulls:
                    violations.append(f"Row {i}: null value not allowed")
                continue
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                violations.append(f"Row {i}: non-numeric value '{value}'")
                continue

            if self.min_value is not None and numeric < self.min_value:
                violations.append(f"Row {i}: {numeric} < min {self.min_value}")
            elif self.max_value is not None and numeric > self.max_value:
                violations.append(f"Row {i}: {numeric} > max {self.max_value}")

        meta = {
            "total_rows": len(rows),
            "null_count": null_count,
            "violation_count": len(violations),
        }

        if violations:
            return failed(self.name, f"{len(violations)} value(s) out of range", meta)

        if self.warning_min is not None or self.warning_max is not None:
            warn_violations = []
            for row in rows:
                value = row.get(self.column)
                if value is None:
                    continue
                numeric = float(value)
                if self.warning_min is not None and numeric < self.warning_min:
                    warn_violations.append(numeric)
                elif self.warning_max is not None and numeric > self.warning_max:
                    warn_violations.append(numeric)
            if warn_violations:
                return warned(self.name, f"{len(warn_violations)} value(s) near range boundary", meta)

        return passed(self.name, "All values within range", meta)
