from dataclasses import dataclass, field
from typing import Any, Optional
from pipewarden.checks.base import BaseCheck, CheckResult, passed, failed, warned


@dataclass
class DistributionCheck(BaseCheck):
    """Check that a column's value distribution matches expected proportions."""

    column: str
    expected: dict[str, float]  # {value: expected_proportion}
    tolerance: float = 0.05
    warning_tolerance: Optional[float] = None
    name: str = "distribution_check"

    def run(self, rows: list[dict[str, Any]]) -> CheckResult:
        if not rows:
            return failed(self.name, "No rows provided", {})

        total = len(rows)
        counts: dict[str, int] = {}
        for row in rows:
            val = str(row.get(self.column, ""))
            counts[val] = counts.get(val, 0) + 1

        actual = {k: v / total for k, v in counts.items()}
        deviations = {}
        max_deviation = 0.0

        for value, expected_prop in self.expected.items():
            actual_prop = actual.get(value, 0.0)
            deviation = abs(actual_prop - expected_prop)
            deviations[value] = round(deviation, 4)
            if deviation > max_deviation:
                max_deviation = deviation

        details = {
            "column": self.column,
            "expected": self.expected,
            "actual": {k: round(v, 4) for k, v in actual.items()},
            "deviations": deviations,
            "max_deviation": round(max_deviation, 4),
            "tolerance": self.tolerance,
        }

        if max_deviation <= self.tolerance:
            return passed(self.name, details)

        if self.warning_tolerance is not None and max_deviation <= self.warning_tolerance:
            return warned(
                self.name,
                f"Max deviation {max_deviation:.4f} exceeds tolerance {self.tolerance}",
                details,
            )

        return failed(
            self.name,
            f"Max deviation {max_deviation:.4f} exceeds tolerance {self.tolerance}",
            details,
        )
