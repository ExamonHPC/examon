# Query with Trino

!!! info "Status: Live (reproduced 2026-05-25)"
    Queries verified against the ExaMon-shipped Trino overlays on both Docker Compose and Kubernetes.

> This page runs your first SQL query against ExaMon through Trino. It is deliberately short: the goal is to prove the federation path from the analyst's side. For the full SQL surface (catalog and schema layout, aggregation pushdown, cross-store joins, per-tool connection guides), see [Users → Analyze](index.md).

!!! note "Prerequisites"
    This page assumes a Trino is already running with the ExaMon catalog wired in. If you don't have one yet, install it from [Administrators → Add-ons → Trino](../../administrators/add-ons/trino.md), then come back here.

## Reach Trino

The examples below assume Trino is reachable on `http://localhost:8080`.

- **Docker Compose**: the [Trino overlay](../../administrators/add-ons/trino.md#on-docker-compose) publishes port 8080 on the host. Nothing to do.
- **Kubernetes**: port-forward the Trino Service to your host:
  ```bash
  kubectl port-forward -n <namespace> svc/<trino-service> 8080:8080 &
  ```
  The Service name is `trino` for the fresh-install path and typically `<release>-trino` for an existing release. Use `kill %1` when done.

The CLI examples use the [Trino Docker image](https://hub.docker.com/r/trinodb/trino); the [native CLI](https://trino.io/docs/current/client/cli.html) works the same way.

## First SQL query

The connector lifts each KairosDB tag to a column and exposes the sample value as `VARCHAR`; cast at query time for numeric metrics. The simulated `random_sensor` metric is published by `random_pub` in every default ExaMon install:

```sql
SELECT timestamp,
       CAST(value AS DOUBLE) AS sensor_value
FROM examon_ts_timestamps.kairosdb."random_sensor"
WHERE timestamp > current_timestamp - INTERVAL '5' MINUTE
ORDER BY timestamp DESC
LIMIT 20;
```

Run it from the Trino CLI:

```bash
docker run --rm -it --network host trinodb/trino:476 \
  trino --server http://localhost:8080 \
        --catalog examon_ts_timestamps \
        --schema kairosdb
```

Paste the query at the `trino>` prompt. The result is the most recent samples from the simulated publisher, the same data the [`Random Sensor` Grafana dashboard](../../get-started/quickstart.md#step-3-open-grafana) plots.

On installs where you've wired ExaMon's KairosDB to a real fleet, substitute a metric you know is being published; `SHOW TABLES FROM examon_ts_timestamps.kairosdb` lists them.

## Same query from Python

```python
import pandas as pd
from trino.dbapi import connect

with connect(
    host="localhost",
    port=8080,
    user="examon",
    catalog="examon_ts_timestamps",
    schema="kairosdb",
) as conn:
    df = pd.read_sql(
        """
        SELECT timestamp,
               CAST(value AS DOUBLE) AS sensor_value
        FROM "random_sensor"
        WHERE timestamp > current_timestamp - INTERVAL '5' MINUTE
        ORDER BY timestamp DESC
        LIMIT 20
        """,
        conn,
    )
print(df.head())
```

The dependencies are `pip install trino pandas`. The same connection works from any Trino client: Superset, DBeaver, Power BI, JDBC.

## Where next

- The full SQL surface, catalog layout, and per-tool connection guides: [Users → Analyze](index.md).
- The bundled notebook walks the pre-Trino `examon-client` interface against the ExaMon REST API: [`Demo_ExamonQL.ipynb`](Demo_ExamonQL.ipynb).

---

## Source

- Trino Python client: [trinodb/trino-python-client](https://github.com/trinodb/trino-python-client)
- Install path for Trino itself: [Administrators → Add-ons → Trino](../../administrators/add-ons/trino.md)
