# Core Concepts

!!! info "Status: Live (reproduced 2026-05-23)"
    Verified against examon-core v0.5.0.

> This page lists the five concepts every reader needs before going deeper into the platform. None of them require code or commands; each takes one paragraph. After this page, every other guide assumes these terms.

## 1. The data model is schema-less time series

Every measurement in ExaMon is a tuple `(metric_name, tags, value, timestamp)`. A new collector introduces new metric names and new tag combinations at run time; no migration is required, and no central registry needs to be updated. This is the single most consequential design choice in the platform: it makes it possible to bring up a new publisher on a new node type without coordinating with the database team.

A separate structured-data path handles records that are not time series, such as Slurm job accounting. The structured-data path lives in the same Cassandra cluster as the time-series store but is queried directly through SQL rather than through the time-series API.

## 2. MQTT is the transport between producers and storage

Collectors do not write to the database. They publish to an MQTT broker, and a separate bridge subscribes to MQTT topics and writes to KairosDB. This decoupling means a new consumer (a live anomaly detector, a debug subscriber, a secondary storage backend) can be added without modifying any collector. It also means transient broker outages or storage backpressure do not bring down the producers.

MQTT topic paths carry routing information directly:

```
org/<organization>/plugin/<plugin_name>/chnl/<channel>/<metric_name>
```

A subscriber filters by topic without needing a schema registry. The payload is `value;unix_timestamp`. The format is deliberately minimal so per-message overhead stays near zero on high-frequency sensor streams.

## 3. One SQL endpoint federates every store

ExaMon data lives in at least two stores: time-series data in KairosDB on Cassandra, structured data directly in Cassandra. A planned third tier moves cold historical data to an S3-compatible object store as Parquet. A user or AI agent should not need to know which store holds which data, or how to write queries in three different languages.

Trino provides one SQL endpoint over all of them. Every consumer (Grafana, Superset, Power BI, Jupyter, ExaMon AI) connects to one host, one port, one SQL dialect. The custom [`trino-kairosdb-connector`](https://github.com/ExamonHPC/trino-kairosdb-connector) is the only known Trino-KairosDB integration in the open-source ecosystem; it pushes aggregation down to KairosDB and parallelizes large time ranges across Trino workers. Cassandra has a stock Trino connector; the future cold tier uses the Hive/Iceberg connector.

The practical consequence is that the storage layer can change (KairosDB to another time-series database, a new cold tier added) without breaking a single dashboard, notebook, or AI query.

## 4. Collectors are an ETL pipeline written in YAML

A collector ("publisher") in ExaMon is a small declarative configuration on top of the SDK v3 framework. The pipeline has three stages: extract from a source, transform into ExaMon's metric format, load to a backend (MQTT, KairosDB, or another collector's input queue). Each stage runs in its own worker pool, restartable independently, with exponential-backoff retry on failure.

A publisher's Python entry point is four lines; everything else is in YAML. The framework ships built-in workers for common cases: an MQTT subscriber, a Prometheus scraper, a KairosDB batch loader, a TDengine batch loader. The two reference implementations are `prometheus_pub` (any Prometheus exporter becomes an ExaMon data source) and `mqtt2kairosdb-v3` (the MQTT-to-storage bridge that runs inside core). Adding a new source means writing one small worker class, not building a daemon from scratch.

## 5. The platform is composable, not monolithic

ExaMon is not a single deployable. Core (broker, bridge, time-series store, Cassandra, Grafana) is one component. The Trino-KairosDB connector is another. The 3D Digital Twin Grafana plugin is another. ExaMon AI is another. Each ships from its own repository with its own release cadence, and each is opt-in. How any given component plugs in is documented inside that component's own installation and configuration pages.

## Where next

- [Architecture](../concepts/architecture.md) — the long-form walk through the same stack, layer by layer.
- [Quickstart](quickstart.md) — if you have not yet brought the stack up, this is the 15-minute path.

---

## Source

- ExaMon source repository: [ExamonHPC/examon](https://github.com/ExamonHPC/examon) (release/v0.5.0).
- Trino-KairosDB connector: [ExamonHPC/trino-kairosdb-connector](https://github.com/ExamonHPC/trino-kairosdb-connector).
