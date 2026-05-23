# Developers

!!! info "Status: Live (reproduced 2026-05-23)"
    Verified against SDK v3 (examon-base-plugin) and the v0.5.0 repository structure. Sub-sections carry their own status: SDK v3 (Live), Contributing (Beta (the open-source contribution flow is still maturing)).

> The Developers guide is for anyone extending ExaMon: writing a new publisher with SDK v3, adding a custom tool or runbook to ExaMon AI, building a custom Grafana panel, or contributing patches and pull requests to the core repositories. It assumes Python familiarity and basic ETL patterns; no prior ExaMon knowledge is required.

## Pick the path

| The goal is ... | Read |
|---|---|
| Write a new publisher (a process that scrapes a data source and ships into ExaMon) | [SDK v3](sdk-v3/index.md) |
| Submit a patch, file an issue, or open a pull request against an ExaMon repository | [Contributing](contributing.md) |
| Extend ExaMon AI with a new tool or runbook | [Users → AI → Customize](../users/ai/index.md#customize) |
| Add a custom dashboard to the bundled Grafana | [Users → Dashboards → Add a custom dashboard](../users/dashboards/index.md#add-a-custom-dashboard) |

## ExaMon is composable, not monolithic

Before writing any new component, it is useful to know that ExaMon is a federation of independent repositories rather than a single codebase. Each component has its own release cadence, its own license, and its own contribution flow:

| Component | Repository |
|---|---|
| Core (broker, bridge, time-series store, Helm chart, server) | [ExamonHPC/examon](https://github.com/ExamonHPC/examon) |
| SDK v3 base library | [E4-Computer-Engineering/examon-base-plugin](https://github.com/E4-Computer-Engineering/examon-base-plugin) |
| Reference SDK v3 publisher (Prometheus) | [E4-Computer-Engineering/prometheus_pub](https://github.com/E4-Computer-Engineering/prometheus_pub) |
| Other SDK v3 publishers (`ipmi_pub`, `nvml_pub`, `pmu_pub`, `slurm_pub`) | One repository each under [E4-Computer-Engineering](https://github.com/E4-Computer-Engineering) |
| Trino-KairosDB connector | [ExamonHPC/trino-kairosdb-connector](https://github.com/ExamonHPC/trino-kairosdb-connector) |
| ExaMon AI agent | Public release pending |
| 3D Digital Twin Grafana plugin (`examon-dt-panel`) | Public release pending |

The full inventory and current status of every component is in [Reference → Component catalog](../reference/component-catalog.md).

A patch to the Helm chart goes to `ExamonHPC/examon`. A new publisher gets its own repository under `E4-Computer-Engineering`. A bug fix in the Trino connector goes to `ExamonHPC/trino-kairosdb-connector`. Each repository owns its own release path; the umbrella project is a federation, not a monorepo.

## What this guide assumes

- Python 3.10 or later for SDK v3 work and ExaMon AI customization.
- Working familiarity with Git and GitHub for the contribution flow.
- For SDK v3 publishers: a target data source to scrape and either a target MQTT broker or a target KairosDB endpoint to load into.
- For contributing: a GitHub account.

## In this section

- [**SDK v3**](sdk-v3/index.md): write a publisher in a few lines of Python. The framework supplies workers (extractors, transformers, loaders), a lifecycle, restart backoff, MQTT and Cassandra connection handling, job replication, and the configuration model. The page covers the architectural shape; for full install + run, see [Publishers](../administrators/publishers/index.md).
- [**Contributing**](contributing.md): issue tracker pointers, the pull-request process, the release flow (`release/*` branches), and the commit-message convention.

---

## Source

- Core repository: [ExamonHPC/examon](https://github.com/ExamonHPC/examon) (release/v0.5.0).
- SDK v3 base library: [E4-Computer-Engineering/examon-base-plugin](https://github.com/E4-Computer-Engineering/examon-base-plugin).
- Component catalog (every shipped component with its repository and status): [Reference → Component catalog](../reference/component-catalog.md).
