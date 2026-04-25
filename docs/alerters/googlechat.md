# Google Chat Alerter

The `GoogleChatAlerter` sends pipeline health notifications to a Google Chat space via an incoming webhook.

## Prerequisites

1. Open your Google Chat space.
2. Click the space name → **Apps & integrations** → **Add webhooks**.
3. Name the webhook (e.g. `pipewarden`) and copy the generated URL.

## Configuration

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `webhook_url` | `str` | ✅ | — | Incoming webhook URL from Google Chat. |
| `timeout` | `int` | ❌ | `10` | HTTP request timeout in seconds. |
| `only_on_failure` | `bool` | ❌ | `False` | Skip sending when the pipeline is healthy. |
| `session` | `requests.Session` | ❌ | `None` | Custom session (useful for testing/proxies). |

## Usage

```python
from pipewarden.alerting import GoogleChatAlerter

alerter = GoogleChatAlerter(
    webhook_url="https://chat.googleapis.com/v1/spaces/XXX/messages?key=abc&token=xyz",
    only_on_failure=True,
)
```

### With the runner

```python
from pipewarden.runner import run_pipeline
from pipewarden.alerting import GoogleChatAlerter

alerter = GoogleChatAlerter(
    webhook_url="https://chat.googleapis.com/v1/spaces/XXX/messages?key=abc&token=xyz",
)

result = run_pipeline("my_pipeline", checks=checks, rows=rows, alerters=[alerter])
```

## Message Format

Messages are plain text cards with emoji status indicators:

```
✅ Pipeline: orders — HEALTHY
Ran 3 check(s): 3 passed, 0 warned, 0 failed.
```

or on failure:

```
❌ Pipeline: orders — UNHEALTHY
Ran 3 check(s): 1 passed, 1 warned, 1 failed.
  • FAIL `row_count`: too few rows
  • WARN `freshness`: aging data
```
