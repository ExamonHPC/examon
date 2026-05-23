# Analyze

!!! info "Status: Beta (Trino-KairosDB connector available, not bundled into the local chart)"
    The [`trino-kairosdb-connector`](https://github.com/ExamonHPC/trino-kairosdb-connector) is published publicly as v3.0.0-rc1 (Apache-2.0, May 2026). It plugs into an existing Trino installation per the standard Trino plugin install path; the local-development Helm chart does not bundle Trino. For the connector install path, follow the connector README. The schema layout and example queries below are stable.

> The Analyze section is for data scientists, analysts, and ML engineers running queries against ExaMon. ExaMon exposes its data through a Trino SQL surface so any tool that speaks Trino — Jupyter, Superset, Power BI, DBeaver, raw `trino-cli` — can connect with the same SQL. This page covers the surface itself: what catalogs exist, what schemas live inside each, what tags become columns, and how to walk from a question to a query.

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
| Mandatory timestamp | `time` (`TIMESTAMP(3) WITH TIME ZONE`) | KairosDB sample timestamp. Also available as `BIGINT` epoch milliseconds. |
| Mandatory value | `value` (`DOUBLE`) | The numeric sample. |
| One column per tag | `org`, `cluster`, `node`, `plugin`, ... | Lifted from the metric's KairosDB tags. The full tag set varies per metric. |
| Hidden `sampling_aggregator` | n/a | Pushdown of KairosDB aggregators via `WHERE` clause. See below. |

A metric like `power.draw` published from `nvml_pub` with tags `(org=examon, cluster=e4red, node=cn01, plugin=nvml_pub, gpu=0)` is queryable as:

```sql
SELECT time, value
FROM examon_ts_timestamps.kairosdb."power.draw"
WHERE node = 'cn01'
  AND gpu = '0'
  AND time > current_timestamp - INTERVAL '1' HOUR
ORDER BY time;
```

The tag-as-column mapping is what makes WHERE-clause filtering against ExaMon's data idiomatic SQL rather than a custom DSL.

### Aggregation pushdown

KairosDB's native aggregators (`avg`, `sum`, `min`, `max`, `count`, `first`, `last`, `dev`, `percentile`, `rate`, `sampler`, `scale`, `trim`, `gaps`, `histogram`, `least_squares`) are pushed down to KairosDB via the hidden `sampling_aggregator` column in `WHERE`:

```sql
SELECT time, value
FROM examon_ts_timestamps.kairosdb."CPU1_Temp"
WHERE node = 'acnode03'
  AND time BETWEEN TIMESTAMP '2026-05-23 00:00:00 UTC'
              AND TIMESTAMP '2026-05-23 23:59:59 UTC'
  AND sampling_aggregator = 'avg;1m;start_time'
ORDER BY time;
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
SELECT j.job_id, j.user, AVG(g.value) AS avg_gpu_temp
FROM failed_jobs j
JOIN examon_ts_timestamps.kairosdb."temperature.gpu" g
  ON g.time BETWEEN j.start_time AND j.end_time
WHERE g.sampling_aggregator = 'avg;1m;start_time'
GROUP BY j.job_id, j.user
ORDER BY avg_gpu_temp DESC;
```

## Walk through an end-to-end example

The repository ships an executable notebook that walks the analyst's path end to end against a reference deployment: connecting to Trino, exploring the schema, querying time-series with aggregation pushdown, and assembling cross-store joins.

- [`Demo_ExamonQL.ipynb`](Demo_ExamonQL.ipynb) — the ExamonQL demo notebook (Jupyter).

Open it in JupyterLab or VS Code and run cell by cell. The notebook assumes the Trino endpoint is reachable; for a local deployment, see the connector README for the local install path.

## Connect from common tools

The Trino client surface is the same regardless of caller — JDBC, ODBC, REST, and the Python `trino` package all hit the same endpoint. The minimum information needed:

| Setting | Value (reference) |
|---|---|
| Host | The Trino coordinator host |
| Port | 8080 (HTTP) or 8443 (HTTPS) |
| User | Any string; ExaMon does not currently enforce per-user authentication at the Trino layer |
| Catalog | One of the configured catalogs (e.g. `examon_ts_timestamps`, `examon_meta`) |
| Schema | The metric keyspace (`kairosdb`) or the Slurm schema (`e4_slurm`) |

Per-tool connection guides (Jupyter, Superset, Power BI, DBeaver, raw `trino-cli`, the Python `trino` package) follow the upstream connector documentation; for the Trino client surface itself, see the [Trino client documentation](https://trino.io/docs/current/client.html). Per-tool ExaMon-specific walkthroughs are planned but not yet shipped.

---

## Source

- Trino-KairosDB connector: [ExamonHPC/trino-kairosdb-connector](https://github.com/ExamonHPC/trino-kairosdb-connector) (Apache-2.0, v3.0.0-rc1).
- Connector clean-room rewrite plan and audit (technical background): tracked alongside the connector repository.
- Upstream Trino client surface: [Trino client documentation](https://trino.io/docs/current/client.html).
- Upstream KairosDB aggregator reference: [KairosDB aggregators](https://kairosdb.github.io/docs/restapi/Aggregators.html).
- Reference deployment used by the demo notebook: e4red cluster (the same testbed referenced by [AI → Verify](../ai/index.md#verify)).
