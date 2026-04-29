# OpsGenie Alerter

The `OpsGenieAlerter` sends pipeline failure and warning notifications to
[OpsGenie](https://www.atlassian.com/software/opsgenie) via the **Alert API v2**.

## Installation

No extra dependencies are required beyond `requests`, which pipewarden already
includes.

## Configuration

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `api_key` | `str` | ✅ | — | OpsGenie API integration key |
| `pipeline_name` | `str` | ✅ | — | Human-readable pipeline identifier |
| `region` | `str` | ❌ | `"us"` | API region: `"us"` or `"eu"` |
| `priority` | `str` | ❌ | `"P3"` | Alert priority (`P1`–`P5`) |
| `tags` | `list[str]` | ❌ | `[]` | Tags attached to the alert |
| `responders` | `list[dict]` | ❌ | `[]` | OpsGenie responder objects |
| `session` | `requests.Session` | ❌ | `None` | Custom HTTP session (useful for testing) |

## Usage

```python
from pipewarden.alerting.opsgenie_alerter import OpsGenieAlerter
from pipewarden.runner import run_pipeline

alerter = OpsGenieAlerter(
    api_key="your-opsgenie-api-key",
    pipeline_name="orders_etl",
    priority="P2",
    tags=["etl", "production"],
    responders=[{"type": "team", "name": "data-engineering"}],
)

result = run_pipeline(checks=[...], alerters=[alerter])
```

## EU Region

If your OpsGenie account is hosted in the EU data centre, set `region="eu"`:

```python
alerter = OpsGenieAlerter(
    api_key="your-key",
    pipeline_name="orders_etl",
    region="eu",
)
```

## Behaviour

- Alerts are **only sent** when the pipeline has at least one `FAILED` or
  `WARNING` result. Healthy runs are silently skipped.
- The alert message includes the pipeline name and overall status.
- The description lists all failed and warned check names for quick triage.
