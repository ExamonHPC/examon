# Data Model

!!! info "Status: Live (reproduced 2026-05-23)"
    Verified against examon-core v0.5.0 and the KairosDB / Cassandra schemas it ships against.

> The data model is the contract ExaMon makes with everything that reads or writes data: publishers, the bridge, the time-series store, the structured store, the federation layer, and every downstream consumer. The model is intentionally simple: tagged time-series for sensor data, native Cassandra rows for structured records, MQTT topics that mirror the tag structure. This page covers the model from end to end, separately from any deployment shape.

## Two data shapes, one platform

ExaMon stores two structurally different kinds of data:

| Shape | What it is | Where it lives |
|---|---|---|
| **Tagged time-series** | A scalar value, sampled at a point in time, tagged with identifying metadata. Most ExaMon data is this shape: every IPMI sensor, GPU metric, performance counter, Prometheus metric. | KairosDB (over Cassandra). |
| **Structured records** | A row with a fixed schema. Job accounting (Slurm), inventory metadata, schema registries. | Cassandra directly. |

A single SQL query in [Trino](../users/analyze/index.md) can join both shapes via the federation layer; from a consumer's perspective they look like two databases under one connection. The split exists because each shape has a different access pattern: time-series are append-heavy with range scans, structured records are point lookups with low cardinality.

## The time-series model

### Schema-less by design

A KairosDB metric is not declared. The first time a sample arrives, KairosDB creates the metric implicitly. The publisher controls what metrics exist by what it publishes; no schema migration step is required to add a new sensor, a new node, or a new publisher.

This is essential for ExaMon's deployment story. A new cluster brings new hardware, new monitoring interfaces, and new metric names; if every new metric required a coordinated schema change, ExaMon could not bring up a new site without bespoke up-front work. Schema-less ingest means a publisher dropped on a new node starts emitting useful data the instant it can reach the broker.

