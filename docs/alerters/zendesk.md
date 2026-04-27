# Zendesk Alerter

The `ZendeskAlerter` creates a Zendesk support ticket when one or more pipeline
checks fail. Healthy pipeline runs are silently ignored.

## Configuration

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `subdomain` | `str` | ✅ | — | Your Zendesk subdomain (e.g. `mycompany` for `mycompany.zendesk.com`) |
| `email` | `str` | ✅ | — | Zendesk agent email address used for authentication |
| `api_token` | `str` | ✅ | — | Zendesk API token |
| `ticket_tags` | `list[str]` | ❌ | `["pipewarden"]` | Tags to attach to the created ticket |
| `priority` | `str` | ❌ | `"normal"` | Ticket priority: `low`, `normal`, `high`, or `urgent` |
| `ticket_type` | `str` | ❌ | `"incident"` | Ticket type: `problem`, `incident`, `question`, or `task` |
| `assignee_email` | `str` | ❌ | `None` | Email of the agent to assign the ticket to |
| `group_id` | `int` | ❌ | `None` | Zendesk group ID to assign the ticket to |

## Authentication

Zendesk uses **email + API token** authentication. Generate a token in your
Zendesk Admin Center under **Apps and Integrations → APIs → Zendesk API**.

## Usage

```python
from pipewarden.alerting.zendesk_alerter import ZendeskAlerter

alerter = ZendeskAlerter(
    subdomain="mycompany",
    email="admin@example.com",
    api_token="your-api-token",
    priority="high",
    ticket_tags=["pipewarden", "data-quality"],
    assignee_email="oncall@example.com",
)
```

Then pass the alerter to your pipeline runner:

```python
from pipewarden.runner import run_pipeline

result = run_pipeline(checks, rows, alerters=[alerter])
```

## Ticket Contents

Each ticket includes:

- **Subject** — `[PipeWarden] Pipeline UNHEALTHY: <pipeline_name>`
- **Body** — A summary listing all failed checks, warnings, and the count of
  passing checks, including per-check detail messages.

## Notes

- No ticket is created when all checks pass.
- `raise_for_status()` is called on the Zendesk API response; any HTTP error
  will propagate as an exception so you can handle it in your alerting logic.
