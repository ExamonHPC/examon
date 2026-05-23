# Administrators

!!! info "Status: Live (reproduced 2026-05-23)"
    Verified against examon-core v0.5.0.

> The Administrators guide is for anyone making ExaMon run somewhere: DevOps engineers deploying core on a Kubernetes cluster, sysadmins installing publishers on individual nodes, fleet operators rolling ExaMon across a multi-cluster inventory. The guide is split into three sub-paths that match the three operational concerns: deploying the platform, installing the collectors that feed it, and running it day to day.

## Pick the path

A reader new to ExaMon as infrastructure usually wants one of three things. Each sub-section starts with a landing page that funnels further.

| The reader wants to ... | Read |
|---|---|
| Install ExaMon core on a Kubernetes cluster, on a single machine with Docker Compose, or harden an existing install for production | [Deploy](deploy/index.md) |
| Install collectors on individual compute, login, or BMC nodes so they publish metrics into a running ExaMon | [Publishers](publishers/index.md) |
| Configure a running deployment, propagate changes safely, troubleshoot a failure, or perform day-2 operations | [Operations](operations/index.md) |

A reader who has not yet installed anything starts at [Deploy → Overview](deploy/index.md). A reader who has core running and wants to add data sources starts at [Publishers](publishers/index.md). A reader operating an installed cluster jumps straight to [Operations](operations/index.md).

## What this guide assumes

- Familiarity with the Linux command line, Docker, and Kubernetes at the level needed to run `kubectl`, `helm`, and `docker compose` against a working cluster.
- Network access from the install host to the target hosts (Kubernetes API, MQTT broker, BMC interfaces where applicable).
- The architectural context covered in [Concepts → Architecture](../concepts/architecture.md). The Administrators guide explains *how* to run the stack; the architecture page explains *what* runs and *why*.

A reader who has not yet seen ExaMon at all should walk [Get Started](../get-started/index.md) first; the 15-minute [Quickstart](../get-started/quickstart.md) brings up the full stack locally in one script.

## Scope

The guide covers the v0.5.0 line: Kubernetes via Helm as the recommended production target, Docker Compose as a stable legacy single-machine path, and the supporting publisher and operations surface. Where a capability is shipped but still maturing (3D Digital Twin Grafana plugin, ExaMon AI, the publisher scheduler), the relevant page says so in its Status admonition.

---

## Source

- ExaMon source repository: [ExamonHPC/examon](https://github.com/ExamonHPC/examon) (release/v0.5.0).
- Helm chart: [`deploy/helm/examon/`](https://github.com/ExamonHPC/examon/tree/release/v0.5.0/deploy/helm/examon).
- Local-development scripts: [`scripts/`](https://github.com/ExamonHPC/examon/tree/release/v0.5.0/scripts).
