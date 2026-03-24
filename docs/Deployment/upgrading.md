# Upgrading from v0.4.0 to v0.5.0

This guide covers migrating from the Docker Compose deployment (v0.4.0) to the Kubernetes Helm deployment (v0.5.0).

## What Changed

### Architecture

| Aspect | v0.4.0 (Docker Compose) | v0.5.0 (Kubernetes) |
|--------|------------------------|---------------------|
| Orchestration | Docker Compose | Helm on Kubernetes |
| ExaMon services | Single fat container (supervisord) | Individual pods per service |
| Cassandra | Docker container (3.0.19) | K8ssandra operator (4.0+) |
| KairosDB | Docker container (1.2.2) | Deployment (1.3.0) |
| Grafana | Docker container (7.3.10) | Helm subchart (latest) |
| Configuration | Environment variables + sed | ConfigMaps + Secrets |
| Scaling | Manual (add more containers) | `kubectl scale` / HPA |
| HA | Not supported | Built-in (anti-affinity, replicas) |

### Component Versions

| Component | v0.4.0 | v0.5.0 |
|-----------|--------|--------|
| Cassandra | 3.0.19 | 4.0.14 |
| KairosDB | 1.2.2 | 1.3.0 |
| Grafana | 7.3.10 | Latest |
| Python base | 3.12 (pypy3 for plugins) | 3.12 (CPython) |
| Java (KairosDB) | OpenJDK 8 | Eclipse Temurin 17 |

## Migration Steps

### Step 1: Back Up Data

Before migrating, back up your Cassandra data and Grafana dashboards:

```bash
# Export Cassandra data
docker exec examon-cassandra-1 nodetool snapshot

# Export Grafana dashboards
# Use Grafana API or export from the UI
```

### Step 2: Export Configuration

Note your current configuration from:

- `docker-compose.yml` -- environment variables
- `web/examon-server/example_server.conf` -- API server config
- Grafana datasources and dashboards

### Step 3: Set Up Kubernetes

Follow one of the deployment guides:

- [Local Development](kubernetes-local.md)
- [Staging](kubernetes-staging.md)
- [Production](kubernetes-production.md)

### Step 4: Restore Data

For Cassandra data migration from 3.0.19 to 4.0+, consult the [Apache Cassandra upgrade documentation](https://cassandra.apache.org/doc/latest/cassandra/operating/upgrading.html).

Re-import Grafana dashboards through the Grafana UI or API.

### Step 5: Update Publishers

External publishers need to update their MQTT broker connection to point to the Kubernetes Mosquitto service:

- **Internal (in-cluster):** `examon-mosquitto:1883`
- **External (via LoadBalancer/NodePort):** Use the service's external IP/port

## Keeping Docker Compose

The Docker Compose deployment remains functional in v0.5.0. Both deployment methods can coexist. The `docker-compose.yml` file is unchanged and continues to work as before.
