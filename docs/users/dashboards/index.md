# Dashboards

!!! info "Status: Live (Grafana core); Beta (public release pending) (3D Digital Twin plugin)"
    Grafana access, the auto-provisioned KairosDB datasource, the bundled test dashboard, and custom dashboard provisioning via ConfigMaps are all verified against examon-core v0.5.0. The 3D Digital Twin Grafana plugin (`examon-dt-panel`) is not yet publicly distributed and not yet listed on the Grafana plugin marketplace.

> Dashboards are the primary entry point for users consuming ExaMon data visually rather than through queries. ExaMon ships Grafana as part of the umbrella Helm chart with the KairosDB datasource pre-provisioned and a test dashboard auto-loaded. Adding custom dashboards is a one-step ConfigMap operation that requires no chart edit and no `helm upgrade`.

## Open Grafana

Grafana is exposed on port 3000 in K3d environments (local and staging) and through an Ingress in production. The address depends on the deployment:

| Environment | Address |
|---|---|
| Local (K3d) | [http://localhost:3000](http://localhost:3000) |
| Staging (K3d on VM) | `http://<vm-host>:3000` |
| Production | The Ingress host configured in `values-production.yaml` (typically `https://grafana.<your-domain>`) |

The default admin user is `admin`. The password is whatever was passed at install time via `grafana.adminPassword`. For local development bring-ups via [`scripts/k8s-local-setup.sh`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/scripts/k8s-local-setup.sh), the script prints the password it generated.

For production, the password is the value supplied to the install command; see [Harden for production → Step 6](../../administrators/deploy/harden-for-production.md#step-6-deploy-examon). It is also stored in the `examon-grafana` Kubernetes Secret:

```bash
kubectl get secret examon-grafana -n examon -o jsonpath='{.data.admin-password}' | base64 -d && echo
```

## The auto-provisioned KairosDB datasource

The Helm chart provisions the KairosDB datasource on every deploy; no manual datasource setup is needed:

- **Name:** `kairosdb`
- **Type:** `arpnetworking-kairosdb-datasource` (the React-based ArpNetworking fork; the legacy AngularJS plugin is not compatible with Grafana 11+).
- **UID:** `examon-kairosdb`: every shipped panel and dashboard references this UID.
- **URL:** `http://examon-kairosdb:8083` (in-cluster service name, port 8083).
- **Access mode:** proxy.

The plugin itself is installed at chart deploy time from its GitHub release URL via `grafana.plugins` and whitelisted (unsigned) via `grafana.grafana.ini.plugins.allow_loading_unsigned_plugins`. The full configuration sits in [`deploy/helm/examon/values.yaml`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/deploy/helm/examon/values.yaml). For the underlying mechanism and the Grafana 7.x legacy path on Docker Compose, see [Administrators → On Kubernetes → Grafana Dashboards](../../administrators/deploy/on-kubernetes.md#grafana-dashboards).

## The bundled test dashboard

The chart auto-loads one dashboard out of the box: **Examon Test – Random Sensor**. It plots the synthetic time-series produced by the `random_pub` container, which is enabled by default in local and staging deployments. Its purpose is end-to-end pipeline verification:

- If the dashboard shows live data after install, the pipeline `random_pub → Mosquitto → mqtt2kairosdb → KairosDB → Cassandra → Grafana` is wired correctly.
- If it shows no data, [Administrators → Troubleshoot](../../administrators/operations/troubleshoot.md) covers the most common failure points.

The dashboard JSON ships in [`deploy/helm/examon/dashboards/`](https://github.com/ExamonHPC/examon/tree/release/v0.5.0/deploy/helm/examon/dashboards) and the same smoke check is also executed automatically by [`scripts/k8s-smoke-test.sh`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/scripts/k8s-smoke-test.sh) at the end of the local bring-up.

The legacy v0.4.0 version of the same dashboard (Grafana 7.3.10 / AngularJS) is preserved at [`dashboards/legacy/`](https://github.com/ExamonHPC/examon/tree/release/v0.5.0/dashboards/legacy) for the Docker Compose stack and is **not** loaded by the Helm chart.

## Add a custom dashboard

ExaMon uses the standard [Grafana dashboard sidecar](https://github.com/grafana/helm-charts/tree/main/charts/grafana#sidecar-for-dashboards): any ConfigMap in the cluster carrying the label `grafana_dashboard=1` is auto-loaded into Grafana within about 30 seconds. The sidecar runs with `searchNamespace: ALL`, so the ConfigMap can live in any namespace.

This means a new dashboard can be added without editing the chart and without `helm upgrade`.

### Single dashboard from a JSON file

```bash
kubectl -n examon create configmap my-dashboard \
  --from-file=my-dashboard.json=./my-dashboard.json
kubectl -n examon label configmap my-dashboard grafana_dashboard=1
```

Within about 30 seconds the dashboard appears in Grafana under **Dashboards**. Deleting the ConfigMap removes it.

### A whole directory of dashboards

One ConfigMap per file keeps every dashboard safely below the 1 MiB ConfigMap size limit:

```bash
for f in ./dashboards/*.json; do
  name="examon-dash-$(basename "$f" .json | tr '[:upper:] _' '[:lower:]--')"
  kubectl -n examon create configmap "$name" --from-file="$(basename "$f")=$f"
  kubectl -n examon label configmap "$name" grafana_dashboard=1
done
```

### GitOps / YAML manifest variant

The same pattern as a plain manifest, suitable for ArgoCD, Flux, or `kubectl apply -f`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-dashboard
  namespace: examon
  labels:
    grafana_dashboard: "1"
data:
  my-dashboard.json: |-
    {
      "title": "My Dashboard",
      "panels": [ /* ... */ ]
    }
```

### Datasource references inside custom dashboards

Every panel and the dashboard root must point at the chart-provisioned KairosDB datasource:

```json
{ "type": "arpnetworking-kairosdb-datasource", "uid": "examon-kairosdb" }
```

Dashboards exported from a Grafana 7.x v0.4.0 deployment still reference the legacy `grafana-kairosdb-datasource` plugin and must be rewritten before they will work on v0.5.0. The `jq` rewrite recipe is in [Administrators → Upgrade → Step 4](../../administrators/deploy/upgrade.md#step-4-restore-data).

## 3D Digital Twin (Beta)

The ExaMon 3D Digital Twin Grafana plugin (`examon-dt-panel`) renders a 3D model of the physical infrastructure inside a Grafana dashboard, with live data overlays on the meshes. It uses Babylon.js as the rendering engine and supports glTF/glB model loading, metric-driven mesh coloring, interactive drill-down, auto-rotation, and Grafana template variables.

The original proof-of-concept was used as the visualization layer for a data-driven cooling-optimization study on a production HPC facility; the measured outcome was approximately an 8% PUE reduction compared to historical operating conditions, by exposing cooling-efficiency curves (COP versus heat load and outdoor temperature) directly to operators and letting them adjust individual cooling-device setpoints.

**Status.** Beta (public release pending). The proof-of-concept is being ported to the Grafana panel SDK (Grafana v10+). The target architecture is parametric: the ExaMon inventory schema drives model selection, data-to-mesh binding, and 3D widget placement, so adding a new site requires only a glTF/glB model and matching inventory entries, with no custom 3D modeling work per site.

**Availability.** Source is not yet public and the plugin is not yet listed on the Grafana plugin marketplace, so it is not `grafana-cli`-installable today. Interested integrators should reach the team through [Community → Contact](../../community/contact.md).

The architecture of the plugin and its relationship to the inventory schema is covered in [Concepts → Architecture](../../concepts/architecture.md).

---

## Source

- Helm umbrella chart values for Grafana: [`deploy/helm/examon/values.yaml`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/deploy/helm/examon/values.yaml).
- Bundled dashboards: [`deploy/helm/examon/dashboards/`](https://github.com/ExamonHPC/examon/tree/release/v0.5.0/deploy/helm/examon/dashboards).
- Legacy v0.4.0 dashboard snapshot: [`dashboards/legacy/`](https://github.com/ExamonHPC/examon/tree/release/v0.5.0/dashboards/legacy).
- Smoke test that verifies the bundled dashboard end to end: [`scripts/k8s-smoke-test.sh`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/scripts/k8s-smoke-test.sh).
- Upstream: [Grafana](https://grafana.com/), [Grafana dashboard sidecar](https://github.com/grafana/helm-charts/tree/main/charts/grafana#sidecar-for-dashboards), [ArpNetworking KairosDB plugin](https://github.com/ArpNetworking/kairosdb-datasource), [Babylon.js](https://www.babylonjs.com/).
