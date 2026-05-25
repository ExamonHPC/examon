# Harden for production

!!! info "Status: Live (reproduced 2026-05-23)"
    Verified against examon-core v0.5.0.

Production targets a real Kubernetes cluster: on-premises (OpenStack,
RKE2, kubeadm) or cloud-managed (EKS, GKE, AKS). This page covers the
hardening posture (TLS, secrets, anti-affinity, backups, monitoring)
that separates a production install from the local-development
bring-up, plus the gaps to be aware of in v0.5.0.

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

## Step 1: Create the namespace

All ExaMon resources install into a dedicated namespace. Create it
before anything else so subsequent steps (pull secrets, cert-manager
issuers, the Helm release itself) have a namespace to target:

```bash
kubectl create namespace examon
```

## Step 2: Build and Push Images

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

See the [Private Container Registries](on-kubernetes.md#private-container-registries)
section for per-subchart overrides and further details.

## Step 3: Install cert-manager

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

## Step 4: Configure Production Values

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

### MQTT TLS

To enable TLS on the MQTT broker, set `mqtt.tls.enabled=true` in
`values-production.yaml` and provide a Kubernetes TLS secret named
`mosquitto-tls` containing the broker certificate and key. The secret
must live in the `examon` namespace and use the standard `tls.crt` /
`tls.key` / `ca.crt` keys.

There are two common ways to create the secret.

**Option A: cert-manager Certificate (recommended).** Reuse the
ClusterIssuer created in Step 3 to mint the broker certificate
automatically. The DNS name should match the LoadBalancer hostname you
plan to advertise to publishers:

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: mosquitto-tls
  namespace: examon
spec:
  secretName: mosquitto-tls
  issuerRef:
    name: letsencrypt-prod        # or selfsigned-issuer
    kind: ClusterIssuer
  commonName: mqtt.examon.example.com
  dnsNames:
    - mqtt.examon.example.com
  duration: 2160h                  # 90 days
  renewBefore: 360h                # 15 days
```

```bash
kubectl apply -f mosquitto-tls-cert.yaml
```

cert-manager populates the `mosquitto-tls` Secret with the issued
certificate and rotates it automatically before expiry.

**Option B: manual secret.** If you already have a certificate (for
example, issued by an internal CA outside the cluster), create the
secret directly:

```bash
kubectl create secret tls mosquitto-tls \
  --cert=path/to/mqtt.crt \
  --key=path/to/mqtt.key \
  -n examon
# Add the CA bundle so MQTT clients can verify the chain:
kubectl create secret generic mosquitto-tls-ca \
  --from-file=ca.crt=path/to/ca.crt \
  -n examon
```

Then enable TLS in your values:

```yaml
mqtt:
  tls:
    enabled: true
    secretName: mosquitto-tls
```

!!! warning "v0.5.0 caveat: plaintext listener stays open"
    In v0.5.0, enabling MQTT TLS adds port 8883 alongside the existing
    plaintext listener on 1883 rather than replacing it. Operators who
    require TLS-only must restrict 1883 at the LoadBalancer service or
    NetworkPolicy layer. See [Known gaps in v0.5.0](#known-gaps-in-v050)
    for the workaround and tracking issue.

## Step 5: Install K8ssandra Operator

The K8ssandra operator must be installed as a separate Helm release before
the ExaMon chart. Its validating webhook must be fully running before Helm
submits the `K8ssandraCluster` custom resource:

```bash
helm repo add k8ssandra https://helm.k8ssandra.io/stable
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

helm install k8ssandra-operator k8ssandra/k8ssandra-operator \
  -n examon --wait --timeout 5m
```

The `examon` namespace was created in Step 1.

## Step 6: Deploy ExaMon

```bash
cd deploy/helm/examon
helm dependency update
cd ../../..

helm install examon ./deploy/helm/examon \
  -f ./deploy/helm/examon/values-production.yaml \
  --set grafana.adminPassword="$(openssl rand -base64 32)" \
  -n examon --wait --timeout 20m
```

Cassandra credentials are injected automatically. Both KairosDB and
examon-server read them from the K8ssandra-generated secret
(`examon-cassandra-superuser`) via `secretKeyRef` environment variables.
No second `helm upgrade` is needed.

## Step 7: Verify

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

# Plaintext listener (always exposed in v0.5.0; see Known gaps)
mosquitto_sub -h "$MQTT_IP" -p 1883 -t '#' -v -C 3

# TLS listener (only if mqtt.tls.enabled=true)
kubectl get secret mosquitto-tls -n examon \
  -o jsonpath='{.data.ca\.crt}' | base64 -d > /tmp/ca.crt
mosquitto_sub -h "$MQTT_IP" -p 8883 --cafile /tmp/ca.crt -t '#' -v -C 3
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

The KairosDB data source is **fully auto-provisioned** by the chart on
every deploy; no manual setup is required. The umbrella chart:

1. Installs the React-based [ArpNetworking
   KairosDB data source plugin](https://github.com/ArpNetworking/kairosdb-datasource)
   from its GitHub release URL via `grafana.plugins`.
2. Whitelists the unsigned plugin via
   `grafana.grafana.ini.plugins.allow_loading_unsigned_plugins`.
3. Provisions the data source as `type: arpnetworking-kairosdb-datasource`
   with `uid: examon-kairosdb`, pointing at `http://examon-kairosdb:8083`
   in `accesss: proxy` mode.
4. Auto-loads the bundled "Examon Test - Random Sensor" dashboard via the
   Grafana dashboard sidecar (ConfigMaps labeled `grafana_dashboard=1`).

After `helm upgrade`, open Grafana and you should already see the data
source listed (test connection returns OK) and the dashboard available
under Dashboards. The legacy `grafana-kairosdb-datasource` plugin is
AngularJS-only and is **not** compatible with Grafana 11+; do not
provision it manually.

The relevant Helm values are documented in
[Reference → Configuration](../../reference/configuration.md): `grafana.plugins`,
`grafana.datasources`, `grafana.sidecar.dashboards.enabled`, and the
top-level `bundledDashboards.enabled` toggle.

### Backups

Cassandra backup and restore is handled by [Medusa](https://github.com/k8ssandra/medusa)
(part of K8ssandra). **In v0.5.0 the umbrella chart does not configure
Medusa in the `K8ssandraCluster` template**, so backups are not enabled
out of the box. Operators who need automated backups must patch the CR
after `helm install`.

Create a Kubernetes Secret in the `examon` namespace containing the
credentials for your backup storage backend. For S3-compatible storage
the secret keys are typically `credentials` (an INI-style file with
`aws_access_key_id` / `aws_secret_access_key`):

```bash
kubectl create secret generic medusa-bucket-key \
  --from-file=credentials=path/to/credentials \
  -n examon
```

Then patch the `K8ssandraCluster` resource to add a `spec.medusa` block:

```yaml
apiVersion: k8ssandra.io/v1alpha1
kind: K8ssandraCluster
metadata:
  name: examon-cassandra
  namespace: examon
spec:
  medusa:
    storageProperties:
      storageProvider: s3_compatible
      bucketName: examon-cassandra-backups
      host: s3.example.com
      port: 443
      secure: true
      prefix: examon
      storageSecretRef:
        name: medusa-bucket-key
```

```bash
kubectl patch k8ssandracluster examon-cassandra -n examon \
  --type merge --patch-file medusa-patch.yaml
```

K8ssandra schedules backups via the `MedusaBackupSchedule` custom
resource; see the [Medusa documentation](https://docs.k8ssandra.io/tasks/backup-restore/)
for the schedule resource definition and restore procedure.

!!! note "v0.5.0 caveat: Medusa not wired in the chart"
    The post-install patch above is the documented workaround until the
    chart's `K8ssandraCluster` template gains a `spec.medusa` block. See
    [Known gaps in v0.5.0](#known-gaps-in-v050) for the tracking issue.

### Monitoring

Production deployments should run a cluster-side Prometheus operator
(typically [`kube-prometheus-stack`](https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack))
both to monitor ExaMon itself and to scrape Cassandra.

**Cassandra metrics (K8ssandra-native):** the umbrella chart exposes
`cassandra.telemetry.prometheus.*`, which is wired straight into the
K8ssandra `CassandraDatacenter` CR. When enabled, K8ssandra creates a
`ServiceMonitor` for the Cassandra metric endpoint, with no extra manifest
to maintain. Requires the `ServiceMonitor` CRD (shipped by
`kube-prometheus-stack`):

```yaml
# values-production.yaml
cassandra:
  telemetry:
    prometheus:
      enabled: true
      commonLabels:
        # Match the kube-prometheus-stack default ServiceMonitor selector
        release: kube-prometheus-stack
```

Or via `--set` at deploy time:

```bash
helm upgrade examon ./deploy/helm/examon \
  -f ./deploy/helm/examon/values-production.yaml \
  --set cassandra.telemetry.prometheus.enabled=true \
  --set cassandra.telemetry.prometheus.commonLabels.release=kube-prometheus-stack \
  -n examon
```

If your Prometheus operator uses a different `ServiceMonitor` selector,
adjust `commonLabels` accordingly. See
[Reference → Configuration](../../reference/configuration.md) for the full key reference.

**Other ExaMon components** (KairosDB, examon-server, mqtt2kairosdb,
Mosquitto) do not yet ship their own `ServiceMonitor` manifests; if you
need them, define your own pointing at the existing Services for now.

## Scaling

```bash
# Scale KairosDB
kubectl scale deployment examon-kairosdb --replicas=3 -n examon

# Scale examon-server
kubectl scale deployment examon-examon-server --replicas=3 -n examon
```

Cassandra scaling is managed via the K8ssandraCluster CR: update the
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

## Known gaps in v0.5.0

A small number of production-hardening features are documented as
manual workarounds in this page because they are not yet wired into
the umbrella chart. Each item below is tracked as a GitHub issue;
this section will shrink as those issues close.

**MQTT plaintext listener stays open when TLS is enabled.** Setting
`mqtt.tls.enabled=true` adds an 8883 listener but does not remove the
1883 listener. Operators who require TLS-only must restrict 1883 at
the LoadBalancer service or at a NetworkPolicy applied externally.
Tracked in a follow-up issue (link added before promotion).

**NetworkPolicies are not shipped in the chart.** The umbrella chart
does not currently include `NetworkPolicy` resources for inter-service
isolation. Operators who need pod-to-pod isolation must author and
apply their own `NetworkPolicy` manifests against the rendered
Service labels (`app.kubernetes.io/name=mosquitto`, `=kairosdb`,
`=examon-server`, `=cassandra`, and so on). Tracked in a follow-up
issue (link added before promotion).

**Medusa backups are not configured by the chart.** The
`K8ssandraCluster` template does not include a `spec.medusa` block.
Automated Cassandra backups require the post-install patch shown in
the [Backups](#backups) subsection above. Tracked in a follow-up
issue (link added before promotion).

---

## Source

- Production values overlay: [`deploy/helm/examon/values-production.yaml`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/deploy/helm/examon/values-production.yaml).
- Helm umbrella chart: [`deploy/helm/examon/`](https://github.com/ExamonHPC/examon/tree/release/v0.5.0/deploy/helm/examon).
- Upstream: [cert-manager](https://cert-manager.io/), [NGINX Ingress](https://kubernetes.github.io/ingress-nginx/), [K8ssandra operator](https://docs.k8ssandra.io/), [ArpNetworking KairosDB plugin](https://github.com/ArpNetworking/kairosdb-datasource), [kube-prometheus-stack](https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack).
