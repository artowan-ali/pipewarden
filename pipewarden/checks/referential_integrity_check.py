from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Optional
from pipewarden.checks.base import BaseCheck, CheckResult, passed, failed, warned


@dataclass
class ReferentialIntegrityCheck(BaseCheck):
    """Checks that all values in a foreign key column exist in a reference set."""

    column: str
    reference_values: Iterable[Any]
    allowed_violation_rate: float = 0.0
    warning_violation_rate: Optional[float] = None
    name: str = "ReferentialIntegrityCheck"

    def __post_init__(self):
        self._reference_set = set(self.reference_values)

    def run(self, rows: Iterable[dict]) -> CheckResult:
        rows = list(rows)
        if not rows:
            return passed(self.name, "No rows to check.")

        total = len(rows)
        violations = [
            row for row in rows
            if row.get(self.column) not in self._reference_set
        ]
        violation_count = len(violations)
        violation_rate = violation_count / total
        violation_values = list({row.get(self.column) for row in violations})

        detail = (
            f"{violation_count}/{total} rows have values in '{self.column}' "
            f"not found in reference set (rate={violation_rate:.2%}). "
            f"Offending values: {violation_values[:10]}"
        )

        if violation_rate > self.allowed_violation_rate:
            return failed(self.name, detail)

        if (
            self.warning_violation_rate is not None
            and violation_rate > self.warning_violation_rate
        ):
            return warned(self.name, detail)

        return passed(
            self.name,
            f"All {total} rows satisfy referential integrity on '{self.column}'.",
        )
