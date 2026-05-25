# Local Trino Quickstart

!!! info "Status: Live (reproduced 2026-05-25)"
    Verified against examon-core v0.5.0, the upstream Trino chart 1.42.2 (Trino image 476), and [`trino-kairosdb-connector`](https://github.com/ExamonHPC/trino-kairosdb-connector) v3.0.0-rc1.

> This page adds a Trino SQL surface to the local ExaMon stack you brought up with the [Get Started Quickstart](../../get-started/quickstart.md). At the end you can run cross-source SQL against the simulated `random_sensor` metric flowing through the local pipeline, from the `trino` CLI and from Python.
>
> Trino is kept outside the ExaMon umbrella chart on purpose: its lifecycle (upgrades, scaling, JVM tuning, authentication) belongs with the operator, not with ExaMon. ExaMon ships a tested values overlay for the upstream Trino Helm chart instead.

## Before you start

- The [Quickstart](../../get-started/quickstart.md) is done: K3d cluster `examon-local` is running, the `examon` namespace is healthy, and `random_pub` is publishing into KairosDB.
- About 2 GB of free RAM in addition to what the ExaMon stack already uses (Trino coordinator + 1 worker, JVM heap capped at 1 GB each by the overlay).
- `helm` v3.x and `kubectl` already configured against `examon-local`.
- A `trino` client, either the [Docker image](https://hub.docker.com/r/trinodb/trino) or the [native CLI](https://trino.io/docs/current/client/cli.html). The examples below use the Docker image.

## Step 1. Add the Trino Helm repository

```bash
helm repo add trino https://trinodb.github.io/charts
helm repo update
```

## Step 2. Install Trino with the ExaMon overlay

From the repository root (where [`deploy/trino/values-examon-local.yaml`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/deploy/trino/values-examon-local.yaml) lives):

```bash
helm install trino trino/trino \
  --version 1.42.2 \
  -f deploy/trino/values-examon-local.yaml \
  -n examon \
  --wait --timeout 5m
```

The overlay does four things:

- Pins the Trino image to `476`, the version the connector is tested against.
- Caps coordinator and worker JVM heap at `1G` and per-node query memory at `512MB`, so the install fits the 8 GB laptop target the ExaMon Quickstart assumes.
- Adds an init-container on both the coordinator and the worker that fetches `kairosdb-connector-3.0.0-rc1.jar` from the connector's GitHub release and drops it into the Trino plugin directory.
- Wires a single catalog, `examon_ts_timestamps`, pointing at the same-namespace `examon-kairosdb` service.

The Cassandra catalog (`examon_meta`) is intentionally not wired in the local overlay: the local stack carries no Slurm job metadata, so the catalog would be empty. Staging and production overlays add it.

## Step 3. Verify the install

```bash
kubectl get pods -n examon -l 'app.kubernetes.io/name=trino'
```

You should see one coordinator pod and one worker pod, both `Running` with the `install-kairosdb-connector` init-container `Completed`.

Confirm the catalog is live. The examples below port-forward Trino to host port `18080` rather than `8080`; this is deliberate. Another Trino on the same host (a Docker Compose dev stack, a different K3d cluster, anything else listening on `0.0.0.0:8080`) silently steals the connection: `kubectl port-forward` exits without binding, and the `trino` client happily talks to the wrong server. Picking a free port avoids the collision; any free port works.

```bash
kubectl port-forward -n examon svc/trino 18080:8080 &
docker run --rm -it --network host trinodb/trino:476 \
  trino --server http://localhost:18080 \
  --execute 'SHOW CATALOGS'
```

The output lists `examon_ts_timestamps` alongside the upstream defaults `system`, `tpch`, and `tpcds`. If you see other catalogs (e.g. `examon_meta`, `examon_ts`), the port-forward did not bind and you are talking to a different Trino: confirm with `curl http://localhost:18080/v1/info` (the K3d coordinator reports `"uptime"` in minutes for a fresh install).

## Step 4. Run your first query

The local pipeline's canonical metric is `random_sensor`, published by `random_pub` and ingested through `mqtt2kairosdb`. The connector lifts each KairosDB tag to a column and exposes the sample value as `VARCHAR`; cast at query time for numeric metrics.

```sql
SELECT timestamp,
       CAST(value AS DOUBLE) AS sensor_value
FROM examon_ts_timestamps.kairosdb."random_sensor"
WHERE timestamp > current_timestamp - INTERVAL '5' MINUTE
ORDER BY timestamp DESC
LIMIT 20;
```

Run it through the same CLI (still on the `18080` port-forward from Step 3):

```bash
docker run --rm -it --network host trinodb/trino:476 \
  trino --server http://localhost:18080 \
        --catalog examon_ts_timestamps \
        --schema kairosdb
```

Paste the query at the `trino>` prompt. The result is the most recent samples from the simulated publisher, the same data the [`Random Sensor` Grafana dashboard](../../get-started/quickstart.md#step-3-open-grafana) plots.

## Step 5. Run the same query from Python

```python
import pandas as pd
from trino.dbapi import connect

with connect(
    host="localhost",
    port=18080,   # match the kubectl port-forward host port from Step 3
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

The dependencies are `pip install trino pandas`. The same connection works against any Trino client: Superset, DBeaver, Power BI, JDBC.

## Step 6. Tear down

```bash
helm uninstall trino -n examon
kill %1   # the kubectl port-forward backgrounded in Step 3
```

The ExaMon stack itself is untouched: only Trino is removed.

## What this does and does not do

- **Does**: give a laptop-sized Trino install wired to your local ExaMon and a first SQL query that proves the federation path works end to end.
- **Does not**: provision the Cassandra catalog (no Slurm metadata locally), enable Trino authentication, persist Trino state across `helm uninstall`, or tune the install for production load. Those are the job of the staging and production overlays, planned for v0.5.1.

For the full SQL surface (catalog and schema layout, aggregation pushdown, cross-store joins, per-tool connection guides), see [Users → Analyze](index.md).

---

## Source

- Values overlay: [`deploy/trino/values-examon-local.yaml`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/deploy/trino/values-examon-local.yaml)
- Overlay README: [`deploy/trino/README.md`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/deploy/trino/README.md)
- Upstream Trino Helm chart: [trinodb/charts (trino 1.42.2)](https://github.com/trinodb/charts/tree/main/charts/trino)
- Connector: [ExamonHPC/trino-kairosdb-connector](https://github.com/ExamonHPC/trino-kairosdb-connector) (Apache-2.0, v3.0.0-rc1)
- Trino Python client: [trinodb/trino-python-client](https://github.com/trinodb/trino-python-client)
