# ServiceNow Alerter

The `ServiceNowAlerter` creates an **Incident** in ServiceNow via the
[Table API](https://developer.servicenow.com/dev.do#!/reference/api/tokyo/rest/c_TableAPI)
whenever a pipeline run is unhealthy.

## Prerequisites

- A ServiceNow instance (developer or production).
- A user account with the `itil` role (or equivalent) so it can create incidents.

## Configuration

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `instance` | `str` | ✅ | — | Subdomain of your ServiceNow instance, e.g. `dev12345`. |
| `username` | `str` | ✅ | — | Basic-auth username. |
| `password` | `str` | ✅ | — | Basic-auth password. |
| `assignment_group` | `str` | ❌ | `None` | Name of the assignment group to set on the incident. |
| `urgency` | `int` | ❌ | `2` | Incident urgency: `1` High, `2` Medium, `3` Low. |
| `impact` | `int` | ❌ | `2` | Incident impact: `1` High, `2` Medium, `3` Low. |
| `only_on_failure` | `bool` | ❌ | `True` | Skip sending when the pipeline is healthy. |

## Usage

```python
from pipewarden.alerting.servicenow_alerter import ServiceNowAlerter

alerter = ServiceNowAlerter(
    instance="dev12345",
    username="admin",
    password="s3cr3t",
    assignment_group="data-engineering",
    urgency=1,
    impact=1,
)
```

Pass the alerter to `run_pipeline`:

```python
from pipewarden.runner import run_pipeline

result = run_pipeline("orders_etl", checks, alerters=[alerter])
```

## Incident fields

| ServiceNow field | Value |
|---|---|
| `short_description` | `[PipeWarden] <pipeline> — FAILED` |
| `description` | Pipeline name, failed checks, warning checks. |
| `urgency` | Configured value (string). |
| `impact` | Configured value (string). |
| `assignment_group` | Configured value (omitted if not set). |

## Security note

Avoid hard-coding credentials.  Use environment variables or a secrets manager
and pass them at runtime:

```python
import os

alerter = ServiceNowAlerter(
    instance=os.environ["SNOW_INSTANCE"],
    username=os.environ["SNOW_USER"],
    password=os.environ["SNOW_PASS"],
)
```
