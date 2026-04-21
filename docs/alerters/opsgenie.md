# OpsGenie Alerter

The `OpsGenieAlerter` sends alerts to [OpsGenie](https://www.atlassian.com/software/opsgenie) when one or more pipeline checks fail or warn.

## Configuration

| Parameter      | Type        | Required | Default                                  | Description                                      |
|----------------|-------------|----------|------------------------------------------|--------------------------------------------------|
| `api_key`      | `str`       | ✅ Yes   | —                                        | OpsGenie API integration key.                    |
| `priority`     | `str`       | No       | `"P3"`                                   | Alert priority (`P1`–`P5`).                      |
| `tags`         | `list[str]` | No       | `[]`                                     | Tags attached to the OpsGenie alert.             |
| `alias_prefix` | `str`       | No       | `"pipewarden"`                           | Prefix for the deduplication alias.              |
| `api_url`      | `str`       | No       | `"https://api.opsgenie.com/v2/alerts"`  | Override for self-hosted / EU instances.         |

## Usage

```python
from pipewarden.alerting.opsgenie_alerter import OpsGenieAlerter

alerter = OpsGenieAlerter(
    api_key="your-opsgenie-api-key",
    priority="P2",
    tags=["etl", "production"],
)
```

Pass the alerter to the pipeline runner:

```python
from pipewarden.runner import run_pipeline

result = run_pipeline(
    pipeline_name="orders_pipeline",
    checks=[...],
    alerters=[alerter],
)
```

## Deduplication

Each alert is assigned an **alias** derived from the `alias_prefix` and the pipeline name (e.g. `pipewarden-orders_pipeline`). OpsGenie uses this alias to deduplicate repeated alerts for the same pipeline.

## Priority levels

| Level | Meaning        |
|-------|----------------|
| P1    | Critical        |
| P2    | High            |
| P3    | Moderate (default) |
| P4    | Low             |
| P5    | Informational   |

## EU / Self-hosted instances

If you use the OpsGenie EU region or a self-hosted instance, override `api_url`:

```python
alerter = OpsGenieAlerter(
    api_key="your-key",
    api_url="https://api.eu.opsgenie.com/v2/alerts",
)
```
