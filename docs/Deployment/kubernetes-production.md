# Production Deployment

Production targets a real Kubernetes cluster — on-premises (OpenStack,
RKE2, kubeadm) or cloud-managed (EKS, GKE, AKS).

## Service Exposure Architecture

ExaMon has three user-facing services that external clients need to reach
(the same services available in Docker Compose and K3d local/staging):

| Service | Protocol | Exposure method | Why |
|---------|----------|----------------|-----|
| **Grafana** | HTTP/S | Ingress + TLS | Standard web dashboard, benefits from path routing and TLS termination |
| **ExaMon API** | HTTP/S | Ingress + TLS | REST API used by `examon-client`, benefits from TLS termination |
| **MQTT broker** | MQTT (TCP) | LoadBalancer (L4) | Non-HTTP protocol, needs raw TCP passthrough |

```
                       Internet / Intranet
                              │
              ┌───────────────┼───────────────┐
              │               │               │
        ┌─────┴─────┐  ┌─────┴─────┐  ┌──────┴──────┐
        │  Ingress   │  │  Ingress   │  │ LoadBalancer │
        │ Controller │  │ Controller │  │   (TCP L4)   │
        │  :443/80   │  │  :443/80   │  │    :1883     │
        └─────┬─────┘  └─────┬─────┘  └──────┬──────┘
              │               │               │
        ┌─────┴─────┐  ┌─────┴─────┐  ┌──────┴──────┐
        │  Grafana   │  │  ExaMon   │  │  Mosquitto   │
        │  svc :80   │  │ API :5000 │  │  svc :1883   │
        └───────────┘  └───────────┘  └─────────────┘
```

Internal services (Cassandra, KairosDB, mqtt2kairosdb) remain `ClusterIP`
and are not exposed externally.

## Prerequisites

- A Kubernetes cluster (v1.24+) with at least 3 worker nodes
- `kubectl` configured to access the cluster
- Helm v3 installed
- A container registry (GHCR, ECR, or private)
- An **Ingress controller** installed in the cluster (see below)
- DNS records pointing to the Ingress controller / load balancer IPs
- cert-manager for automated TLS certificates

### Ingress Controller

An Ingress controller must be installed before deploying ExaMon. Choose one
based on your platform:

| Platform | Recommended Ingress | Install |
|----------|-------------------|---------|
| OpenStack | NGINX Ingress (+ Octavia LB) | `helm install ingress-nginx ingress-nginx/ingress-nginx -n ingress-nginx --create-namespace` |
| RKE2 | NGINX Ingress (bundled) | Enabled by default in RKE2 |
| EKS/GKE/AKS | Cloud-native or NGINX | Provider-specific |
| Bare metal | NGINX Ingress + MetalLB | NGINX + MetalLB for external IPs |

Verify the Ingress controller is running and has an external IP:

```bash
kubectl get svc -n ingress-nginx
```

## Step 1: Build and Push Images

Build images and push to your production registry:

```bash
./scripts/build-and-push-images.sh ghcr.io/examonhpc
```

Update `values-production.yaml` image repositories if using a different
registry.

If your registry is **private** (requires authentication), create an image
pull secret and enable it globally:

```bash
kubectl create secret docker-registry ghcr-cred \
  --docker-server=ghcr.io \
  --docker-username=<github-user> \
  --docker-password=<personal-access-token> \
  -n examon
```

Then set it in your values or via `--set`:

```yaml
# values-production.yaml
global:
  imagePullSecrets:
    - name: ghcr-cred
```

