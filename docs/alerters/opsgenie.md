# OpsGenie Alerter

The `OpsGenieAlerter` sends pipeline health alerts to [OpsGenie](https://www.atlassian.com/software/opsgenie) via the OpsGenie Alerts REST API (v2).

## Requirements

- An OpsGenie account with an **API integration** configured.
- The integration's **API key**.

## Configuration

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `api_key` | `str` | ✅ | — | OpsGenie API integration key |
| `region` | `str` | ❌ | `"us"` | OpsGenie region: `"us"` or `"eu"` |
| `priority` | `str` | ❌ | `"P3"` | Alert priority (`P1`–`P5`) |
| `tags` | `list[str]` | ❌ | `[]` | Tags to attach to the alert |
| `responders` | `list[dict]` | ❌ | `[]` | OpsGenie responder objects (teams, users, etc.) |

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
alerter.send_if_needed(result)
```

## EU Region

If your OpsGenie account is on the EU instance, set `region="eu"`:

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

## Alert Content

Each alert includes:

- **Message**: Pipeline name and health status (`HEALTHY` / `UNHEALTHY`).
- **Description**: Lists failed and warned check names.
- **Details**: Structured metadata — pipeline name, total checks, failed count, warned count.
- **Priority**: Configurable (`P1`–`P5`).
- **Tags**: Any custom tags you specify.

## Notes

- Alerts are only sent when the pipeline is unhealthy (contains failed or warned checks). Use `send_if_needed` for conditional sending.
- HTTP errors from the OpsGenie API (e.g. invalid API key) will raise an exception.
