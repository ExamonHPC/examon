# Kubernetes Deployment Guide

This guide covers the Helm chart structure, image building, and common operations for all environments.

## Building Container Images

ExaMon decomposes the monolithic container into individual images:

| Image | Dockerfile | Description |
|-------|-----------|-------------|
| `examon/mosquitto` | `deploy/docker/mosquitto/Dockerfile` | Eclipse Mosquitto MQTT broker |
| `examon/kairosdb` | `deploy/docker/kairosdb/Dockerfile` | KairosDB v1.3.0 on Eclipse Temurin 17 |
| `examon/mqtt2kairosdb` | `deploy/docker/mqtt2kairosdb/Dockerfile` | MQTT to KairosDB bridge |
| `examon/random-pub` | `deploy/docker/random-pub/Dockerfile` | Random test data publisher |
| `examon/examon-server` | `deploy/docker/examon-server/Dockerfile` | Flask REST API server |

### Build All Images

Use the provided script to build and push all images to a registry:

```bash
./scripts/build-and-push-images.sh <registry>
```

For local K3d development:

```bash
./scripts/build-and-push-images.sh examon-registry:5111
```

For production (GitHub Container Registry):

```bash
./scripts/build-and-push-images.sh ghcr.io/examonhpc
```

## Helm Chart Dependencies

Before deploying, update the chart dependencies:

```bash
helm repo add jetstack https://charts.jetstack.io
helm repo add k8ssandra https://helm.k8ssandra.io/stable
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

cd deploy/helm/examon
helm dependency update
```

### cert-manager Prerequisite

cert-manager **must** be installed before deploying ExaMon, as the K8ssandra
operator's cass-operator webhooks require it for TLS certificate provisioning:

```bash
helm install cert-manager jetstack/cert-manager \
  -n cert-manager --create-namespace \
  --set crds.enabled=true --wait --timeout 3m
```

### Rebuilding After Subchart Changes

The umbrella chart packages each subchart into a `.tgz` archive inside
`deploy/helm/examon/charts/`. If you edit files under `subcharts/`, you must
re-run `helm dependency update` so Helm packages the updated templates.
Without this step, Helm will continue using the stale archive and your changes
will have no effect.

## Deploying ExaMon

### Install

```bash
helm install examon ./deploy/helm/examon \
  -f ./deploy/helm/examon/values-<environment>.yaml \
  -n examon --create-namespace
```

Replace `<environment>` with `local`, `staging`, or `production`.

### Upgrade

```bash
helm upgrade examon ./deploy/helm/examon \
  -f ./deploy/helm/examon/values-<environment>.yaml \
  -n examon
```

### Uninstall

```bash
helm uninstall examon -n examon
```

## Cassandra Authentication

K8ssandra creates Cassandra with authentication enabled by default. A
superuser secret is generated automatically during the first deployment:

```bash
kubectl get secret examon-cassandra-superuser -n examon \
  -o jsonpath='{.data.username}' | base64 -d && echo
kubectl get secret examon-cassandra-superuser -n examon \
  -o jsonpath='{.data.password}' | base64 -d && echo
```

**KairosDB** reads credentials from this secret automatically via the
`cassandraAuth.secretName` setting in its subchart values (injected as
`CASSANDRA_USER` / `CASSANDRA_PASSWORD` environment variables). No
additional configuration is needed.

**examon-server** reads credentials from its `server.conf` ConfigMap.
Credentials must be passed at deploy time via `--set` — never hardcode them
in values files that are committed to git:

```bash
helm upgrade examon ./deploy/helm/examon \
  -f ./deploy/helm/examon/values-<env>.yaml \
  --set examon-server.config.cassandraPassword="$(kubectl get secret \
    examon-cassandra-superuser -n examon \
    -o jsonpath='{.data.password}' | base64 -d)" \
  -n examon
```

## Secrets Management

**Never commit real passwords** to values files. The values files checked
into git contain empty strings for all secret fields. Pass credentials at
deploy time using one of these methods:

