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

### Iterative Development (Single Service)

During development, you typically modify and rebuild a single service
rather than all images. The recommended inner-loop workflow — build, push
to the local registry, restart the pod — is documented in detail in the
[Local Development Workflow](kubernetes-local.md#local-development-workflow)
section. That section also covers K3d image caching behavior, the
`pullPolicy: Always` setting, and alternatives like `k3d image import`
and unique tags.

## Helm Chart Dependencies

Before deploying, add the required Helm repositories and update chart
dependencies:

```bash
helm repo add jetstack https://charts.jetstack.io
helm repo add k8ssandra https://helm.k8ssandra.io/stable
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

cd deploy/helm/examon
helm dependency update
```

The `k8ssandra` repo is needed for installing the K8ssandra operator as a
separate release (see below). The `grafana` repo is a dependency declared
in `Chart.yaml`.

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

## K8ssandra Operator (Separate Release)

The K8ssandra operator is installed as a **separate Helm release** before
deploying the ExaMon chart. This is required because the operator's
validating webhook must be fully running before Helm submits the
`K8ssandraCluster` custom resource. Bundling both in one release causes a
race condition where the CR is rejected because the webhook endpoint is not
yet available.

```bash
helm repo add k8ssandra https://helm.k8ssandra.io/stable
helm repo update

kubectl create namespace examon
helm install k8ssandra-operator k8ssandra/k8ssandra-operator \
  -n examon --wait --timeout 5m
```

The `--wait` flag ensures the operator pods and webhook are fully ready
before returning. The setup scripts (`k8s-local-setup.sh`) handle this
automatically.

## Deploying ExaMon

### Install

With the K8ssandra operator already running:

```bash
helm install examon ./deploy/helm/examon \
  -f ./deploy/helm/examon/values-<environment>.yaml \
  -n examon --wait --timeout 10m
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

# Optionally uninstall the K8ssandra operator
helm uninstall k8ssandra-operator -n examon
```

## Cassandra Authentication

K8ssandra creates Cassandra with authentication enabled by default. A
superuser secret (`examon-cassandra-superuser`) is generated automatically
during the first deployment. You can inspect it with:

```bash
kubectl get secret examon-cassandra-superuser -n examon \
  -o jsonpath='{.data.username}' | base64 -d && echo
kubectl get secret examon-cassandra-superuser -n examon \
  -o jsonpath='{.data.password}' | base64 -d && echo
```

### Automatic credential injection

Both services that connect to Cassandra read credentials **automatically**
from this secret — no manual `--set` flags are needed:

| Service | Mechanism | Values key |
|---------|-----------|------------|
| **KairosDB** | `secretKeyRef` env vars (`CASSANDRA_USER`, `CASSANDRA_PASSWORD`) | `kairosdb.config.cassandraAuth.secretName` |
| **examon-server** | `secretKeyRef` env vars override `server.conf` at runtime | `examon-server.config.cassandraAuth.secretName` |

All environment values files (`values-local.yaml`, `values-staging.yaml`,
`values-production.yaml`) have this pre-configured:

```yaml
examon-server:
  config:
    cassandraAuth:
      secretName: "examon-cassandra-superuser"  # K8ssandra auto-generated
```

The `server.py` application checks environment variables `CASSANDRA_USER`
and `CASSANDRA_PASSWORD` first, falling back to `server.conf` values if the
env vars are not set. This means a simple `helm install` (or upgrade) is
sufficient — the pod will authenticate to Cassandra automatically on
startup once the secret exists.

!!! note "Bootstrap ordering"
    On a fresh `helm install`, `examon-server` and `kairosdb` may restart a
    few times while Cassandra initializes and the superuser secret is
    created. This is expected — Kubernetes will restart them automatically
    and they will connect once Cassandra is ready.

### Custom secret name

If you use a different secret (e.g. created by External Secrets Operator),
override the secret name and key names:

```yaml
examon-server:
  config:
    cassandraAuth:
      secretName: "my-custom-cassandra-secret"
      usernameKey: "user"       # default: "username"
      passwordKey: "pass"       # default: "password"
```

Set `secretName` to `""` to disable automatic injection and fall back to
`server.conf` values only (useful for non-K8ssandra Cassandra clusters
where you manage credentials differently).

## Secrets Management

**Never commit real passwords** to values files. Cassandra credentials are
handled automatically (see above). The remaining secret that needs to be
passed at deploy time is the **Grafana admin password**:

```bash
helm upgrade examon ./deploy/helm/examon \
  -f ./deploy/helm/examon/values-<env>.yaml \
  --set grafana.adminPassword="my-grafana-password" \
  -n examon
```

### Method 1: --set flags (recommended for local/staging)

```bash
helm upgrade examon ./deploy/helm/examon \
  -f ./deploy/helm/examon/values-local.yaml \
  --set grafana.adminPassword="my-grafana-password" \
  -n examon
```

### Method 2: Secret override file (gitignored)

Create a file named `values-<env>.secret.yaml` (e.g.
`values-local.secret.yaml`). These files are gitignored and will never
be committed:

```yaml
# values-local.secret.yaml — DO NOT COMMIT
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

| Values path | Description | Injected from |
|-------------|-------------|---------------|
| `grafana.adminPassword` | Grafana admin password | `--set` flag |
| `examon-server.config.cassandraAuth.secretName` | K8s Secret for Cassandra creds | Auto from K8ssandra |
| `kairosdb.config.cassandraAuth.secretName` | K8s Secret for Cassandra creds | Auto from K8ssandra |
| `random-pub.config.mqttPassword` | MQTT password (if auth enabled) | `--set` flag |
| `mqtt2kairosdb.config.kairosdb.password` | KairosDB password (if auth enabled) | `--set` flag |

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

## Grafana Dashboards

The chart auto-provisions a KairosDB datasource and bundles the test
dashboard `Examon Test - Random Sensor.json` (Grafana 10+/11+ compatible).
After install it appears automatically in Grafana — no manual import is
required to verify the data pipeline.

The legacy v0.4.0 version of the same dashboard, kept for users of the
docker-compose stack, lives under `dashboards/legacy/` and is **not**
loaded by the chart.

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
