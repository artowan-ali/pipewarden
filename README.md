# pipewarden

Lightweight CLI to validate and monitor ETL pipeline health with configurable alerting.

## Checks

| Check | Description |
|---|---|
| `RowCountCheck` | Validates row count is within expected range |
| `NullCheck` | Detects null values in specified columns |
| `UniquenessCheck` | Ensures column values meet uniqueness requirements |
| `FreshnessCheck` | Validates data is not stale based on a timestamp column |
| `SchemaCheck` | Confirms expected columns are present |
| `ValueRangeCheck` | Ensures numeric values fall within defined bounds |
| `CustomSQLCheck` | Runs a custom SQL query and evaluates the result |
| `RegexCheck` | Validates column values match a regular expression |
| `CompletenessCheck` | Ensures required columns have no missing or empty values |

## Usage

```python
from pipewarden.checks import CompletenessCheck

check = CompletenessCheck(
    name="user_completeness",
    columns=["name", "email", "phone"],
    allowed_missing_rate=0.05,
    warning_missing_rate=0.01,
)

result = check.run(rows)
print(result.status, result.message)
```

## Installation

```bash
pip install pipewarden
```
