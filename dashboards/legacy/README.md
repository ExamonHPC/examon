# Legacy dashboards (docker-compose v0.4.0)

This folder holds dashboards that target the **legacy docker-compose v0.4.0**
ExaMon stack only. They are kept here for users who are still running that
deployment and have not migrated to the Kubernetes-based v0.5.0+ stack.

## What's here

- `Examon Test - Random Sensor.json` — random-sensor verification dashboard
  compatible with Grafana 7.3.10 and the AngularJS-based
  `grafana-kairosdb-datasource` plugin, both shipped by `docker-compose.yml`.

## When to use these

Use these files **only** with the legacy Docker Compose deployment described
in the top-level `README.md`. They are imported manually via the Grafana UI
or HTTP API on a running Grafana 7.x instance.

## For Kubernetes (v0.5.0+) users

Use the dashboards in the parent `dashboards/` folder. They are compatible
with Grafana 10+ / 11+ (the Kubernetes Helm chart deploys current Grafana)
and the React-based `arpnetworking-kairosdb-datasource` plugin. The bundled
"Examon Test - Random Sensor" dashboard is also auto-provisioned by the
Helm chart via the Grafana dashboard sidecar — no manual import needed.
