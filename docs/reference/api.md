# API

!!! info "Status: Live (reproduced 2026-05-23)"
    Verified against examon-core v0.5.0 ([`examon-server`](https://github.com/ExamonHPC/examon/tree/release/v0.5.0/web/examon-server)), KairosDB 1.3.0, and [`trino-kairosdb-connector`](https://github.com/ExamonHPC/trino-kairosdb-connector) v3.0.0-rc1. The KairosDB and Trino surfaces are upstream and stable; their authoritative documentation is the upstream reference, cited at the bottom. This page documents what ExaMon exposes through them and where ExaMon adds connector-specific extensions.

> The external interfaces ExaMon presents to consumers. Three surfaces: the `examon-server` REST API (legacy, kept for `examon-client` and historical consumers), the KairosDB HTTP API (the read/write path Grafana uses), and the Trino SQL surface (the federation layer for SQL-based consumers including BI tools, notebooks, and ExaMon AI).

## `examon-server` REST API

The Flask-based REST API exposed by the `examon-server` component. The service runs on port 5000 by default and is reachable inside the cluster as `http://examon-examon-server:5000` or externally via the Ingress configured at `examon-server.ingress` in the Helm values.

### Authentication

Authentication is delegated to Grafana via `examon-server.config.authUrl` (`http://examon-grafana/api/datasources/id/kairosdb` by default). The unauthenticated root endpoint returns HTTP 401; consumers authenticate using a Grafana API key passed in the standard `Authorization` header:

```bash
curl -H "Authorization: Bearer <grafana-api-key>" \
     http://examon-examon-server:5000/api/...
```

The Grafana admin user can mint API keys under **Configuration → API Keys** in the Grafana UI or via the Grafana API.

### Surface

The endpoint surface is the legacy v0.4.0 contract preserved for `examon-client` and other historical consumers. The shape (paths under `/api/`, JSON request and response bodies, pagination conventions) is unchanged from the v0.4.0 line. The authoritative reference is the [`web/examon-server/server.py`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/web/examon-server/server.py) source itself.

The high-level path families:

| Path family | Returns | Typical consumer |
|---|---|---|
| `/api/health` | Service health and status. | Smoke tests, liveness probes. |
| `/api/...metrics...` | Metric listings and metadata. | `examon-client` for tab-completion and discovery. |
| `/api/...query...` | Time-series queries with caching. | `examon-client` and legacy dashboards that pre-dated the Trino federation. |
| `/api/...jobs...` | Slurm job listing and per-job query helpers. | `examon-client` and HPC operators using the legacy interface. |

### When to use this API versus Trino

The `examon-server` REST API is the right surface when the consumer already speaks the v0.4.0 contract (`examon-client`, legacy dashboards) and migration is not in scope. For new analytical work, the [Trino SQL surface](#trino-sql-surface) is the recommended path: it joins time-series and structured data in one query, exposes the data as standard SQL, and is what every new BI integration and ExaMon AI is built on.

A practical heuristic: if a query touches only one store (just time-series, or just job records) and the consumer already exists, the legacy API may be acceptable. If the query crosses stores, or if the consumer is new, use Trino.

### Readiness and liveness probes

The Kubernetes Deployment uses TCP socket probes rather than HTTP probes against `/` (the root endpoint requires Grafana authentication and returns HTTP 401, which Kubernetes interprets as unhealthy):

```yaml
readinessProbe:
  tcpSocket:
    port: http
  initialDelaySeconds: 10
  periodSeconds: 10
livenessProbe:
  tcpSocket:
    port: http
  initialDelaySeconds: 15
  periodSeconds: 20
```

This is a v0.5.0 fix; see [Administrators → Troubleshoot → 9. examon-server Not Ready](../administrators/operations/troubleshoot.md#9-examon-server-not-ready-readiness-probe-returns-401) for the background.

## KairosDB HTTP API

KairosDB exposes a JSON-over-HTTP API on port 8083 in the chart. Inside the cluster: `http://examon-kairosdb:8083`. The full surface is upstream and stable; the cited endpoints below are the ones ExaMon-specific consumers (Grafana, the bridge, ExaMon AI discovery, the Trino connector internally) rely on.

### Health

```
GET  /api/v1/health/check
```

Returns HTTP 204 when KairosDB is healthy. Used by the smoke test and by manual debugging:

```bash
kubectl port-forward svc/examon-kairosdb 8083:8083 -n examon &
curl http://localhost:8083/api/v1/health/check
```

### Read path

```
POST /api/v1/datapoints/query
GET  /api/v1/metricnames
GET  /api/v1/datapoints/query/tags
```

| Endpoint | Use |
|---|---|
| `POST /api/v1/datapoints/query` | The main time-series query endpoint. JSON body specifies metrics, time range, tag filters, and aggregators. Used by Grafana's KairosDB datasource and by the Trino connector. |
| `GET /api/v1/metricnames` | Lists every metric name the store has ever seen. The discovery primitive: a new metric appears here as soon as the first sample is written. |
| `GET /api/v1/datapoints/query/tags` | Lists the tag keys and values associated with a metric. The discovery primitive for "what tags does this metric carry". |

### Write path

```
POST /api/v1/datapoints
```

JSON array of tagged data points. The bridge (`mqtt2kairosdb`) uses this endpoint internally; publishers using `KairosDBLoader` from SDK v3 use the same endpoint. Direct writes are valid but uncommon: the MQTT path is preferred because it gives publishers a buffered transport with broker-side fan-out.

### Reference

The full KairosDB REST API reference is upstream: [KairosDB REST API documentation](https://kairosdb.github.io/docs/restapi/Overview.html). ExaMon adds no proprietary endpoints to KairosDB; ExaMon-specific behavior is implemented inside the Trino connector, not as KairosDB modifications.

## Trino SQL surface

The Trino federation endpoint is the most analytically expressive surface in ExaMon. A single SQL query joins time-series (via `trino-kairosdb-connector`), structured data (via the built-in Cassandra connector), and future cold-tier data (via the Hive or Iceberg connector). The default Trino client port is 8080 (HTTP) or 8443 (HTTPS).

ExaMon does not ship Trino in the Helm chart; sites deploy Trino independently and install the connector. The connector install path is in the connector README.

### Client surface (standard Trino)

Trino's client surface is JDBC, ODBC, REST, and a growing ecosystem of language-native libraries. The minimum information to connect:

| Setting | Value (reference) |
|---|---|
| Host | The Trino coordinator host |
| Port | 8080 (HTTP) or 8443 (HTTPS) |
| User | Any string; per-user auth at the Trino layer is the deployer's choice |
| Catalog | One of the configured catalogs (`examon_ts_timestamps`, `examon_meta`) |
| Schema | The metric keyspace (`kairosdb`) or the Slurm schema (`e4_slurm`) |

The full client reference is upstream: [Trino client documentation](https://trino.io/docs/current/client.html).

### The KairosDB virtual schema (ExaMon-specific)

The `trino-kairosdb-connector` exposes each KairosDB metric as a virtual table inside its catalog. Tags become columns; the connector is the layer that turns ExaMon's [tag-and-value time-series model](../concepts/data-model.md#a-sample) into idiomatic SQL.

Column shape:

| Column | Type | Source |
|---|---|---|
| `time` | `TIMESTAMP(3) WITH TIME ZONE` | KairosDB sample timestamp. Also available as `BIGINT` epoch milliseconds and `TIMESTAMP(3)` (no zone). |
| `value` | `DOUBLE` | The numeric sample. |
| (one per tag) | `VARCHAR` | Lifted from the metric's KairosDB tags. The column set varies per metric. |
| `sampling_aggregator` | `VARCHAR` (hidden) | Pushdown mechanism for KairosDB aggregators. Hidden by default; usable only in `WHERE`. |

A query against one metric:

```sql
SELECT time, value
FROM examon_ts_timestamps.kairosdb."power.draw"
WHERE node = 'cn01'
  AND gpu = '0'
  AND time > current_timestamp - INTERVAL '1' HOUR
ORDER BY time;
```

### Aggregation pushdown (the `sampling_aggregator` column)

The hidden `sampling_aggregator` column is the connector's pushdown mechanism. KairosDB's native aggregators (`avg`, `sum`, `min`, `max`, `count`, `first`, `last`, `dev`, `percentile`, `rate`, `sampler`, `scale`, `trim`, `gaps`, `histogram`, `least_squares`) are pushed down to KairosDB and only the aggregated points cross the wire:

```sql
SELECT time, value
FROM examon_ts_timestamps.kairosdb."CPU1_Temp"
WHERE node = 'acnode03'
  AND time BETWEEN TIMESTAMP '2026-05-23 00:00:00 UTC'
              AND TIMESTAMP '2026-05-23 23:59:59 UTC'
  AND sampling_aggregator = 'avg;1m;start_time';
```

Aggregator syntax: `<aggregator>;<sampling>;<alignment>`. Chained aggregators use `|` separation (the `IN (...)` form is preserved as a legacy alias):

```sql
WHERE sampling_aggregator = 'sum;10m;start_time|max;1h;start_time'
```

For long time ranges, pushdown is the difference between a query that returns in seconds and a query that exhausts memory.

### Time-range split parallelism

The connector automatically divides a query's time range into splits (configurable via `split.size.millis`, default 24 hours) that execute in parallel across Trino workers. Querying a month of high-cardinality data parallelizes naturally; no manual partitioning is required.

Per-session overrides:

```sql
SET SESSION kairosdb.split_size = '6h';
SET SESSION kairosdb.look_back = '30d';
```

### Connector versions and capabilities

The connector's authoritative capability list is the [`trino-kairosdb-connector`](https://github.com/ExamonHPC/trino-kairosdb-connector) README. Version-relevant notes:

- **v3.0.0-rc1 (May 2026, current).** Clean-room rewrite targeting Trino 476. Virtual schema with one column per tag, hash-suffixed handling for case collisions, `|`-separated chained aggregators, per-session split-size and look-back overrides, three timestamp formats (`BIGINT`, `TIMESTAMP(3)`, `TIMESTAMP(3) WITH TIME ZONE`). v3.0.0 final is planned for June 2026.
- **Pre-v3.** Legacy syntax (`IN (...)` aggregator chaining, fixed split sizes) is preserved as an alias in v3 for backward compatibility.

### Cassandra connector (structured data)

The built-in Trino Cassandra connector exposes the structured-data side of ExaMon. The conventional layout is one catalog per Cassandra cluster, with one schema per HPC cluster's keyspace, and one table per record type:

```sql
SELECT job_id, user, start_time, end_time, state, exit_code, n_nodes, n_cores
FROM examon_meta.e4_slurm.job_info_e4red
WHERE start_time > current_timestamp - INTERVAL '30' DAY
  AND state IN ('FAILED', 'TIMEOUT', 'OUT_OF_MEMORY')
ORDER BY start_time DESC;
```

The Cassandra connector is upstream-standard; ExaMon does not add ExaMon-specific behavior to it. Reference: [Trino Cassandra connector](https://trino.io/docs/current/connector/cassandra.html).

### Cross-store joins

The federation's analytical advantage is `JOIN` across stores. The pattern:

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

This is the kind of query that drives ExaMon AI's most valuable analyses (the GPU-XID-by-job correlation in the [AI demonstrated capabilities](../users/ai/index.md#demonstrated-capabilities) is a variant of this shape).

### Cold tier (planned)

The third connector slot is for the cold tier: S3-compatible object storage with Parquet files queried via Trino's Hive or Iceberg connector. The tiering policy ages data out of KairosDB/Cassandra after a configurable retention window, writes to the object store, and deletes from Cassandra. Trino's query planner routes time-range queries to the appropriate tier automatically.

Status: in development for v0.5.0. The connector configuration will land in the Helm chart when the tiering implementation ships.

## Surface stability

| Surface | Stability |
|---|---|
| `examon-server` REST API | Stable but legacy. Preserved for `examon-client` and historical consumers. New work should target Trino. |
| KairosDB HTTP API | Stable (upstream). Used internally by Grafana and the Trino connector; direct use by consumers is uncommon. |
| Trino client surface | Stable (upstream). The recommended surface for analytical consumers. |
| `trino-kairosdb-connector` virtual schema and pushdown | Active development (v3.0.0-rc1). The shape described above is stable; the syntax is preserved as aliases across major versions. |
| `examon-scheduler` REST/CLI | Not yet shipped. |
| ExaMon AI HTTP surface | The agent is a CLI today; a future HTTP surface is on the roadmap but not yet shipped. |

---

## Source

- `examon-server` source: [`web/examon-server/server.py`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/web/examon-server/server.py) in the core repository.
- KairosDB REST API reference: [KairosDB REST API documentation](https://kairosdb.github.io/docs/restapi/Overview.html).
- Trino client surface: [Trino client documentation](https://trino.io/docs/current/client.html).
- Trino-KairosDB connector: [ExamonHPC/trino-kairosdb-connector](https://github.com/ExamonHPC/trino-kairosdb-connector).
- Trino Cassandra connector: [Trino Cassandra connector documentation](https://trino.io/docs/current/connector/cassandra.html).
