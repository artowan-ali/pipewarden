# pipewarden

Lightweight CLI to validate and monitor ETL pipeline health with configurable alerting.

---

## Installation

```bash
pip install pipewarden
```

Or install from source:

```bash
git clone https://github.com/youruser/pipewarden.git && cd pipewarden && pip install .
```

---

## Usage

Define your pipeline checks in a YAML config file:

```yaml
# pipewarden.yml
pipelines:
  - name: daily_sales_etl
    checks:
      - type: row_count
        min: 1000
      - type: null_check
        columns: [order_id, customer_id]
    alerts:
      email: ops-team@example.com
```

Then run the warden:

```bash
pipewarden run --config pipewarden.yml
```

Check a specific pipeline:

```bash
pipewarden check --pipeline daily_sales_etl --verbose
```

View pipeline status history:

```bash
pipewarden status --last 7d
```

---

## Commands

| Command | Description |
|---|---|
| `run` | Execute all configured pipeline checks |
| `check` | Validate a single pipeline |
| `status` | View historical health reports |
| `init` | Generate a starter config file |

---

## License

MIT © 2024 pipewarden contributors