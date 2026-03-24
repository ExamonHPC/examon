# Local Development (K3d)

Set up a complete ExaMon stack on your laptop or desktop using K3d.

## Prerequisites

Ensure you have installed all [prerequisites](prerequisites.md): Docker, K3d, kubectl, and Helm.

**Hardware:** 4 CPU cores and 8 GB RAM recommended.

## Automated Setup

The fastest way to get started:

```bash
./scripts/k8s-local-setup.sh
```

This script will:

1. Create a K3d cluster with a local image registry
2. Add the registry hostname to `/etc/hosts` (if not already present)
3. Build and push all container images
4. Install cert-manager (required by K8ssandra)
5. Deploy the ExaMon umbrella chart (includes K8ssandra operator, Grafana, and all ExaMon services)

## Manual Setup

### Step 1: Create the K3d Cluster

```bash
k3d cluster create --config deploy/k3d/local-cluster.yaml
```

This creates a cluster with:

- 1 server node (control plane)
- 2 agent nodes (workers)
- A local container registry at `examon-registry:5111`
- Port mappings for HTTP (8880) and MQTT (1883)

Verify:

```bash
kubectl get nodes
```

### Step 2: Register the K3d Registry Hostname

K3d creates a local container registry as a Docker container named
`examon-registry`. K3d nodes can reach it by that name via Docker networking,
but your **host machine** cannot resolve it without an `/etc/hosts` entry.
This entry is required so that `docker push` can reach the registry, and so
the image repository names match what containerd expects inside the cluster:

```bash
# Check if the entry already exists
grep examon-registry /etc/hosts

# If not present, add it
echo "127.0.0.1 examon-registry" | sudo tee -a /etc/hosts
```

!!! note
    The automated setup script (`k8s-local-setup.sh`) performs this step
    automatically. You only need to do this once per machine — the entry
    persists across cluster recreations.

### Step 3: Build and Push Images

```bash
./scripts/build-and-push-images.sh examon-registry:5111
```

### Step 4: Install cert-manager

cert-manager is required by the K8ssandra operator (its cass-operator webhooks
depend on it for TLS certificate management):

```bash
helm repo add jetstack https://charts.jetstack.io
helm repo update

helm install cert-manager jetstack/cert-manager \
  -n cert-manager --create-namespace \
  --set crds.enabled=true --wait --timeout 3m
```

### Step 5: Deploy ExaMon

The umbrella chart includes K8ssandra operator and Grafana as dependencies.
Add their Helm repos so `helm dependency update` can fetch them:

```bash
helm repo add k8ssandra https://helm.k8ssandra.io/stable
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

cd deploy/helm/examon
helm dependency update
cd ../../..

kubectl create namespace examon 2>/dev/null || true
helm install examon ./deploy/helm/examon \
  -f ./deploy/helm/examon/values-local.yaml \
  -n examon --wait --timeout 10m
```

!!! warning
    Do **not** install `k8ssandra-operator` as a separate Helm release.
    It is bundled as a dependency of the ExaMon umbrella chart. Installing it
    separately causes webhook certificate conflicts.

!!! important
    After editing any subchart template (e.g. files under
    `deploy/helm/examon/subcharts/`), you **must** run `helm dependency update`
    in `deploy/helm/examon/` before upgrading. Without this step, Helm continues
    to use the previously packaged subchart `.tgz` and your template changes will
    not take effect.

### Step 6: Configure Cassandra Authentication

K8ssandra creates Cassandra with authentication enabled by default. After the
initial deployment, a superuser secret is automatically generated.

KairosDB reads these credentials from the K8ssandra secret automatically (via
`secretKeyRef`). No additional configuration is needed for KairosDB.

For examon-server, pass the Cassandra password at deploy time using `--set`:

```bash
helm upgrade examon ./deploy/helm/examon \
  -f ./deploy/helm/examon/values-local.yaml \
  --set examon-server.config.cassandraPassword="$(kubectl get secret \
    examon-cassandra-superuser -n examon \
    -o jsonpath='{.data.password}' | base64 -d)" \
  -n examon --timeout 10m
```

