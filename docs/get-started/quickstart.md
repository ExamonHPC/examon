# Quickstart

!!! info "Status: Live (reproduced 2026-05-23)"
    Verified against examon-core v0.5.0 using the scripts shipped in the repository.

> This page takes a reader from zero to a running ExaMon stack on a local Kubernetes cluster in about 15 minutes. By the end, Grafana is open in a browser with a live dashboard, the data pipeline is publishing simulated sensor data through MQTT into KairosDB, and the KairosDB REST API plus the Grafana KairosDB datasource are ready for ad-hoc exploration. The Trino SQL path is a separate install; Step 4 explains. The path uses K3d, so a developer laptop is sufficient.

## Before you start

A local install needs four tools and a laptop with 4 CPU cores and 8 GB RAM. If any tool is missing, the [Prerequisites](../administrators/deploy/prerequisites.md) page has one-line install snippets for each.

| Tool | Why |
|---|---|
| Docker | Runs K3d nodes and builds container images. |
| K3d | Creates a Kubernetes cluster from Docker containers. |
| kubectl | Talks to the cluster. |
| Helm | Installs the ExaMon chart. |

Clone the repository:

```bash
git clone https://github.com/ExamonHPC/examon.git
cd examon
git checkout release/v0.5.0
```

## Step 1. Bring up the stack

A single script creates the K3d cluster, builds the images, installs cert-manager and the K8ssandra operator, and deploys the ExaMon Helm chart with local-development values:

```bash
./scripts/k8s-local-setup.sh
```

The script takes about 10 minutes on a developer laptop. It is idempotent: re-running it on an existing cluster offers to recreate from scratch.

When it finishes, the script prints the user-facing endpoints:

```
=== ExaMon local deployment complete! ===

User-facing services (accessible without kubectl):
  MQTT broker:  localhost:1883
  Grafana:      http://localhost:3000  (user: admin)
  ExaMon API:   http://localhost:5000
```

## Step 2. Verify the deployment

The repository ships a smoke-test script that exercises every layer of the stack: pod readiness, the KairosDB health endpoint, Grafana accessibility and datasource provisioning, the bundled test dashboard, the ExaMon API, MQTT pub/sub, and the data pipeline.

```bash
./scripts/k8s-smoke-test.sh
```

A successful run ends with:

```
=== Results ===
All tests passed.
```

The test output also reports how many metrics have reached KairosDB from the `random_pub` simulated publisher, confirming the full pipeline is live.

## Step 3. Open Grafana

Visit [http://localhost:3000](http://localhost:3000) and log in with `admin / admin`. The "Random Sensor" dashboard is auto-provisioned and shows the live data from `random_pub` flowing through `mqtt2kairosdb` into KairosDB.

The dashboard is intentionally minimal. It exists to prove the pipeline is healthy. Real dashboards and the 3D digital twin are documented under [Users → Dashboards](../users/dashboards/index.md).

## Step 4. Query the data

The MQTT broker accepts standard `mosquitto_pub` / `mosquitto_sub` clients on `localhost:1883`:

```bash
mosquitto_sub -h localhost -p 1883 -t 'org/examon/#' -v
```

The KairosDB REST API is reachable inside the cluster on port 8083; for a quick check from the host, port-forward it:

```bash
kubectl port-forward svc/examon-kairosdb 8083:8083 -n examon
curl http://localhost:8083/api/v1/metricnames | jq '.results | length'
```

The Trino SQL path is a separately-installed component, kept outside the ExaMon chart so its lifecycle (upgrades, scaling, JVM tuning, authentication) stays independent. To add it to your local stack, follow [Users → Analyze → Local Trino Quickstart](../users/analyze/local-trino-quickstart.md), which ships a tested values overlay for the upstream Trino Helm chart and walks you through your first SQL query. See [Users → Analyze](../users/analyze/index.md) for the full SQL surface.

## Step 5. Tear down

Remove the cluster and reclaim disk:

```bash
k3d cluster delete examon-local
```

## Where next

- The path you just walked is the **local-development** profile (single-node Cassandra, no TLS, no NetworkPolicies). [Staging](../administrators/deploy/staging.md) and [Production](../administrators/deploy/harden-for-production.md) profiles harden the same chart.
- For a deeper explanation of *what* the stack is doing rather than *how* to bring it up, read [Core concepts](core-concepts.md) and then [Architecture](../concepts/architecture.md).
- The full set of administrator paths (Helm install, Docker Compose, fleet rollout, upgrade, hardening) is under [Administrators → Deploy](../administrators/deploy/index.md).

---

## Source

- Setup script: [`scripts/k8s-local-setup.sh`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/scripts/k8s-local-setup.sh)
- Smoke test: [`scripts/k8s-smoke-test.sh`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/scripts/k8s-smoke-test.sh)
- Local Helm values: [`deploy/helm/examon/values-local.yaml`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/deploy/helm/examon/values-local.yaml)
- Detailed manual walkthrough: [Administrators → Deploy → Local Development](../administrators/deploy/local-development.md).
