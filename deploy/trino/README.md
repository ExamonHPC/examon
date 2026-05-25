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

| File | Use case | Sets | Status |
|---|---|---|---|
| [`values-examon-local.yaml`](values-examon-local.yaml) | Fresh Trino install on a laptop (K3d, 8 GB host) | Image tag, worker count, JVM heap, query memory, connector init-container, KairosDB catalog | Live in v0.5.0 |
| [`values-examon-addon.yaml`](values-examon-addon.yaml) | Add ExaMon catalogs and the connector to an **existing** `trino/trino` Helm release | Connector init-container, KairosDB catalog only (no image, heap, workers, auth) | Live in v0.5.0 |
| `values-examon-staging.yaml` | Single-VM K3d HA | KairosDB + Cassandra (Slurm) | Planned, v0.5.1+ |
| `values-examon-production.yaml` | Real Kubernetes cluster | KairosDB + Cassandra (Slurm), TLS, persistent storage | Planned, v0.5.1+ |

## Usage

See [Users -> Analyze -> Trino Quickstart](../../docs/users/analyze/local-trino-quickstart.md)
for the operator-facing install procedure. The short forms are:

Fresh install (laptop):

```bash
helm repo add trino https://trinodb.github.io/charts
helm repo update
helm install trino trino/trino \
  --version 1.42.2 \
  -f deploy/trino/values-examon-local.yaml \
  -n examon --wait --timeout 5m
```

Add to an existing `trino/trino` release:

```bash
helm upgrade <your-release> trino/trino \
  -f <your-current-values>.yaml \
  -f deploy/trino/values-examon-addon.yaml \
  -n <your-namespace>
```

Pass your existing values file (or one exported with `helm get values <your-release> -n <your-namespace> -o yaml`) as the first `-f`, otherwise `helm upgrade` resets unset fields back to chart defaults. Edit `catalogs.examon_ts_timestamps`' `kairosdb.url` first if your Trino and ExaMon live in different namespaces.

## Pin policy

The local overlay pins **both** the upstream chart version (`1.42.2`)
and the Trino image tag (`476`). The image tag matches the connector's
documented Trino compatibility line. Operators who want a different
combination edit the `--version` flag and `image.tag` in the overlay.

The add-on overlay does not pin chart version or image tag: those stay
with the operator's own values file. Connector 3.0.0-rc1 is tested
against Trino 476; if your existing release runs a much older Trino,
rebuild the connector against the matching SPI.
