# Component Catalog

!!! info "Status: Live (reproduced 2026-05-23)"
    Verified against the public state of the [ExamonHPC GitHub organization](https://github.com/ExamonHPC) and examon-core v0.5.0. Component repositories that are still in private development are listed as such; their status flips when they ship.

> This page lists every component shipped by the ExaMon project, with its current maturity status and a link to its source repository. It exists so an operator, evaluator, or new contributor can answer "what exists and where" in one page without traversing the rest of the documentation. Each entry links to the relevant deeper page or the upstream README.

## How to read the status column

| Status | Meaning |
|---|---|
| **Stable** | Production-grade. Used in live deployments. Public release available. |
| **Beta** | Working with documented caveats: limited validation, internal pilots, or restricted release. |
| **In development** | Active work toward a public release; not recommended for production yet. |
| **Proof of concept** | Validated on a specific test case; not yet a product. |
| **Planned** | On the current roadmap; not yet started or in early prototype. |

## Core platform

| Component | Status | Source | Notes |
|---|---|---|---|
| ExaMon core (Helm chart and Docker Compose) | Stable | [ExamonHPC/examon](https://github.com/ExamonHPC/examon) | The always-on platform: MQTT broker (Mosquitto), MQTT-to-storage bridge (`mqtt2kairosdb`), KairosDB on Cassandra, Grafana, ExaMon API server. Helm chart in `deploy/helm/examon/`. |
| ExaMon API server | Stable | [ExamonHPC/examon](https://github.com/ExamonHPC/examon) | REST API shipped inside the core deployment. Reachable through the chart Ingress at `/api`. |

## Storage and federation

| Component | Status | Source | Notes |
|---|---|---|---|
| KairosDB | Stable (upstream) | [kairosdb/kairosdb](https://github.com/kairosdb/kairosdb) | Schema-less time-series database used as the primary store. ExaMon runs the 1.2.x line and tracks 1.4.x for Cassandra 4.x compatibility. |
| Cassandra (via K8ssandra operator on Kubernetes) | Stable | [k8ssandra/k8ssandra-operator](https://github.com/k8ssandra/k8ssandra-operator) | Distributed wide-column store. Used both as KairosDB's storage backend and directly for structured data (Slurm jobs, metadata). |
| `trino-kairosdb-connector` | Stable (public release available) | [ExamonHPC/trino-kairosdb-connector](https://github.com/ExamonHPC/trino-kairosdb-connector) | Custom Trino connector for KairosDB. Apache-2.0. Plugs into an existing Trino installation; see the connector README for the install path. |
| Trino (upstream) | Stable (upstream) | [trinodb/trino](https://github.com/trinodb/trino) | Distributed SQL query engine. Hosts the KairosDB connector and the stock Cassandra connector for unified SQL over ExaMon data. Deployed externally; ExaMon ships no Trino chart. |
| Cold tier (S3 / Parquet via Trino Hive or Iceberg) | In development | [ExamonHPC/examon](https://github.com/ExamonHPC/examon) | Planned third storage tier for ageing data out of Cassandra. Trino connector configuration is the integration surface. |

## Transport

| Component | Status | Source | Notes |
|---|---|---|---|
| Mosquitto (MQTT broker, upstream) | Stable | [eclipse/mosquitto](https://github.com/eclipse/mosquitto) | Shipped inside the ExaMon core deployment. ExaMon's contribution is the topic structure and payload format, not the broker itself. |

## Publishers (SDK v3 framework + collectors)

| Component | Status | Source | Notes |
|---|---|---|---|
| SDK v3 framework (`examon-base-plugin`) | Stable (public release pending) | private repository today; planned PyPI release | The publisher framework: extract / transform / load worker model, declarative YAML configuration, daemon mode, exponential-backoff restart. MIT license. |
| `prometheus_pub` | Stable | (publication pending; tracked in the SDK v3 release) | SDK v3 reference implementation for the *collection* side. Ingests from any Prometheus-compatible endpoint. Two scraping methods (Query API, direct `/metrics` endpoint), regex metric filtering, dynamic tag extraction, multi-server fan-out. |
| `mqtt2kairosdb-v3` | Stable | (publication pending; tracked in the SDK v3 release) | SDK v3 reference implementation for the *ingestion* side. The MQTT-to-storage bridge that runs inside core. Ships with both `KairosDBBatchLoader` and `TDengineBatchLoader` Load workers, proving the backend abstraction. |
| `ipmi_pub` | Stable (legacy framework) | (publication pending) | BMC / IPMI out-of-band sensor collector. Migration to SDK v3 planned. |
| `nvml_pub` | Stable (legacy framework) | (publication pending) | NVIDIA GPU telemetry collector via NVML. Migration to SDK v3 planned. |
| `pmu_pub` | Stable (legacy framework, native C) | (publication pending) | CPU PMU counter collector via Linux `perf` and MSR. |
| `slurm_pub` | Stable (legacy framework) | (publication pending) | Slurm job accounting collector. Writes structured records directly to Cassandra. |

## Visualization

| Component | Status | Source | Notes |
|---|---|---|---|
| Grafana (upstream) | Stable | [grafana/grafana](https://github.com/grafana/grafana) | Shipped inside the ExaMon core deployment. The chart auto-provisions the KairosDB datasource and a bundled test dashboard. |
| KairosDB datasource for Grafana (ArpNetworking) | Stable (upstream) | [grafana/arpnetworking-kairosdb-datasource](https://github.com/grafana/arpnetworking-kairosdb-datasource) | Grafana plugin that talks to KairosDB. Provisioned automatically by the core chart. |
| 3D Digital Twin Grafana plugin (`examon-dt-panel`) | Beta | private repository today; customer delivery target | Custom Grafana panel plugin rendering glTF / glB 3D models with metric-driven colouring. Babylon.js. The proof-of-concept measured an approximately 8% PUE reduction at a production site through cooling-set-point optimization. |
| Apache Superset (upstream) | Stable (upstream) | [apache/superset](https://github.com/apache/superset) | Connects to Trino via JDBC for ad-hoc analytical SQL. Deployed externally; ExaMon ships no Superset chart. |
| Power BI (commercial) | Supported | upstream commercial product | Connects to Trino via the official Trino connector. No ExaMon-specific integration. |
| Jupyter (upstream) | Stable (upstream) | [jupyter/jupyter](https://github.com/jupyter/jupyter) | The reference notebooks are the [`Demo_ExamonQL`](../users/analyze/Demo_ExamonQL.ipynb) walkthrough and the [Monte Cimone notebook](../community/clusters/montecimone-notebook.ipynb). |

## Intelligence

| Component | Status | Source | Notes |
|---|---|---|---|
| ExaMon AI (`examon-ai`) | Internal beta | private repository today; pip-installable | Discovery-driven analytics agent: HolmesGPT + Trino + runbooks. Locally deployed LLM (Ollama, vLLM, or any OpenAI-compatible endpoint). Tool-call architecture rather than text-to-SQL generation. |
| HolmesGPT (upstream) | Stable (upstream) | [robusta-dev/holmesgpt](https://github.com/robusta-dev/holmesgpt) | The agent framework used by ExaMon AI. CNCF Sandbox project. |
| pyWhy (causal inference, upstream) | Used in PoC | [py-why](https://github.com/py-why) | Used by ExaMon's causal-analysis CLI for causal discovery on operational time series. |

## Power management

| Component | Status | Source | Notes |
|---|---|---|---|
| Power-capping controller (Dynamo-based) | Proof of concept | private repository today | Closed-loop power capping. Reads current power through ExaMon's data layer, applies caps via RAPL / NVML / IPMI according to a priority-based policy. Validated against Marconi 100 data. |

## Inventory and orchestration

| Component | Status | Source | Notes |
|---|---|---|---|
| Inventory schema (YAML) | In development | (publication pending) | Internal contract for what infrastructure exists and what should be monitored. First user is the 3D twin's parametric model. |
| `examon-scheduler` (publisher scheduler CLI) | Planned | (publication pending) | CLI that compiles the inventory YAML into Ansible artifacts for fleet rollout, plus K8s Helm values for internal services. |
| `netbox-adapter` | Planned | (publication pending) | Reads Netbox device data and generates the ExaMon inventory YAML. |

## Documentation toolchain

| Component | Status | Source | Notes |
|---|---|---|---|
| ExaMon documentation site (this site) | Stable | [ExamonHPC/examon](https://github.com/ExamonHPC/examon) (`docs/` and `mkdocs.yml`) | MkDocs Material with the `mike` versioning plugin and a Jupyter conversion plugin. Built and published by the `Docs` GitHub Actions workflow. |

---

## How this catalog is maintained

The catalog tracks the state of the public ExaMon ecosystem. An entry flips from a "publication pending" note to a concrete repository link when the corresponding repository is published on GitHub. Maturity status follows the same rule: Stable means a deployment uses it in production today and a public release exists; Beta is acceptable for sites that accept documented caveats; In development and Proof of concept are deliberate signals not to use the component in production yet.

Cross-component compatibility is tracked in two places: each component repository's README declares its compatibility range against the others, and the central compatibility matrix in the core repository is updated on each release.

---

## Source

- [ExamonHPC GitHub organization](https://github.com/ExamonHPC) — the public source of truth for component repositories and releases.
- ExaMon core repository: [ExamonHPC/examon](https://github.com/ExamonHPC/examon) (release/v0.5.0).
- Trino-KairosDB connector: [ExamonHPC/trino-kairosdb-connector](https://github.com/ExamonHPC/trino-kairosdb-connector).