### Method 1: --set flags (recommended for local/staging)

```bash
helm upgrade examon ./deploy/helm/examon \
  -f ./deploy/helm/examon/values-local.yaml \
  --set examon-server.config.cassandraPassword="$(kubectl get secret \
    examon-cassandra-superuser -n examon \
    -o jsonpath='{.data.password}' | base64 -d)" \
  --set grafana.adminPassword="my-grafana-password" \
  -n examon
```

### Method 2: Secret override file (gitignored)

Create a file named `values-<env>.secret.yaml` (e.g.
`values-local.secret.yaml`). These files are gitignored and will never
be committed:

```yaml
# values-local.secret.yaml — DO NOT COMMIT
examon-server:
  config:
    cassandraPassword: "actual-password-here"
grafana:
  adminPassword: "my-grafana-password"
```

Then pass both files to Helm (the last `-f` wins for duplicate keys):

```bash
helm upgrade examon ./deploy/helm/examon \
  -f ./deploy/helm/examon/values-local.yaml \
  -f ./deploy/helm/examon/values-local.secret.yaml \
  -n examon
```

### Method 3: External secrets (recommended for production)

For production, use a secrets management solution such as:

- [External Secrets Operator](https://external-secrets.io/) — syncs
  secrets from AWS Secrets Manager, Vault, GCP Secret Manager, etc.
- [Sealed Secrets](https://sealed-secrets.netlify.app/) — encrypted
  secrets that are safe to commit to git
- [SOPS](https://github.com/getsops/sops) with
  [helm-secrets](https://github.com/jkroepke/helm-secrets) — encrypts
  values files in-place

### Secret fields reference

| Values path | Description | Default |
|-------------|-------------|---------|
| `grafana.adminPassword` | Grafana admin password | `""` |
| `examon-server.config.cassandraUser` | Cassandra username | `examon-cassandra-superuser` |
| `examon-server.config.cassandraPassword` | Cassandra password | `""` |
| `random-pub.config.mqttPassword` | MQTT password (if auth enabled) | `""` |
| `mqtt2kairosdb.config.kairosdb.password` | KairosDB password (if auth enabled) | `""` |

## Private Container Registries

When pulling images from a private registry (e.g. GitHub Container Registry,
private Docker Hub, or a corporate registry), Kubernetes needs credentials to
authenticate. All ExaMon subcharts support `imagePullSecrets` at both
per-subchart and global levels.

### Step 1: Create the Pull Secret

```bash
kubectl create secret docker-registry ghcr-cred \
  --docker-server=ghcr.io \
  --docker-username=<github-user> \
  --docker-password=<personal-access-token> \
  -n examon
```

Replace `ghcr.io` with your registry server, and provide the appropriate
credentials. For GHCR, the password is a Personal Access Token (PAT) with
`read:packages` scope.

### Step 2: Reference the Secret in Values

**Option A — Global (recommended):** Set once, applies to all subcharts.

```yaml
global:
  imagePullSecrets:
    - name: ghcr-cred
```

This can be set in `values-production.yaml`, via `--set`, or in a secret
override file:

```bash
helm upgrade examon ./deploy/helm/examon \
  -f ./deploy/helm/examon/values-production.yaml \
  --set 'global.imagePullSecrets[0].name=ghcr-cred' \
  -n examon
```

**Option B — Per-subchart:** Override for a specific component only.

```yaml
kairosdb:
  imagePullSecrets:
    - name: ghcr-cred
mqtt2kairosdb:
  imagePullSecrets:
    - name: another-registry-cred
```

Per-subchart values take priority over global values (via `coalesce`). If a
subchart has its own `imagePullSecrets` set, the global value is ignored for
that subchart.

### Supported Subcharts

| Subchart | Template | Supports `imagePullSecrets` |
|----------|----------|:-:|
| `kairosdb` | `deployment.yaml` | Yes |
| `examon-server` | `deployment.yaml` | Yes |
| `mosquitto` | `statefulset.yaml` | Yes |
| `mqtt2kairosdb` | `deployment.yaml` | Yes |
| `random-pub` | `deployment.yaml` | Yes |
| `grafana` (upstream) | upstream chart | Yes (via `grafana.image.pullSecrets`) |

!!! note "Local Development"
    For local K3d with a local registry (`examon-registry:5111`), image pull
    secrets are not needed — K3d connects to the local registry without
    authentication.

## Service Name Reference

| Service | Kubernetes Service Name | Port |
|---------|------------------------|------|
| Cassandra CQL | `examon-cassandra-dc1-service` | 9042 |
| KairosDB HTTP | `examon-kairosdb` | 8083 |
| Grafana HTTP | `examon-grafana` | 80 |
| Mosquitto MQTT | `examon-mosquitto` | 1883 |
| ExaMon API | `examon-examon-server` | 5000 |

!!! note
    The Grafana Kubernetes service exposes port **80** (not 3000). When
    referencing Grafana from other services (e.g. `authUrl`), use
    `http://examon-grafana/...` without specifying a port.

## Verifying the Deployment

```bash
# Check all pods
kubectl get pods -n examon -o wide

# Check services
kubectl get svc -n examon

# Check Cassandra cluster
kubectl get k8ssandraclusters -n examon

# Check KairosDB health
kubectl port-forward svc/examon-kairosdb 8083:8083 -n examon &
curl http://localhost:8083/api/v1/health/check
```

## Accessing Services

### User-Facing Services

ExaMon exposes three services that external users and clients need to reach
directly (the same services that were accessible in Docker Compose):

| Service | Port | Protocol | Users |
|---------|------|----------|-------|
| **MQTT broker** | 1883 | MQTT | `examon-client`, publishers, subscribers |
| **Grafana** | 3000 | HTTP | Admins, dashboard users |
| **ExaMon API** | 5000 | HTTP | `examon-client`, data consumers |

### K3d Environments (Local & Staging)

In K3d deployments, these services are configured as `NodePort` and mapped
through the K3d load balancer so they are directly reachable on the host
(or VM) without `kubectl` or any Kubernetes knowledge. The k3s API server
port range is extended to `1883-32767` to allow standard ports as NodePorts.

| Service | Local | Staging |
|---------|-------|---------|
| MQTT | `<host>:1883` | `<host>:1883` |
| Grafana | `<host>:3000` | `<host>:3000` |
| ExaMon API | `<host>:5000` | `<host>:5000` |

Internal services (KairosDB, Cassandra) are only accessible via
`kubectl port-forward` for debugging.

### Production

In production, HTTP services (Grafana, ExaMon API) are exposed via an
**Ingress controller** with TLS termination and DNS, while the MQTT broker
uses a **LoadBalancer** service (TCP L4) since MQTT is not an HTTP protocol:

| Service | Method | Example address |
|---------|--------|-----------------|
| Grafana | Ingress + TLS | `https://grafana.examon.example.com` |
| ExaMon API | Ingress + TLS | `https://api.examon.example.com` |
| MQTT | LoadBalancer (TCP) | `mqtt.examon.example.com:1883` |

This works on OpenStack (with Octavia), RKE2, cloud providers, and bare
metal (with MetalLB). See the [Production guide](kubernetes-production.md)
for platform-specific details.

## Managing Plugins

In the Kubernetes deployment, plugins run as separate Deployments. To enable/disable:

```bash
# Disable random-pub
helm upgrade examon ./deploy/helm/examon \
  -f ./deploy/helm/examon/values-<env>.yaml \
  --set random-pub.enabled=false \
  -n examon

# Scale mqtt2kairosdb
kubectl scale deployment examon-mqtt2kairosdb --replicas=2 -n examon
```

## Logs

```bash
# View logs for a specific service
kubectl logs -l app.kubernetes.io/name=mqtt2kairosdb -n examon -f

# View Cassandra logs
kubectl logs -l app.kubernetes.io/name=cassandra -n examon -f

# View all ExaMon logs
kubectl logs -l app.kubernetes.io/part-of=examon -n examon -f
```
