# VictorOps (Splunk On-Call) Alerter

The `VictorOpsAlerter` sends pipeline health alerts to
[VictorOps / Splunk On-Call](https://help.victorops.com/knowledge-base/rest-endpoint-integration-guide/)
using the generic REST endpoint integration.

## Prerequisites

1. In your VictorOps account, navigate to **Integrations → REST Endpoint**.
2. Enable the integration and copy the **API Key** shown in the URL template.
3. Create or choose a **Routing Key** that maps to the correct escalation policy.

## Configuration

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `api_key` | `str` | ✅ | — | REST endpoint API key from VictorOps |
| `routing_key` | `str` | ✅ | — | Routing key for escalation policy |
| `integration_url` | `str` | ❌ | VictorOps default | Base URL of the REST endpoint |
| `only_on_failure` | `bool` | ❌ | `True` | Skip alert when pipeline is healthy |
| `extra_fields` | `dict` | ❌ | `{}` | Additional key-value pairs merged into the payload |

## Usage

```python
from pipewarden.alerting.victorops_alerter import VictorOpsAlerter
from pipewarden.runner import run_pipeline

alerter = VictorOpsAlerter(
    api_key="<YOUR_API_KEY>",
    routing_key="database-team",
    only_on_failure=True,
    extra_fields={"env": "production", "team": "data-engineering"},
)

result = run_pipeline("orders_pipeline", checks=[...], data=rows)
alerter.send(result.to_alert_context())
```

## Payload Example

```json
{
  "message_type": "CRITICAL",
  "entity_id": "pipewarden/orders_pipeline",
  "entity_display_name": "PipeWarden: orders_pipeline",
  "state_message": "Failed checks: row_count, null_check",
  "monitoring_tool": "pipewarden",
  "pipeline": "orders_pipeline",
  "failed_count": 2,
  "warned_count": 0,
  "passed_count": 5,
  "env": "production",
  "team": "data-engineering"
}
```

When `message_type` is `"CRITICAL"` VictorOps will trigger an incident and
page the on-call responder according to the selected routing key.
Once all checks pass the next run will send `"INFO"` which automatically
resolves the incident if `only_on_failure` is set to `False`.
