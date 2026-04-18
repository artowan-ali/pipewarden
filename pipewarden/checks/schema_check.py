from typing import Any, Dict, List, Optional
from pipewarden.checks.base import BaseCheck, CheckResult, passed, failed, warned


class SchemaCheck(BaseCheck):
    """
    Validates that rows conform to an expected schema.
    Checks for required columns and optionally validates types.
    """

    name = "schema_check"

    def __init__(
        self,
        required_columns: List[str],
        type_map: Optional[Dict[str, type]] = None,
        allow_extra_columns: bool = True,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.required_columns = required_columns
        self.type_map = type_map or {}
        self.allow_extra_columns = allow_extra_columns

    def run(self, rows: List[Dict[str, Any]]) -> CheckResult:
        if not rows:
            return failed(self.name, "No rows provided for schema validation")

        sample = rows[0]
        actual_columns = set(sample.keys())
        required = set(self.required_columns)

        missing = required - actual_columns
        if missing:
            return failed(
                self.name,
                f"Missing required columns: {sorted(missing)}",
                details={"missing_columns": sorted(missing)},
            )

        extra = actual_columns - required
        if extra and not self.allow_extra_columns:
            return failed(
                self.name,
                f"Unexpected extra columns: {sorted(extra)}",
                details={"extra_columns": sorted(extra)},
            )

        if self.type_map:
            type_errors = []
            for row in rows:
                for col, expected_type in self.type_map.items():
                    val = row.get(col)
                    if val is not None and not isinstance(val, expected_type):
                        type_errors.append(
                            {"column": col, "expected": expected_type.__name__, "got": type(val).__name__}
                        )
            if type_errors:
                return failed(
                    self.name,
                    f"Type mismatches found in {len(type_errors)} instance(s)",
                    details={"type_errors": type_errors[:10]},
                )

        extra_info = f" ({len(extra)} extra column(s) present)" if extra else ""
        return passed(self.name, f"Schema is valid{extra_info}")
