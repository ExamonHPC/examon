# ExaMon Trino overlays

ExaMon does not bundle [Trino](https://trino.io/). The umbrella Helm
chart stops at the KairosDB / Cassandra storage layer; the SQL surface
described in [Users -> Analyze](../../docs/users/analyze/index.md) is
provided by a separately-installed Trino release plus the
[`trino-kairosdb-connector`](https://github.com/ExamonHPC/trino-kairosdb-connector).
Keeping Trino outside the umbrella means its lifecycle (upgrades,
scaling, auth, JVM tuning) stays with the operator, not with ExaMon.

This directory ships ExaMon's "wiring recipe": values overlays for the
upstream [`trino/trino`](https://github.com/trinodb/charts/tree/main/charts/trino)
Helm chart that wire the connector into ExaMon's storage layer and tune
the install for a known target.

## Overlays

| File | Profile | Catalogs | Status |
|---|---|---|---|
| [`values-examon-local.yaml`](values-examon-local.yaml) | Local development (K3d, 8 GB laptop) | KairosDB only | Live in v0.5.0 |
| `values-examon-staging.yaml` | Single-VM K3d HA | KairosDB + Cassandra (Slurm) | Planned, v0.5.1+ |
| `values-examon-production.yaml` | Real Kubernetes cluster | KairosDB + Cassandra (Slurm), TLS, persistent storage | Planned, v0.5.1+ |

## Usage

See [Users -> Analyze -> Local Trino Quickstart](../../docs/users/analyze/local-trino-quickstart.md)
for the operator-facing install procedure. The short form is:

```bash
helm repo add trino https://trinodb.github.io/charts
helm repo update
helm install trino trino/trino \
  --version 1.42.2 \
  -f deploy/trino/values-examon-local.yaml \
  -n examon --wait --timeout 5m
```

## Pin policy

The local overlay pins **both** the upstream chart version (`1.42.2`)
and the Trino image tag (`476`). The image tag matches the connector's
documented Trino compatibility line. Operators who want a different
combination edit the `--version` flag and `image.tag` in the overlay.
