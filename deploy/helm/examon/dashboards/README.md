# Chart-bundled Grafana dashboards

> **Most users should NOT add files here.** To ship a custom dashboard,
> create a `ConfigMap` labeled `grafana_dashboard=1` in any namespace —
> the Grafana sidecar will load it automatically without a `helm
> upgrade`. See
> [Grafana Dashboards](../../../../docs/Deployment/kubernetes.md#grafana-dashboards)
> in the Kubernetes deployment guide for the recipe.
>
> This folder is for chart **forks and maintainers** who want a
> dashboard baked into the umbrella chart artifact itself.

Dashboards in this folder are packaged into the umbrella chart and
auto-provisioned in Grafana via the dashboard sidecar (one ConfigMap per
file, labeled `grafana_dashboard: "1"`).

The canonical user-facing copy lives at the repository root under
`dashboards/`. When updating a dashboard, edit both copies (or sync from
the root via `cp ../../../dashboards/*.json .`). Helm's `.Files` API can
only read files inside the chart directory, so the chart needs its own
copy of any dashboard it ships.

To disable bundling without removing the files, set
`bundledDashboards.enabled=false` in `values.yaml`.
