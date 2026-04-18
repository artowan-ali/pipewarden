from datetime import datetime, timezone
from typing import Optional
from pipewarden.checks.base import BaseCheck, CheckResult, passed, failed, warned


class FreshnessCheck(BaseCheck):
    """Check that data is fresh based on a timestamp column."""

    def __init__(
        self,
        name: str,
        column: str,
        max_age_seconds: float,
        warning_age_seconds: Optional[float] = None,
    ):
        super().__init__(name)
        self.column = column
        self.max_age_seconds = max_age_seconds
        self.warning_age_seconds = warning_age_seconds

    def run(self, rows: list[dict]) -> CheckResult:
        if not rows:
            return failed(self.name, "No rows provided to check freshness")

        timestamps = []
        for row in rows:
            val = row.get(self.column)
            if val is None:
                return failed(self.name, f"Column '{self.column}' contains null timestamps")
            if isinstance(val, (int, float)):
                val = datetime.fromtimestamp(val, tz=timezone.utc)
            if not isinstance(val, datetime):
                return failed(self.name, f"Column '{self.column}' has unsupported type: {type(val)}")
            if val.tzinfo is None:
                val = val.replace(tzinfo=timezone.utc)
            timestamps.append(val)

        latest = max(timestamps)
        now = datetime.now(tz=timezone.utc)
        age_seconds = (now - latest).total_seconds()

        return self._evaluate(age_seconds, latest)

    def _evaluate(self, age_seconds: float, latest: datetime) -> CheckResult:
        details = {
            "latest_timestamp": latest.isoformat(),
            "age_seconds": round(age_seconds, 2),
            "max_age_seconds": self.max_age_seconds,
        }
        if age_seconds > self.max_age_seconds:
            return failed(
                self.name,
                f"Data is stale: {age_seconds:.1f}s old (max {self.max_age_seconds}s)",
                details,
            )
        if self.warning_age_seconds is not None and age_seconds > self.warning_age_seconds:
            return warned(
                self.name,
                f"Data aging: {age_seconds:.1f}s old (warning at {self.warning_age_seconds}s)",
                details,
            )
        return passed(self.name, f"Data is fresh: {age_seconds:.1f}s old", details)
