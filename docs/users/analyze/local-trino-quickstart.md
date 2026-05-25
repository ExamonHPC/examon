# Trino Quickstart

!!! info "Status: Live (reproduced 2026-05-25)"
    Verified against examon-core v0.5.0, the upstream Trino chart 1.42.2 (Trino image 476), and [`trino-kairosdb-connector`](https://github.com/ExamonHPC/trino-kairosdb-connector) v3.0.0-rc1. Both paths below were tested end to end against the same K3d cluster.

> This page wires a Trino SQL surface to an ExaMon installation. The procedure is the same for two shapes:
>
> - **Fresh install**: you have no Trino in your cluster yet and want one sized for a laptop-scale ExaMon (the [Get Started Quickstart](../../get-started/quickstart.md) profile). You install Trino alongside ExaMon in the `examon` namespace.
> - **Existing release**: you already operate Trino with the upstream [`trino/trino`](https://github.com/trinodb/charts/tree/main/charts/trino) Helm chart and want to add ExaMon's catalog and connector to it without disturbing your image tag, JVM heap, worker count, auth, or networking.
>
> Both paths use the **same** ExaMon wiring overlay, [`deploy/trino/values-examon.yaml`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/deploy/trino/values-examon.yaml). It ships only ExaMon's contract: the connector init-container, the plugin volume + mount, and the `examon_ts_timestamps` catalog. Sizing, image tag, auth, and everything else stay with your own values file. Steps 2 and 6 fork on the helm verb (`install` vs `upgrade`) and the sizing file you bring; the rest is identical.
>
> Trino is kept outside the ExaMon umbrella chart on purpose: its lifecycle (upgrades, scaling, JVM tuning, authentication) belongs with the operator, not with ExaMon. ExaMon ships only its contract with Trino, not Trino itself.

## Before you start

- `helm` v3.x and `kubectl` configured against the target cluster.
- A `trino` client, either the [Docker image](https://hub.docker.com/r/trinodb/trino) or the [native CLI](https://trino.io/docs/current/client/cli.html). The examples below use the Docker image.
- For the **fresh install** path: the [Get Started Quickstart](../../get-started/quickstart.md) is done (K3d cluster `examon-local`, healthy `examon` namespace, `random_pub` publishing into KairosDB) and you have about 2 GB of free RAM on top of the existing ExaMon stack.
- For the **existing release** path: your Trino was installed with the upstream `trino/trino` chart (the procedure below does not apply to manually-managed Trino, custom images, operator-managed deployments, or Starburst). You also need network reachability from your Trino pods to your ExaMon KairosDB Service.
- If Trino and ExaMon live in different namespaces, edit `catalogs.examon_ts_timestamps`' `kairosdb.url` in [`deploy/trino/values-examon.yaml`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/deploy/trino/values-examon.yaml) before applying. Both common shapes are documented in the file's comment.

## Step 1. Add the Trino Helm repository

```bash
helm repo add trino https://trinodb.github.io/charts
helm repo update
```

## Step 2. Pair a sizing file with the ExaMon wiring overlay

The ExaMon wiring overlay sets only the connector and catalog. You pair it with a sizing file: a fresh laptop install brings a paste-this snippet, an existing release brings its own current values.

=== "Fresh install (laptop, no Trino yet)"

    The sizing snippet below targets the 8 GB host documented in the [Get Started Quickstart](../../get-started/quickstart.md). It is an **example**, not chart-side material: operators with different targets supply their own.

    ```bash
    cat > /tmp/trino-laptop.yaml <<'EOF'
    image:
      tag: "476"           # tested with trino-kairosdb-connector 3.0.0-rc1

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

## Step 3. Verify the install

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

## Step 4. Run your first query

The connector lifts each KairosDB tag to a column and exposes the sample value as `VARCHAR`; cast at query time for numeric metrics. The fresh-install path has the simulated `random_sensor` metric available out of the box:

```sql
SELECT timestamp,
       CAST(value AS DOUBLE) AS sensor_value
FROM examon_ts_timestamps.kairosdb."random_sensor"
WHERE timestamp > current_timestamp - INTERVAL '5' MINUTE
ORDER BY timestamp DESC
LIMIT 20;
```

On the existing-release path, substitute a metric you know is being published into your ExaMon KairosDB; `SHOW TABLES FROM examon_ts_timestamps.kairosdb` lists them.

Run it through the same CLI (still using the port-forward from Step 3):

```bash
docker run --rm -it --network host trinodb/trino:476 \
  trino --server http://localhost:8080 \
        --catalog examon_ts_timestamps \
        --schema kairosdb
```

Paste the query at the `trino>` prompt. On the fresh-install path the result is the most recent samples from the simulated publisher, the same data the [`Random Sensor` Grafana dashboard](../../get-started/quickstart.md#step-3-open-grafana) plots.

## Step 5. Run the same query from Python

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

## Step 6. Roll back

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

## What this does and does not do

- **Does**: install or extend a Trino instance with the ExaMon KairosDB connector and the `examon_ts_timestamps` catalog, and prove the federation path with a first SQL query.
- **Does not**: provision the Cassandra catalog (no Slurm metadata locally on the fresh-install path), enable Trino authentication, persist Trino state across uninstall, or tune the install for production load. Those are the job of the staging and production overlays, planned for v0.5.1.

For the full SQL surface (catalog and schema layout, aggregation pushdown, cross-store joins, per-tool connection guides), see [Users → Analyze](index.md).

---

## Source

- ExaMon wiring overlay: [`deploy/trino/values-examon.yaml`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/deploy/trino/values-examon.yaml)
- Overlay README: [`deploy/trino/README.md`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/deploy/trino/README.md)
- Upstream Trino Helm chart: [trinodb/charts (trino 1.42.2)](https://github.com/trinodb/charts/tree/main/charts/trino)
- Connector: [ExamonHPC/trino-kairosdb-connector](https://github.com/ExamonHPC/trino-kairosdb-connector) (Apache-2.0, v3.0.0-rc1)
- Trino Python client: [trinodb/trino-python-client](https://github.com/trinodb/trino-python-client)
