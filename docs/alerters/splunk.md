# Splunk HEC Alerter

The `SplunkAlerter` sends pipeline health events to a **Splunk HTTP Event Collector (HEC)** endpoint, making them available for dashboards, saved searches, and Splunk alerts.

## Prerequisites

1. Enable the HTTP Event Collector in your Splunk instance (*Settings → Data Inputs → HTTP Event Collector*).
2. Create a new HEC token and note the token value and the endpoint URL.
3. Install the `requests` library (already a PipeWarden dependency).

## Configuration

| Parameter    | Type  | Required | Default                  | Description                                  |
|--------------|-------|----------|--------------------------|----------------------------------------------|
| `hec_url`    | `str` | ✅       | —                        | Full URL to the HEC `/services/collector/event` endpoint. |
| `hec_token`  | `str` | ✅       | —                        | Splunk HEC authentication token.             |
| `index`      | `str` | ❌       | `"main"`                 | Splunk index to write events into.           |
| `source`     | `str` | ❌       | `"pipewarden"`           | Value for the Splunk `source` field.         |
| `sourcetype` | `str` | ❌       | `"pipewarden:alert"`     | Value for the Splunk `sourcetype` field.     |

## Usage

```python
from pipewarden.alerting.splunk_alerter import SplunkAlerter

alerter = SplunkAlerter(
    hec_url="https://splunk.example.com:8088/services/collector/event",
    hec_token="YOUR-HEC-TOKEN",
    index="pipewarden",
    sourcetype="pipewarden:alert",
)
```

Pass the alerter to your pipeline runner:

```python
from pipewarden.runner import run_pipeline

result = run_pipeline(checks=my_checks, alerters=[alerter])
```

## Event Schema

Each alert produces a single Splunk event with the following fields:

```json
{
  "time": 1718000000.0,
  "index": "pipewarden",
  "source": "pipewarden",
  "sourcetype": "pipewarden:alert",
  "event": {
    "pipeline": "my_pipeline",
    "status": "unhealthy",
    "total_checks": 5,
    "failed_checks": 1,
    "warned_checks": 0,
    "failures": [
      {"check": "row_count", "detail": "Row count 42 is below minimum 100"}
    ],
    "warnings": []
  }
}
```

## Notes

- Only **failed** and **warned** checks are listed in the event body; passing checks are counted but not enumerated to keep event size small.
- The alerter calls `raise_for_status()` on the HEC response, so HTTP errors (e.g. invalid token → 403) will surface as exceptions in your pipeline run.
- For SSL-pinning or proxy scenarios, supply a pre-configured `requests.Session` via the `session` parameter.
