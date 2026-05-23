# Users

!!! info "Status: Live (reproduced 2026-05-23)"
    Verified against examon-core v0.5.0. Individual sub-sections carry their own status: Dashboards (Live for core Grafana, Beta for the 3D Digital Twin plugin), Analyze (Beta — Trino connector is shipped publicly but not bundled into the local chart), AI (Beta — public pip install pending).

> The Users guide is for anyone extracting value from a running ExaMon deployment: data scientists running SQL or pandas analyses, facility managers monitoring the data center through dashboards (including the 3D digital twin in Grafana), on-call engineers investigating incidents through the AI agent. It assumes ExaMon is already deployed and emitting data — for the deployment path, see the [Administrators](../administrators/index.md) guide.

## Pick the tool

ExaMon exposes the same underlying data through three different surfaces. The right surface depends on the question being asked.

| The question is ... | Read |
|---|---|
| "What does this rack / cluster / building look like right now? Are temperatures within range? Is power normal?" | [Dashboards](dashboards/index.md) |
| "What was the average GPU power per job for cluster X over the last 30 days? Which jobs failed and why?" | [Analyze](analyze/index.md) |
| "I have a vague problem. Tell me what is going on, what to look at, and what to do next." | [AI](ai/index.md) |

The same data backs all three: Cassandra holds the source-of-truth, KairosDB serves time-series, and Trino federates the SQL surface. The choice of tool is purely about how the answer is best delivered to the human — visual, structured query, or natural language.

## What this guide assumes

- The ExaMon deployment is up and emitting data. (If not, the [Quickstart](../get-started/quickstart.md) brings up a local stack in 15 minutes.)
- Credentials for whichever surface is being accessed: Grafana admin or viewer (Dashboards), the Trino endpoint (Analyze), the configured LLM endpoint (AI).
- For Analyze: working familiarity with SQL. For AI: a question to ask.

## In this section

- [**Dashboards**](dashboards/index.md) — Grafana access, the auto-provisioned KairosDB datasource, the bundled "Random Sensor" test dashboard, adding custom dashboards via ConfigMaps, and the 3D Digital Twin Grafana plugin (Beta).
- [**Analyze**](analyze/index.md) — SQL access via the Trino federation layer (KairosDB connector for time-series + Cassandra connector for job accounting), the schema layout, and an end-to-end notebook walkthrough using ExamonQL.
- [**AI**](ai/index.md) — ExaMon AI: a HolmesGPT-based agent that uses the Trino SQL surface to answer natural-language questions, supported by domain runbooks and custom toolsets.

---

## Source

- ExaMon source repository: [ExamonHPC/examon](https://github.com/ExamonHPC/examon) (release/v0.5.0).
- ExaMon AI repository: not yet public; published pip install path is pending.
- Trino-KairosDB connector: [ExamonHPC/trino-kairosdb-connector](https://github.com/ExamonHPC/trino-kairosdb-connector).
- 3D Digital Twin Grafana plugin (`examon-dt-panel`): private repository pending Grafana plugin marketplace submission.
