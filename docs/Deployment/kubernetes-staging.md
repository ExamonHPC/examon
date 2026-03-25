# Staging Environment (K3d Multi-Node on VM)

The staging environment runs a **full HA topology** on a single VM using K3d, mirroring production's replica counts, pod anti-affinity, NetworkPolicies, and TLS -- but with minimal resources.

## Why Staging?

Staging validates:

- **HA behavior:** 3-node Cassandra with anti-affinity across simulated zones
- **Service replication:** 2 KairosDB replicas, 2 examon-server replicas
- **Full data pipeline:** `random_pub` enabled to exercise MQTT -> KairosDB -> Cassandra
- **TLS:** Self-signed certificates via cert-manager
- **NetworkPolicies:** Same isolation rules as production

## How It Works

K3d creates multiple Kubernetes "nodes" as Docker containers inside a single VM:

```
VM (e.g. 8 CPU, 16 GB RAM, 100 GB disk)
  └── Docker
       ├── k3d-examon-staging-server-0    (K8s control plane)
       ├── k3d-examon-staging-agent-0     (worker, zone-a)
       ├── k3d-examon-staging-agent-1     (worker, zone-b)
       ├── k3d-examon-staging-agent-2     (worker, zone-c)
       ├── k3d-examon-staging-serverlb    (load balancer)
       └── examon-registry                 (local image registry)
```

Each agent has a `topology.kubernetes.io/zone` label, simulating availability zones so Cassandra pods spread correctly.

## Prerequisites

- A Linux VM with **8 CPU cores, 16 GB RAM, 100 GB disk** (recommended)
- All tools from [prerequisites](prerequisites.md) installed on the VM

## Setup

### Step 1: Create the Multi-Node Cluster

```bash
k3d cluster create --config deploy/k3d/staging-cluster.yaml
```

Verify nodes and their zone labels:

```bash
kubectl get nodes --show-labels | grep zone
```

### Step 2: Register the K3d Registry Hostname

The K3d registry runs as a Docker container named `examon-registry`. Your host
machine needs an `/etc/hosts` entry so that `docker push` can reach it by name
and the image repository names match what containerd expects inside the cluster:

```bash
# Check if the entry already exists
grep examon-registry /etc/hosts

# If not present, add it
echo "127.0.0.1 examon-registry" | sudo tee -a /etc/hosts
```

!!! note
    This only needs to be done once per machine. If you already set it up for
    local development, the same entry works for staging.

### Step 3: Build and Push Images

```bash
./scripts/build-and-push-images.sh examon-registry:5111
```

### Step 4: Install cert-manager

cert-manager is needed for K8ssandra operator webhooks and self-signed TLS certificates:

```bash
helm repo add jetstack https://charts.jetstack.io
helm install cert-manager jetstack/cert-manager \
  -n cert-manager --create-namespace \
  --set crds.enabled=true --wait
```

### Step 5: Deploy ExaMon

The umbrella chart includes K8ssandra operator and Grafana as dependencies:

```bash
helm repo add k8ssandra https://helm.k8ssandra.io/stable
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

cd deploy/helm/examon
helm dependency update
cd ../../..

kubectl create namespace examon 2>/dev/null || true
helm install examon ./deploy/helm/examon \
  -f ./deploy/helm/examon/values-staging.yaml \
  -n examon --wait --timeout 15m
```

!!! warning
    Do **not** install `k8ssandra-operator` as a separate Helm release.
    It is bundled as a dependency of the ExaMon umbrella chart.

!!! important
    After editing any subchart template, run `helm dependency update` in
    `deploy/helm/examon/` before upgrading. See the
    [local deployment guide](kubernetes-local.md) for details.

### Step 6: Configure Cassandra Authentication

K8ssandra enables Cassandra authentication by default. Both KairosDB and
examon-server read credentials automatically from the K8ssandra-generated
secret (`examon-cassandra-superuser`) via `secretKeyRef` environment
variables. No manual `--set` for Cassandra passwords is needed.

Only Grafana admin password requires a `--set` flag:

```bash
helm upgrade examon ./deploy/helm/examon \
  -f ./deploy/helm/examon/values-staging.yaml \
  --set grafana.adminPassword="<your-grafana-password>" \
  -n examon --timeout 15m
```

!!! warning
    **Never hardcode real passwords** in values files. See the
    [Secrets Management](kubernetes.md#secrets-management) guide for all
    available methods.

For more details on service names, Grafana ports, and KairosDB configuration,
see the [Important Configuration Details](kubernetes-local.md#important-configuration-details) section.

### Step 7: Validate HA

```bash
# Verify pods are spread across nodes/zones
kubectl get pods -n examon -o wide

# Check Cassandra cluster status
kubectl exec -it examon-cassandra-dc1-default-sts-0 -c cassandra -n examon \
  -- nodetool status
```

## Accessing Services

All user-facing services are exposed directly on the host via the K3d load
balancer and `NodePort` services. External clients connect to the VM's
IP/hostname — no Kubernetes knowledge required:

| Service | Address | Protocol | Users |
|---------|---------|----------|-------|
| MQTT broker | `<host>:1883` | MQTT | `examon-client`, publishers, subscribers |
| Grafana | `<host>:3000` | HTTP | Admins, dashboard users |
| ExaMon API | `<host>:5000` | HTTP | `examon-client`, data consumers |
| HTTP (Ingress) | `<host>:80` | HTTP | Requires Ingress configuration |
| HTTPS (Ingress) | `<host>:443` | HTTPS | Self-signed TLS via cert-manager |

For internal/debugging services, use `kubectl port-forward`:

```bash
kubectl port-forward svc/examon-kairosdb 8083:8083 -n examon
```

## Staging vs Production Comparison

```
                  Staging                   Production
                  ────────────────          ────────────────
Cassandra         3 nodes, 512Mi each       3 nodes, 4Gi each
                  soft anti-affinity         hard anti-affinity
KairosDB          2 replicas, 256Mi         2 replicas, 2Gi
TLS               self-signed               Let's Encrypt
Backups           disabled                  Medusa enabled
Cluster           K3d on single VM          Real K8s cluster
```

## Teardown

```bash
k3d cluster delete examon-staging
```
