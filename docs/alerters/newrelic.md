# New Relic Alerter

The `NewRelicAlerter` sends a custom NRDB event to **New Relic Insights** every time a PipeWarden pipeline run completes.  You can then build dashboards and alert policies directly inside New Relic.

## Prerequisites

1. A New Relic account with an **Insights Insert Key** (or a License Key that has insert permissions).
2. Your numeric **Account ID** (visible in the New Relic UI under *Account settings*).

## Configuration

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `api_key` | `str` | ✅ | — | New Relic Insights insert key. |
| `account_id` | `str` | ✅ | — | New Relic account ID. |
| `event_type` | `str` | | `PipeWardenRun` | Custom event type name stored in NRDB. |
| `eu_region` | `bool` | | `False` | Set to `True` to use the EU data centre endpoint. |
| `session` | `requests.Session` | | `None` | Optional session (useful for testing). |

## Example

```python
from pipewarden.alerting.newrelic_alerter import NewRelicAlerter

alerter = NewRelicAlerter(
    api_key="NRII-xxxxxxxxxxxxxxxxxxxx",
    account_id="1234567",
    event_type="PipeWardenRun",
)
```

Pass the alerter to your pipeline runner:

```python
from pipewarden.runner import run_pipeline

result = run_pipeline(checks=my_checks, alerters=[alerter])
```

## Event Schema

Each run posts a single JSON event with the following fields:

```json
{
  "eventType": "PipeWardenRun",
  "pipeline": "orders",
  "healthy": false,
  "total_checks": 5,
  "failed_checks": 1,
  "warned_checks": 2,
  "failed_check_names": "row_count",
  "warned_check_names": "freshness, null_check"
}
```

## Querying in New Relic

```sql
SELECT latest(healthy), latest(failed_checks)
FROM PipeWardenRun
WHERE pipeline = 'orders'
SINCE 1 day ago
```

## EU Region

If your New Relic account is hosted in the EU data centre, set `eu_region=True`:

```python
alerter = NewRelicAlerter(
    api_key="NRII-xxxx",
    account_id="1234567",
    eu_region=True,
)
```
