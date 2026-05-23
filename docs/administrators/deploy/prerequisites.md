# Prerequisites

All Kubernetes deployment environments (local, staging, production) require the following tools.

## Required Tools

### Docker

Docker is required for building container images and running K3d clusters.

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

Log out and back in for the group change to take effect.

### K3d

K3d creates lightweight Kubernetes clusters using Docker containers as nodes.

```bash
curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash
```

Verify:

```bash
k3d version
```

### kubectl

The Kubernetes command-line tool.

```bash
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/
```

Verify:

```bash
kubectl version --client
```

### Helm

The Kubernetes package manager, used to deploy the ExaMon chart.

```bash
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

Verify:

```bash
helm version
```

## Hardware Requirements

| Environment | CPU | RAM | Disk |
|-------------|-----|-----|------|
| Local | 2 cores (min), 4 cores (rec) | 4 GB (min), 8 GB (rec) | 20 GB (min), 40 GB (rec) |
| Staging | 4 cores (min), 8 cores (rec) | 8 GB (min), 16 GB (rec) | 50 GB (min), 100 GB (rec) |
| Production | Per cloud provider / infrastructure requirements | | |

## Network Requirements

The following ports are used by ExaMon:

| Port | Service | Protocol |
|------|---------|----------|
| 1883 | Mosquitto MQTT | TCP |
| 3000 | Grafana | HTTP |
| 5000 | ExaMon REST API | HTTP |
| 8083 | KairosDB API | HTTP |
| 9042 | Cassandra CQL | TCP |
