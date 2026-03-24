#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
NAMESPACE="${NAMESPACE:-examon}"

echo "=== ExaMon Local K8s Setup ==="

# Check prerequisites
for cmd in docker k3d kubectl helm; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "ERROR: $cmd is not installed. Please install it first."
    exit 1
  fi
done

# Create K3d cluster
echo "==> Creating K3d cluster..."
if k3d cluster list | grep -q examon-local; then
  echo "    Cluster 'examon-local' already exists. Delete with: k3d cluster delete examon-local"
  read -p "    Delete and recreate? [y/N] " -r
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    k3d cluster delete examon-local
  else
    echo "    Using existing cluster."
  fi
fi

if ! k3d cluster list | grep -q examon-local; then
  k3d cluster create --config "${REPO_ROOT}/deploy/k3d/local-cluster.yaml"
fi

# Ensure the K3d registry hostname is resolvable from the host.
# K3d nodes know the registry as "examon-registry" (without the k3d- prefix).
# We use the same name for docker push so the stored repository name matches
# what containerd expects inside the cluster.
REGISTRY_NAME="examon-registry"
if ! grep -q "${REGISTRY_NAME}" /etc/hosts 2>/dev/null; then
  echo "==> Adding ${REGISTRY_NAME} to /etc/hosts (requires sudo)..."
  echo "127.0.0.1 ${REGISTRY_NAME}" | sudo tee -a /etc/hosts >/dev/null
fi

echo "==> Waiting for cluster to be ready..."
kubectl wait --for=condition=Ready nodes --all --timeout=120s

# Build and push images using host port 5111 (maps to registry container port 5000).
# Tag as examon-registry:5111 so the repo name matches a containerd mirror inside K3d.
echo "==> Building and pushing container images..."
"${SCRIPT_DIR}/build-and-push-images.sh" "${REGISTRY_NAME}:5111"

# Add Helm repos (needed for umbrella chart dependency resolution)
echo "==> Adding Helm repositories..."
helm repo add jetstack https://charts.jetstack.io 2>/dev/null || true
helm repo add k8ssandra https://helm.k8ssandra.io/stable 2>/dev/null || true
helm repo add grafana https://grafana.github.io/helm-charts 2>/dev/null || true
helm repo update

# Install cert-manager (required by K8ssandra's cass-operator webhooks)
echo "==> Installing cert-manager..."
if ! helm status cert-manager -n cert-manager &>/dev/null; then
  helm install cert-manager jetstack/cert-manager \
    -n cert-manager --create-namespace \
    --set crds.enabled=true --wait --timeout 3m
else
  echo "    cert-manager already installed."
fi

# Update Helm dependencies (pulls k8ssandra-operator + grafana charts)
echo "==> Updating Helm chart dependencies..."
cd "${REPO_ROOT}/deploy/helm/examon"
helm dependency update

# Deploy ExaMon (k8ssandra-operator is installed as part of the umbrella chart)
echo "==> Deploying ExaMon with local values..."
kubectl create namespace "${NAMESPACE}" 2>/dev/null || true

HELM_SET_ARGS=()
SECRET_FILE="${REPO_ROOT}/deploy/helm/examon/values-local.secret.yaml"
if [[ -f "$SECRET_FILE" ]]; then
  echo "    Using secret overrides from values-local.secret.yaml"
  HELM_SET_ARGS+=(-f "$SECRET_FILE")
fi

helm upgrade --install examon "${REPO_ROOT}/deploy/helm/examon" \
  -f "${REPO_ROOT}/deploy/helm/examon/values-local.yaml" \
  "${HELM_SET_ARGS[@]+"${HELM_SET_ARGS[@]}"}" \
  -n "${NAMESPACE}" --wait --timeout 10m

# Inject Cassandra credentials (secret is created by K8ssandra after first deploy)
if kubectl get secret examon-cassandra-superuser -n "${NAMESPACE}" &>/dev/null; then
  CASS_PASS="$(kubectl get secret examon-cassandra-superuser -n "${NAMESPACE}" \
    -o jsonpath='{.data.password}' | base64 -d)"
  echo "==> Injecting Cassandra credentials into examon-server..."
  helm upgrade examon "${REPO_ROOT}/deploy/helm/examon" \
    -f "${REPO_ROOT}/deploy/helm/examon/values-local.yaml" \
    "${HELM_SET_ARGS[@]+"${HELM_SET_ARGS[@]}"}" \
    --set examon-server.config.cassandraPassword="${CASS_PASS}" \
    -n "${NAMESPACE}" --timeout 10m
fi

echo ""
echo "=== ExaMon local deployment complete! ==="
echo ""
echo "Check pod status:  kubectl get pods -n ${NAMESPACE}"
echo "Access Grafana:    kubectl port-forward svc/examon-grafana 3000:80 -n ${NAMESPACE}"
echo "Access MQTT:       kubectl port-forward svc/examon-mosquitto 1883:1883 -n ${NAMESPACE}"
echo "Access API:        kubectl port-forward svc/examon-examon-server 5000:5000 -n ${NAMESPACE}"
