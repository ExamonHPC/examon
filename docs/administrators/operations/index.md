# Operations

!!! info "Status: Live (reproduced 2026-05-23)"
    Verified against examon-core v0.5.0.

> The Operations sub-section covers running ExaMon day to day after the deployment is up: applying configuration changes safely, propagating those changes across the layered Helm + container stack, and diagnosing the failures most likely to appear in practice. It assumes the deployment has already been brought up via the [Deploy](../deploy/index.md) sub-section and that publishers are installed per [Publishers](../publishers/index.md).

## When to read this section

The Deploy pages get an operator from "nothing installed" to "ExaMon running". The Operations pages take over from there: every change after install, every failure recovery, every cluster-side adjustment to a running deployment.

| Day-2 concern | Read |
|---|---|
| Find or change a configuration value in the running deployment | [Configure](configure.md) |
| Propagate a change through the values / template / Dockerfile chain without breaking it | [Change propagation](change-propagation.md) |
| Diagnose a `CrashLoopBackOff`, a connection error, or a stuck `helm upgrade` | [Troubleshoot](troubleshoot.md) |

## How configuration flows

A single configuration value in ExaMon passes through six layers before it reaches the running container process: subchart defaults, umbrella chart defaults, environment overlay, rendered Helm template, Kubernetes resource, container runtime. Most day-2 operational failures are propagation failures: an edit in one layer that silently does not reach the container because a step in the chain was skipped.

[Change propagation](change-propagation.md) is the page that maps the chain end to end. Read it before making any configuration change that touches more than the environment-specific values overlay; it documents the four common change scenarios (value change, template change, Dockerfile change, new field end-to-end) and the exact follow-up actions each requires.

## Troubleshooting posture

[Troubleshoot](troubleshoot.md) is structured in two halves:

- A **systematic methodology** (get the big picture, read the logs, inspect the pod spec, verify what Helm actually deployed, test connectivity, fix-rebuild-redeploy) that applies to any unhealthy pod.
- A **cookbook** of eighteen specific failure signatures observed during v0.5.0 bring-up, each with symptom, root cause, and resolution. These are the failures actually encountered during integration; the cookbook is intentionally a recovery aid, not an exhaustive failure taxonomy.

## What is in scope here, and what is not

In scope:

- Configuration changes against a running Helm release (`helm upgrade`).
- Rolling restarts (`kubectl rollout restart`) and Helm rollbacks (`helm rollback`).
- Diagnosing the failure classes most likely to appear in v0.5.0: image caching, K8ssandra webhook ordering, Cassandra credential injection, Grafana plugin compatibility, mqtt2kairosdb topic shape, examon-server readiness probes.

Out of scope on these pages (covered elsewhere):

- The configuration parameter dictionary itself: see [Reference → Configuration](../../reference/configuration.md).
- The architectural background for *why* configuration is layered this way: see [Concepts → Architecture](../../concepts/architecture.md).
- Backing up KairosDB / Cassandra (Medusa) and restoring from snapshot: covered as part of [Harden for production → Backups](../deploy/harden-for-production.md#backups); a dedicated page is planned but not yet authored.
- Cluster-side meta-monitoring of ExaMon itself (Prometheus scrape of the ExaMon components): noted in [Harden for production → Monitoring](../deploy/harden-for-production.md#monitoring); a dedicated page is planned but not yet authored.

## In this section

- [**Configure**](configure.md) — the parameter surface of the running deployment, indexed by component (Cassandra, KairosDB, Grafana, Mosquitto, mqtt2kairosdb, random-pub, examon-server).
- [**Change propagation**](change-propagation.md) — the propagation chain from values to container; what to do after each kind of change.
- [**Troubleshoot**](troubleshoot.md) — systematic debugging methodology and a cookbook of known failure signatures.

---

## Source

- Helm umbrella chart and subcharts: [`deploy/helm/examon/`](https://github.com/ExamonHPC/examon/tree/release/v0.5.0/deploy/helm/examon).
- Local-development bring-up script: [`scripts/k8s-local-setup.sh`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/scripts/k8s-local-setup.sh).
- Reference: [Configuration parameters](../../reference/configuration.md).
