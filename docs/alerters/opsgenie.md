# OpsGenie Alerter

The `OpsGenieAlerter` sends pipeline health alerts to [OpsGenie](https://www.atlassian.com/software/opsgenie) via the OpsGenie Alerts API.

## Configuration

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `api_key` | `str` | ✅ | — | OpsGenie API integration key |
| `region` | `str` | ❌ | `"us"` | API region: `"us"` or `"eu"` |
| `priority` | `str` | ❌ | `"P3"` | Alert priority (`P1`–`P5`) |
| `tags` | `list[str]` | ❌ | `[]` | Tags to attach to the alert |
| `responders` | `list[dict]` | ❌ | `[]` | OpsGenie responder objects |
| `alert_on_recovery` | `bool` | ❌ | `True` | Send an alert even when pipeline is healthy |
| `session` | `requests.Session` | ❌ | `None` | Custom HTTP session (useful for testing) |

## Basic Usage

```python
from pipewarden.alerting.opsgenie_alerter import OpsGenieAlerter
from pipewarden.runner import run_pipeline

alerter = OpsGenieAlerter(
    api_key="your-opsgenie-api-key",
    priority="P2",
    tags=["etl", "production"],
)

result = run_pipeline("my_pipeline", checks=[...])
alerter.send(result.to_alert_context())
```

## EU Region

If your OpsGenie account is hosted in the EU, set `region="eu"`:

```python
alerter = OpsGenieAlerter(
    api_key="your-opsgenie-api-key",
    region="eu",
)
```

## Responders

You can route alerts to specific teams or users:

```python
alerter = OpsGenieAlerter(
    api_key="your-opsgenie-api-key",
    responders=[
        {"type": "team", "name": "data-engineering"},
        {"type": "user", "username": "oncall@example.com"},
    ],
)
```

## Suppressing Recovery Alerts

By default, an alert is sent whether the pipeline is healthy or not. To only
alert on failures:

```python
alerter = OpsGenieAlerter(
    api_key="your-opsgenie-api-key",
    alert_on_recovery=False,
)
```

## Notes

- Requires the `requests` library (`pip install requests`).
- The `api_key` should be an **API Integration** key created in OpsGenie, not an account API key.
- Alert priority follows the OpsGenie convention: `P1` (critical) through `P5` (informational).
