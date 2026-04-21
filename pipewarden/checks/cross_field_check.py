from dataclasses import dataclass, field
from typing import Callable, Iterable, Optional
from pipewarden.checks.base import BaseCheck, CheckResult, passed, failed, warned


@dataclass
class CrossFieldCheck(BaseCheck):
    """Validates a user-supplied predicate across two or more fields in each row."""

    predicate: Callable[[dict], bool]
    allowed_failure_rate: float = 0.0
    warning_failure_rate: Optional[float] = None
    name: str = "CrossFieldCheck"

    def run(self, rows: Iterable[dict]) -> CheckResult:
        rows = list(rows)
        if not rows:
            return passed(self.name, "No rows to check.")

        total = len(rows)
        failures = [row for row in rows if not self.predicate(row)]
        failure_count = len(failures)
        failure_rate = failure_count / total

        detail = (
            f"{failure_count}/{total} rows failed the cross-field predicate "
            f"(rate={failure_rate:.2%})."
        )

        if failure_rate > self.allowed_failure_rate:
            return failed(self.name, detail)

        if (
            self.warning_failure_rate is not None
            and failure_rate > self.warning_failure_rate
        ):
            return warned(self.name, detail)

        return passed(
            self.name,
            f"All {total} rows satisfy the cross-field predicate.",
        )
