from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from pipewarden.checks.base import BaseCheck, CheckResult, passed, failed, warned


@dataclass
class TrendCheck(BaseCheck):
    """Checks that a numeric metric does not deviate too far from a historical baseline.

    Compares the current value (derived from rows) against a provided baseline
    value and raises warnings or failures when the relative change exceeds the
    configured thresholds.

    Attributes:
        name: Identifier for this check instance.
        column: Name of the column to aggregate and compare.
        baseline: The historical reference value to compare against.
        warning_threshold: Maximum relative change before a WARN result
            (e.g. 0.10 = 10%). Must be less than failure_threshold.
        failure_threshold: Maximum relative change before a FAIL result
            (e.g. 0.25 = 25%).
        aggregator: Callable that reduces a list of numeric values to a single
            float. Defaults to the arithmetic mean.
    """

    name: str = "trend_check"
    column: str = ""
    baseline: float = 0.0
    # Maximum relative change before WARN  (e.g. 0.10 = 10 %)
    warning_threshold: float = 0.10
    # Maximum relative change before FAIL  (e.g. 0.25 = 25 %)
    failure_threshold: float = 0.25
    # Optional aggregation function; defaults to average
    aggregator: Callable[[list[Any]], float] = field(
        default=lambda values: sum(values) / len(values) if values else 0.0
    )

    def __post_init__(self) -> None:
        """Validate threshold configuration after initialisation."""
        if self.warning_threshold >= self.failure_threshold:
            raise ValueError(
                f"warning_threshold ({self.warning_threshold}) must be strictly less than "
                f"failure_threshold ({self.failure_threshold})"
            )
        if self.warning_threshold < 0 or self.failure_threshold < 0:
            raise ValueError("Thresholds must be non-negative values")

    def run(self, rows: list[dict]) -> CheckResult:
        if not rows:
            return failed(self.name, "No rows provided to TrendCheck")

        values: list[Any] = []
        for row in rows:
            val = row.get(self.column)
            if val is None:
                continue
            try:
                values.append(float(val))
            except (TypeError, ValueError):
                return failed(
                    self.name,
                    f"Non-numeric value '{val}' found in column '{self.column}'",
                )

        if not values:
            return failed(
                self.name,
                f"Column '{self.column}' contained no usable numeric values",
            )

        current = self.aggregator(values)

        if self.baseline == 0.0:
            relative_change = abs(current)
        else:
            relative_change = abs((current - self.baseline) / self.baseline)

        detail = (
            f"current={current:.4f}, baseline={self.baseline:.4f}, "
            f"relative_change={relative_change:.2%}"
        )

        if relative_change > self.failure_threshold:
            return failed(self.name, f"Trend deviation exceeds failure threshold. {detail}")

        if relative_change > self.warning_threshold:
            return warned(self.name, f"Trend deviation exceeds warning threshold. {detail}")

        return passed(self.name, f"Trend within acceptable range. {detail}")
