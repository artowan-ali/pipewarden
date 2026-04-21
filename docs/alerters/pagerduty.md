# PagerDuty Alerter

The `PagerDutyAlerter` sends an event to the
[PagerDuty Events API v2](https://developer.pagerduty.com/docs/ZG9jOjExMDI5NTgw-send-an-alert-event)
whenever a pipeline run is **unhealthy** (one or more checks fail).

## Requirements

- A PagerDuty **Integration Key** (also called a *routing key*) from an
  **Events API v2** integration on your service.

## Configuration

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `integration_key` | `str` | ✅ | — | PagerDuty routing key |
| `severity` | `str` | ❌ | `"error"` | One of `critical`, `error`, `warning`, `info` |
| `source` | `str` | ❌ | `"pipewarden"` | Logical name of the event source |
| `component` | `str` | ❌ | `None` | Pipeline or component name shown in PD |

## Usage

```python
from pipewarden.alerting import PagerDutyAlerter
from pipewarden.runner import run_pipeline

alerter = PagerDutyAlerter(
    integration_key="your-integration-key",
    severity="critical",
    component="orders-etl",
)

result = run_pipeline(checks=[...], alerters=[alerter])
```

## Behaviour

- If the pipeline is **healthy**, no request is made.
- On failure, a `trigger` event is sent with a summary listing the failed
  check names and `custom_details` containing counts for total, failed,
  warned, and passed checks.
- The alerter raises `urllib.error.HTTPError` on non-2xx responses so
  failures surface immediately in your pipeline logs.
