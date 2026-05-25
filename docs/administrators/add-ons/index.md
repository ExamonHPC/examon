# Add-ons

!!! info "Status: Live"
    Verified against examon-core v0.5.0.

> Add-ons are optional components that extend ExaMon's surface without being part of the core release. ExaMon ships small, opinionated overlays that wire each component to the core stack while leaving the component's own lifecycle (upgrades, scaling, tuning, authentication) with the operator.

## What an add-on is

An add-on in this section satisfies three properties:

- It is **not required** to run ExaMon. The core stack ([Deploy](../deploy/index.md)) works without it.
- It has an **independent upstream lifecycle**. ExaMon does not vendor or fork it; it tracks upstream versions.
- ExaMon ships a small **wiring overlay** so the add-on talks to ExaMon's data stores or APIs out of the box, in both deployment shapes (Docker Compose and Kubernetes) where applicable.

## Available add-ons

| Add-on | What it adds | Page |
|---|---|---|
| **Trino** | SQL federation over KairosDB (and Cassandra in later overlays). Powers the user-facing [Query with Trino](../../users/analyze/query-with-trino.md) page and every BI / notebook integration. | [Trino](trino.md) |

More add-ons (Superset, ExaMon AI gateway) are planned for v0.5.1 and will land in this section.

---

## Source

- Trino overlays: [`deploy/trino/`](https://github.com/ExamonHPC/examon/tree/release/v0.5.0/deploy/trino), [`deploy/docker/trino/`](https://github.com/ExamonHPC/examon/tree/release/v0.5.0/deploy/docker/trino), [`compose.trino.yml`](https://github.com/ExamonHPC/examon/blob/release/v0.5.0/compose.trino.yml).
