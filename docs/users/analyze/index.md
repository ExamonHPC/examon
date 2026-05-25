# Analyze

!!! info "Status: Beta (Trino-KairosDB connector v3.0.0-rc1 available; fresh-install and existing-release paths shipped, see Trino Quickstart below)"
    The [`trino-kairosdb-connector`](https://github.com/ExamonHPC/trino-kairosdb-connector) is published publicly as v3.0.0-rc1 (Apache-2.0, May 2026). It plugs into an existing Trino installation per the standard Trino plugin install path. ExaMon does not bundle Trino in its umbrella chart, but ships a single tested values overlay for the upstream Trino Helm chart, [`values-examon.yaml`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/deploy/trino/values-examon.yaml), that adds the connector and the `examon_ts_timestamps` catalog to either a fresh laptop install or an existing release; see the [Trino Quickstart](local-trino-quickstart.md). The schema layout and example queries below are stable.

> The Analyze section is for data scientists, analysts, and ML engineers running queries against ExaMon. ExaMon exposes its data through a Trino SQL surface, so any tool that speaks Trino (Jupyter, Superset, Power BI, DBeaver, raw `trino-cli`) can connect with the same SQL. This page covers the surface itself: what catalogs exist, what schemas live inside each, what tags become columns, and how to walk from a question to a query.

!!! tip "Install or wire Trino"
    The [Trino Quickstart](local-trino-quickstart.md) covers both paths: a laptop-sized fresh install for the local ExaMon, and adding the connector and catalog to an existing `trino/trino` Helm release. Both paths use the same wiring overlay, paired with whatever sizing values your Trino needs. The sections below describe the full SQL surface.

## The federation model

ExaMon's analytical surface is a single Trino endpoint backed by three connectors:

| Connector | What it accesses | Origin |
|---|---|---|
| [`trino-kairosdb-connector`](https://github.com/ExamonHPC/trino-kairosdb-connector) | KairosDB time-series data | Custom (ExaMon, Apache-2.0). |
| Trino Cassandra connector | Direct Cassandra tables: Slurm job accounting, ExaMon metadata | Trino ecosystem (built-in). |
| Trino Hive / Iceberg connector | Cold-tier S3 / Parquet (when configured) | Trino ecosystem (built-in). Cold tier is planned, not yet shipped. |

The federation means a single SQL query can join GPU temperature samples (from KairosDB) against Slurm job records (from Cassandra) without the analyst knowing which physical store answered which part of the query. This cross-store join is what makes correlation analyses tractable: *"join GPU thermal events with job failures for user X over the last 90 days"* is one query, not three plus a pandas merge.

The architectural rationale for the federation layer is in [Concepts → Architecture](../../concepts/architecture.md). Below is the practical surface.

## Catalog and schema layout

By Trino convention every fully-qualified table is `<catalog>.<schema>.<table>`. The catalogs ExaMon installations typically expose:

| Catalog | Connector | Schema | Contents |
|---|---|---|---|
| `examon_ts_timestamps` (or similar) | `trino-kairosdb-connector` | `kairosdb` (the KairosDB keyspace) | One virtual table per metric. Tags become columns. |
| `examon_meta` (or similar) | Trino Cassandra connector | `e4_slurm` (or per-cluster) | Slurm job accounting tables (`job_info_<cluster>`), schema registry (`row_keys`), and other metadata. |

The exact catalog names are deployment-specific: they are set in the Trino server's `etc/catalog/*.properties` files at install time. The names above match the reference deployment; the ExaMon AI configuration ships the same defaults (see [ExaMon AI → Configure](../ai/index.md#configure)).

### The KairosDB virtual schema (connector v3.0.0+)

The connector exposes each KairosDB metric as a virtual table. The columns are:

| Column type | Example | Source |
|---|---|---|
| Mandatory timestamp | `timestamp` | Sample timestamp. The SQL type is configurable in the connector catalog via `kairosdb.timestamp.format`: `BIGINT` (epoch milliseconds, connector default), `TIMESTAMP(3)` (UTC), or `TIMESTAMP(3) WITH TIME ZONE`. The examples below assume `TIMESTAMP(3) WITH TIME ZONE`; rewrite the `WHERE` literals as epoch milliseconds if your catalog uses `BIGINT`. |
| Mandatory value | `value` (`VARCHAR`) | The raw KairosDB sample as a string. KairosDB allows per-metric value types (numeric, string, complex); the connector echoes whatever the storage layer returns rather than guessing a type per metric. For numeric metrics, cast at query time with `CAST(value AS DOUBLE)`. |
| One column per tag | `org`, `cluster`, `node`, `plugin`, ... | Lifted from the metric's KairosDB tags. The full tag set varies per metric. |
| Hidden `sampling_aggregator` | n/a | Pushdown of KairosDB aggregators via `WHERE` clause. See below. |

The `value` column is `VARCHAR` so that string, numeric, and complex (histogram, percentile) metrics share one schema. For metrics you know are numeric, wrap each read in `CAST(value AS DOUBLE)`; if you query the same metric repeatedly, a SQL view over the cast hides the boilerplate from downstream consumers without changing the connector.

A metric like `power.draw` published from `nvml_pub` with tags `(org=examon, cluster=e4red, node=cn01, plugin=nvml_pub, gpu=0)` is queryable as:

```sql
SELECT timestamp, CAST(value AS DOUBLE) AS power_w
FROM examon_ts_timestamps.kairosdb."power.draw"
WHERE node = 'cn01'
  AND gpu = '0'
  AND timestamp > current_timestamp - INTERVAL '1' HOUR
ORDER BY timestamp;
```

The tag-as-column mapping is what makes WHERE-clause filtering against ExaMon's data idiomatic SQL rather than a custom DSL.

### Aggregation pushdown

KairosDB's native aggregators (`avg`, `sum`, `min`, `max`, `count`, `first`, `last`, `dev`, `percentile`, `rate`, `sampler`, `scale`, `trim`, `gaps`, `histogram`, `least_squares`) are pushed down to KairosDB via the hidden `sampling_aggregator` column in `WHERE`:

```sql
SELECT timestamp, CAST(value AS DOUBLE) AS temp_c
FROM examon_ts_timestamps.kairosdb."CPU1_Temp"
WHERE node = 'acnode03'
  AND timestamp BETWEEN TIMESTAMP '2026-05-23 00:00:00 UTC'
                    AND TIMESTAMP '2026-05-23 23:59:59 UTC'
  AND sampling_aggregator = 'avg;1m;start_time'
ORDER BY timestamp;
```

This avoids transferring raw sample points to Trino for aggregation: KairosDB performs the bucketing, only the aggregated points cross the wire. For long time ranges (weeks or months), pushdown is the difference between a query that returns in seconds and a query that exhausts memory.

Multiple aggregators chain together with `|` separation (the `IN (...)` form is preserved as a legacy alias):

```sql
WHERE sampling_aggregator = 'sum;10m;start_time|max;1h;start_time'
```

### Time-range split parallelism

For large time ranges, the connector automatically divides the query into time-range splits (configurable via `split.size.millis`, default 24 hours) that execute in parallel across Trino workers. Querying a month of high-cardinality data parallelizes naturally; no manual partitioning is needed.

## Slurm job accounting (Cassandra connector)

Job accounting tables live in the Cassandra catalog under the per-cluster Slurm schema. A typical table layout:

```sql
SELECT job_id, user, start_time, end_time, state, exit_code, n_nodes, n_cores
FROM examon_meta.e4_slurm.job_info_e4red
WHERE start_time > current_timestamp - INTERVAL '30' DAY
  AND state IN ('FAILED', 'TIMEOUT', 'OUT_OF_MEMORY')
ORDER BY start_time DESC;
```

Cross-domain joins (the analytical advantage of the federation layer) chain the two:

```sql
WITH failed_jobs AS (
  SELECT job_id, user, start_time, end_time
  FROM examon_meta.e4_slurm.job_info_e4red
  WHERE state = 'FAILED'
    AND start_time > current_timestamp - INTERVAL '30' DAY
)
SELECT j.job_id, j.user, AVG(CAST(g.value AS DOUBLE)) AS avg_gpu_temp
FROM failed_jobs j
JOIN examon_ts_timestamps.kairosdb."temperature.gpu" g
  ON g.timestamp BETWEEN j.start_time AND j.end_time
WHERE g.sampling_aggregator = 'avg;1m;start_time'
GROUP BY j.job_id, j.user
ORDER BY avg_gpu_temp DESC;
```

## Walk through an end-to-end example

The repository ships an executable notebook that walks the analyst's path end to end against a reference deployment, covering schema exploration, time-series queries with tag filters, and combining sensor data with Slurm job records.

- [`Demo_ExamonQL.ipynb`](Demo_ExamonQL.ipynb): the ExamonQL demo notebook (Jupyter).

The notebook does not use the Trino federation path described above; it uses the legacy `examon-client` Python package, which queries KairosDB and Cassandra directly. See [Legacy Python client](#legacy-python-client) below for context. The SQL-like DSL the notebook demonstrates (`sq.SELECT(...).FROM(...).WHERE(...)`) is the pre-Trino interface; the underlying tag-and-metric data model is the same as the one Trino exposes, so the notebook remains a useful introduction to the data model even for deployments that have adopted Trino.

A native Trino notebook walkthrough is planned for a future release.

## Connect from common tools

The Trino client surface is the same regardless of caller: JDBC, ODBC, REST, and the Python `trino` package all hit the same endpoint. The minimum information needed:

| Setting | Value (reference) |
|---|---|
| Host | The Trino coordinator host |
| Port | 8080 (HTTP) or 8443 (HTTPS) |
| User | Any string; ExaMon does not currently enforce per-user authentication at the Trino layer |
| Catalog | One of the configured catalogs (e.g. `examon_ts_timestamps`, `examon_meta`) |
| Schema | The metric keyspace (`kairosdb`) or the Slurm schema (`e4_slurm`) |

Per-tool connection guides (Jupyter, Superset, Power BI, DBeaver, raw `trino-cli`, the Python `trino` package) follow the upstream connector documentation; for the Trino client surface itself, see the [Trino client documentation](https://trino.io/docs/current/client.html). Per-tool ExaMon-specific walkthroughs are planned but not yet shipped.

## Legacy Python client

For deployments that do not run Trino, the [`examon-client`](https://github.com/fbeneventi/examon-client) Python package queries KairosDB and Cassandra directly using a SQL-like DSL inherited from the pre-Trino era:

```python
from examon.examon import Client, ExamonQL

sq = ExamonQL(Client(...))
data = (sq.SELECT('*')
          .FROM('p0_power')
          .WHERE(cluster='marconi100', node='r255n18')
          .TSTART(10, 'minutes')
          .execute())
```

`examon-client` is the surface the bundled notebooks (`Demo_ExamonQL.ipynb`, the [Monte Cimone notebook](../../community/clusters/montecimone-notebook.ipynb)) currently use. It is suitable for analyses that hit a single store at a time and that do not require cross-store joins. New analytical work that needs to combine time-series and Slurm job records, or that targets a non-Python consumer (Superset, Power BI, DBeaver), should use Trino as described above.

The full API reference is in the [`examon-client` repository](https://github.com/fbeneventi/examon-client). The package will receive a refresh in a future release; the existing API is stable for v0.5.0 consumers.

---

## Source

- Trino-KairosDB connector: [ExamonHPC/trino-kairosdb-connector](https://github.com/ExamonHPC/trino-kairosdb-connector) (Apache-2.0, v3.0.0-rc1).
- Connector clean-room rewrite plan and audit (technical background): tracked alongside the connector repository.
- Upstream Trino client surface: [Trino client documentation](https://trino.io/docs/current/client.html).
- Upstream KairosDB aggregator reference: [KairosDB aggregators](https://kairosdb.github.io/docs/restapi/Aggregators.html).
- Reference deployment used by the demo notebook: e4red cluster (the same testbed referenced by [AI → Verify](../ai/index.md#verify)).
