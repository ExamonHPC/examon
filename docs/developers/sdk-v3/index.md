# SDK v3

!!! info "Status: Live (reproduced 2026-05-23)"
    Verified against [`examon-base-plugin`](https://github.com/E4-Computer-Engineering/examon-base-plugin) on v0.5.0. The framework is in production use across every shipped SDK v3 publisher (`prometheus_pub`, `ipmi_pub`, `nvml_pub`, `pmu_pub`, `slurm_pub`).

> SDK v3 is the framework for writing ExaMon publishers. A new publisher is a four-line `ExamonApp` entry point plus a YAML configuration file describing one or more extract / transform / load pipelines; everything else (workers, lifecycle, restart backoff, MQTT and Cassandra connection handling, job replication, the three concurrency modes) is supplied by the base library. This page describes the architectural shape; the [Publishers](../../administrators/publishers/index.md) section covers install + run end to end, with the reference [Prometheus publisher](../../administrators/publishers/prometheus-pub.md) as a worked example.

## The four-line entry point

Every SDK v3 publisher boils down to the same Python entry point:

```python
from examon.plugin.examonapp import ExamonApp

if __name__ == '__main__':
    args = ExamonApp.parse_args()
    app = ExamonApp(args.config, args.runmode)
    app.run()
```

The shape of the publisher — what it scrapes, how it transforms, where it sends the result — is defined entirely in the YAML configuration. Switching a publisher from "scrape Prometheus and write to KairosDB" to "scrape Prometheus and publish over MQTT" is a one-block edit, no Python change.

## Install

```bash
git clone https://github.com/E4-Computer-Engineering/examon-base-plugin.git
cd examon-base-plugin
pip install .
```

This installs the `examon.plugin` package (the `ExamonApp` runtime), the queue/worker infrastructure, and every built-in worker listed below.

For a publisher under development, create a sibling directory:

```
my_pub/
    my_pub.py            # the four-line ExamonApp entry point
    config/
        plugin.yaml      # the pipeline definition
    extract/
        my_extractor.py  # custom extractor (optional)
    transform/
        my_transformer.py# custom transformer (optional)
    load/
        my_loader.py     # custom loader (optional)
```

Custom extract / transform / load classes inherit from the base interfaces shipped by `examon-base-plugin`. Only the stages the publisher actually customizes need a class; for the others, point the configuration at a built-in.

## The ETL pipeline

Every job in a publisher follows the same three-stage pipeline:

```
Source -> Extract worker -> Transform worker -> Load worker -> Target
```

Each stage has its own worker pool. The default execution model is one Python process per stage with multiprocessing queues between stages.

| Stage | What it does | Built-in examples |
|---|---|---|
| **Extract** | Reads from a source on an interval, or as a stream. | `RandomNumberGenerator`, `MQTTSubscriber`, `QueueReader`. Per-source extractors (Prometheus, IPMI, NVML, ...) live in the per-publisher repositories. |
| **Transform** | Normalizes the source-specific shape into a target-specific shape. Typically applies tag mappings and adds organizational metadata. | `PassThroughTransformer`, `NumberTransformer`, `NumberMultiplierTransformer`, `KairosDBTransformer`, `PBSNodeTransformer`, `PBSJobTransformer`. |
| **Load** | Writes to the configured target. | `DebugLoader` (stdout), `QueueLoader` (chain to another job), `MQTTPublisher`, `KairosDBLoader`, `CassandraLoader`. |

A publisher chooses one built-in per stage, or writes its own; mixing built-ins and custom workers in the same pipeline is the common case.

## Worker types

Each worker has a *type* that controls its lifecycle:

| Worker type | Behavior |
|---|---|
| `loop` | Runs on a fixed interval (`interval: 60`). The default for extractors that poll a source. |
| `stream` | Runs continuously, blocking on input. The default for transformers and loaders, and for extractors that read from a streaming source (MQTT, queue). |

The framework restarts failed workers with exponential backoff (`restart_backoff.initial`, `restart_backoff.max`, `restart_backoff.reset_alive`). A worker that crashes and immediately succeeds is fine; a worker that crashes repeatedly is throttled.

## Worker pools and parallelism

Workers within a stage can be fanned out using `foreach`, which creates one worker per item:

```yaml
extract:
  module: my_pub.extract.scraper
  class: PrometheusMetricsScraper
  type: loop
  interval: 60
  foreach:
    type: list
    items:
      - prometheus_url: http://node-01:9090
        specific_metrics: ["node_cpu_seconds_total"]
      - prometheus_url: http://node-02:9090
        specific_metrics: []
```

`foreach` supports four shapes: `list` (explicit items), `range` (a numeric range), `line` (lines of a file), and `directory` (files matching a glob).

Each item in the `foreach` becomes a worker with its own parameters; multiple workers in the same stage process different sources in parallel.

## Job replication

`replicate_on` operates at the *job* level rather than the *stage* level. A job replicated across N items becomes N independent jobs, each with its own extract/transform/load triplet, processing one of the items:

```yaml
jobs:
  - name: per_cluster_collector
    replicate_on:
      type: line
      target: /etc/examon/clusters.txt
    extract:
      module: my_pub.extract.scraper
      class: PrometheusMetricsScraper
      params:
        prometheus_url: "http://{{ replicate_item }}:9090"
    transform: ...
    load: ...
```

Each replicated job receives the replicating item as `replicate_item` in worker `params`, available for templating. The four `replicate_on` shapes mirror `foreach` (list, range, line, directory).

`foreach` parallelizes inside a stage; `replicate_on` parallelizes the whole pipeline. The choice depends on isolation: `foreach` shares a job's pipeline (and its restart envelope); `replicate_on` gives each item its own isolated pipeline.

## Concurrency modes

The base library runs each pipeline stage in its own Python process by default, with `multiprocessing` queues between stages. Two flags adjust this:

| Mode | Flag | When to use |
|---|---|---|
| Process per stage (default) | (no flag) | The safest choice. Each stage is fully isolated; a crash in transform does not bring down extract. |
| Threads inside one process | `--threads` | Lower per-message latency. All stages share the same Python process and the same GIL. Useful for I/O-bound publishers where the GIL is rarely held. |
| Process per job, threads per stage | `--threads --process-per-job` | One OS process per job; each job's stages run as threads, but inter-job queues remain `multiprocessing` queues. Preserves crash isolation at the job boundary while reducing per-stage process overhead. |

Most publishers use the default. The `--threads` modes are tuning knobs for high-throughput cases.

## Configuration shape

The YAML configuration has two top-level sections: a `global` block and a list of `jobs`.

### Global

| Block | Purpose |
|---|---|
| `global.daemon` | Process lifecycle: log file, PID file, log level, monitor interval, queue size, restart backoff. |
| `global.mqtt` | MQTT broker connection (when the publisher loads via MQTT). |
| `global.kairosdb` | KairosDB endpoint (when the publisher loads directly into KairosDB). |
| `global.cassandra` | Cassandra connection (when the publisher loads directly into Cassandra). |
| `global.examon` | ExaMon-wide tag policy and MQTT topic shape: `tags` (the canonical `org` / `cluster` / `plugin` / `chnl` / `node` set), `topic_prefix`, `sanitize_topic`, `topic_cache.{enabled,size}`. |

`global.examon.tags` is what defines the publisher's identity in the data: every metric the publisher emits is stamped with these tags and the bridge writes them through to KairosDB. The `node` tag is commonly dynamic (extracted from a per-sample label via a regex).

### Jobs

Each job has:

- A unique `name`.
- Optional `replicate_on` (whole-pipeline replication, see above).
- A required `extract`, `transform`, and `load` block, each specifying `module`, `class`, optional `type` (`stream` or `loop`), optional `foreach` (worker fan-out), and optional `params` (passed to the worker constructor).

The full schema, key by key with every default, lives in [Reference → Configuration](../../reference/configuration.md).

## Built-in workers

The base library ships ready-to-use workers for the common cases. Per-source workers (Prometheus, IPMI, NVML, ...) live in the per-publisher repositories.

### Extractors

| Class | What it does |
|---|---|
| `RandomNumberGenerator` | Generates synthetic numeric samples. Useful for end-to-end pipeline tests; powers the bundled `random_pub` test publisher. |
| `QueueReader` | Reads from a `multiprocessing.Queue`. Used to chain jobs together when paired with `QueueLoader`. |
| `MQTTSubscriber` | Subscribes to MQTT topics from `global.mqtt`. The standard input stage for a pure consumer. |
| `PBSNodeReader`, `PBSJobReader` | PBS scheduler integration (TBD; placeholder in the upstream library). |

### Transformers

| Class | What it does |
|---|---|
| `PassThroughTransformer` | No-op; passes data downstream untouched. |
| `NumberTransformer` | Adds the tags from `global.examon.tags` to a numeric sample (test example). |
| `NumberMultiplierTransformer` | Multiplies a numeric value by `multiplier` from `params` (test example). |
| `KairosDBTransformer` | Reshapes data into KairosDB ingest format (TBD; the per-source transformers in publisher repositories typically subclass or replace this). |
| `PBSNodeTransformer`, `PBSJobTransformer` | PBS integration (TBD). |

### Loaders

| Class | What it does |
|---|---|
| `DebugLoader` | Writes received samples to the log. The standard development loader for verifying the extract+transform stages without touching a real backend. |
| `QueueLoader` | Sends samples to one or more other jobs by name (`params.target_jobs`). The mechanism for fan-out across jobs. |
| `MQTTPublisher` | Publishes to the MQTT broker from `global.mqtt`. The standard way to ship into core via the broker. |
| `KairosDBLoader` | Writes directly to the KairosDB HTTP API. Used when the publisher does not go through MQTT. |
| `CassandraLoader` | Writes directly into Cassandra (TBD; primarily for structured data such as Slurm job records that bypass the time-series path). |

The status notes (`TBD`, "test example") match the current state of the upstream `examon-base-plugin` README. A publisher targeting one of these surfaces today typically ships its own transformer/loader subclass; the test workers are useful as templates.

## Worked example

The repository ships a Jupyter notebook walking through the construction of a working publisher end to end:

- [`examon_pub.ipynb`](examples/examon_pub.ipynb) — a step-by-step build that exercises the ExamonApp entry point, the configuration loader, the worker types, and the queue model.

The reference per-publisher example with full install instructions is the [Prometheus publisher](../../administrators/publishers/prometheus-pub.md): a complete SDK v3 publisher with its own repository, the same shape every new publisher should follow.

## Related reading

- [Publishers (overview)](../../administrators/publishers/index.md) — the install pattern shared across every SDK v3 publisher, plus fleet rollout considerations.
- [Concepts → Plugin model](../../concepts/plugin-model.md) — the architectural background on workers, queues, restart semantics, and the relationship between SDK v3 and the legacy `examon-common` predecessor.
- [Reference → Configuration](../../reference/configuration.md) — the full publisher YAML schema, key by key.

---

## Source

- SDK v3 base library: [E4-Computer-Engineering/examon-base-plugin](https://github.com/E4-Computer-Engineering/examon-base-plugin).
- Reference publisher implementation: [E4-Computer-Engineering/prometheus_pub](https://github.com/E4-Computer-Engineering/prometheus_pub).
- Example notebook included in this site: [`examples/examon_pub.ipynb`](examples/examon_pub.ipynb).
