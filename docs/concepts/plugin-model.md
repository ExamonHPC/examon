# Plugin Model

!!! info "Status: Live (reproduced 2026-05-23)"
    Verified against [`examon-base-plugin`](https://github.com/E4-Computer-Engineering/examon-base-plugin) (SDK v3) on v0.5.0. The architectural model below is stable; the worker reference is the upstream library README.

> This page is the architectural background to the SDK v3 plugin framework: the ETL pipeline as a model, the worker lifecycle, the queue model that connects stages, the restart semantics, the three concurrency modes, the job replication primitive, and the migration story from the legacy `examon-common` predecessor. The [SDK v3 developer page](../developers/sdk-v3/index.md) covers the concrete "how to write a publisher" path; this page explains *why* the framework is shaped the way it is.

## Why a plugin model

Every publisher in ExaMon does the same three things: read data from a source, reshape it into the canonical [tagged time-series form](data-model.md#the-time-series-model), and ship it to a target (the MQTT broker, KairosDB, or both). The differences between publishers are local to the source: Prometheus is HTTP/JSON, IPMI is BMC sensors over the network, NVML is a C library, Slurm accounting is database polling. The shared 90% (worker scheduling, restart on failure, MQTT or KairosDB connection handling, graceful shutdown, configuration parsing) has no business being re-implemented per publisher.

The SDK v3 plugin framework is the answer to that observation. It supplies the shared 90% as a library (`examon-base-plugin`) and constrains the publisher to plug into three well-defined extension points: `Extract`, `Transform`, `Load`. A new publisher is the three extension classes (or one, if it reuses two built-ins) and a YAML configuration file. The publisher does not implement its own worker pool, its own restart logic, or its own configuration parser.

The benefit is consistency. Every SDK v3 publisher has the same lifecycle (`run` / `start` / `stop` / `restart`), the same configuration shape, the same logging conventions, the same restart-on-failure behavior. An operator who knows one publisher knows the operational shape of every publisher.

The cost is the framework's opinion. A publisher that needs a non-pipeline shape (a long-running daemon that maintains state across samples, an event-driven model that does not fit `Extract → Transform → Load`) either fits awkwardly inside SDK v3 or sits outside it. In practice every shipped publisher fits.

## The ETL pipeline as a model

The pipeline:

```
Source -> Extract worker -> [queue] -> Transform worker -> [queue] -> Load worker -> Target
```

Three stages, each is a worker, queues between stages.

### Stages have different default lifecycles

| Stage | Default worker type | Why |
|---|---|---|
| Extract | `loop` | Most sources are polled: a Prometheus scrape, an IPMI sensor read, a database query on an interval. The `loop` type runs the extract function on a fixed `interval`. |
| Transform | `stream` | Transforms run on every message that arrives from the upstream queue; they have no scheduling concern of their own. The `stream` type blocks on input and processes as messages arrive. |
| Load | `stream` | Same as transform: a load worker writes whatever the transform stage hands it. |

An extract worker can also be `stream` (for sources that push data, like an MQTT subscriber); a transform or load worker can be `loop` (rare, used for batching or for periodic flushing). The default per-stage type matches the conventional case; overriding it is explicit in the YAML.

### Queues are bounded

The framework uses `multiprocessing.Queue` between stages with `queue_maxsize` (default 1000) capping the number of in-flight messages. The cap exists to handle back-pressure: if the load stage cannot keep up with the extract stage, the queue fills, the extract worker's `put` blocks, and the source is implicitly throttled.

The behavior matters because the alternative (an unbounded queue) silently grows memory until the publisher is OOM-killed when the load target is slow or unreachable. The bounded queue makes the back-pressure visible: the operator sees the extract loop pause rather than a crashed publisher.

### Workers are restartable, not crash-proof

A worker that throws an unhandled exception is logged, terminated, and restarted by the framework with exponential backoff:

| `restart_backoff` setting | Default | Effect |
|---|---|---|
| `initial` | 2 seconds | First restart waits this long after the crash. |
| `max` | 60 seconds | The cap on the backoff growth. |
| `reset_alive` | 30 seconds | If the restarted worker stays alive for at least this long, the backoff resets. |

The shape matters for the common failure case of an intermittently flaky upstream. The first failure restarts immediately (2s); a tight crash loop backs off to 60s and stays there until the upstream recovers; once the worker stays up for 30s, the backoff resets so the next isolated failure restarts quickly again. The publisher does not need its own retry logic: the framework provides it uniformly.

The deliberate non-feature is that a permanently broken worker is allowed to keep retrying forever. ExaMon assumes the upstream will eventually come back; it does not fail-fast a publisher because that would silently lose data when the operator is not looking.

## Concurrency: three modes

The framework supports three execution models, chosen at invocation time, not in the configuration. The model affects only how workers are scheduled; the pipeline shape is identical in all three.

### Mode 1: process per stage (default)

Each stage runs in its own Python process. Inter-stage communication uses `multiprocessing.Queue`. This is the safest mode: a transform crash does not bring down extract, and the GIL is a per-process bottleneck not a per-pipeline bottleneck.

The cost is process overhead: each stage carries its own Python interpreter and its own copy of the library state. For lightweight publishers this is invisible; for high-throughput publishers (thousands of samples per second per worker) the process boundary's serialization cost shows up.

### Mode 2: `--threads`

All stages run as Python threads in the main process. Queues become `queue.Queue` (thread-safe but not process-safe). The pipeline is identical in shape but executes in one process, one interpreter, one GIL.

The benefit is lower per-message latency (no serialization across the process boundary). The cost is that any stage's crash brings down the whole publisher (the framework still restarts the worker, but the process boundary's isolation is gone).

Useful when the publisher is I/O-bound (most of the work is socket reads and HTTP calls, the GIL is rarely held) and latency matters.

### Mode 3: `--threads --process-per-job`

One OS process per job. Each job's stages run as threads inside that process. Inter-job queues remain `multiprocessing.Queue`.

This preserves crash isolation at the job boundary (a failure in job A does not affect job B) while reducing the per-stage process overhead within a job. It is the right mode for a publisher with many independent jobs (one per cluster, one per source).

The default is mode 1. Switching modes is a tuning decision, made when the default has been observed to be insufficient.

## Job replication

`replicate_on` operates at the job level. A job replicated across N items becomes N independent jobs, each with its own extract/transform/load triplet:

```yaml
jobs:
  - name: per_cluster
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

The four supported shapes (`list`, `range`, `line`, `directory`) mirror `foreach`. The difference is the level at which the replication operates:

| Primitive | Level | Use when |
|---|---|---|
| `foreach` | Inside a single worker stage | Multiple sources of the same kind that share the rest of the pipeline. (Multiple Prometheus servers, single load target.) |
| `replicate_on` | Whole-job | Independent pipelines per item. Crash isolation between items matters; per-item rate limiting matters; per-item configuration drift matters. |

A publisher running against 50 Prometheus servers with the same load target uses `foreach`. A publisher running against 50 clusters where each cluster has its own ingest endpoint and its own failure budget uses `replicate_on`.

## What the framework is not

It is worth being precise about the framework's scope:

- **It is not a stream-processing engine.** There is no windowing, no aggregation, no state across messages. Each message flows independently through the pipeline; cross-message state is the publisher's responsibility (and is rarely needed).
- **It is not a scheduler.** It runs the publisher; it does not decide when to run the publisher or what nodes to run it on. Fleet rollout uses Ansible, systemd, or `examon-scheduler` (planned).
- **It is not opinionated about the wire format.** The `Extract` stage returns Python objects; the `Transform` stage reshapes them; the `Load` stage serializes. The shape on the wire is the Load stage's choice. The conventional choice for MQTT is the [JSON payload described in the data model](data-model.md#payload-format), but a custom loader can ship in any format the bridge or store accepts.

## The legacy `examon-common` predecessor

Before SDK v3 there was `examon-common`: the publisher framework used in the v0.4.0 line. Its conceptual shape is similar (a pipeline, workers, queues), but the framework was less opinionated, the configuration model was less structured (mostly Python plus a `.conf` file), and the lifecycle around restart and shutdown was per-publisher rather than framework-supplied.

SDK v3 was designed to keep the data model identical (so v0.4.0-style publishers and v0.5.0-style publishers interoperate on the wire) while improving the developer ergonomics and the operational shape. The migration path per legacy publisher is:

1. Replace the legacy entry point with the four-line `ExamonApp` form.
2. Move the per-publisher configuration into the canonical YAML shape.
3. Re-implement the legacy extract / transform / load classes against the SDK v3 interfaces. The actual scraping logic typically transfers verbatim; only the framework adapter changes.

Several publishers (`prometheus_pub`, `ipmi_pub`, `nvml_pub`, `pmu_pub`, `slurm_pub`) have already migrated; the remaining legacy publishers are tracked in [Reference → Component catalog](../reference/component-catalog.md#publishers-sdk-v3-framework-collectors).

The intent is that `examon-common` is deprecated when every legacy publisher has been migrated, not before. There is no in-place upgrade path; the migration is a rewrite per publisher (often a small one, since the source-specific logic carries over directly).

## Related reading

- [Developers → SDK v3](../developers/sdk-v3/index.md): how to write a publisher in practice, with the built-in worker catalog.
- [Administrators → Publishers](../administrators/publishers/index.md): the install pattern and fleet rollout considerations.
- [Concepts → Data model](data-model.md): what the framework's output looks like on the wire and in storage.
- [Reference → Configuration](../reference/configuration.md): the full publisher YAML schema.

---

## Source

- SDK v3 base library: [E4-Computer-Engineering/examon-base-plugin](https://github.com/E4-Computer-Engineering/examon-base-plugin).
- Reference per-source publisher: [E4-Computer-Engineering/prometheus_pub](https://github.com/E4-Computer-Engineering/prometheus_pub).
- The in-cluster MQTT-to-KairosDB bridge built on the same framework: [E4-Computer-Engineering/mqtt2kairosdb-v3](https://github.com/E4-Computer-Engineering/mqtt2kairosdb-v3).
