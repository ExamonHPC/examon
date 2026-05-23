# Docker Compose Deployment (Legacy)

The Docker Compose deployment is the original v0.4.0 deployment method. It runs all services on a single machine.

!!! note
    For new deployments, the [Kubernetes deployment](kubernetes.md) is recommended. Docker Compose remains supported for quick testing and backward compatibility.

## Prerequisites

- [Docker and Docker Compose](https://docs.docker.com/engine/installation/)
- Hardware: see [Cassandra hardware recommendations](https://cassandra.apache.org/doc/latest/cassandra/managing/operating/hardware.html)

## Setup

### Clone the Repository

```bash
git clone https://github.com/ExamonHPC/examon.git
cd examon
```

### Start Services

```bash
docker compose up -d
```

This will build and start:

- **Cassandra** (port 9042)
- **KairosDB** (port 8083)
- **Grafana** (port 3000)
- **ExaMon** container with Mosquitto (port 1883), mqtt2kairosdb, random_pub

### Configure Grafana

1. Open [http://localhost:3000](http://localhost:3000)
2. Log in with the credentials set in `docker-compose.yml` (`GF_SECURITY_ADMIN_PASSWORD`)
3. Add a KairosDB data source:
   - **Type:** KairosDB
   - **Name:** kairosdb
   - **URL:** `http://kairosdb:8083`
   - **Access:** Server

### Test Dashboard

This Docker Compose stack runs Grafana 7.3.10 with the legacy AngularJS
`grafana-kairosdb-datasource` plugin. Import the v0.4.0-compatible
snapshot from `dashboards/legacy/Examon Test - Random Sensor.json`.

The dashboards directly under `dashboards/` target the Kubernetes
(v0.5.0+) stack instead: they use the React-based
`arpnetworking-kairosdb-datasource` plugin and are not compatible with
Grafana 7.x.

### Data Persistence

Two Docker volumes are created:

- `examon_cassandra_volume` -- collected metrics
- `examon_grafana_volume` -- Grafana dashboards and user data

## Migration to Kubernetes

See the [Upgrade Guide](upgrading.md) for migrating from Docker Compose to Kubernetes.
