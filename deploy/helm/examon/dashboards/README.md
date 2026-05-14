# Chart-bundled Grafana dashboards

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
