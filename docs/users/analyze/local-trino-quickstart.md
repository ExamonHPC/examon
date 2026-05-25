# Trino Quickstart

!!! info "Status: Live (reproduced 2026-05-25)"
    Verified against examon-core v0.5.0 and [`trino-kairosdb-connector`](https://github.com/ExamonHPC/trino-kairosdb-connector) v3.0.0-rc1 on Trino 476. The Kubernetes path was tested end to end on K3d; the Docker Compose path uses the same connector and image pin.

> This page wires a Trino SQL surface to an ExaMon installation. Trino is kept outside the ExaMon core on purpose: its lifecycle (upgrades, scaling, JVM tuning, authentication) belongs with the operator, not with ExaMon. ExaMon ships only its contract with Trino, not Trino itself.
>
> Pick the section that matches your deployment target. Both land on the same first SQL query.

## Before you start

- A `trino` client, either the [Docker image](https://hub.docker.com/r/trinodb/trino) or the [native CLI](https://trino.io/docs/current/client/cli.html). The examples below use the Docker image.
- The core ExaMon stack is already running (the [Get Started Quickstart](../../get-started/quickstart.md) is done) and `random_pub` is publishing into KairosDB.
- About 2 GB of free RAM on top of the existing ExaMon stack.

## On Docker Compose

The Compose stack ships an optional Trino overlay, [`compose.trino.yml`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/compose.trino.yml). It adds a single-node Trino plus a one-shot init service that fetches the KairosDB connector into a named volume, and mounts the ExaMon-owned catalog from [`deploy/docker/trino/catalog/`](https://github.com/ExamonHPC/examon/tree/release/v0.5.0/deploy/docker/trino/catalog).

### Step 1. Apply the overlay

From the repository root, with the core stack already up:

```bash
docker compose -f docker-compose.yml -f compose.trino.yml up -d
```

The init service downloads the connector once and caches it in the `trino_kairosdb_plugin` volume. Trino is reachable on `http://localhost:8080`.

### Step 2. Verify the install

```bash
docker compose -f docker-compose.yml -f compose.trino.yml ps trino
docker run --rm -it --network host trinodb/trino:476 \
  trino --server http://localhost:8080 \
        --execute 'SHOW CATALOGS'
```

`examon_ts_timestamps` should appear alongside the Trino defaults `system`, `tpch`, and `tpcds`.

### Step 3. Open a Trino session

```bash
docker run --rm -it --network host trinodb/trino:476 \
  trino --server http://localhost:8080 \
        --catalog examon_ts_timestamps \
        --schema kairosdb
```

At the `trino>` prompt, paste the query from [First SQL query](#first-sql-query). The result is the most recent samples from the simulated `random_sensor` publisher.

### Step 4. Roll back

To remove only the Trino overlay and keep the core stack:

```bash
docker compose -f docker-compose.yml -f compose.trino.yml stop trino trino-connector-init
docker compose -f docker-compose.yml -f compose.trino.yml rm -f trino trino-connector-init
```

## On Kubernetes

Trino is installed as a separate Helm release alongside the ExaMon release. ExaMon ships only the wiring overlay, [`deploy/trino/values-examon.yaml`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/deploy/trino/values-examon.yaml): the connector init-container, the plugin volume + mount, and the `examon_ts_timestamps` catalog. Sizing, image tag, auth, and everything else stay with your own values file.

This section forks on whether you already operate a `trino/trino` Helm release. The wiring overlay is the same in both cases; only the helm verb (`install` vs `upgrade`) and the sizing file you pair with it change.

### Step 1. Add the Trino Helm repository

```bash
helm repo add trino https://trinodb.github.io/charts
helm repo update
```

### Step 2. Pair a sizing file with the ExaMon wiring overlay

=== "Fresh install (laptop, no Trino yet)"

    The sizing snippet below targets the 8 GB host documented in the [Get Started Quickstart](../../get-started/quickstart.md). It is an **example**, not chart-side material: operators with different targets supply their own.

    ```bash
    cat > /tmp/trino-laptop.yaml <<'EOF'
    image:
      tag: "476"

    server:
      workers: 1

    coordinator:
      jvm: { maxHeapSize: "1G" }
      config:
        query: { maxMemoryPerNode: "512MB" }

    worker:
      jvm: { maxHeapSize: "1G" }
      config:
        query: { maxMemoryPerNode: "512MB" }
    EOF
    ```

    Then install Trino from the repository root, pairing the sizing snippet with the ExaMon wiring overlay:

    ```bash
    helm install trino trino/trino --version 1.42.2 \
      -f /tmp/trino-laptop.yaml \
      -f deploy/trino/values-examon.yaml \
      -n examon --wait --timeout 5m
    ```

    The Cassandra catalog (`examon_meta`) is intentionally not wired by the overlay: the local stack carries no Slurm job metadata, so the catalog would be empty. Staging and production overlays will add it.

=== "Add ExaMon catalogs to an existing trino/trino Helm release"

    The wiring overlay leaves your image tag, JVM heap, worker count, auth, and networking untouched: those stay in your own values file. Pass your existing values as the first `-f`, or `helm upgrade` will reset unset fields back to chart defaults. If you don't have a copy on disk, export the current ones first:

    ```bash
    helm get values <your-release> -n <your-namespace> -o yaml \
      > /tmp/current-values.yaml

    helm upgrade <your-release> trino/trino \
      -f /tmp/current-values.yaml \
      -f deploy/trino/values-examon.yaml \
      -n <your-namespace> \
      --wait --timeout 5m
    ```

    !!! warning "Helm list-merge gotcha"
        Helm merges YAML maps deeply but lists by replacement. The wiring overlay defines `initContainers.coordinator`, `initContainers.worker`, `coordinator.additionalVolumes`, `coordinator.additionalVolumeMounts`, `worker.additionalVolumes`, and `worker.additionalVolumeMounts` as lists. If your own values already define any of these (for example, a sidecar volume or a different init-container), the overlay will **replace** your entries, not append. Detect this with `helm get values <release> -a` before upgrading; if any of those keys are non-empty, paste the four blocks from `values-examon.yaml` into your own values file (concatenating the lists) and skip the second `-f`.

    !!! note "Trino version compatibility"
        Connector 3.0.0-rc1 was tested against Trino 476. If your existing release runs a much older Trino, rebuild the connector against the matching SPI before upgrading; see the [connector repository](https://github.com/ExamonHPC/trino-kairosdb-connector).

### Step 3. Verify the install

```bash
kubectl get pods -n <namespace> -l 'app.kubernetes.io/name=trino'
```

Where `<namespace>` is `examon` for the fresh-install path or your own namespace for the existing-release path. Both pods should be `Running` with the `install-kairosdb-connector` init-container `Completed`.

Confirm the catalog is live:

```bash
kubectl port-forward -n <namespace> svc/<trino-service> 8080:8080 &
docker run --rm -it --network host trinodb/trino:476 \
  trino --server http://localhost:8080 \
  --execute 'SHOW CATALOGS'
```

The Service name is `trino` for the fresh-install path and whatever name your existing release uses (typically `<release>-trino`) for the existing-release path. The output lists `examon_ts_timestamps` alongside the chart defaults `system`, `tpch`, and `tpcds`, plus any catalogs your existing release already had.

### Step 4. Roll back

=== "Fresh install"

    ```bash
    helm uninstall trino -n examon
    kill %1   # the kubectl port-forward backgrounded in Step 3
    ```

    The ExaMon stack itself is untouched: only Trino is removed.

=== "Existing release"

    Roll the release back to the revision before the wiring overlay was applied:

    ```bash
    helm history <your-release> -n <your-namespace>
    helm rollback <your-release> <previous-revision> -n <your-namespace> --wait
    kill %1   # the kubectl port-forward backgrounded in Step 3
    ```

    Your operator-side values (image tag, JVM heap, worker count, etc.) come back to whatever they were on that revision. ExaMon's catalog and connector are removed.

## First SQL query

The connector lifts each KairosDB tag to a column and exposes the sample value as `VARCHAR`; cast at query time for numeric metrics. With either path complete, the simulated `random_sensor` metric is available:

```sql
SELECT timestamp,
       CAST(value AS DOUBLE) AS sensor_value
FROM examon_ts_timestamps.kairosdb."random_sensor"
WHERE timestamp > current_timestamp - INTERVAL '5' MINUTE
ORDER BY timestamp DESC
LIMIT 20;
```

For an existing-release path on Kubernetes, substitute a metric you know is being published into your ExaMon KairosDB; `SHOW TABLES FROM examon_ts_timestamps.kairosdb` lists them.

The result is the most recent samples from the simulated publisher, the same data the [`Random Sensor` Grafana dashboard](../../get-started/quickstart.md#step-3-open-grafana) plots.

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

## What this does and does not do

- **Does**: install or extend a Trino instance with the ExaMon KairosDB connector and the `examon_ts_timestamps` catalog, and prove the federation path with a first SQL query.
- **Does not**: provision the Cassandra catalog (no Slurm metadata available on the local stack), enable Trino authentication, persist Trino state across uninstall, or tune the install for production load. Those are the job of the staging and production overlays, planned for v0.5.1.

For the full SQL surface (catalog and schema layout, aggregation pushdown, cross-store joins, per-tool connection guides), see [Users → Analyze](index.md).

---

## Source

- Docker Compose overlay: [`compose.trino.yml`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/compose.trino.yml), [`deploy/docker/trino/`](https://github.com/ExamonHPC/examon/tree/release/v0.5.0/deploy/docker/trino)
- Kubernetes wiring overlay: [`deploy/trino/values-examon.yaml`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/deploy/trino/values-examon.yaml), [`deploy/trino/README.md`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/deploy/trino/README.md)
- Upstream Trino Helm chart: [trinodb/charts](https://github.com/trinodb/charts/tree/main/charts/trino)
- Connector: [ExamonHPC/trino-kairosdb-connector](https://github.com/ExamonHPC/trino-kairosdb-connector)
- Trino Python client: [trinodb/trino-python-client](https://github.com/trinodb/trino-python-client)
