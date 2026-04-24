# Microsoft Teams Webhook Alerter

Send pipeline health alerts to a Microsoft Teams channel using an **Incoming Webhook** connector.

## Setup

1. In Teams, navigate to the channel where you want alerts.
2. Click **...** → **Connectors** → **Incoming Webhook** → **Configure**.
3. Give the webhook a name (e.g. *PipeWarden*) and optionally upload an icon.
4. Copy the generated webhook URL.

## Usage

```python
from pipewarden.alerting import MSTeamsWebhookAlerter

alerter = MSTeamsWebhookAlerter(
    webhook_url="https://outlook.office.com/webhook/<your-webhook-id>",
    pipeline_name="Sales ETL",
    alert_on_failure=True,
    alert_on_warning=False,
)
```

## Configuration

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `webhook_url` | `str` | ✅ | — | Teams Incoming Webhook URL |
| `pipeline_name` | `str` | ❌ | `"ETL Pipeline"` | Display name shown in the card |
| `alert_on_failure` | `bool` | ❌ | `True` | Send alert when checks fail |
| `alert_on_warning` | `bool` | ❌ | `False` | Send alert on warnings |
| `mention_on_failure` | `bool` | ❌ | `False` | Reserved for future @mention support |

## Message Format

Alerts are delivered as **MessageCard** payloads (legacy connector format supported by all Teams tenants).

Each card includes:
- Pipeline name and overall status
- Total / failed / warning check counts
- Names of any failed checks

## Example Card

```
[Test Pipeline] pipeline report
❌ Unhealthy

Pipeline    : Test Pipeline
Status      : ❌ Unhealthy
Total Checks: 5
Failed      : 2
Warnings    : 1
Failed Checks: row_count, null_check
```

## Notes

- The alerter uses Python's built-in `urllib` — no extra dependencies required.
- Timeout is fixed at **10 seconds** per request.
- HTTP status codes outside `200–202` raise a `RuntimeError`.
