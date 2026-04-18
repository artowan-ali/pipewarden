# pipewarden

Lightweight CLI to validate and monitor ETL pipeline health with configurable alerting.

## Checks

| Check | Description |
|---|---|
| `RowCountCheck` | Validates row count is within expected range |
| `NullCheck` | Detects null values in specified columns |
| `UniquenessCheck` | Ensures column values are unique |
| `FreshnessCheck` | Validates data is not stale |
| `SchemaCheck` | Confirms expected columns are present |
| `ValueRangeCheck` | Ensures numeric values fall within bounds |
| `CustomSQLCheck` | Runs arbitrary SQL and evaluates result |
| `RegexCheck` | Validates values match a regex pattern |
| `CompletenessCheck` | Checks for missing or empty values |
| `DistributionCheck` | Validates column value distribution matches expected proportions |

## Installation

```bash
pip install pipewarden
```

## Usage

```python
from pipewarden.checks import DistributionCheck

check = DistributionCheck(
    column="status",
    expected={"active": 0.6, "inactive": 0.4},
    tolerance=0.05,
)
result = check.run(rows)
print(result.to_dict())
```
