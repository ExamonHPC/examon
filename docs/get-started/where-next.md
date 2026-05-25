# Where Next

!!! info "Status: Live (reproduced 2026-05-23)"
    Verified against examon-core v0.5.0.

> A reader who has finished [What is ExaMon](what-is-examon.md), [Quickstart](quickstart.md), and [Core concepts](core-concepts.md) has the context to branch into the rest of the site. This page is the branch point: three audience guides, three universal sections, and pointers into the most-asked entries inside each.

## I run ExaMon as infrastructure

Read the [Administrators guide](../administrators/index.md). It covers three operational paths:

- **Deploy**: install ExaMon core on Kubernetes (Helm), on a single machine with Docker Compose, or across a fleet from an inventory. The [Deploy overview](../administrators/deploy/index.md) chooses between the paths; [On Kubernetes](../administrators/deploy/on-kubernetes.md) and [With Docker Compose](../administrators/deploy/with-docker-compose.md) are the two stable endpoints today. [Harden for production](../administrators/deploy/harden-for-production.md) covers TLS, secrets, backups, and known gaps in production hardening. [Upgrade](../administrators/deploy/upgrade.md) covers the migration path from v0.4.0 Docker Compose to v0.5.0 Kubernetes.
- **Publishers**: install collectors on individual nodes via the SDK v3 install pattern (pip, systemd, MQTT). The [Publishers section](../administrators/publishers/index.md) is the catalog of available collectors.
- **Operations**: configure the deployment after install, propagate changes across a running fleet, troubleshoot common failures. The [Operations section](../administrators/operations/index.md) is the day-to-day reference.

## I use ExaMon to extract value from data

Read the [Users guide](../users/index.md). It covers three consumption paths:

- **Dashboards**: Grafana for operational dashboards, including the 3D Digital Twin for facility-scale visualization. The [Dashboards section](../users/dashboards/index.md) covers both.
- **Analyze**: SQL through Trino from any BI tool, notebook, or scripting language, plus a legacy Python client for pre-Trino deployments. The [Analyze section](../users/analyze/index.md) covers the Trino schema, example queries, per-tool connection guides. The [Local Trino Quickstart](../users/analyze/local-trino-quickstart.md) is the fastest way to a first SQL query against your local stack. The bundled [ExamonQL notebook](../users/analyze/Demo_ExamonQL.ipynb) uses the legacy `examon-client` interface against the ExaMon REST API and remains useful in pre-Trino deployments.
- **AI**: natural-language questions and runbook-driven investigation through ExaMon AI. The [AI section](../users/ai/index.md) covers the agent's capabilities and current beta status.

## I extend ExaMon with new code

Read the [Developers guide](../developers/index.md). It covers two paths:

- **SDK v3**: write a new publisher in a few lines of Python on top of the framework's worker model and YAML configuration. The [SDK v3 section](../developers/sdk-v3/index.md) is the entry point; the [`examon_pub` worked example](../developers/sdk-v3/examples/examon_pub.ipynb) is the reference walkthrough.
- **Contributing**: submit changes to the core repository. The [Contributing page](../developers/contributing.md) covers code style, the PR process, and the release flow.

## I want the long-form explanation

The [Concepts section](../concepts/index.md) is the universal explanation surface, for readers who want to understand the *how* and the *why* of the stack rather than the *how to use it*. The foundation page is [Architecture](../concepts/architecture.md). For the concrete deployment shape on Docker Compose and on Kubernetes, see [Administrators → Deploy → Deployment topology](../administrators/deploy/topology.md).

## I want a single page of facts

The [Reference section](../reference/index.md) is universal lookup: terse, complete, alphabetized where useful. The [Component catalog](../reference/component-catalog.md) lists every shipped component with its current status and source repository, in one place.

## I want context: papers, contributors, history

The [Community section](../community/index.md) covers context that is not about using or running ExaMon:

- [About](../community/about.md): the project's origin at the University of Bologna with CINECA and E4.
- [Publications](../community/publications.md): academic papers describing ExaMon and its use.
- [Clusters](../community/clusters/index.md): case studies at [Marconi 100](../community/clusters/marconi100.md) and [Monte Cimone](../community/clusters/montecimone.md).
- [Releases](../community/releases/index.md): release notes and release plans.
- [Contact](../community/contact.md): how to reach the maintainers.

---

## Source

- This page is a pure cross-link funnel. Each linked page carries its own Source section.