See the [Private Container Registries](kubernetes.md#private-container-registries)
section for per-subchart overrides and further details.

## Step 2: Install cert-manager

```bash
helm repo add jetstack https://charts.jetstack.io
helm repo update
helm install cert-manager jetstack/cert-manager \
  -n cert-manager --create-namespace \
  --set crds.enabled=true --wait
```

Create a ClusterIssuer for TLS certificates. For public-facing clusters
with Let's Encrypt:

```yaml
# cluster-issuer.yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
      - http01:
          ingress:
            class: nginx
```

For internal/on-prem clusters without public DNS, use a self-signed CA or
your organization's internal CA instead:

```yaml
# cluster-issuer-selfsigned.yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: selfsigned-issuer
spec:
  selfSigned: {}
```

```bash
kubectl apply -f cluster-issuer.yaml
```

## Step 3: Configure Production Values

Edit `values-production.yaml` before deploying. Key settings to customize:

### DNS and Ingress

Replace the example domains with your actual hostnames:

```yaml
grafana:
  ingress:
    ingressClassName: nginx          # your Ingress controller class
    hosts:
      - grafana.examon.example.com   # your Grafana domain

examon-server:
  ingress:
    ingressClassName: nginx
    hosts:
      - host: api.examon.example.com # your API domain
        paths:
          - path: /
            pathType: Prefix
```

### MQTT LoadBalancer

The Mosquitto service is exposed as a `LoadBalancer`. On OpenStack with
Octavia, Kubernetes automatically provisions a load balancer. You can
customize it via annotations:

```yaml
mosquitto:
  service:
    type: LoadBalancer
    annotations:
      # OpenStack Octavia example:
      loadbalancer.openstack.org/flavor-id: "<flavor-uuid>"
      # AWS NLB example:
      # service.beta.kubernetes.io/aws-load-balancer-type: nlb
```

After deployment, get the MQTT external IP:

```bash
kubectl get svc examon-mosquitto -n examon \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
```

### Storage

Set the storage class to match your infrastructure:

```yaml
cassandra:
  datacenters:
    dc1:
      storageClass: "cinder-ssd"  # OpenStack Cinder
      # storageClass: "longhorn"  # RKE2 with Longhorn
      # storageClass: "gp3"       # AWS EBS
```

### Availability Zones

Set rack labels to match your cluster's actual zone topology:

```yaml
cassandra:
  datacenters:
    dc1:
      racks:
        - name: rack1
          affinityLabels:
            topology.kubernetes.io/zone: "az-1"
        - name: rack2
          affinityLabels:
            topology.kubernetes.io/zone: "az-2"
        - name: rack3
          affinityLabels:
            topology.kubernetes.io/zone: "az-3"
```

### TLS Issuer

If using a self-signed CA instead of Let's Encrypt, update the annotation
in both Ingress sections:

```yaml
annotations:
  cert-manager.io/cluster-issuer: selfsigned-issuer
```

## Step 4: Install K8ssandra Operator

The K8ssandra operator must be installed as a separate Helm release before
the ExaMon chart. Its validating webhook must be fully running before Helm
submits the `K8ssandraCluster` custom resource:

```bash
helm repo add k8ssandra https://helm.k8ssandra.io/stable
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

kubectl create namespace examon 2>/dev/null || true
helm install k8ssandra-operator k8ssandra/k8ssandra-operator \
  -n examon --wait --timeout 5m
```

## Step 5: Deploy ExaMon

```bash
cd deploy/helm/examon
helm dependency update
cd ../../..

helm install examon ./deploy/helm/examon \
  -f ./deploy/helm/examon/values-production.yaml \
  --set grafana.adminPassword="$(openssl rand -base64 32)" \
  -n examon --wait --timeout 20m
```

Cassandra credentials are injected automatically — both KairosDB and
examon-server read them from the K8ssandra-generated secret
(`examon-cassandra-superuser`) via `secretKeyRef` environment variables.
No second `helm upgrade` is needed.

## Step 6: Verify

```bash
# All pods running
kubectl get pods -n examon -o wide

# Cassandra cluster healthy (3 nodes)
kubectl exec -it examon-cassandra-dc1-default-sts-0 -c cassandra -n examon \
  -- nodetool status

# KairosDB healthy
kubectl port-forward svc/examon-kairosdb 8083:8083 -n examon &
curl http://localhost:8083/api/v1/health/check
kill %1
```

### Verify user-facing services

```bash
# Grafana via Ingress
curl -I https://grafana.examon.example.com

# ExaMon API via Ingress
curl https://api.examon.example.com/

# MQTT via LoadBalancer
MQTT_IP=$(kubectl get svc examon-mosquitto -n examon \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
mosquitto_sub -h "$MQTT_IP" -p 1883 -t '#' -v -C 3
```

## Post-Deployment

### DNS Configuration

Create DNS records pointing to the services:

| Record | Type | Target |
|--------|------|--------|
| `grafana.examon.example.com` | A / CNAME | Ingress controller external IP |
| `api.examon.example.com` | A / CNAME | Ingress controller external IP |
| `mqtt.examon.example.com` | A | Mosquitto LoadBalancer IP |

### Configure Grafana Data Source

The data source is auto-provisioned via `values-production.yaml`. If you
need to add it manually:

- **Type:** KairosDB
- **Name:** kairosdb
- **URL:** `http://examon-kairosdb:8083`
- **Access:** Server

### Backups

Cassandra backups are handled by Medusa (part of K8ssandra). Configure
backup storage (S3, GCS, Azure Blob, Ceph/S3) in the K8ssandraCluster CR.

### Monitoring

Install Prometheus and ServiceMonitors for all components to monitor the
ExaMon infrastructure itself.

## Scaling

```bash
# Scale KairosDB
kubectl scale deployment examon-kairosdb --replicas=3 -n examon

# Scale examon-server
kubectl scale deployment examon-examon-server --replicas=3 -n examon
```

Cassandra scaling is managed via the K8ssandraCluster CR — update the
datacenter `size` in `values-production.yaml` and run `helm upgrade`.

## Platform-Specific Notes

### OpenStack

- **Ingress controller**: NGINX Ingress with Octavia load balancer for the
  controller's `Service` of type `LoadBalancer`
- **MQTT LoadBalancer**: Octavia provisions a TCP load balancer automatically.
  Use `loadbalancer.openstack.org/flavor-id` annotation to select an Octavia
  flavor if needed
- **Storage**: Use Cinder CSI (`cinder-ssd`, `cinder-default`) for
  Cassandra PVCs
- **Volumes**: OpenStack Cinder volumes are automatically provisioned by the
  CSI driver when a PVC is created

### RKE2

- **Ingress controller**: NGINX Ingress is bundled with RKE2 and enabled by
  default (IngressClass `nginx`)
- **MQTT LoadBalancer**: Use MetalLB or kube-vip if running on bare metal.
  On cloud VMs, the cloud provider's LB integration applies
- **Storage**: Longhorn (bundled with Rancher) or local-path provisioner for
  development; production should use a distributed storage backend
