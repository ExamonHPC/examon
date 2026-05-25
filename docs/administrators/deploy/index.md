# Deploy

!!! info "Status: Live (reproduced 2026-05-23)"
    Verified against examon-core v0.5.0.

> The Deploy section covers every path that brings ExaMon core up on a host: a developer laptop, a single staging VM, a multi-node Kubernetes cluster, or a legacy single-machine Docker Compose host. It is the entry point for the V1 administrator: an operator who needs to go from "nothing installed" to "ExaMon collecting and serving data" against a defined target environment.

## Pick a target

ExaMon ships two deployment shapes today. Kubernetes via Helm is the recommended target for any new installation; Docker Compose is preserved as a single-machine compatibility path from the v0.4.0 line.

| Target | Use case |
|---|---|
| **Kubernetes (Helm)** | Recommended for development, staging, and production. The same chart drives all three through environment-specific value overlays. |
| **Docker Compose** | Single-machine legacy path. Useful for quick demos and for hosts where Kubernetes is not justified. |

The architectural difference between the two is documented in [Deployment topology](topology.md).

## Kubernetes environments

The Helm chart supports three environment profiles through values files. Each profile defines the storage, replication, and TLS posture appropriate for that environment.

| Environment | Target host | Cassandra nodes | KairosDB replicas | TLS |
|---|---|---|---|---|
| **Local** | Laptop or desktop running K3d | 1 | 1 | None |
| **Staging** | Single VM with K3d multi-node | 3 (soft affinity) | 2 | Self-signed |
| **Production** | Real Kubernetes cluster | 3 (hard affinity) | 2 | Let's Encrypt |

Approximate resource requirements:

| | Local | Staging | Production |
|---|---|---|---|
| Host CPU / RAM / disk | 4C / 8G / 40G | 8C / 16G / 100G | Per cluster sizing |
| Cassandra RAM per node | 512Mi | 512Mi | 4Gi |
| KairosDB RAM per replica | 256Mi | 256Mi | 2Gi |
| Total pods | ~8 | ~12 | ~12 |

## Quick start (local)

A single script brings up the entire local-development stack on K3d in about 10 minutes:

```bash
./scripts/k8s-local-setup.sh
```

The exhaustive walkthrough is in [Local development](local-development.md). For background and tool installation, see [Prerequisites](prerequisites.md).

## In this section

The pages below cover each deployment path end to end.

### Setup

- [Prerequisites](prerequisites.md): Docker, K3d, kubectl, Helm; hardware and network requirements.
- [Deployment topology](topology.md): the concrete shape of the v0.4.0 Docker Compose stack and the v0.5.0 Kubernetes stack, side by side.

### Kubernetes

- [On Kubernetes](on-kubernetes.md): the conceptual install path, covering chart structure, value overlays, secrets, and the day-1 install sequence.
- [Local development](local-development.md): full K3d-on-laptop walkthrough, both automated and manual.
- [Staging](staging.md): multi-node HA on a single VM using K3d.
- [Harden for production](harden-for-production.md): TLS, secret handling, anti-affinity, backups, and known gaps in the production hardening posture.

### Docker Compose

- [With Docker Compose](with-docker-compose.md): the legacy single-machine path inherited from v0.4.0.

### Migration

- [Upgrade](upgrade.md): migration from v0.4.0 Docker Compose to v0.5.0 Kubernetes.

## Related sections

- For configuration parameters (Helm values, environment variables, publisher YAML), see [Reference → Configuration](../../reference/configuration.md).
- For day-2 operations once a deployment is live (configure changes, troubleshoot, propagate changes), see [Operations](../operations/index.md).
- For installing collectors on individual nodes after core is running, see [Publishers](../publishers/index.md).

---

## Source

- Helm chart: [`deploy/helm/examon/`](https://github.com/ExamonHPC/examon/tree/release/v0.5.0/deploy/helm/examon).
- Local-development bring-up script: [`scripts/k8s-local-setup.sh`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/scripts/k8s-local-setup.sh).
- Per-environment value overlays: [`deploy/helm/examon/values-local.yaml`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/deploy/helm/examon/values-local.yaml), [`values-staging.yaml`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/deploy/helm/examon/values-staging.yaml), [`values-production.yaml`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/deploy/helm/examon/values-production.yaml).
