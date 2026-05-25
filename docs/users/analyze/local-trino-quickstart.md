# Trino Quickstart

!!! info "Status: Live (reproduced 2026-05-25)"
    Verified against examon-core v0.5.0, the upstream Trino chart 1.42.2 (Trino image 476), and [`trino-kairosdb-connector`](https://github.com/ExamonHPC/trino-kairosdb-connector) v3.0.0-rc1. Both paths below were tested end to end against the same K3d cluster.

> This page wires a Trino SQL surface to an ExaMon installation. It covers two shapes:
>
> - **Fresh install**: you have no Trino in your cluster yet and want one sized for a laptop-scale ExaMon (the [Get Started Quickstart](../../get-started/quickstart.md) profile). ExaMon's local values overlay installs Trino alongside ExaMon in the `examon` namespace.
> - **Existing release**: you already operate Trino with the upstream [`trino/trino`](https://github.com/trinodb/charts/tree/main/charts/trino) Helm chart and want to add ExaMon's catalog and connector to it. ExaMon's add-on overlay leaves your image tag, JVM heap, worker count, auth, and networking untouched.
>
> Both paths share the same verification, query, and Python-client steps. Use the tab headers at Step 2 and Step 6 to pick your branch.
>
> Trino is kept outside the ExaMon umbrella chart on purpose: its lifecycle (upgrades, scaling, JVM tuning, authentication) belongs with the operator, not with ExaMon. ExaMon ships values overlays for the upstream Trino Helm chart instead.

## Before you start

- `helm` v3.x and `kubectl` configured against the target cluster.
- A `trino` client, either the [Docker image](https://hub.docker.com/r/trinodb/trino) or the [native CLI](https://trino.io/docs/current/client/cli.html). The examples below use the Docker image.
- For the **fresh install** path: the [Get Started Quickstart](../../get-started/quickstart.md) is done (K3d cluster `examon-local`, healthy `examon` namespace, `random_pub` publishing into KairosDB) and you have about 2 GB of free RAM on top of the existing ExaMon stack.
- For the **existing release** path: your Trino was installed with the upstream `trino/trino` chart (the procedure below does not apply to manually-managed Trino, custom images, operator-managed deployments, or Starburst). You also need network reachability from your Trino pods to your ExaMon KairosDB Service.

## Step 1. Add the Trino Helm repository

```bash
helm repo add trino https://trinodb.github.io/charts
helm repo update
```

## Step 2. Install Trino with ExaMon's overlay

=== "Fresh install (laptop, no Trino yet)"

    Uses [`deploy/trino/values-examon-local.yaml`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/deploy/trino/values-examon-local.yaml). The overlay pins the Trino image to `476` (the version the connector is tested against), caps coordinator and worker JVM heap at `1G` with per-node query memory at `512MB` (laptop-sized), adds an init-container on both pods that fetches `kairosdb-connector-3.0.0-rc1.jar`, and wires a single catalog `examon_ts_timestamps` pointing at the same-namespace `examon-kairosdb` Service.

    From the repository root:

    ```bash
    helm install trino trino/trino \
      --version 1.42.2 \
      -f deploy/trino/values-examon-local.yaml \
      -n examon \
      --wait --timeout 5m
    ```

    The Cassandra catalog (`examon_meta`) is intentionally not wired in the local overlay: the local stack carries no Slurm job metadata, so the catalog would be empty. Staging and production overlays add it.

=== "Add ExaMon catalogs to an existing trino/trino Helm release"

    Uses [`deploy/trino/values-examon-addon.yaml`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/deploy/trino/values-examon-addon.yaml). The add-on overlay ships only the connector init-container, the plugin volume + mount on coordinator and worker, and the `examon_ts_timestamps` catalog. It deliberately does **not** set image tag, server.workers, JVM heap, query memory, auth, or networking; those stay with your own values file.

    Open `deploy/trino/values-examon-addon.yaml` and adjust `kairosdb.url` for your topology before applying. Two common shapes:

    - Trino and ExaMon in the same namespace: `http://examon-kairosdb:8083`
    - Trino and ExaMon in different namespaces (same cluster): `http://examon-kairosdb.<examon-namespace>.svc.cluster.local:8083`

    Then upgrade your existing release. **Pass your existing values file as the first `-f`**, or `helm upgrade` will reset unset fields back to chart defaults. If you don't have a copy on disk, export the current ones first:

    ```bash
    helm get values <your-release> -n <your-namespace> -o yaml > /tmp/current-values.yaml

    helm upgrade <your-release> trino/trino \
      -f /tmp/current-values.yaml \
      -f deploy/trino/values-examon-addon.yaml \
      -n <your-namespace> \
      --wait --timeout 5m
    ```

    !!! warning "Helm list-merge gotcha"
        Helm merges YAML maps deeply but lists by replacement. The add-on overlay defines `initContainers.coordinator`, `initContainers.worker`, `coordinator.additionalVolumes`, `coordinator.additionalVolumeMounts`, `worker.additionalVolumes`, and `worker.additionalVolumeMounts` as lists. If your own values already define any of these (for example, a sidecar volume or a different init-container), the overlay will **replace** your entries, not append. Detect this with `helm get values <release> -a` before upgrading; if any of those keys are non-empty, paste the four blocks from `values-examon-addon.yaml` into your own values file (concatenating the lists) and skip the second `-f`.

    !!! note "Trino version compatibility"
        Connector 3.0.0-rc1 was tested against Trino 476. If your existing release runs a much older Trino, rebuild the connector against the matching SPI before upgrading; see the [connector repository](https://github.com/ExamonHPC/trino-kairosdb-connector).

## Step 3. Verify the install

```bash
kubectl get pods -n <namespace> -l 'app.kubernetes.io/name=trino'
```

Where `<namespace>` is `examon` for the fresh-install path or your own namespace for the add-on path. Both pods should be `Running` with the `install-kairosdb-connector` init-container `Completed`.

Confirm the catalog is live:

```bash
kubectl port-forward -n <namespace> svc/<trino-service> 8080:8080 &
docker run --rm -it --network host trinodb/trino:476 \
  trino --server http://localhost:8080 \
  --execute 'SHOW CATALOGS'
```

The Service name is `trino` for the fresh-install path and whatever name your existing release uses (typically `<release>-trino`) for the add-on path. The output lists `examon_ts_timestamps` alongside the chart defaults `system`, `tpch`, and `tpcds`, plus any catalogs your existing release already had.

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

On the add-on path, substitute a metric you know is being published into your ExaMon KairosDB; `SHOW TABLES FROM examon_ts_timestamps.kairosdb` lists them.

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

=== "Add-on overlay"

    Roll the release back to the revision before the add-on was applied:

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

- Local-install overlay: [`deploy/trino/values-examon-local.yaml`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/deploy/trino/values-examon-local.yaml)
- Add-on overlay: [`deploy/trino/values-examon-addon.yaml`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/deploy/trino/values-examon-addon.yaml)
- Overlay README: [`deploy/trino/README.md`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/deploy/trino/README.md)
- Upstream Trino Helm chart: [trinodb/charts (trino 1.42.2)](https://github.com/trinodb/charts/tree/main/charts/trino)
- Connector: [ExamonHPC/trino-kairosdb-connector](https://github.com/ExamonHPC/trino-kairosdb-connector) (Apache-2.0, v3.0.0-rc1)
- Trino Python client: [trinodb/trino-python-client](https://github.com/trinodb/trino-python-client)
