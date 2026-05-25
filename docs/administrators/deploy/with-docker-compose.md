# With Docker Compose

!!! info "Status: Live (reproduced 2026-05-23)"
    Verified against examon-core v0.5.0. Docker Compose is a first-class deployment target alongside Kubernetes.

The Docker Compose target runs the full ExaMon core on a single host with one command. It is the right choice when Kubernetes would be operational overkill: developer loops, demos, captive single-tenant lab nodes, edge or HPC login nodes, and small deployments where lifecycle complexity is not justified.

For multi-node, HA, or cluster-managed environments, use the [Kubernetes (Helm) target](on-kubernetes.md) instead. The two paths target the same component versions and the same data model; only the orchestration shape changes.

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

The Compose stack runs Grafana 7.3.10 with the AngularJS `grafana-kairosdb-datasource` plugin. Import the Compose-compatible snapshot from `dashboards/legacy/Examon Test - Random Sensor.json`.

The dashboards directly under `dashboards/` target the Kubernetes stack instead: they use the React-based `arpnetworking-kairosdb-datasource` plugin and are not compatible with Grafana 7.x.

### Data Persistence

Two Docker volumes are created:

- `examon_cassandra_volume` -- collected metrics
- `examon_grafana_volume` -- Grafana dashboards and user data

## Optional: add Trino

The Compose stack ships an optional Trino overlay that brings a single-node Trino with the KairosDB connector wired against the same `kairosdb` service. Apply it on top of the core compose file:

```bash
docker compose -f docker-compose.yml -f compose.trino.yml up -d
```

The install walkthrough is in [Add-ons → Trino](../add-ons/trino.md); the first SQL query is in [Users → Analyze → Query with Trino](../../users/analyze/query-with-trino.md).

## Moving to Kubernetes

If a deployment outgrows the single-host shape, the [Upgrade](upgrade.md) page covers migration from a Compose stack to a Kubernetes (Helm) install.

---

## Source

- Docker Compose file: [`docker-compose.yml`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/docker-compose.yml).
- Trino overlay: [`compose.trino.yml`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/compose.trino.yml).
- Compose-compatible dashboard: [`dashboards/legacy/`](https://github.com/ExamonHPC/examon/tree/release/v0.5.0/dashboards/legacy).
