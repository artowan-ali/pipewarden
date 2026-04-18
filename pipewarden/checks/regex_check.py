from dataclasses import dataclass, field
from typing import Any, Optional
import re

from pipewarden.checks.base import BaseCheck, CheckResult, passed, failed, warned


@dataclass
class RegexCheck(BaseCheck):
    """Check that values in a column match a given regex pattern."""

    column: str
    pattern: str
    max_failure_rate: float = 0.0
    warning_threshold: Optional[float] = None
    name: str = "RegexCheck"

    def __post_init__(self):
        self._compiled = re.compile(self.pattern)

    def run(self, rows: list[dict[str, Any]]) -> CheckResult:
        if not rows:
            return passed(self.name, "No rows to validate", metadata={"total": 0})

        total = len(rows)
        failures = sum(
            1 for row in rows
            if not self._compiled.fullmatch(str(row.get(self.column, "") or ""))
        )
        failure_rate = failures / total

        metadata = {
            "column": self.column,
            "pattern": self.pattern,
            "total": total,
            "failures": failures,
            "failure_rate": round(failure_rate, 4),
        }

        if failure_rate > self.max_failure_rate:
            return failed(
                self.name,
                f"{failures}/{total} values in '{self.column}' do not match pattern '{self.pattern}'",
                metadata=metadata,
            )

        if self.warning_threshold is not None and failure_rate > self.warning_threshold:
            return warned(
                self.name,
                f"{failures}/{total} values in '{self.column}' approaching pattern failure threshold",
                metadata=metadata,
            )

        return passed(self.name, f"All sampled values in '{self.column}' match pattern", metadata=metadata)
