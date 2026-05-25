# What is ExaMon

!!! info "Status: Live (reproduced 2026-05-23)"
    Verified against examon-core v0.5.0.

> This page answers the 30-second question: what is ExaMon, what problem does it solve, and what does it look like end-to-end. A reader who finishes this page knows whether ExaMon is relevant to their work and where to go next.

## ExaMon in one paragraph

ExaMon is an open-source data platform for continuous, heterogeneous measurement of large physical systems, primarily high-performance computing clusters. It collects metrics from any source through a publish-subscribe transport, stores them in a schema-less time-series database, exposes them through a single SQL endpoint, and renders them through dashboards, notebooks, BI tools, and a 3D digital twin of the data center. The same data layer also powers an AI agent that answers operational questions in natural language.

## The problem ExaMon solves

A modern HPC cluster generates millions of data points per hour across dozens of heterogeneous sources: BMC/IPMI sensors, GPU telemetry, CPU performance counters, job schedulers, network devices, facility cooling systems. These streams arrive through incompatible protocols, at different frequencies, with different schemas. No single off-the-shelf monitoring tool covers all of them.

The usual response is a stack of disconnected tools, each showing a partial view. Operators correlate by hand. Novel failure modes that do not trip threshold alerts go undetected until they cause job failures or hardware damage. Researchers who want a complete picture of a workload's behaviour have to assemble it from several incompatible exports.

ExaMon's response is to normalize everything into one model: collect, transport, store, federate, visualize, reason. One data layer; many consumers.

## End-to-end pipeline

The stack is the same on every deployment:

```
Sources               Transport         Storage              Federation     Consumers
───────               ─────────         ───────              ──────────     ─────────

IPMI / BMC sensors                                                          Grafana
GPU telemetry (NVML)                                                        Superset
CPU PMU counters     ─▶  MQTT      ─▶   KairosDB        ─▶   Trino    ─▶   Power BI
Slurm jobs               broker         (time series)        (SQL)         Jupyter
Prometheus exporters    (Mosquitto)     on Cassandra                       3D Digital Twin
Facility cooling                        +                                  ExaMon AI
                                        Cassandra direct
                                        (job records,
                                        metadata)
```

- **Sources** publish through SDK v3 collectors that run on individual nodes (compute, login, BMC hosts) or pull from existing endpoints (Prometheus, Slurm).
- **MQTT** carries the data from collectors to the central broker; the protocol is designed for many-producer, intermittent-connectivity environments.
- **KairosDB on Cassandra** stores time-series data in a schema-less model (new metrics and new tag combinations need no migration); a second Cassandra path holds structured records like Slurm job accounting and infrastructure metadata.
- **Trino** federates time-series data and structured data behind one SQL endpoint via a custom Trino-KairosDB connector. Every consumer talks SQL to one host.
- **Consumers** include Grafana dashboards, Apache Superset, Power BI, Jupyter notebooks, the 3D Digital Twin Grafana plugin, and the ExaMon AI agent.

## What is shipped today

| Capability | Status |
|---|---|
| Kubernetes deployment via Helm chart | Stable |
| Docker Compose deployment | Stable (single-host target) |
| MQTT publish-subscribe transport (Mosquitto) | Stable |
| KairosDB on Cassandra (3-node K8ssandra StatefulSet on Kubernetes) | Stable |
| Trino federation with the public [`trino-kairosdb-connector`](https://github.com/ExamonHPC/trino-kairosdb-connector) | Available as an Apache-2.0 release on GitHub |
| Grafana dashboards (auto-provisioned KairosDB datasource + bundled test dashboard) | Stable |
| SDK v3 collector framework (`prometheus_pub`, `mqtt2kairosdb-v3` reference implementations) | Beta (public release pending) |
| 3D Digital Twin Grafana plugin | Beta (public release pending) |
| ExaMon AI (natural-language analytics agent) | Beta (public release pending) |

## Who ExaMon is for

ExaMon serves three audiences:

- **Administrators** run ExaMon as infrastructure: a DevOps engineer deploying core on Kubernetes, a sysadmin installing publishers on individual nodes, a fleet operator rolling out across an inventory. The [Administrators guide](../administrators/index.md) covers deployment, publisher installation, and operations.
- **Users** extract value from a running ExaMon: a data scientist running SQL or pandas analyses, a facility manager watching the 3D digital twin in Grafana, an on-call engineer asking the AI agent why a job failed. The [Users guide](../users/index.md) covers dashboards, analyze, and AI.
- **Developers** extend ExaMon: writing a new publisher with SDK v3, building a custom Grafana panel, adding a tool to the AI agent, contributing to the core repositories. The [Developers guide](../developers/index.md) covers the SDK and the contribution process.

A newcomer who does not yet identify with any of those starts with the [Quickstart](quickstart.md): a 15-minute path from zero to seeing real data on a local Kubernetes cluster.

## Where ExaMon comes from

ExaMon is developed at the [DEI Department of Electrical, Electronic, and Information Engineering "Guglielmo Marconi"](https://dei.unibo.it/en/index.html) of the University of Bologna, in collaboration with [CINECA](https://www.hpc.cineca.it/) and [E4 Computer Engineering](https://www.e4company.com/en/). The platform has been deployed at CINECA's Tier-0 supercomputers (Marconi 100, Galileo) and the Monte Cimone RISC-V testbed. The 49.9 TB Marconi 100 operational dataset (ExaData) was published in Nature Scientific Data (2023). See [Publications](../community/publications.md) and [Clusters](../community/clusters/index.md) for the full record.

## Where next

- [Quickstart](quickstart.md): 15-minute local install on Kubernetes (K3d).
- [Core concepts](core-concepts.md): the five things to know before going deeper.
- [Architecture](../concepts/architecture.md): the long-form explanation of the stack.

---

## Source

- The ExaMon source repository: [ExamonHPC/examon](https://github.com/ExamonHPC/examon) (release/v0.5.0).
- About: [community/about.md](../community/about.md).
- Trino-KairosDB connector: [ExamonHPC/trino-kairosdb-connector](https://github.com/ExamonHPC/trino-kairosdb-connector).
- Reference dataset: [Borghesi, A., Di Santi, C., Molan, M. et al. M100 ExaData: a data collection campaign on the CINECA’s Marconi100 Tier-0 supercomputer. Sci Data 10, 288 (2023)](https://doi.org/10.1038/s41597-023-02174-3).
