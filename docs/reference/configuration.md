# Configuration

!!! info "Status: Live (reproduced 2026-05-23)"
    Verified against examon-core v0.5.0 ([`deploy/helm/examon/values.yaml`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/deploy/helm/examon/values.yaml)) and [`examon-base-plugin`](https://github.com/E4-Computer-Engineering/examon-base-plugin). For day-2 operational guidance on how to apply configuration changes safely (the propagation chain, what to rebuild after each kind of change), see [Administrators → Change propagation](../administrators/operations/change-propagation.md).

> This page is the parameter dictionary. It documents every configurable surface ExaMon exposes, organized by what is being configured: the Helm chart for deploying core, the SDK v3 publisher YAML for collectors, the in-cluster bridge, and the lower-level subchart defaults. Each section is alphabetized by key where useful and cites the authoritative source so a reader can verify against the running code.

## Helm chart configuration

The Helm umbrella chart is the deployment-level configuration surface. Values are layered: subchart defaults (`subcharts/<name>/values.yaml`) are overridden by the umbrella default (`values.yaml`) which is overridden by the environment overlay (`values-<env>.yaml`). The propagation rules are documented in [Change propagation](../administrators/operations/change-propagation.md).

### Global toggles

| Key | Type | Default | Description |
|---|---|---|---|
| `cassandra.enabled` | bool | `true` | Deploy Cassandra via the K8ssandra operator. Disable for clusters that bring their own Cassandra. |
| `kairosdb.enabled` | bool | `true` | Deploy the KairosDB time-series store. |
| `grafana.enabled` | bool | `true` | Deploy the Grafana dashboard. |
| `mosquitto.enabled` | bool | `true` | Deploy the Mosquitto MQTT broker. |
| `mqtt2kairosdb.enabled` | bool | `true` | Deploy the MQTT-to-KairosDB bridge. |
| `random-pub.enabled` | bool | `true` | Deploy the synthetic test publisher. Disable for production. |
| `examon-server.enabled` | bool | `true` | Deploy the Flask REST API server. |
| `bundledDashboards.enabled` | bool | `true` | Ship the chart's bundled Grafana dashboards as `grafana_dashboard=1` ConfigMaps. Disable to skip the bundled test dashboard. |
| `global.imagePullSecrets` | list | `[]` | Image pull secrets applied to all subcharts. Used for private registries. |

### Cassandra (K8ssandra)

The Cassandra subchart wraps K8ssandra's `K8ssandraCluster` custom resource. The operator itself is installed separately, before the umbrella chart; see [Administrators → On Kubernetes → K8ssandra Operator](../administrators/deploy/on-kubernetes.md#k8ssandra-operator-separate-release).

| Key | Type | Default | Description |
|---|---|---|---|
| `cassandra.serverVersion` | string | `4.0.14` | Cassandra container version. |
| `cassandra.datacenters.dc1.size` | int | `1` | Number of Cassandra nodes in DC1. Local: 1; staging/production: 3. |
| `cassandra.datacenters.dc1.storage` | string | `10Gi` | PVC storage size per node. |
| `cassandra.datacenters.dc1.storageClass` | string | `""` | StorageClass name. Empty uses the cluster default. |
| `cassandra.datacenters.dc1.heapSize` | string | `512M` | JVM heap size. |
| `cassandra.datacenters.dc1.resources.requests.{memory,cpu}` | string | `512Mi` / `500m` | Container resource requests. |
| `cassandra.datacenters.dc1.resources.limits.{memory,cpu}` | string | `2Gi` / `2` | Container resource limits. |
| `cassandra.datacenters.dc1.podAntiAffinity` | bool | `false` | Enable pod anti-affinity to spread Cassandra nodes across Kubernetes nodes. Staging uses soft, production uses hard. |
| `cassandra.datacenters.dc1.racks` | list | `[]` | Rack definitions with zone labels. Used by anti-affinity to spread across availability zones. |
| `cassandra.reaper.enabled` | bool | `false` | Enable Reaper for repair scheduling. |
| `cassandra.telemetry.prometheus.enabled` | bool | `false` | Let K8ssandra emit a `ServiceMonitor` for Cassandra metrics. Requires a `ServiceMonitor` CRD in the cluster (`kube-prometheus-stack` or equivalent). |
| `cassandra.telemetry.prometheus.commonLabels` | dict | `{}` | Labels attached to every Cassandra metric. Set to match a `ServiceMonitor` selector (e.g. `release: kube-prometheus-stack`). |

### KairosDB

| Key | Type | Default | Description |
|---|---|---|---|
| `kairosdb.replicaCount` | int | `1` | Number of KairosDB pods. Local: 1; production: 2+. |
| `kairosdb.image.repository` | string | `examonhpc/kairosdb` | Container image. |
| `kairosdb.image.tag` | string | `1.3.0` | Image tag. |
| `kairosdb.config.cassandraHostList` | string | `examon-cassandra-dc1-service:9042` | Cassandra contact point. |
| `kairosdb.config.jettyPort` | int | `8083` | KairosDB HTTP port. |
| `kairosdb.config.javaOpts` | string | `-Xmx1g -Xms512m` | JVM options. `--add-opens` flags for Java 17+ module access are added by `kairosdb-env.sh` and do not need to be set here. |
| `kairosdb.config.cassandraAuth.secretName` | string | `examon-cassandra-superuser` | Kubernetes Secret with Cassandra credentials. Auto-generated by K8ssandra. |
| `kairosdb.config.cassandraAuth.usernameKey` | string | `username` | Key in the secret holding the username. |
| `kairosdb.config.cassandraAuth.passwordKey` | string | `password` | Key in the secret holding the password. |
| `kairosdb.resources.requests.{memory,cpu}` | string | `512Mi` / `250m` | Resource requests. |
| `kairosdb.resources.limits.{memory,cpu}` | string | `2Gi` / `2` | Resource limits. |

### Grafana

The Grafana subchart is the upstream [`grafana/helm-charts/charts/grafana`](https://github.com/grafana/helm-charts/tree/main/charts/grafana) chart. ExaMon overrides:

| Key | Type | Default | Description |
|---|---|---|---|
| `grafana.adminPassword` | string | `""` (must be supplied) | Admin password. Pass at deploy time via `--set grafana.adminPassword=...`. |
| `grafana.plugins` | list | (see below) | Plugin install list. Includes the ArpNetworking KairosDB datasource installed from its GitHub release URL. |
| `grafana.env.GF_PANELS_DISABLE_SANITIZE_HTML` | string | `"true"` | Allow HTML in panel descriptions. |
| `grafana.grafana.ini.plugins.allow_loading_unsigned_plugins` | string | `arpnetworking-kairosdb-datasource` | Whitelist for unsigned plugins. |
| `grafana.sidecar.datasources.enabled` | bool | `true` | Auto-provision datasources from ConfigMaps. |
| `grafana.sidecar.dashboards.enabled` | bool | `true` | Auto-load dashboards from ConfigMaps labeled `grafana_dashboard=1`. |
| `grafana.sidecar.dashboards.label` | string | `grafana_dashboard` | Label name for dashboard ConfigMaps. |
| `grafana.sidecar.dashboards.labelValue` | string | `"1"` | Label value for dashboard ConfigMaps. |
| `grafana.sidecar.dashboards.searchNamespace` | string | `ALL` | Cluster-wide search for dashboard ConfigMaps. |
| `grafana.datasources.datasources.yaml` | yaml | (see below) | The KairosDB datasource provisioning. UID `examon-kairosdb`, type `arpnetworking-kairosdb-datasource`. |
| `grafana.persistence.enabled` | bool | `false` | Enable PVC for Grafana state. |
| `grafana.persistence.size` | string | `10Gi` | PVC size. |
| `grafana.ingress.enabled` | bool | `false` | Enable Ingress. Production-only. |

The default `grafana.plugins` list:

```yaml
grafana:
  plugins:
    - ae3e-plotly-panel
    - grafana-piechart-panel
    - yesoreyeram-infinity-datasource
    - marcusolsson-gantt-panel
    - flant-statusmap-panel
    - gapit-htmlgraphics-panel
    - https://github.com/ArpNetworking/kairosdb-datasource/releases/download/v4.0.7/kairosdb-datasource.zip;arpnetworking-kairosdb-datasource
```

The default `grafana.datasources` block:

```yaml
grafana:
  datasources:
    datasources.yaml:
      apiVersion: 1
      datasources:
        - name: kairosdb
          uid: examon-kairosdb
          type: arpnetworking-kairosdb-datasource
          access: proxy
          url: http://examon-kairosdb:8083
          isDefault: true
```

### Mosquitto (MQTT broker)

| Key | Type | Default | Description |
|---|---|---|---|
| `mosquitto.replicaCount` | int | `1` | Number of broker pods. |
| `mosquitto.image.repository` | string | `eclipse-mosquitto` | Upstream image. |
| `mosquitto.image.tag` | string | `2` | Eclipse Mosquitto major version. |
| `mosquitto.persistence.enabled` | bool | `false` | PVC for broker state. |
| `mosquitto.persistence.size` | string | `1Gi` | PVC size. |
| `mosquitto.tls.enabled` | bool | `false` | Enable TLS on the listener. |
| `mosquitto.tls.secretName` | string | `""` | Secret holding the TLS certificate. |
| `mosquitto.service.type` | string | `ClusterIP` | Service type. Production uses `LoadBalancer` (TCP L4) for external publishers. |
| `mosquitto.config.allowAnonymous` | bool | `true` | Allow unauthenticated MQTT connections. Production should set `false` and configure a password file. |

### `mqtt2kairosdb` (bridge)

The in-cluster service that subscribes to MQTT and writes through to KairosDB.

| Key | Type | Default | Description |
|---|---|---|---|
| `mqtt2kairosdb.replicaCount` | int | `1` | Number of bridge pods. |
| `mqtt2kairosdb.image.repository` | string | `examonhpc/mqtt2kairosdb` | Image. |
| `mqtt2kairosdb.image.tag` | string | `latest` | Image tag. Pin to a specific version in production. |
| `mqtt2kairosdb.config.mqtt.broker` | string | `examon-mosquitto` | MQTT broker hostname (in-cluster service name). |
| `mqtt2kairosdb.config.mqtt.port` | int | `1883` | MQTT broker port. |
| `mqtt2kairosdb.config.mqtt.topic` | string | `org/#` | MQTT topic wildcard the bridge subscribes to. |
| `mqtt2kairosdb.config.kairosdb.servers` | string | `examon-kairosdb` | KairosDB hostname. |
| `mqtt2kairosdb.config.kairosdb.port` | int | `8083` | KairosDB HTTP port. |
| `mqtt2kairosdb.config.daemon.numWorkers` | int | `4` | Number of parallel insert workers. |
| `mqtt2kairosdb.config.daemon.logLevel` | string | `INFO` | Log level. |

### `random-pub` (synthetic test publisher)

| Key | Type | Default | Description |
|---|---|---|---|
| `random-pub.replicaCount` | int | `1` | Number of publisher pods. |
| `random-pub.image.repository` | string | `examonhpc/random-pub` | Image. |
| `random-pub.image.tag` | string | `latest` | Image tag. |
| `random-pub.config.mqttBroker` | string | `examon-mosquitto` | MQTT broker hostname. |
| `random-pub.config.mqttPort` | int | `1883` | MQTT port. |
| `random-pub.config.mqttTopic` | string | `""` | Topic prefix. Empty means use the publisher's defaults. |
| `random-pub.config.mqttUser` | string | `""` | MQTT username. |
| `random-pub.config.mqttPassword` | string | `""` | MQTT password. Pass via `--set` for non-empty values. |
| `random-pub.config.numSensors` | int | `10` | Number of simulated sensors. |
| `random-pub.config.sampleInterval` | int | `1` | Seconds between samples (default `1` in `values.yaml`; some overlays use `2`). |

### `examon-server` (REST API)

| Key | Type | Default | Description |
|---|---|---|---|
| `examon-server.replicaCount` | int | `1` | Number of API server pods. Production: 2+. |
| `examon-server.image.repository` | string | `examonhpc/examon-server` | Image. |
| `examon-server.image.tag` | string | `latest` | Image tag. |
| `examon-server.config.authUrl` | string | `http://examon-grafana/api/datasources/id/kairosdb` | Grafana auth URL. Note: the Grafana service exposes port 80, not 3000. |
| `examon-server.config.cassandraIp` | string | `examon-cassandra-dc1-service` | Cassandra CQL service name. |
| `examon-server.config.cassandraKeySpace` | string | `kairosdb` | Cassandra keyspace. |
| `examon-server.config.cassandraUser` | string | `""` | Cassandra username (fallback if `secretKeyRef` is unset). |
| `examon-server.config.cassandraPassword` | string | `""` | Cassandra password (fallback). |
| `examon-server.config.cassandraAuth.secretName` | string | `examon-cassandra-superuser` | K8s Secret with Cassandra credentials. Auto-generated by K8ssandra. |
| `examon-server.config.cassandraAuth.usernameKey` | string | `username` | Key in the secret. |
| `examon-server.config.cassandraAuth.passwordKey` | string | `password` | Key in the secret. |
| `examon-server.config.serverHost` | string | `0.0.0.0` | Bind address. |
| `examon-server.config.serverPort` | int | `5000` | API port. |
| `examon-server.config.threadsNum` | int | `8` | Worker thread count. |
| `examon-server.config.schedulerType` | string | `SLURM` | HPC scheduler type for job-related endpoints. |
| `examon-server.config.cacheType` | string | `simple` | Cache backend. |
| `examon-server.config.cacheTimeout` | int | `18000` | Cache TTL in seconds. |

### Environment overlays

The chart ships three environment overlays. Each overrides a subset of the umbrella defaults; the rest is inherited.

| Overlay | Purpose | Key differences from `values.yaml` |
|---|---|---|
| [`values-local.yaml`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/deploy/helm/examon/values-local.yaml) | Laptop/desktop K3d | `imagePullPolicy: Always` for fast iteration; single-node Cassandra; no anti-affinity. |
| [`values-staging.yaml`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/deploy/helm/examon/values-staging.yaml) | Single VM K3d multi-node | 3-node Cassandra with soft anti-affinity; 2 KairosDB replicas; cert-manager self-signed TLS. |
| [`values-production.yaml`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/deploy/helm/examon/values-production.yaml) | Real Kubernetes cluster | 3-node Cassandra with hard anti-affinity and rack labels; 2 KairosDB replicas; Let's Encrypt or internal CA via cert-manager; Ingress + LoadBalancer. |

## SDK v3 publisher configuration

Every SDK v3 publisher reads a YAML configuration file at startup. The shape is the same across every publisher; only the `extract` module/class and its `params` differ per publisher.

### Top-level structure

```yaml
version: "0.5"

global:
  daemon: {...}
  mqtt: {...}
  kairosdb: {...}
  cassandra: {...}
  examon: {...}

jobs:
  - name: my_job
    replicate_on: {...}    # optional
    extract: {...}
    transform: {...}
    load: {...}
```

### `version`

| Key | Type | Default | Description |
|---|---|---|---|
| `version` | string | (required) | Configuration schema version. Use `0.5` for SDK v3 with MQTT/examon blocks. The version history is documented in the [`examon-base-plugin` README](https://github.com/E4-Computer-Engineering/examon-base-plugin). |

### `global.daemon`

| Key | Type | Default | Description |
|---|---|---|---|
| `log_filename` | string | `examon.log` | Log file path. |
| `pid_filename` | string | `examon.pid` | PID file path (daemon mode). |
| `log_level` | string | `INFO` | One of `DEBUG`, `INFO`, `WARNING`, `ERROR`. |
| `log_max_bytes` | int | `10485760` | Maximum log file size before rotation (bytes). Default 10 MiB. |
| `monitor_interval` | int | `10` | Seconds between worker health-check heartbeats. |
| `timeout` | int | `30` | Default per-worker timeout (seconds). Overridden by per-stage `params.timeout`. |
| `queue_maxsize` | int | `1000` | Maximum in-flight messages between stages. Bounds memory and provides back-pressure. |
| `restart_backoff.initial` | int | `2` | Initial backoff before first restart of a crashed worker (seconds). |
| `restart_backoff.max` | int | `60` | Maximum backoff (seconds). |
| `restart_backoff.reset_alive` | int | `30` | Reset backoff after a worker stays alive for at least this long (seconds). |

### `global.kairosdb`

Used when the load stage targets KairosDB directly (`KairosDBLoader`).

| Key | Type | Default | Description |
|---|---|---|---|
| `servers` | string | `localhost` | KairosDB hostname or IP. |
| `port` | int | `8080` | KairosDB HTTP port. (KairosDB 1.3+ commonly uses 8083; check the deployment.) |
| `username` | string | `""` | Authentication username (optional). |
| `password` | string | `""` | Authentication password (optional). |

### `global.mqtt`

Used when the load stage targets MQTT (`MQTTPublisher`) or when the extract stage subscribes (`MQTTSubscriber`).

| Key | Type | Default | Description |
|---|---|---|---|
| `broker` | string | (required) | MQTT broker hostname. |
| `port` | int | `1883` | MQTT broker port. `8883` for MQTT-over-TLS. |
| `topic` | string | (publisher-specific) | Base MQTT topic. Used by `MQTTPublisher` as the publish prefix and by `MQTTSubscriber` as the subscription topic. |
| `username` | string | `""` | Authentication username (optional). |
| `password` | string | `""` | Authentication password (optional). |

### `global.examon`

ExaMon-wide identity and topic shape.

| Key | Type | Default | Description |
|---|---|---|---|
| `topic_prefix` | string | `""` | Static prefix prepended to every generated MQTT topic. |
| `sanitize_topic` | bool | `true` | URL-encode reserved MQTT characters (`+`, `#`, `/`) in tag values to prevent topic-hierarchy breakage. |
| `tags` | dict | `{}` | Ordered tag mapping for the canonical tag set (`org`, `cluster`, `node`, `plugin`, `chnl`). The `node` tag is commonly a dynamic mapping with `key` (the source label name) and `regex` (the extraction regex). |
| `topic_cache.enabled` | bool | `false` | Enable per-worker LRU topic cache. Speeds up emission when the same topics are emitted repeatedly. |
| `topic_cache.size` | int | `1024` | LRU cache size. |

### `global.cassandra`

Used when the load stage targets Cassandra directly (`CassandraLoader`).

| Key | Type | Default | Description |
|---|---|---|---|
| `hosts` | list[string] | (required) | Cassandra contact points (format: `hostname:port`). |
| `username` | string | `""` | Authentication username. |
| `password` | string | `""` | Authentication password. |
| `keyspace` | string | (required) | Cassandra keyspace. |

### `jobs[]`

Each job is a complete ETL pipeline. Required fields: `name`, `extract`, `transform`, `load`. Optional: `replicate_on`.

#### Job-level

| Key | Type | Default | Description |
|---|---|---|---|
| `name` | string | (required) | Unique job name within the publisher. |
| `replicate_on.type` | string | `""` | Whole-job replication. One of `range`, `line`, `list`, `directory`. See [Concepts → Plugin model → Job replication](../concepts/plugin-model.md#job-replication). |
| `replicate_on.start` / `.end` / `.step` | int | `0` / `10` / `1` | For `range` type. |
| `replicate_on.target` | string | (required for `line`/`directory`) | File path (for `line`) or directory path (for `directory`). |
| `replicate_on.items` | list | (required for `list`) | Explicit list of items. |
| `replicate_on.pattern` | string | `*` | Glob pattern (for `directory`). |

#### Stage-level (`extract`, `transform`, `load`)

| Key | Type | Default | Description |
|---|---|---|---|
| `module` | string | (required) | Python module path containing the stage class. |
| `class` | string | (required) | Stage class name within the module. |
| `type` | string | per-stage default | Worker type. `loop` (interval-driven) or `stream` (input-driven). Extract default `loop`; transform and load default `stream`. |
| `interval` | int | (required for `loop`) | Interval between executions (seconds). Loop workers only. |
| `foreach.type` | string | `""` | Worker fan-out. Same four shapes as `replicate_on`: `range`, `line`, `list`, `directory`. |
| `foreach.{start,end,step,target,items,pattern}` | (per type) | (per type) | Same semantics as `replicate_on`. |
| `params.timeout` | int | `30` | Per-stage worker timeout (seconds). |
| `params.<custom>` | (any) | (any) | Stage-specific parameters passed to the worker constructor. |

#### Common per-stage `params`

A non-exhaustive list of the parameters the built-in workers expect; per-source workers (Prometheus, IPMI, NVML, ...) carry their own additional parameters documented in the publisher's repository.

| Worker | `params` keys |
|---|---|
| `KairosDBTransformer` | `metric_name` (string), `tags` (dict). |
| `NumberMultiplierTransformer` | `multiplier` (int). |
| `QueueLoader` | `target_jobs` (list of job names to fan out to). |
| `MQTTLoader` | `inherit_mqtt` (bool, default `true` — pull broker config from `global.mqtt`). |
| `CassandraLoader` | `inherit_cassandra` (bool, default `true`), `table` (string), `schema_file` (string, optional schema definition), `update_field` (string, field to update). |
| `MQTTSubscriber` | (uses `global.mqtt` via `inherit_mqtt`). |

For per-source publisher `params` (Prometheus URL, IPMI BMC host, NVML device filter, ...), see the corresponding [publisher page](../administrators/publishers/index.md#catalog-v050) or the publisher's repository README.

## SDK v3 publisher CLI

Every SDK v3 publisher inherits the same CLI from `ExamonApp.parse_args()`.

```
usage: <publisher>.py [-h] -c CONFIG [-l] [--threads] [--process-per-job] {run,start,stop,restart}

positional arguments:
  {run,start,stop,restart}    Runmode: run (foreground), start/stop/restart (daemon mode)

options:
  -h, --help                  show help and exit
  -c CONFIG, --config CONFIG  Path to configuration file
  -l, --lib-version           Show base library version
  --threads                   Run every stage as a Python thread inside the main process
  --process-per-job           One OS process per job (combined with --threads)
```

See [Concepts → Plugin model → Concurrency: three modes](../concepts/plugin-model.md#concurrency-three-modes) for the trade-offs between modes.

## What is not on this page

A few configuration surfaces that exist outside the umbrella chart and the SDK v3 publishers:

- **Trino server configuration.** ExaMon does not ship Trino in the Helm chart. The Trino server is configured per the upstream documentation; ExaMon adds the [`trino-kairosdb-connector`](https://github.com/ExamonHPC/trino-kairosdb-connector) as a plugin (drop the JAR under `<trino>/plugin/kairosdb/`, add a catalog properties file, restart). The connector's own configuration (split sizes, lookback windows, timestamp formats) is documented in the connector README.
- **ExaMon AI configuration.** The agent configuration lives at `~/.config/examon-ai/` and is created by `examon-ai init`. The full key reference is in [Users → AI → Configure](../users/ai/index.md#configure).
- **3D Digital Twin (`examon-dt-panel`) configuration.** Grafana plugin settings, driven by the inventory schema. Public release pending; settings are documented inside the plugin repository.

---

## Source

- Helm umbrella chart values: [`deploy/helm/examon/values.yaml`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/deploy/helm/examon/values.yaml).
- Per-environment overlays: [`values-local.yaml`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/deploy/helm/examon/values-local.yaml), [`values-staging.yaml`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/deploy/helm/examon/values-staging.yaml), [`values-production.yaml`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/deploy/helm/examon/values-production.yaml).
- Subchart defaults: [`deploy/helm/examon/subcharts/`](https://github.com/ExamonHPC/examon/tree/release/v0.5.0/deploy/helm/examon/subcharts).
- SDK v3 base library: [E4-Computer-Engineering/examon-base-plugin](https://github.com/E4-Computer-Engineering/examon-base-plugin) (the configuration shape is documented in the upstream README).
- Trino-KairosDB connector configuration: [ExamonHPC/trino-kairosdb-connector](https://github.com/ExamonHPC/trino-kairosdb-connector).
