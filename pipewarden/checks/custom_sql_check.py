from typing import Any, Callable, Optional
from pipewarden.checks.base import BaseCheck, CheckResult, passed, failed, warned


class CustomSQLCheck(BaseCheck):
    """
    Runs a user-supplied SQL query and evaluates the scalar result
    against configurable thresholds.

    The query must return a single scalar value (e.g. SELECT COUNT(*) ...).
    """

    def __init__(
        self,
        name: str,
        query: str,
        execute_fn: Callable[[str], Any],
        expected_value: Optional[Any] = None,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        warning_min: Optional[float] = None,
        warning_max: Optional[float] = None,
    ):
        super().__init__(name)
        self.query = query
        self.execute_fn = execute_fn
        self.expected_value = expected_value
        self.min_value = min_value
        self.max_value = max_value
        self.warning_min = warning_min
        self.warning_max = warning_max

    def run(self) -> CheckResult:
        try:
            result = self.execute_fn(self.query)
        except Exception as exc:  # noqa: BLE001
            return failed(self.name, f"Query execution error: {exc}", {"query": self.query})

        details = {"query": self.query, "result": result}

        if self.expected_value is not None:
            if result == self.expected_value:
                return passed(self.name, f"Result matched expected value {self.expected_value}", details)
            return failed(
                self.name,
                f"Expected {self.expected_value}, got {result}",
                details,
            )

        try:
            numeric = float(result)
        except (TypeError, ValueError):
            return failed(self.name, f"Result {result!r} is not numeric", details)

        if self.min_value is not None and numeric < self.min_value:
            return failed(self.name, f"Result {numeric} is below minimum {self.min_value}", details)
        if self.max_value is not None and numeric > self.max_value:
            return failed(self.name, f"Result {numeric} is above maximum {self.max_value}", details)

        if self.warning_min is not None and numeric < self.warning_min:
            return warned(self.name, f"Result {numeric} is below warning threshold {self.warning_min}", details)
        if self.warning_max is not None and numeric > self.warning_max:
            return warned(self.name, f"Result {numeric} is above warning threshold {self.warning_max}", details)

        return passed(self.name, f"Result {numeric} is within acceptable range", details)
