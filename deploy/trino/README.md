# ExaMon Trino wiring overlay

ExaMon does not bundle [Trino](https://trino.io/). The umbrella Helm
chart stops at the KairosDB / Cassandra storage layer; the SQL surface
is provided by a separately-installed Trino release plus the
[`trino-kairosdb-connector`](https://github.com/ExamonHPC/trino-kairosdb-connector).
Keeping Trino outside the umbrella means its lifecycle (upgrades,
scaling, auth, JVM tuning) stays with the operator, not with ExaMon.

This directory ships one file: ExaMon's "wiring recipe" for the
upstream [`trino/trino`](https://github.com/trinodb/charts/tree/main/charts/trino)
Helm chart. It plugs the connector and the `examon_ts_timestamps`
catalog into a Trino release without touching image tag, JVM heap,
worker count, auth, networking, or persistence. Pair it with whatever
sizing values your deployment needs.

## The overlay

| File | Contents |
|---|---|
| [`values-examon.yaml`](values-examon.yaml) | Init-container that fetches the connector JAR on coordinator and worker, plugin volume + mount on both pods, and the `examon_ts_timestamps` catalog pointing at the ExaMon KairosDB Service. Nothing else. |

That's it. Sizing, image tag, worker count, auth, networking, and
persistence all stay in your own values file (or `--set` flags). The
end-to-end install walkthrough and the first SQL query live in the
published ExaMon documentation (Administrators -> Add-ons -> Trino,
Users -> Analyze -> Query with Trino).

## Usage

### Fresh install (laptop-sized example)

The sizing snippet below targets the 8 GB host documented in the
ExaMon Quickstart. It is an **example**, not chart-side material:
operators with different targets supply their own.

```bash
cat > /tmp/trino-laptop.yaml <<'EOF'
image:
  tag: "476"           # tested with trino-kairosdb-connector 3.0.0-rc1

server:
  workers: 1

coordinator:
  jvm: { maxHeapSize: "1G" }
  config:
    query: { maxMemoryPerNode: "512MB" }

worker:
  jvm: { maxHeapSize: "1G" }
  config:
    query: { maxMemoryPerNode: "512MB" }
EOF

helm repo add trino https://trinodb.github.io/charts
helm repo update

helm install trino trino/trino --version 1.42.2 \
  -f /tmp/trino-laptop.yaml \
  -f deploy/trino/values-examon.yaml \
  -n examon --wait --timeout 5m
```

### Add ExaMon catalogs to an existing `trino/trino` release

Pass your existing values file as the first `-f`, or `helm upgrade`
resets unset fields to chart defaults. If you don't have a copy on
disk, export the current ones first:

```bash
helm get values <your-release> -n <your-namespace> -o yaml \
  > /tmp/current-values.yaml

helm upgrade <your-release> trino/trino \
  -f /tmp/current-values.yaml \
  -f deploy/trino/values-examon.yaml \
  -n <your-namespace>
```

Edit `catalogs.examon_ts_timestamps`' `kairosdb.url` in
`values-examon.yaml` so it resolves from your Trino pods to your
ExaMon KairosDB Service. Two common shapes:

- Trino and ExaMon in the same namespace:
  `http://examon-kairosdb:8083`
- Trino and ExaMon in different namespaces (same cluster):
  `http://examon-kairosdb.<examon-namespace>.svc.cluster.local:8083`

For cross-cluster or external KairosDB, point at the exposed endpoint
(Ingress, LoadBalancer, external DNS) instead.

## Pin policy

The wiring overlay does not pin chart version or image tag: those
stay with the operator. Connector 3.0.0-rc1 is tested against Trino
**476**; the laptop example above sets `image.tag: "476"` so operators
who paste it land on a tested combination. If your existing release
runs a much older Trino, rebuild the connector against the matching
SPI; see the [connector repository](https://github.com/ExamonHPC/trino-kairosdb-connector).

## Helm list-merge caveat

Helm merges YAML maps deeply but lists by replacement.
`initContainers.coordinator`, `initContainers.worker`,
`coordinator.additionalVolumes`, `coordinator.additionalVolumeMounts`,
`worker.additionalVolumes`, and `worker.additionalVolumeMounts` are
lists. If your other values file already defines any of these, the
overlay will replace your entries rather than append. Inspect with
`helm get values <release> -a` first; if any are non-empty, paste the
ExaMon blocks into your own values file (concatenating the lists) and
skip the second `-f`.
