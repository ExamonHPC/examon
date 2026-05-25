# Glossary

!!! info "Status: Live (reproduced 2026-05-23)"
    Verified against examon-core v0.5.0 and the surrounding ecosystem references.

> Terms used across the ExaMon documentation, with the definition that applies in this site. External terms (Kubernetes, Helm, Grafana, ...) are defined here in the sense ExaMon uses them, not as their upstream documentation's definitive treatment.

### ArpNetworking KairosDB datasource

The React-based KairosDB datasource plugin for Grafana, maintained by ArpNetworking. ExaMon v0.5.0 uses this plugin (type identifier `arpnetworking-kairosdb-datasource`) because the legacy AngularJS `grafana-kairosdb-datasource` plugin is no longer compatible with Grafana 11+. The plugin is installed at chart deploy time from its GitHub release URL and whitelisted as unsigned.

### Bridge

Short for the **MQTT-to-KairosDB bridge** (`mqtt2kairosdb`): the in-cluster service that subscribes to MQTT topics published by publishers and writes them into KairosDB. The reference implementation is on SDK v3 ([`mqtt2kairosdb-v3`](https://github.com/E4-Computer-Engineering/mqtt2kairosdb-v3)); the legacy v0.4.0 implementation ships inside the umbrella container.

### Cassandra

A wide-column NoSQL distributed database. ExaMon uses Apache Cassandra in two roles: as the storage backend for KairosDB (which sees Cassandra purely as bytes-in/bytes-out), and as a direct store for structured data (Slurm job accounting, schema registries). The two roles share the same Cassandra cluster but live in different keyspaces.

### Cassandra connector (Trino)

The built-in Trino connector that exposes Cassandra tables as Trino tables. ExaMon uses it to query the structured-data side of the platform (Slurm jobs, metadata) through the federation layer.

### Channel (`chnl`)

A canonical [tag](#tag) on every metric. Conventionally `data` for time-series samples, `events` or `state` for non-numeric streams. Used by consumers to filter out non-data streams without inspecting metric names.

### Cluster (`cluster` tag)

A canonical tag identifying the logical cluster the data belongs to. Distinct from the Kubernetes cluster running ExaMon itself: this tag refers to the *monitored* infrastructure (`e4red`, `marconi100`, ...).

### ConfigMap (Kubernetes)

A Kubernetes resource holding key/value configuration data, typically mounted into pods as files. ExaMon uses ConfigMaps to ship application configuration (mosquitto.conf, server.conf, random_pub.conf) and to provision Grafana dashboards (any ConfigMap labeled `grafana_dashboard=1` is auto-loaded; see [Users → Dashboards](../users/dashboards/index.md#add-a-custom-dashboard)).

### DCGM

NVIDIA Data Center GPU Manager. The vendor library for GPU telemetry on NVIDIA hardware. ExaMon publishers (`nvml_pub`) read DCGM/NVML metrics directly and emit them through the standard MQTT path.

### ETL

Extract, Transform, Load. The three-stage pipeline shape used by every SDK v3 publisher: a stage that reads from a source, a stage that reshapes into the canonical [tag-set form](../concepts/data-model.md#the-tag-hierarchy-and-sensor-identity), and a stage that writes to a target (MQTT broker, KairosDB, Cassandra, debug log). See [Concepts → Plugin model](../concepts/plugin-model.md).

### `examon-base-plugin`

The SDK v3 base library. Supplies the `ExamonApp` runtime, the worker classes, the queue model, and the lifecycle (`run` / `start` / `stop` / `restart`). Every SDK v3 publisher imports from this library; the publisher's own code is the source-specific extract/transform/load classes. Source: [E4-Computer-Engineering/examon-base-plugin](https://github.com/E4-Computer-Engineering/examon-base-plugin).

### ExaMon AI

The natural-language operations agent that turns questions into SQL-backed answers against an ExaMon deployment. Built on [HolmesGPT](#holmesgpt) for LLM reasoning and on [Trino](#trino) for data access; uses domain runbooks and custom tools to ensure query correctness. See [Users → AI](../users/ai/index.md).

### ExaMon Server (`examon-server`)

The Flask-based REST API service shipped with ExaMon core. Currently exposes legacy v0.4.0-style endpoints (`/api/...`) for `examon-client` and other historical consumers. Authenticates against Grafana for user identity.

### `examon-scheduler`

A planned (not yet shipped) fleet-rollout tool that translates an [inventory](#inventory-schema) into the set of publishers to install on each node, with the right credentials and configuration. The current substitute is Ansible plus per-node systemd units.

### ExaData

The historical name for the structured data layer (Slurm job records, metadata) in ExaMon. Currently realised as direct Cassandra tables; the name is preserved in some legacy documentation and configuration keys.

### ExamonQL

The SQL surface ExaMon exposes through the Trino federation layer. Not a separate query language: standard ANSI SQL, with the Trino dialect's extensions, with one connector-specific convention (the hidden `sampling_aggregator` column for KairosDB aggregation pushdown). See [Users → Analyze](../users/analyze/index.md) for the practical surface.

### Federation layer

Trino plus the three connectors (KairosDB, Cassandra, future Hive/Iceberg). The federation layer presents a single SQL endpoint over the three stores so consumers see one endpoint, one SQL dialect, one auth flow.

### Grafana sidecar (dashboards)

The standard Grafana sub-feature that watches the cluster for ConfigMaps carrying a configured label (`grafana_dashboard=1` in ExaMon's case) and auto-loads them into Grafana. ExaMon uses the sidecar for both the bundled test dashboard and any operator-added custom dashboards.

### Helm umbrella chart

The Helm chart that packages every ExaMon core component into a single deployable. Located at [`deploy/helm/examon/`](https://github.com/ExamonHPC/examon/tree/release/v0.5.0/deploy/helm/examon) in the core repository. Composed of an umbrella chart (`Chart.yaml`, `values.yaml`) and a set of subcharts (mosquitto, kairosdb, mqtt2kairosdb, random-pub, examon-server) plus the upstream Grafana subchart. The K8ssandra operator is intentionally outside the chart; it must be installed as a separate Helm release first.

### HolmesGPT

The open-source LLM reasoning loop ExaMon AI is built on. See [HolmesGPT/holmesgpt](https://github.com/HolmesGPT/holmesgpt). ExaMon AI supplies the tools (Python scripts), the runbooks (Markdown), and the system-prompt overlay; HolmesGPT supplies the LLM loop that ties them together.

### Inventory schema

The YAML-based schema ExaMon defines as its internal contract for what infrastructure exists. Consumers (the 3D Digital Twin, the AI agent, the future `examon-scheduler`) read the schema; external DCIM tools (Netbox, RacksDB, CSV) populate it through adapters. See [Concepts → Architecture](../concepts/architecture.md).

### IPMI

Intelligent Platform Management Interface. The out-of-band hardware management protocol exposed by BMCs (Baseboard Management Controllers) on most server hardware. ExaMon publishers (`ipmi_pub`) read BMC sensor data (temperatures, voltages, fan RPMs) and publish them as the canonical tagged time-series.

### K8ssandra (K8ssandra operator)

The Cassandra operator for Kubernetes maintained by the K8ssandra project. ExaMon installs the K8ssandra operator as a separate Helm release before the ExaMon chart (the operator's webhook must be ready before the `K8ssandraCluster` CR is submitted). The operator manages the Cassandra `StatefulSet`, the per-cluster credentials secret (`examon-cassandra-superuser`), repair scheduling, and optional Medusa backups.

### KairosDB

A schema-less time-series database that uses Cassandra as its storage backend. ExaMon uses KairosDB as the primary time-series store. The "schema-less" nature is important: a new metric name from a new publisher is implicitly created on first write, no schema migration is required.

### Keyspace (Cassandra)

A Cassandra-level namespace for tables. KairosDB writes to its own keyspace (`kairosdb` by default); ExaMon's structured-data tables (Slurm job records) live in separate per-cluster keyspaces (`e4_slurm`, ...). The federation layer queries both through the same Cassandra connector.

### MQTT

Message Queuing Telemetry Transport. The lightweight pub/sub messaging protocol ExaMon uses as the transport between publishers and the in-cluster bridge. Implemented by [Mosquitto](#mosquitto) in ExaMon's stack.

### MQTT topic

The hierarchical name under which an MQTT message is published. ExaMon's topic convention is a sequence of alternating `key/value` segments mirroring the tag hierarchy, with a mandatory `plugin/<plugin_name>/chnl/<data|cmd>` block and the metric name as the last segment, for example `org/cineca/cluster/marconi100/node/r255n18/plugin/ipmi_pub/chnl/data/p0_power`. See [Concepts → Data model → Transport](../concepts/data-model.md#transport-mqtt-topics-and-payloads).

### Mosquitto

The MQTT broker shipped in the ExaMon Helm chart. Upstream: [Eclipse Mosquitto](https://mosquitto.org/). ExaMon runs Mosquitto 2.x as a `StatefulSet` in Kubernetes; the v0.4.0 Docker Compose stack runs it inside the supervisord container.

### `mqtt2kairosdb`

The in-cluster service that subscribes to MQTT and writes through to KairosDB. The bridge between the transport layer and the time-series store. Two implementations exist: the legacy v0.4.0 implementation embedded in the umbrella container, and the SDK v3 implementation at [`mqtt2kairosdb-v3`](https://github.com/E4-Computer-Engineering/mqtt2kairosdb-v3).

### Node (`node` tag)

A canonical tag identifying the host a sample was collected from. Typically the hostname (`cn01`, `acnode04`); the publisher's `global.examon.tags.node` configuration block describes how to derive it from per-sample labels.

### NVML

NVIDIA Management Library. The C library that exposes GPU telemetry on NVIDIA hardware. ExaMon's `nvml_pub` reads NVML/DCGM metrics and publishes them as the canonical tagged time-series.

### Organization (`org` tag)

A canonical tag identifying the organization or deployment owner. Conventionally a short identifier (`examon`, `e4`, `cineca`); used to distinguish data when one MQTT broker carries traffic for multiple deployments.

### Plugin (`plugin` tag)

A canonical tag identifying the publisher that emitted the sample. Conventionally the publisher's repository name without the underscore suffix (`nvml_pub`, `ipmi_pub`, `prometheus_pub`, `pmu_pub`, `slurm_pub`).

### PMU

Performance Monitoring Unit. The CPU hardware counters exposed via Linux `perf`. ExaMon's `pmu_pub` reads PMU counters and publishes them as the canonical tagged time-series.

### Prometheus

The CNCF time-series database and monitoring system. ExaMon does not use Prometheus as a primary store; it bridges *from* Prometheus into KairosDB via the [Prometheus publisher](../administrators/publishers/prometheus-pub.md), so sites that already run Prometheus can keep using it while gaining ExaMon's long-term storage and federation.

### Publisher

A standalone process that collects data from a source and publishes it to ExaMon over MQTT (or, less commonly, writes directly to KairosDB or Cassandra). Built on SDK v3. See [Administrators → Publishers](../administrators/publishers/index.md) for the install pattern and [Reference → Component catalog](component-catalog.md#publishers-sdk-v3-framework-collectors) for the inventory.

### RAPL

Running Average Power Limit. The Intel CPU interface for reading and controlling per-package and per-DRAM power consumption. Used by the planned ExaMon power-capping component.

### `replicate_on`

The SDK v3 primitive for whole-job replication. A job replicated across N items becomes N independent pipelines, each with its own extract/transform/load triplet. See [Concepts → Plugin model → Job replication](../concepts/plugin-model.md#job-replication).

### SDK v3

The publisher framework currently in use, distributed as the `examon-base-plugin` library. Replaces the legacy `examon-common` predecessor. See [Concepts → Plugin model](../concepts/plugin-model.md) and [Developers → SDK v3](../developers/sdk-v3/index.md).

### Sidecar (Kubernetes)

A secondary container running alongside the primary container in a pod, sharing the pod's network and (optionally) storage. The [Grafana dashboard sidecar](#grafana-sidecar-dashboards) is the example most relevant to ExaMon.

### supervisord

A POSIX process manager. The v0.4.0 Docker Compose stack runs Mosquitto, the random publisher, the bridge, the API server, and the log collector as supervisord-managed processes inside a single "examon" container. The v0.5.0 Kubernetes stack decomposes these into separate pods; supervisord is not used.

### Tag

A key/value pair attached to a [time-series sample](../concepts/data-model.md#core-entities). Tags are first-class: consumers query by tag (`WHERE node = 'cn01' AND gpu = '0'`), the Trino connector lifts tags into virtual table columns, and the MQTT topic shape is derived from the canonical tag set.

### Trino

A distributed SQL query engine with a connector architecture. ExaMon uses Trino as the federation layer: one SQL endpoint that joins time-series data (from KairosDB via the custom connector), structured data (from Cassandra directly), and future cold-tier data (from S3-compatible object storage via the Hive or Iceberg connector). Upstream: [trino.io](https://trino.io/).

### `trino-kairosdb-connector`

The Trino connector that exposes KairosDB time-series data as Trino virtual tables. Custom-developed by ExaMon (no other public Trino-KairosDB connector exists). Implements tag-as-column virtual schema, time-range split parallelism, and KairosDB aggregator pushdown via a hidden `sampling_aggregator` column. Apache-2.0; current release is v3.0.0-rc1 (May 2026). Source: [ExamonHPC/trino-kairosdb-connector](https://github.com/ExamonHPC/trino-kairosdb-connector).

### Umbrella chart

See [Helm umbrella chart](#helm-umbrella-chart).

---

## Source

- ExaMon source repository: [ExamonHPC/examon](https://github.com/ExamonHPC/examon).
- Component repositories: [Component catalog](component-catalog.md).
- Upstream references: [KairosDB](https://kairosdb.github.io/), [Cassandra](https://cassandra.apache.org/), [Mosquitto](https://mosquitto.org/), [K8ssandra](https://docs.k8ssandra.io/), [Trino](https://trino.io/), [HolmesGPT](https://github.com/HolmesGPT/holmesgpt), [Eclipse Mosquitto](https://mosquitto.org/).
