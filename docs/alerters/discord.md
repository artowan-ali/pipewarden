# Discord Alerter

The `DiscordAlerter` sends pipeline health notifications to a Discord channel
using a [Discord Incoming Webhook](https://discord.com/developers/docs/resources/webhook).

## Setup

1. Open your Discord server settings.
2. Go to **Integrations → Webhooks** and click **New Webhook**.
3. Choose the target channel, give the webhook a name, and copy the **Webhook URL**.

## Configuration

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `webhook_url` | `str` | ✅ | — | Full Discord webhook URL |
| `username` | `str` | ❌ | `"PipeWarden"` | Display name shown in Discord |
| `avatar_url` | `str` | ❌ | `None` | URL of avatar image for the bot |
| `only_on_failure` | `bool` | ❌ | `True` | Skip alert when pipeline is healthy |

## Usage

```python
from pipewarden.alerting.discord_alerter import DiscordAlerter
from pipewarden.runner import run_pipeline

alerter = DiscordAlerter(
    webhook_url="https://discord.com/api/webhooks/123456789/abcdefg",
    username="PipeWarden",
    only_on_failure=True,
)

result = run_pipeline(checks=my_checks, rows=my_rows)
alerter.send(result.to_alert_context(pipeline_name="my_pipeline"))
```

## Message Format

When the pipeline is **unhealthy**, the bot posts a message similar to:

```
🔴 PipeWarden Pipeline Alert — UNHEALTHY
Pipeline: `my_pipeline`

Failed checks:
  • `row_count` — expected at least 1000 rows, got 42

Warnings:
  • `freshness_check` — data is 25 hours old
```

When the pipeline is **healthy** and `only_on_failure=False`:

```
✅ PipeWarden Pipeline Alert — HEALTHY
Pipeline: `my_pipeline`
```

## Notes

- Discord webhooks return HTTP `204 No Content` on success; the alerter treats
  both `200` and `204` as successful responses.
- No third-party libraries are required; the alerter uses Python's built-in
  `urllib` module.