!!! warning
    **Never hardcode real passwords** in values files that are committed to
    git. The `cassandraPassword` field in `values-local.yaml` is intentionally
    empty. Always pass secrets via `--set` or use a gitignored secret override
    file (`values-local.secret.yaml`). See the
    [Secrets Management](kubernetes.md#secrets-management) guide for all
    available methods.

### Step 7: Verify

```bash
kubectl get pods -n examon -o wide
```

All pods should reach `Running` / `Ready` status. Key things to confirm:

- **examon-cassandra-dc1-default-sts-0**: `2/2 Running` (cassandra + server-system-logger)
- **examon-kairosdb**: `1/1 Running` (connected to Cassandra)
- **examon-mosquitto-0**: `1/1 Running`
- **examon-examon-server**: `1/1 Running` (`Serving on http://0.0.0.0:5000`)
- **examon-random-pub**: `1/1 Running` (publishing test data)
- **examon-mqtt2kairosdb**: `1/1 Running` (bridging MQTT to KairosDB)

## Accessing Services

```bash
# Grafana (default password: admin)
kubectl port-forward svc/examon-grafana 3000:80 -n examon

# MQTT broker
kubectl port-forward svc/examon-mosquitto 1883:1883 -n examon

# ExaMon API
kubectl port-forward svc/examon-examon-server 5000:5000 -n examon
```

## Important Configuration Details

### Cassandra Service Name

K8ssandra creates Cassandra services with a naming pattern based on the
K8ssandraCluster resource name and datacenter name. With the default ExaMon
chart configuration, the CQL service is:

```
examon-cassandra-dc1-service    (port 9042)
```

Both KairosDB and examon-server must reference this exact service name.
The umbrella chart defaults already set this correctly. If you rename the
Cassandra cluster, update the service references accordingly.

### Grafana Service Port

The Grafana Helm chart exposes port **80** on the Kubernetes service (which
proxies to the Grafana container's port 3000). When configuring
`examon-server.config.authUrl`, use port 80 (or omit the port entirely):

```yaml
examon-server:
  config:
    authUrl: "http://examon-grafana/api/datasources/id/kairosdb"
```

### KairosDB Configuration

KairosDB 1.3.0 loads two configuration files:

1. **`kairosdb.properties`** — legacy Java properties format
2. **`kairosdb.conf`** — HOCON format (takes precedence)

The `config-kairos.sh` entrypoint script patches both files at startup using
environment variables (`CASSANDRA_HOST_LIST`, `CASSANDRA_USER`,
`CASSANDRA_PASSWORD`, `KAIROS_JETTY_PORT`). The kairosdb Docker image also
includes JVM `--add-opens` flags required for KairosDB's Guice/cglib dependency
to work on Java 17+.

### Python Services Configuration (ExamonApp Framework)

`random_pub`, `mqtt2kairosdb`, and `examon-server` are Python applications
built on the `ExamonApp` framework from the `examon-common` library. They
expect their configuration in `.conf` files (INI format) mounted in the
working directory:

- `random_pub.conf` — mounted from ConfigMap via Helm
- `mqtt2kairosdb.conf` — mounted from ConfigMap via Helm
- `server.conf` — mounted from ConfigMap via Helm

These are generated from the Helm `values.yaml` settings by each subchart's
`configmap.yaml` template.

## Local Development Workflow

### Rebuilding a Single Image

When you change code for a service (e.g., examon-server):

```bash
docker build -t examon-registry:5111/examon/examon-server:latest \
  -f deploy/docker/examon-server/Dockerfile .
docker push examon-registry:5111/examon/examon-server:latest

# Restart the deployment to pick up the new image
kubectl rollout restart deployment/examon-examon-server -n examon
```

!!! tip
    If you use `imagePullPolicy: IfNotPresent` (the default) and push a new
    image with the **same tag**, K3d nodes will keep the cached version. Either
    use a new tag, or use `imagePullPolicy: Always` in the values file. An
    alternative is to force-delete the pod so the new ReplicaSet pulls the
    updated image.

### Rebuilding After Subchart Template Changes

When you modify files under `deploy/helm/examon/subcharts/`, you must rebuild
the Helm dependencies before upgrading:

```bash
cd deploy/helm/examon
helm dependency update
cd ../../..

helm upgrade examon ./deploy/helm/examon \
  -f ./deploy/helm/examon/values-local.yaml \
  -n examon --timeout 10m
```

### Teardown

```bash
k3d cluster delete examon-local
```
