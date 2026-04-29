"""Check for statistical outliers in a numeric column using z-score or IQR method."""

from dataclasses import dataclass, field
from typing import Any, Callable, Literal

from pipewarden.checks.base import BaseCheck, CheckResult, failed, passed, warned


@dataclass
class StatisticalOutlierCheck(BaseCheck):
    """Detects outliers in a numeric column using z-score or IQR method."""

    column: str
    method: Literal["zscore", "iqr"] = "zscore"
    threshold: float = 3.0  # z-score threshold or IQR multiplier
    allowed_outlier_rate: float = 0.0
    warning_outlier_rate: float | None = None
    name: str = "statistical_outlier_check"

    def run(self, rows: list[dict[str, Any]]) -> CheckResult:
        if not rows:
            return passed(self.name, "No rows to evaluate.")

        values = []
        for row in rows:
            val = row.get(self.column)
            if val is not None:
                try:
                    values.append(float(val))
                except (TypeError, ValueError):
                    pass

        if not values:
            return failed(self.name, f"Column '{self.column}' has no numeric values.")

        if self.method == "zscore":
            outlier_indices = self._zscore_outliers(values)
        else:
            outlier_indices = self._iqr_outliers(values)

        outlier_count = len(outlier_indices)
        total = len(values)
        rate = outlier_count / total

        details = (
            f"{outlier_count}/{total} outliers detected in '{self.column}' "
            f"using {self.method} (rate={rate:.2%})."
        )

        if rate > self.allowed_outlier_rate:
            return failed(self.name, details)
        if self.warning_outlier_rate is not None and rate > self.warning_outlier_rate:
            return warned(self.name, details)
        return passed(self.name, details)

    def _zscore_outliers(self, values: list[float]) -> list[int]:
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = variance ** 0.5
        if std == 0:
            return []
        return [i for i, v in enumerate(values) if abs((v - mean) / std) > self.threshold]

    def _iqr_outliers(self, values: list[float]) -> list[int]:
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        q1 = self._percentile(sorted_vals, 25)
        q3 = self._percentile(sorted_vals, 75)
        iqr = q3 - q1
        lower = q1 - self.threshold * iqr
        upper = q3 + self.threshold * iqr
        return [i for i, v in enumerate(values) if v < lower or v > upper]

    def _percentile(self, sorted_vals: list[float], pct: float) -> float:
        """Return the value at the given percentile using linear interpolation."""
        n = len(sorted_vals)
        if n == 1:
            return sorted_vals[0]
        idx = (pct / 100) * (n - 1)
        lower_idx = int(idx)
        upper_idx = min(lower_idx + 1, n - 1)
        fraction = idx - lower_idx
        return sorted_vals[lower_idx] + fraction * (sorted_vals[upper_idx] - sorted_vals[lower_idx])
