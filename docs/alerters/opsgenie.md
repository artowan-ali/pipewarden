# OpsGenie Alerter

The `OpsGenieAlerter` sends pipeline health alerts to [OpsGenie](https://www.atlassian.com/software/opsgenie) using the OpsGenie Alert API v2.

## Requirements

No extra dependencies are required beyond `requests`, which is already a core dependency of pipewarden.

## Configuration

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `api_key` | `str` | ✅ | — | OpsGenie API integration key |
| `region` | `str` | ❌ | `"us"` | API region: `"us"` or `"eu"` |
| `priority` | `str` | ❌ | `"P3"` | Alert priority (`P1`–`P5`) |
| `tags` | `list[str]` | ❌ | `[]` | Tags to attach to the alert |
| `responders` | `list[dict]` | ❌ | `[]` | OpsGenie responder objects |
| `alert_on_recovery` | `bool` | ❌ | `False` | Send alert even when pipeline is healthy |

## Usage

```python
from pipewarden.alerting.opsgenie_alerter import OpsGenieAlerter
from pipewarden.runner import run_pipeline

alerter = OpsGenieAlerter(
    api_key="your-opsgenie-api-key",
    priority="P2",
    tags=["etl", "production"],
    responders=[{"type": "team", "name": "data-engineering"}],
)

result = run_pipeline("my_pipeline", checks=[...])
alerter.send(result.to_alert_context())
```

## EU Region

If your OpsGenie account is on the EU instance, set `region="eu"`:

```python
alerter = OpsGenieAlerter(
    api_key="your-key",
    region="eu",
)
```

## Alert Payload

The alerter sends a JSON payload with:

- **message** — short summary including pipeline name and status
- **description** — multi-line detail listing failed and warned checks
- **priority** — configurable P1–P5
- **tags** — user-defined tags
- **details** — structured metadata (pipeline name, counts of failed/warned checks)
- **responders** — optional OpsGenie team/user responders

## Notes

- Alerts are only sent on failure by default. Set `alert_on_recovery=True` to also notify when the pipeline returns to a healthy state.
- `raise_for_status()` is called on the response, so HTTP errors will propagate as exceptions.
