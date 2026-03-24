# Production Deployment

Production targets a real Kubernetes cluster -- cloud-managed (EKS, GKE, AKS) or on-premises (kubeadm, Rancher, k3s).

## Prerequisites

- A Kubernetes cluster (v1.24+) with at least 3 worker nodes
- `kubectl` configured to access the cluster
- Helm v3 installed
- A container registry (GHCR, ECR, GCR, or private)
- A domain name for TLS (with DNS configured)
- cert-manager installed for TLS certificate management

## Step 1: Build and Push Images

Build images and push to your production registry:

```bash
./scripts/build-and-push-images.sh ghcr.io/examonhpc
```

Update `values-production.yaml` image repositories if using a different registry.

## Step 2: Install cert-manager

```bash
helm repo add jetstack https://charts.jetstack.io
helm install cert-manager jetstack/cert-manager \
  -n cert-manager --create-namespace \
  --set crds.enabled=true --wait
```

Create a ClusterIssuer for Let's Encrypt:

```yaml
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

```bash
kubectl apply -f cluster-issuer.yaml
```

## Step 3: Install K8ssandra Operator

```bash
helm repo add k8ssandra https://helm.k8ssandra.io/stable
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

helm install k8ssandra-operator k8ssandra/k8ssandra-operator \
  -n examon --create-namespace --wait --timeout 5m
```

## Step 4: Configure Production Values

Edit `values-production.yaml` to set:

- **Grafana admin password:** Use `--set grafana.adminPassword=<secure-password>` or reference a K8s Secret
- **Domain names:** Update `grafana.ingress.hosts` with your domain
- **Cassandra storage class:** Set `cassandra.datacenters.dc1.storageClass` to your cloud's SSD class (e.g., `gp3`, `premium-rwo`)
- **Zone labels:** Set `cassandra.datacenters.dc1.racks[*].affinityLabels` to match your cluster's actual availability zones

## Step 5: Deploy

```bash
cd deploy/helm/examon
helm dependency update
cd ../../..

helm install examon ./deploy/helm/examon \
  -f ./deploy/helm/examon/values-production.yaml \
  --set grafana.adminPassword="$(openssl rand -base64 32)" \
  -n examon --create-namespace --wait --timeout 20m
```

## Step 6: Verify

```bash
# All pods running
kubectl get pods -n examon -o wide

# Cassandra cluster healthy
kubectl exec -it examon-cassandra-dc1-default-sts-0 -n examon \
  -- nodetool status

# KairosDB healthy
kubectl port-forward svc/examon-kairosdb 8083:8083 -n examon &
curl http://localhost:8083/api/v1/health/check

# Grafana accessible via ingress
curl -I https://grafana.example.com
```

## Post-Deployment

### Configure Grafana Data Source

If not auto-provisioned, add the KairosDB data source in Grafana:

- **Type:** KairosDB
- **Name:** kairosdb
- **URL:** `http://examon-kairosdb:8083`
- **Access:** Server

### Import Dashboards

Import dashboards from the `dashboards/` folder in the repository.

### Backups

Cassandra backups are handled by Medusa (part of K8ssandra). Configure backup storage (S3, GCS, Azure Blob) in the K8ssandraCluster CR.

### Monitoring

Install Prometheus and ServiceMonitors for all components to monitor the ExaMon infrastructure itself.

## Scaling

```bash
# Scale KairosDB
kubectl scale deployment examon-kairosdb --replicas=3 -n examon

# Scale examon-server
kubectl scale deployment examon-examon-server --replicas=3 -n examon
```

Cassandra scaling is managed via the K8ssandraCluster CR.
