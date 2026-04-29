# OpsGenie Alerter

Send pipeline health alerts to [OpsGenie](https://www.atlassian.com/software/opsgenie) using the OpsGenie Alert API.

## Requirements

- An OpsGenie account with an API integration key.
- The `requests` package (included in pipewarden's default dependencies).

## Configuration

| Parameter     | Type            | Required | Default | Description                                      |
|---------------|-----------------|----------|---------|--------------------------------------------------|
| `api_key`     | `str`           | Yes      | —       | OpsGenie API integration key.                    |
| `region`      | `str`           | No       | `"us"`  | OpsGenie region: `"us"` or `"eu"`.               |
| `priority`    | `str`           | No       | `"P3"`  | Alert priority (`P1`–`P5`).                      |
| `tags`        | `list[str]`     | No       | `[]`    | Tags to attach to the alert.                     |
| `responders`  | `list[dict]`    | No       | `[]`    | OpsGenie responder objects (teams, users, etc.). |
| `session`     | `requests.Session` | No    | `None`  | Custom session (useful for testing/proxies).     |

## Usage

```python
from pipewarden.alerting.opsgenie_alerter import OpsGenieAlerter
from pipewarden.runner import run_pipeline

alerter = OpsGenieAlerter(
    api_key="your-opsgenie-api-key",
    region="us",
    priority="P2",
    tags=["etl", "production"],
    responders=[{"type": "team", "name": "data-engineering"}],
)

result = run_pipeline("my_pipeline", checks=[...])
alerter.send_if_needed(result)
```

## Alert Payload

The alerter sends a JSON payload to `https://api.opsgenie.com/v2/alerts` (or the EU endpoint) with:

- **message** — Short summary: `[pipewarden] <pipeline> is UNHEALTHY`
- **description** — Lists failed and warned check names.
- **priority** — Configurable; defaults to `P3`.
- **details** — Structured key/value map with pipeline name, status, and check names.
- **tags** / **responders** — Optional, appended when configured.

## EU Region

For EU-hosted OpsGenie accounts, set `region="eu"` to route requests to `https://api.eu.opsgenie.com/v2/alerts`.

## Notes

- The alerter only fires when the pipeline is **unhealthy** (has at least one `FAILED` result) unless you call `send()` directly.
- HTTP errors from the OpsGenie API will raise an exception — consider wrapping in a try/except for non-critical alerting paths.
