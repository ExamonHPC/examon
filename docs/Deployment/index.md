# Deployment Overview

ExaMon v0.5.0 supports three deployment methods, from development to production.

## Deployment Options

| Method | Use Case | Description |
|--------|----------|-------------|
| **Kubernetes (Helm)** | Recommended | Full deployment using Helm charts with K8ssandra, Grafana, and all ExaMon components |
| **Docker Compose** | Legacy/Quick start | Single-machine deployment using Docker Compose (v0.4.0 compatible) |

## Kubernetes Environments

The Helm chart supports three environment profiles via values files:

| Environment | Target | Cassandra | KairosDB | TLS | NetworkPolicies |
|-------------|--------|-----------|----------|-----|-----------------|
| **Local** | Laptop / Desktop | 1 node | 1 replica | No | No |
| **Staging** | Single VM (K3d multi-node) | 3 nodes (soft affinity) | 2 replicas | Self-signed | Yes |
| **Production** | Real K8s cluster | 3 nodes (hard affinity) | 2 replicas | Let's Encrypt | Yes |

### Resource Requirements

```
                  Local             Staging             Production
                  ──────────        ──────────          ──────────
VM/Machine        4C / 8G / 40G    8C / 16G / 100G     Per cloud/infra
Cassandra RAM     512Mi per node   512Mi per node      4Gi per node
KairosDB RAM      256Mi            256Mi               2Gi
Total Pods        ~8               ~12                  ~12
```

## Quick Start

For local development:

```bash
./scripts/k8s-local-setup.sh
```

For detailed instructions, see the environment-specific guides:

- [Prerequisites](prerequisites.md) -- Install Docker, K3d, kubectl, Helm
- [Local Development](kubernetes-local.md) -- Get started on your laptop
- [Staging](kubernetes-staging.md) -- Multi-node HA on a single VM
- [Production](kubernetes-production.md) -- Full production deployment
- [Configuration Reference](configuration.md) -- All configurable parameters
- [Secrets Management](kubernetes.md#secrets-management) -- How to handle passwords and credentials
- [Change Propagation](change-propagation.md) -- How and what to propagate when modifying a deployment
- [Troubleshooting](troubleshooting.md) -- Debugging methodology and known issues
- [Upgrading from v0.4.0](upgrading.md) -- Migration from Docker Compose to Kubernetes
- [Docker Compose (Legacy)](docker-compose.md) -- Traditional single-machine setup
