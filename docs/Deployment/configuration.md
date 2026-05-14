# Configuration Reference

All ExaMon Helm chart configuration is managed through values files. This document lists every configurable parameter.

## Global Toggles

| Parameter | Description | Default |
|-----------|-------------|---------|
| `cassandra.enabled` | Deploy Cassandra via K8ssandra | `true` |
| `kairosdb.enabled` | Deploy KairosDB | `true` |
| `grafana.enabled` | Deploy Grafana | `true` |
| `mosquitto.enabled` | Deploy Mosquitto MQTT broker | `true` |
| `mqtt2kairosdb.enabled` | Deploy MQTT-to-KairosDB bridge | `true` |
| `random-pub.enabled` | Deploy random test publisher | `true` |
| `examon-server.enabled` | Deploy ExaMon REST API server | `true` |

## Cassandra (K8ssandra)

| Parameter | Description | Default |
|-----------|-------------|---------|
| `cassandra.serverVersion` | Cassandra version | `4.0.14` |
| `cassandra.datacenters.dc1.size` | Number of Cassandra nodes | `1` |
| `cassandra.datacenters.dc1.storage` | PVC storage size per node | `10Gi` |
| `cassandra.datacenters.dc1.storageClass` | StorageClass name | `""` (default) |
| `cassandra.datacenters.dc1.heapSize` | JVM heap size | `512M` |
| `cassandra.datacenters.dc1.resources.requests.memory` | Memory request | `512Mi` |
| `cassandra.datacenters.dc1.resources.requests.cpu` | CPU request | `500m` |
| `cassandra.datacenters.dc1.resources.limits.memory` | Memory limit | `2Gi` |
| `cassandra.datacenters.dc1.resources.limits.cpu` | CPU limit | `2` |
| `cassandra.datacenters.dc1.podAntiAffinity` | Enable pod anti-affinity | `false` |
| `cassandra.datacenters.dc1.racks` | Rack definitions with zone labels | `[]` |
| `cassandra.reaper.enabled` | Enable Reaper for repairs | `false` |
| `cassandra.telemetry.prometheus.enabled` | Let K8ssandra emit a `ServiceMonitor` for Cassandra metrics. Requires the `ServiceMonitor` CRD (kube-prometheus-stack or equivalent) in the cluster. | `false` |
| `cassandra.telemetry.prometheus.commonLabels` | Labels attached to every Cassandra metric. Use to match a `ServiceMonitor` selector (e.g. `release: kube-prometheus-stack`). | `{}` |

## KairosDB

| Parameter | Description | Default |
|-----------|-------------|---------|
| `kairosdb.replicaCount` | Number of KairosDB replicas | `1` |
| `kairosdb.image.repository` | Container image repository | `examonhpc/kairosdb` |
| `kairosdb.image.tag` | Container image tag | `1.3.0` |
| `kairosdb.config.cassandraHostList` | Cassandra contact points | `examon-cassandra-dc1-service:9042` |
| `kairosdb.config.jettyPort` | KairosDB HTTP port | `8083` |
| `kairosdb.config.javaOpts` | JVM options (heap + `--add-opens` appended at runtime) | `-Xmx1g -Xms512m` |
| `kairosdb.config.cassandraAuth.secretName` | K8s Secret name for Cassandra credentials | `examon-cassandra-superuser` |
| `kairosdb.resources` | Resource requests/limits | See `values.yaml` |

## Grafana

