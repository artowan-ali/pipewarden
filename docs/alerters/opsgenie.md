# OpsGenie Alerter

The `OpsGenieAlerter` sends pipeline health alerts to [OpsGenie](https://www.atlassian.com/software/opsgenie) using the OpsGenie Alert API v2.

## Requirements

No extra dependencies are required beyond `requests`, which is already a core dependency of pipewarden.

## Configuration

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `api_key` | `str` | ✅ | — | OpsGenie API integration key |
| `region` | `str` | | `"us"` | API region: `"us"` or `"eu"` |
| `priority` | `str` | | `"P3"` | Alert priority: `P1`–`P5` |
| `tags` | `list[str]` | | `["pipewarden"]` | Tags to attach to the alert |
| `responders` | `list[dict]` | | `[]` | OpsGenie responder objects (team, user, etc.) |
| `session` | `requests.Session` | | `None` | Optional custom HTTP session |

## Usage

```python
from pipewarden.alerting.opsgenie_alerter import OpsGenieAlerter
from pipewarden.runner import run_pipeline

alerter = OpsGenieAlerter(
    api_key="your-opsgenie-api-key",
    region="us",
    priority="P2",
    tags=["pipewarden", "data-team"],
    responders=[
        {"type": "team", "name": "data-engineering"},
    ],
)

result = run_pipeline(checks=[...], alerters=[alerter])
```

## EU Region

If your OpsGenie account is hosted in the EU region, set `region="eu"`:

```python
alerter = OpsGenieAlerter(
    api_key="your-opsgenie-api-key",
    region="eu",
)
```

## Alert Payload

The alerter sends a JSON payload to `https://api.opsgenie.com/v2/alerts` (or the EU endpoint) with:

- **message**: Short summary including pipeline name and health status.
- **description**: Multi-line detail listing failed and warned check names.
- **priority**: Configurable OpsGenie priority level.
- **tags**: Customisable tag list for routing and filtering.
- **details**: Key/value metadata with counts of failed and warned checks.
- **responders**: Optional list of teams or users to notify.

## Priorities

| Value | Meaning |
|-------|---------|
| `P1` | Critical |
| `P2` | High |
| `P3` | Moderate (default) |
| `P4` | Low |
| `P5` | Informational |
