# AI

!!! info "Status: Beta — public pip install pending"
    ExaMon AI is in internal beta on a reference HPC deployment. The architecture, runbook + tool model, and example outputs below are stable. The public pip-installable package and the canonical install URL are still being prepared; until then, deployment requires direct access to the development repository. Reach the team through [Community → Contact](../../community/contact.md) for evaluation access.

> ExaMon AI is a locally-hosted operations agent that turns natural-language questions into SQL-backed answers against an ExaMon deployment. It is built on [HolmesGPT](https://github.com/HolmesGPT/holmesgpt) as the LLM reasoning loop and on the [Trino federation layer](../analyze/index.md) as the single point of data access. It discovers what data exists at runtime, builds the right queries, and interprets the results without prior knowledge of the metrics, schema, or infrastructure topology of the deployment it is pointed at.

## What it does

ExaMon AI is the natural-language surface on top of the same data the [Analyze](../analyze/index.md) section exposes through SQL. Where Analyze is for users comfortable writing queries, AI is for operators who want answers without having to learn the schema, the metric names, or the query language.

Typical questions it handles end to end:

- *"What metrics are available for node `acnode04`?"*
- *"Compare CPU1 temperature and FAN2 speed on `acnode03` over the last hour."*
- *"Look for failed jobs in the last 30 days and probable root cause."*
- *"Do a complete GPU data analysis for node `cn01` over the last 90 days."*

For each question the agent decides which runbook to follow, calls the appropriate tools (schema exploration, metric discovery, time-series querying, job analysis), executes Trino queries, and presents structured results — typically as tables with summaries and follow-up suggestions. Example outputs are in the [demonstrated capabilities](#demonstrated-capabilities) section below.

## Architecture

The agent has three cooperating parts:

```
User question -> LLM reasoning -> Runbook (strategy) + Tools (execution) -> Result
```

| Part | Role | Where it lives |
|---|---|---|
| **LLM** | Bridges user intent to runbook + tool calls. Reads runbooks to understand strategy, calls tools to execute queries, interprets results. | Local or remote OpenAI-compatible endpoint (Ollama, vLLM, an external API). |
| **Runbooks** | Teach the LLM *how to think*: investigation workflows, when to use which strategy, domain patterns. | Markdown files in `~/.config/examon-ai/runbooks/`. |
| **Tools** | Teach the system *how to execute*: correct SQL syntax (quoting, CAST, WHERE clauses), error handling, output formatting for the LLM. | Python scripts in `~/.config/examon-ai/toolsets/`. |

The separation is what makes the system **portable across domains**. Core runbooks describe domain-independent investigation patterns; domain-specific runbooks and tools (HPC, smart buildings, industrial IoT) plug in on top.

ExaMon AI is also strict about **discovery at runtime**: the runbooks instruct the LLM to look up what metrics, schemas, and tables exist *before* composing a query, rather than rely on memorized topology. This is what lets the agent be pointed at a brand-new deployment and start working with no manual configuration.

## How it fits into the stack

ExaMon AI is a consumer of the existing federation layer, not a new data path:

```
ExaMon AI agent
       │  (Trino SQL via HolmesGPT toolset)
       ▼
   Trino coordinator
       │
       ├──► trino-kairosdb-connector ──► KairosDB ──► Cassandra (time-series)
       │
       └──► Trino Cassandra connector ────────────────► Cassandra (job accounting, metadata)
```

Everything ExaMon AI sees, the [Analyze](../analyze/index.md) section sees too — the agent is a different presentation of the same data. The agent has no privileged data path and no separate store.

## Prerequisites

- An OpenAI-compatible API endpoint for the LLM. Locally hosted via [Ollama](https://ollama.com/), locally hosted via vLLM, or an external endpoint (any OpenAI-compatible service).
- An ExaMon deployment with a reachable Trino endpoint, plus the catalog/schema/table names of that deployment.
- Python 3.10 or later on the host that runs the agent.

The agent runs in user space; no special privileges are needed beyond access to the Trino endpoint.

## Install

!!! warning "Public install path pending"
    The `pip install examon-ai` path is not yet active on PyPI. The instructions below describe the target install path and the current development install. The target install is the canonical one and will not change in shape when the package goes public; only the source line changes.

### Target install (when public)

```bash
pip install examon-ai
examon-ai init
vi ~/.config/examon-ai/.env       # set TRINO_URL, OLLAMA_API_BASE, catalog names
./run_examon.sh                   # interactive session
```

### Current development install (for evaluators with repository access)

```bash
git clone <repo-url> && cd examon-ai
pip install -e .
examon-ai init
```

`examon-ai init` scaffolds the user configuration directory at `~/.config/examon-ai/` with editable defaults.

## Configure

`examon-ai init` creates:

| File | Purpose |
|---|---|
| `.env` | Deployment variables (Trino URL, LLM endpoint, catalog and schema names). |
| `config.yaml` | HolmesGPT configuration (model, toolsets, runbooks). |
| `system_prompt.txt` | Behavioral prompt (tool discipline, SQL conventions, HPC domain notes). |
| `hpc_tools.yaml` | Toolset definitions (schema exploration, metric discovery, job analysis). |
| `runbooks/` | Investigation workflows (metric discovery, time-series querying, job power, GPU health, ...). |

All five are user-editable; the agent re-reads them on every invocation, no rebuild required.

### Environment variables

```bash
# ~/.config/examon-ai/.env

TRINO_URL=http://trino.example.com:8080
OLLAMA_API_BASE=http://localhost:11434/v1
OPENAI_API_KEY=dummy-key

# Catalog and schema names (deployment-specific)
EXAMON_META_CATALOG=examon_meta
EXAMON_TS_CATALOG=examon_ts_timestamps
EXAMON_METRICS_SCHEMA=kairosdb
EXAMON_JOBS_SCHEMA=e4_slurm
EXAMON_REGISTRY_TABLE=row_keys
EXAMON_JOB_TABLE_PREFIX=job_info_
EXAMON_DEFAULT_CLUSTER=e4red
```

Override only the variables that differ from the reference deployment.

### LLM setup (local Ollama example)

A locally-hosted Ollama endpoint is the simplest deployment for a single operator:

```bash
ollama pull gpt-oss:20b
ollama create gpt-oss-examon -f gpt-oss-examon.Modelfile
```

The Modelfile holds only model parameters (temperature, top_p, ...). Behavioral instructions (tool discipline, SQL rules, HPC expertise) are injected at runtime through HolmesGPT's `--system-prompt-additions` flag from `~/.config/examon-ai/system_prompt.txt`. This indirection is required because HolmesGPT overrides Ollama Modelfile `SYSTEM` blocks with its own Jinja2 template.

For a higher-quality reasoning model, `gpt-oss:120b` (Q4 quantized) is the current primary model on the reference deployment.

## Run

```bash
./run_examon.sh                              # interactive session
./run_examon.sh "what GPU jobs ran today?"   # one-shot question
./run_examon.sh --deep "analyze job failures" # deep reasoning mode
EXAMON_MODEL=openai/qwen35-examon:latest ./run_examon.sh   # override the model
```

Equivalently, by invoking HolmesGPT directly:

```bash
holmes ask \
    --config ~/.config/examon-ai/config.yaml \
    --system-prompt-additions "$(cat ~/.config/examon-ai/system_prompt.txt)" \
    --fast-mode
```

## Verify

Three escalating tests validate any new model and deployment:

### Level 1 — Simple query (0 tool calls expected)

```
what can you do?
```

Pass criteria: direct natural-language answer, no tool calls.

### Level 2 — Metric discovery (3–6 tool calls expected)

```
What metrics are available for node acnode04?
```

Pass criteria: fetches the metric-discovery runbook, calls `metric_info`, presents a structured summary grouped by plugin.

### Level 3 — Time-series analysis (5–10 tool calls expected)

```
Compare CPU1 temperature and FAN2 speed on acnode03 over the last hour
```

Pass criteria: fetches the timeseries runbook, uses pushdown aggregation, builds a CTE/JOIN query against the Trino endpoint.

A new model that passes all three is ready to take real questions.

## Demonstrated capabilities

The outputs below are produced by the reference deployment (`e4red` cluster) running ExaMon AI against a locally deployed LLM (`minimax-m2.5` on vLLM + AMD MI300X). They are presented here as a calibration aid — what to expect from a working install, not a feature list.

### Overview answer (no tool calls)

**Question:** *what can you do?*

The agent answers directly with a list of capability groups: HPC / Slurm operations, metric discovery and analysis, SQL analytics, and (when configured) Kubernetes infrastructure inspection. No tool calls; no database access.

### Data discovery

**Question:** *What metrics are available for node `acnode04`?*

The agent fetches the metric-discovery runbook, calls `metric_info` three times (one per discovery stage), and returns a structured per-plugin breakdown:

- `ipmi_pub`: 46 metrics — CPU and VRM temperatures, voltages (BMC, MB, CPU rails), fan RPMs (FAN2/4/6/8), DIMM temperatures, AOC temperatures.
- `gpu_pub`: 20 metrics — power draw and limit, GPU temperature, current and max clocks, memory (total/used/free), utilization, `clocks_event_reasons` (hardware slowdown flags), ECC error counters, P-state.

### Time-series query with pushdown aggregation

**Question:** *Compare CPU1 temperature and FAN2 speed on `acnode03` over the last hour.*

The agent fetches the timeseries runbook, validates both metrics with `metric_info`, then executes a single Trino query that uses `sampling_aggregator` pushdown to KairosDB. The result is a time-aligned table of CPU temperature and fan RPM, plus a narrative summary: *"CPU temp rose from 50°C to 58°C then stabilized around 57°C. FAN2 remained constant at 13,440 RPM throughout the hour — no dynamic fan response to temperature change observed."*

### Job failure root-cause analysis

**Question:** *Look for failed jobs (not completed successfully) in the last 30 days and probable root cause.*

The agent autonomously explores the job table schema, self-corrects a SQL syntax error, runs 5 queries across about 11K tokens, and returns:

- **263 failed jobs total**, broken down by state + reason (NonZeroExitCode 102, TimeLimit 62, various Cancelled 58, OutOfMemory 28, JobLaunchFailure 8, NodeDown 3, BadConstraints 2).
- A per-user table identifying that one user accounts for 57% of all failures.
- Per-user actionable recommendations (debug application crashes; increase memory limits; increase time limit; check specific node health).
- A flag on three `NODE_FAIL` events on the same node suggesting possible hardware instability.

### Cross-domain GPU health analysis

**Question:** *Do a complete GPU data analysis for node `cn01` over the last 90 days.*

The agent runs 12 queries across about 15K tokens, profiling 15 DCGM GPU metrics, and returns a structured analysis:

- Node configuration (GPU models, driver versions).
- Aggregated summary statistics across all GPUs (temperature, power, utilization, framebuffer use, memory temperature, clocks).
- Total energy consumption for the 90-day window.
- Per-GPU breakdown (samples, avg/peak temperature, avg/peak power, utilization, FB use).
- A **flagged anomaly**: 4.1M XID hardware errors over 90 days, prompting an investigation recommendation for GPU health (likely ECC corrections, page faults, or thermal throttling).

The XID flag is the kind of cross-domain signal that motivates the whole architecture: the agent had no prior knowledge that `cn01` was a GPU node, no hardcoded list of metrics to check, and no pre-built dashboard for this question; it discovered everything from the schema and ran the analysis on demand.

## Customize

After `examon-ai init`, everything under `~/.config/examon-ai/` is editable. Changes take effect immediately — no reinstall, no rebuild.

### Add a new tool

Create a Python script under `~/.config/examon-ai/toolsets/`:

```python
#!/usr/bin/env python3
"""My custom tool — describe what it does."""

import sys
from examon_ai.trino_client import run_query
from examon_ai.config import META_CATALOG
from examon_ai.utils import parse_cli_args, print_json

def my_analysis(param1, param2=None):
    sql = (
        f"SELECT * FROM {META_CATALOG}.my_schema.my_table "
        f"WHERE col = '{param1}' LIMIT 10"
    )
    return run_query(sql)

if __name__ == "__main__":
    cli = parse_cli_args(sys.argv[1:])
    result = my_analysis(
        param1=cli.get("param1"),
        param2=cli.get("param2"),
    )
    print_json(result)
```

Register it in `~/.config/examon-ai/hpc_tools.yaml`:

```yaml
my_domain/analysis:
  description: "My custom analysis tools"
  tools:
    - name: my_analysis
      description: "Describe what this does so the LLM knows when to use it"
      parameters:
        param1:
          type: string
          description: "What this parameter means"
          required: true
        param2:
          type: string
          description: "Optional parameter"
          required: false
      command: "python3 ~/.config/examon-ai/toolsets/my_tool.py param1={{ param1 }} param2={{ param2 }}"
```

The new tool is immediately available in the next `./run_examon.sh` session.

### Add a new runbook

Write a Markdown file at `~/.config/examon-ai/runbooks/core/my-workflow.md` and register it in the relevant `catalog.json`:

```json
{
  "runbooks": [
    {"name": "my-workflow.md", "description": "When and how to use this workflow"}
  ]
}
```

Optionally add a `MANDATORY RUNBOOK GATE` in `hpc_tools.yaml`'s `llm_instructions` so the LLM is forced to fetch the runbook for the matching question class.

### Reset to defaults

```bash
examon-ai init --force
```

This overwrites every file under `~/.config/examon-ai/` with the bundled defaults, including `.env`. Back the `.env` up first if it contains site-specific overrides.

## Library imports available to custom tools

Custom tool scripts can import from the pip-installed library:

| Import | What it provides |
|---|---|
| `from examon_ai.config import META_CATALOG, TS_CATALOG, ...` | Deployment-specific names, env-var-backed. |
| `from examon_ai.trino_client import run_query, run_query_with_catalog` | Trino query execution with connection management. |
| `from examon_ai.utils import normalize, parse_cli_args, print_json` | CLI parsing, JSON output formatting. |
| `from examon_ai.tools.schema import list_catalogs, execute_query, ...` | Schema exploration helpers. |
| `from examon_ai.tools.metric_info import metric_info` | Metric metadata discovery. |
| `from examon_ai.tools.job_power import get_job_power` | Job power analysis. |

## Limitations

- **Data quality bounds the agent.** ExaMon AI is only as good as the metrics, tags, and job records present in the deployment. Missing tags, inconsistent metric naming, and partial Slurm accounting all show up as agent confusion.
- **LLM quality bounds the agent.** Small models (≤ 7B parameters) commonly fail at SQL discipline (incorrect quoting, missing `CAST`, malformed `WHERE`). The current reference deployment uses `gpt-oss:120b` (Q4); 20B and smaller models are usable for simple discovery questions but struggle on complex cross-store analyses.
- **Discovery costs tokens.** The discovery-first design means every non-trivial question issues multiple tool calls before composing the final query. Complex questions can run 10–15K tokens.
- **Read-only.** The agent does not write back to ExaMon. No alert creation, no Slurm job submission, no infrastructure change.
- **Beta**. Documentation and packaging are still being prepared. The architecture and the example outputs above are stable; the install URL is the part that will change.

---

## Source

- ExaMon AI architecture documentation: in-development.
- HolmesGPT: [HolmesGPT/holmesgpt](https://github.com/HolmesGPT/holmesgpt) (the underlying LLM reasoning loop).
- Trino query surface used by every tool: [Trino](https://trino.io/).
- Local LLM hosting: [Ollama](https://ollama.com/), [vLLM](https://github.com/vllm-project/vllm).
- Reference deployment: e4red cluster (the same testbed the [Analyze](../analyze/index.md) demo notebook targets).
