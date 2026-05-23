# Publishers

!!! info "Status: Live (reproduced 2026-05-23)"
    Verified against examon-base-plugin (SDK v3) on v0.5.0. Individual publisher repositories are at varying maturity levels; see the catalog table below.

> A publisher is an off-cluster process that collects metrics from a single host or external service and pushes them as MQTT messages into a running ExaMon broker. Publishers are the per-node leaf in the data pipeline: where the deployment chapter brings up *core* (broker, bridge, store, dashboard), this chapter brings up the *edges* (the hosts that feed core).

## What a publisher is

A publisher is a standalone Python program built on the SDK v3 plugin library ([`examon-base-plugin`](https://github.com/E4-Computer-Engineering/examon-base-plugin)). It runs on the host it collects from, scrapes a local data source on an interval, and publishes the result to the central MQTT broker. The broker forwards the data to the `mqtt2kairosdb` bridge, which writes it into the time-series store.

A publisher is intentionally tiny:

- A four-line `<plugin>_pub.py` entry point.
- A YAML configuration file describing the extract / transform / load pipeline.
- Optionally, a systemd unit so it runs as a service.

Everything else (worker scheduling, restart backoff, MQTT connection handling, graceful shutdown) is supplied by the base plugin library. New publishers reuse the framework rather than rewriting it.

## SDK v3 versus legacy publishers

ExaMon has two generations of publishers:

| Generation | Where it lives | Status |
|---|---|---|
| **SDK v3** | Built on [`examon-base-plugin`](https://github.com/E4-Computer-Engineering/examon-base-plugin); each publisher is its own repository | Recommended for all new publishers. |
| **Legacy (examon-common)** | Embedded in the historical `examon` monorepo; uses the older `examon.plugin` package | Functional, but not the install path for new work. The migration path is per-publisher rewrites on SDK v3. |

The SDK v3 install pattern is described below and is identical across every SDK v3 publisher. Legacy publishers carry their own install instructions inside the publisher repository.

## The generic install pattern (SDK v3)

Every SDK v3 publisher follows the same three steps. Replace `<publisher>` with the publisher name (for example, `prometheus_pub`).

### 1. Install the base library and the publisher

```bash
# Base library (once per host)
git clone https://github.com/E4-Computer-Engineering/examon-base-plugin.git
cd examon-base-plugin
pip install .

# Publisher
git clone https://github.com/E4-Computer-Engineering/<publisher>.git
cd <publisher>
pip install -r requirements.txt
```

### 2. Configure

Copy the example configuration and edit it for the local host:

```bash
cp config/plugin.yaml config/my_config.yaml
```

The configuration has two top-level sections that every SDK v3 publisher shares:

- `global.daemon`: process lifecycle (log file, PID file, log level, restart backoff, monitor interval).
- `global.examon.tags`: the identifying tags attached to every emitted metric (`org`, `cluster`, `node`, `plugin`, `chnl`).
- One or more `jobs[]` entries, each defining an `extract` / `transform` / `load` pipeline with its own worker pool.

The `load` stage targets either KairosDB directly (HTTP write) or MQTT (for shipping into core via the broker). For a publisher running on a remote node, the MQTT loader is the standard choice; the in-cluster `mqtt2kairosdb` bridge handles the broker-to-store hop.

### 3. Run

In the foreground (for development and first-time verification):

```bash
python <publisher>.py -c config/my_config.yaml run
```

As a daemon (for ongoing operation):

```bash
python <publisher>.py -c config/my_config.yaml start
```

Stop, restart, and status follow the same pattern:

```bash
python <publisher>.py -c config/my_config.yaml stop
python <publisher>.py -c config/my_config.yaml restart
```

### Run as a systemd service

For unattended operation, wrap the publisher in a systemd unit:

```ini
[Unit]
Description=ExaMon Publisher (<publisher>)
After=network.target

[Service]
Type=forking
User=examon
WorkingDirectory=/opt/examon/<publisher>
ExecStart=/usr/bin/python3 <publisher>.py -c /etc/examon/<publisher>.yaml run
KillSignal=SIGINT
PIDFile=/var/run/examon/<publisher>.pid
Restart=always

[Install]
WantedBy=multi-user.target
```

`SIGINT` triggers the graceful shutdown path inside the base library, draining in-flight workers before exit.

## Concurrency model

The base library runs each pipeline stage in its own Python process by default, with queues between stages. Two flags adjust this:

- `--threads` runs every stage as Python threads inside the main process.
- `--threads --process-per-job` launches one OS process per job, each running its stages as threads, while inter-job queues remain `multiprocessing` queues.

The thread-only mode trades isolation for lower per-message latency; the per-job mode preserves crash isolation at the job boundary. The default (process-per-stage) is the safest choice for new deployments and is what the publisher repositories ship.

## Fleet rollout considerations

A single publisher per host is the per-node unit; an operator running ExaMon on a cluster typically installs the same publisher across dozens or hundreds of nodes:

- **Configuration management.** The YAML file changes per host only in identifying tags (`node`, sometimes `cluster`). Templating via Ansible / Puppet / Salt is the standard practice; the per-host overlay is small.
- **MQTT topic naming.** Every publisher emits to a topic shape derived from its `global.examon.tags` (commonly `<org>/<cluster>/<plugin>/<node>/...`). The bridge subscribes to wildcards, so adding more nodes does not require central reconfiguration.
- **Authentication.** When the broker has MQTT authentication enabled, credentials are passed via the publisher's MQTT loader configuration. The broker's [Mosquitto password file](https://mosquitto.org/documentation/authentication-methods/) is the simplest mechanism; secret distribution is the operator's responsibility.
- **Sizing.** Publishers are I/O-bound (HTTP scrape or socket read, then MQTT publish). A single node typically runs one publisher per data source (one Prometheus scraper, one IPMI scraper, etc.); workers within a publisher scale via the `foreach` mechanism inside the job configuration.

## Catalog (v0.5.0)

The publishers below are tracked in the [Component catalog](../../reference/component-catalog.md#publishers-sdk-v3-framework-collectors). Each one is a separate repository released independently of `examon-core`.

| Publisher | Collects from | Status | Source |
|---|---|---|---|
| `prometheus_pub` | Prometheus servers (query API or `/metrics` endpoint) | Live | [E4-Computer-Engineering/prometheus_pub](https://github.com/E4-Computer-Engineering/prometheus_pub) |
| `ipmi_pub` | BMC out-of-band sensors via IPMI | Live | [E4-Computer-Engineering/ipmi_pub](https://github.com/E4-Computer-Engineering/ipmi_pub) |
| `nvml_pub` | NVIDIA GPU telemetry via NVML | Live | [E4-Computer-Engineering/nvml_pub](https://github.com/E4-Computer-Engineering/nvml_pub) |
| `pmu_pub` | CPU performance counters via Linux `perf` | Live | [E4-Computer-Engineering/pmu_pub](https://github.com/E4-Computer-Engineering/pmu_pub) |
| `slurm_pub` | Slurm accounting and job state | Live | [E4-Computer-Engineering/slurm_pub](https://github.com/E4-Computer-Engineering/slurm_pub) |
| `mqtt2kairosdb-v3` | MQTT-to-KairosDB bridge (in-cluster, not a per-node publisher) | Live | [E4-Computer-Engineering/mqtt2kairosdb-v3](https://github.com/E4-Computer-Engineering/mqtt2kairosdb-v3) |

## In this section

- [**Prometheus publisher**](prometheus-pub.md): the reference SDK v3 publisher install. Read this first to see the end-to-end install path concretely; other SDK v3 publishers follow the same shape.

The remaining publishers above use the same install pattern documented here and detailed in the Prometheus page. Per-publisher pages will land in later cycles; the publisher repositories themselves are the authoritative install reference today.

---

## Source

- SDK v3 base library: [`E4-Computer-Engineering/examon-base-plugin`](https://github.com/E4-Computer-Engineering/examon-base-plugin).
- Prometheus publisher: [`E4-Computer-Engineering/prometheus_pub`](https://github.com/E4-Computer-Engineering/prometheus_pub).
- Component catalog entries: [Reference → Component catalog](../../reference/component-catalog.md#publishers-sdk-v3-framework-collectors).