Grafana uses the [official Grafana Helm chart](https://github.com/grafana/helm-charts/tree/main/charts/grafana). Key overrides:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `grafana.adminPassword` | Admin password | `Password` |
| `grafana.plugins` | Grafana plugins to install | See `values.yaml` |
| `grafana.datasources` | Datasource provisioning (KairosDB pre-configured with `uid: examon-kairosdb`, type `arpnetworking-kairosdb-datasource`) | See `values.yaml` |
| `grafana.sidecar.dashboards.enabled` | Auto-load dashboards from ConfigMaps labeled `grafana_dashboard` | `true` |
| `grafana.persistence.enabled` | Enable persistent storage | `false` |
| `grafana.persistence.size` | PVC size | `10Gi` |
| `grafana.ingress.enabled` | Enable ingress | `false` |

The KairosDB datasource ships as the React-based
[ArpNetworking fork](https://github.com/ArpNetworking/kairosdb-datasource)
(`arpnetworking-kairosdb-datasource`). The legacy AngularJS
`grafana-kairosdb-datasource` is not compatible with Grafana 11+ and is
not used by this chart. The plugin is installed from its GitHub release
URL and allowed via `grafana.ini.plugins.allow_loading_unsigned_plugins`.

## Mosquitto

| Parameter | Description | Default |
|-----------|-------------|---------|
| `mosquitto.replicaCount` | Number of replicas | `1` |
| `mosquitto.image.repository` | Container image | `eclipse-mosquitto` |
| `mosquitto.image.tag` | Image tag | `2` |
| `mosquitto.persistence.enabled` | Enable PVC | `false` |
| `mosquitto.persistence.size` | PVC size | `1Gi` |
| `mosquitto.tls.enabled` | Enable TLS | `false` |
| `mosquitto.tls.secretName` | TLS secret name | `""` |
| `mosquitto.service.type` | Service type | `ClusterIP` |
| `mosquitto.config.allowAnonymous` | Allow anonymous connections | `true` |

## mqtt2kairosdb

| Parameter | Description | Default |
|-----------|-------------|---------|
| `mqtt2kairosdb.replicaCount` | Number of replicas | `1` |
| `mqtt2kairosdb.config.mqtt.broker` | MQTT broker hostname | `examon-mosquitto` |
| `mqtt2kairosdb.config.mqtt.port` | MQTT port | `1883` |
| `mqtt2kairosdb.config.mqtt.topic` | MQTT topic filter | `org/#` |
| `mqtt2kairosdb.config.kairosdb.servers` | KairosDB hostname | `examon-kairosdb` |
| `mqtt2kairosdb.config.kairosdb.port` | KairosDB port | `8083` |
| `mqtt2kairosdb.config.daemon.numWorkers` | Parallel insertion workers | `4` |
| `mqtt2kairosdb.config.daemon.logLevel` | Log level | `INFO` |

## random-pub

| Parameter | Description | Default |
|-----------|-------------|---------|
| `random-pub.enabled` | Enable/disable publisher | `true` |
| `random-pub.config.mqttBroker` | MQTT broker hostname | `examon-mosquitto` |
| `random-pub.config.mqttPort` | MQTT port | `1883` |
| `random-pub.config.mqttTopic` | MQTT topic prefix | `""` |
| `random-pub.config.mqttUser` | MQTT username | `""` |
| `random-pub.config.mqttPassword` | MQTT password | `""` |
| `random-pub.config.numSensors` | Number of simulated sensors | `10` |
| `random-pub.config.sampleInterval` | Seconds between samples | `2` |

## examon-server

| Parameter | Description | Default |
|-----------|-------------|---------|
| `examon-server.replicaCount` | Number of replicas | `1` |
| `examon-server.config.authUrl` | Grafana auth URL (use port 80, not 3000) | `http://examon-grafana/api/datasources/id/kairosdb` |
| `examon-server.config.cassandraIp` | Cassandra CQL service name | `examon-cassandra-dc1-service` |
| `examon-server.config.cassandraKeySpace` | Cassandra keyspace (created by KairosDB) | `kairosdb` |
| `examon-server.config.cassandraUser` | Cassandra username (fallback if secretKeyRef not set) | `""` |
| `examon-server.config.cassandraPassword` | Cassandra password (fallback if secretKeyRef not set) | `""` |
| `examon-server.config.cassandraAuth.secretName` | K8s Secret with Cassandra creds (auto from K8ssandra) | `"examon-cassandra-superuser"` |
| `examon-server.config.cassandraAuth.usernameKey` | Key in secret for username | `"username"` |
| `examon-server.config.cassandraAuth.passwordKey` | Key in secret for password | `"password"` |
| `examon-server.config.serverHost` | API server bind address | `0.0.0.0` |
| `examon-server.config.serverPort` | API server port | `5000` |
| `examon-server.config.threadsNum` | Server threads | `8` |
| `examon-server.config.schedulerType` | HPC scheduler type | `SLURM` |
| `examon-server.config.cacheType` | Cache backend | `simple` |
| `examon-server.config.cacheTimeout` | Cache TTL (seconds) | `18000` |