The cost is that consumers cannot rely on a metric existing. The discovery convention is therefore part of the platform: see [Discovery](#discovery) below.

### A sample

A single time-series sample consists of four parts:

| Part | Type | Example |
|---|---|---|
| Metric name | String | `temperature.gpu`, `power.draw`, `node_cpu_seconds_total` |
| Timestamp | Epoch milliseconds | `1716480000123` |
| Value | Double | `58.0` |
| Tags | Ordered key-value mapping | `{org=examon, cluster=e4red, node=cn01, plugin=nvml_pub, gpu=0}` |

Tags are first-class. They are what `WHERE` clauses match against on read (`WHERE node = 'cn01' AND gpu = '0'`), what the connector lifts into Trino columns ([virtual schema](../users/analyze/index.md#the-kairosdb-virtual-schema-connector-v300)), and what defines the MQTT topic on write.

### Canonical tag set

The ExaMon convention is a small set of tags that every metric carries, plus arbitrary publisher-specific tags on top:

| Tag | Meaning | Example |
|---|---|---|
| `org` | Organization or deployment owner. | `examon`, `e4` |
| `cluster` | The logical cluster the data belongs to. | `e4red`, `marconi100`, `production` |
| `node` | The host the sample was collected from. | `cn01`, `acnode04` |
| `plugin` | The publisher that emitted the sample. | `nvml_pub`, `ipmi_pub`, `prometheus_pub` |
| `chnl` | The channel (typically `data`; `events`, `state`, etc. for non-numeric streams). | `data` |

Any additional tag the publisher emits is preserved verbatim. `gpu=0` (per-GPU disambiguation), `core=12` (per-core), `dimm=A0` (per-DIMM), `exp_name=node_exporter` (Prometheus exporter origin) are all examples.

The canonical set is what the federation layer assumes; it is what makes a query like `WHERE node = 'cn01'` work across every metric on the system. Publishers that omit canonical tags break the convention; the standard practice is to set them once in `global.examon.tags` and let the framework apply them to every emitted sample (see [SDK v3](../developers/sdk-v3/index.md#global)).

### Metric naming

ExaMon does not enforce a metric-naming convention; the convention follows the source:

- IPMI metrics use the BMC sensor name (`CPU1_Temp`, `FAN2`, `Inlet_Temp`, `DIMMA0_Temp`).
- GPU metrics use the DCGM/NVML name (`temperature.gpu`, `power.draw`, `utilization.gpu`).
- Prometheus metrics use the Prometheus name (`node_cpu_seconds_total`, `node_memory_MemAvailable_bytes`).
- PMU metrics use the perf event name.

Preserving the upstream name is deliberate: it keeps the relationship between the ExaMon view of a metric and the source's documentation transparent, and it lets a researcher familiar with the source instrument work in ExaMon without translation.

The cost is that there is no global "what does this metric mean" registry; the user discovers what is available per source (see [Discovery](#discovery) below) and consults the source's documentation for semantics.

## The structured-data model

Time-series is the wrong shape for some ExaMon data:

- **Slurm job records.** A job is a row with about a dozen columns (`job_id`, `user`, `start_time`, `end_time`, `state`, `exit_code`, `n_nodes`, `n_cores`, ...) that changes once when the job completes. Modeling it as a time-series would either waste space (multiple samples of an unchanging row) or lose information (only one sample at the change point, with no row identity).
- **Schema registries** (the `row_keys` table). The list of which metric names exist for a given cluster, used by ExaMon AI's discovery layer to know what to query.
- **Future inventory snapshots**, when the inventory schema lands in the persistence layer.

These are stored as native Cassandra rows in a per-cluster keyspace. The conventional layout uses the `e4_slurm` keyspace (per cluster) with a `job_info_<cluster>` table:

```sql
SELECT job_id, user, start_time, end_time, state, exit_code, n_nodes, n_cores
FROM examon_meta.e4_slurm.job_info_e4red
WHERE state IN ('FAILED', 'TIMEOUT', 'OUT_OF_MEMORY')
ORDER BY start_time DESC
LIMIT 100;
```

The structured store and the time-series store share the same Cassandra cluster — KairosDB writes to its own keyspace, and the direct-Cassandra tables live in their own keyspaces. The federation layer (Trino) connects to one Cassandra cluster and one KairosDB, and `JOIN`s across them as needed.

## The MQTT topic anatomy

Publishers ship data over MQTT. The topic shape mirrors the tag set:

```
<org>/<cluster>/<plugin>/<node>/<metric_name>
```

For the example above (`temperature.gpu` on `cn01`):

```
examon/e4red/nvml_pub/cn01/temperature.gpu
```

The bridge (`mqtt2kairosdb`) subscribes with a wildcard (`org/#` by default) and writes every received message through to KairosDB as a tagged sample. The bridge's only configuration is the wildcard prefix; adding a new metric, a new node, or a new publisher does not require touching the bridge.

The topic ordering matters because MQTT subscriptions are hierarchical. The conventional ordering puts the most stable tag first (`org`), then narrower scopes (cluster, plugin, node), with the metric name last. A subscriber that cares about one cluster subscribes to `examon/e4red/#`; one that cares about one plugin subscribes to `examon/+/+/nvml_pub/#`.

### Payload format

The payload is a JSON-encoded message carrying the value and the timestamp:

```json
{"v": 58.0, "ts": 1716480000123}
```

The base library (`examon-base-plugin`) emits this format from `MQTTPublisher`; the bridge parses it on read. Publishers can ship additional fields (per-sample tags that override the topic-derived defaults, multi-value payloads for compound metrics), but the two-key form above is the minimum.

### Topic prefix and sanitization

Two `global.examon` settings affect the topic shape:

- `topic_prefix` — a static prefix prepended to every topic. Useful when one MQTT broker carries data for multiple ExaMon deployments.
- `sanitize_topic` (default `true`) — URL-encode reserved MQTT characters (`+`, `#`, `/`) when they appear in tag values. Without this, a metric name containing a `/` would break the topic hierarchy.

## Discovery

Because the model is schema-less, consumers need a way to find out what metrics exist for a given node, cluster, or plugin. ExaMon's discovery convention has two layers:

| Layer | Mechanism |
|---|---|
| **Direct, per-cluster** | KairosDB's `/api/v1/metricnames` endpoint lists every metric the store has ever seen. Combined with `/api/v1/datapoints/query/tags` for tag values, this is enough to build a "what is published on this cluster" view. |
| **Cached, structured** | A schema registry table (`row_keys`) in Cassandra holds the mapping of metric to publisher to tag-shape. The federation layer and ExaMon AI prefer this path for performance: looking up the registry is cheaper than scanning KairosDB. |

ExaMon AI uses both in sequence: it queries the registry for a candidate set, then validates against KairosDB for freshness. The discovery layer is what lets the agent be pointed at a new deployment and start answering questions without manual schema input.

## Relationship to the legacy `examon-common` model

The data model on the wire is unchanged from the v0.4.0 era. What changed in v0.5.0 is the publisher framework that emits the data (SDK v3, see [Concepts → Plugin model](plugin-model.md)) and the federation layer that reads it (the `trino-kairosdb-connector`, which puts SQL on top of the existing KairosDB store). A v0.4.0 publisher running today still produces samples that the v0.5.0 stack ingests correctly; a v0.5.0 publisher running against a v0.4.0 store still works the same way. The model is the contract; the producers and consumers are interchangeable on top of it.

## Related reading

- [Concepts → Architecture](architecture.md) — where the data model fits inside the full stack.
- [Concepts → Plugin model](plugin-model.md) — the producer side: how SDK v3 publishers shape and ship samples.
- [Users → Analyze](../users/analyze/index.md) — the consumer side: what the model looks like through Trino SQL.
- [Reference → Configuration](../reference/configuration.md) — the parameter surface for tags, MQTT topic shape, and the bridge.

---

## Source

- KairosDB upstream documentation: [KairosDB project site](https://kairosdb.github.io/).
- Trino-KairosDB connector tag-as-column behavior: [ExamonHPC/trino-kairosdb-connector](https://github.com/ExamonHPC/trino-kairosdb-connector).
- Bridge implementation: [`deploy/docker/mqtt2kairosdb/`](https://github.com/ExamonHPC/examon/tree/release/v0.5.0/deploy/docker/mqtt2kairosdb) and the public [mqtt2kairosdb-v3 repository](https://github.com/E4-Computer-Engineering/mqtt2kairosdb-v3).
- SDK v3 publisher topic emission: [`examon.load.mqtt_loader`](https://github.com/E4-Computer-Engineering/examon-base-plugin) in the base library.
