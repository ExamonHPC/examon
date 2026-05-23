# Reference

!!! info "Status: Live (reproduced 2026-05-23)"
    Verified against examon-core v0.5.0. Individual reference pages carry their own status.

> The Reference section is universal lookup: terse, complete, alphabetized where useful. It is for readers who already know what they need and want the canonical answer (a component status, a configuration key, a CLI flag, a metric name, an API endpoint) without prose. Every page here is intended to be linked into from other sections of the site rather than read end to end.

## In this section

| Page | Use to ... |
|---|---|
| [**Component catalog**](component-catalog.md) | See every shipped component, its status, the source repository, and the maintainer. The single source of truth for "is this component live or planned". |
| [**Glossary**](glossary.md) | Look up a term used elsewhere on the site: MQTT, KairosDB, K8ssandra, supervisord, ETL, ExamonQL, Trino, NVML, IPMI, RAPL, ExaData, and so on. |
| [**Configuration**](configuration.md) | The full parameter surface, organized by component: Helm chart values, SDK v3 publisher YAML schema, bridge configuration. The dictionary that backs every other configuration discussion on the site. |
| [**CLI**](cli.md) | The command-line surfaces shipped with ExaMon: the local-setup and smoke-test scripts, the SDK v3 publisher CLI, the planned `examon-scheduler`. |
| [**API**](api.md) | The external interfaces exposed to consumers: the `examon-server` REST API, the KairosDB HTTP API surface used by Grafana, and the Trino SQL surface presented by the federation layer. |

## What this section is not

- Not a tutorial. Tutorials live in [Get Started](../get-started/index.md). Reference pages assume the reader already knows the goal.
- Not a guide. Guides live in [Administrators](../administrators/index.md), [Users](../users/index.md), and [Developers](../developers/index.md). Reference pages do not walk the reader through a flow.
- Not an architectural explanation. The "why" lives in [Concepts](../concepts/index.md). Reference pages document what exists, not why.

## Citation convention

Every Reference page cites the source of its information at the bottom (Source section). When a parameter's authoritative definition lives in an upstream YAML file or in a public repository, the Reference page cites that file directly so a reader can verify the current truth against the running code.

---

## Source

- ExaMon source repository: [ExamonHPC/examon](https://github.com/ExamonHPC/examon) (release/v0.5.0).
- Component repositories: tracked in [Component catalog](component-catalog.md).
