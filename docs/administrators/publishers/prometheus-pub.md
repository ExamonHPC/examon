# Prometheus Publisher

!!! info "Status: Live (reproduced 2026-05-23)"
    Verified against [`prometheus_pub`](https://github.com/E4-Computer-Engineering/prometheus_pub) on the SDK v3 base library.

> The Prometheus publisher scrapes metrics from one or more Prometheus servers and forwards them into ExaMon. It is the reference SDK v3 publisher: the install pattern, configuration shape, and operational behavior documented here apply to every SDK v3 publisher with only the extract module differing.

## What it does

Each Prometheus publisher worker connects to a configured Prometheus server, runs queries on a fixed interval, converts the response into ExaMon's tagged time-series format, and ships the result to a load target (KairosDB directly, or the MQTT broker for forwarding by the in-cluster bridge). The publisher uses the SDK v3 ETL pipeline:

```
Prometheus server -> Extract worker -> Transform worker -> Load worker -> KairosDB / MQTT
```

Multiple Prometheus servers can be scraped in parallel by listing them under a single job's `foreach` block. Multiple distinct jobs can run in the same publisher process (for example, one for critical fast-poll metrics, one for a slower background poll).

## When to use it

The Prometheus publisher is the right entry point in two common situations:

- An existing site already runs Prometheus (typically for Kubernetes or infrastructure monitoring) and wants ExaMon's long-term storage, federation, and HPC-shaped analytics on top of the same data without re-instrumenting.
- A site uses Prometheus exporters (node_exporter, dcgm_exporter, ipmi_exporter, etc.) on the nodes themselves and wants those exports collected into ExaMon without writing a custom publisher per exporter.

For sites that do not already run Prometheus, the per-source publishers (`ipmi_pub`, `nvml_pub`, `pmu_pub`, `slurm_pub`) are usually a more direct fit because they read the source data directly without the Prometheus hop.

## Prerequisites

- Python 3.10 or later on the host running the publisher.
- Network access from the host to every Prometheus server to be scraped (typically port 9090).
- Network access from the host to the ExaMon load target (the central MQTT broker, or KairosDB directly if loading without the broker).
- Authentication credentials for the Prometheus servers, if they require authentication.

The publisher host does not need to run Prometheus itself; it is a remote scraper.

## Install

### Step 1: Install the SDK v3 base library

```bash
git clone https://github.com/E4-Computer-Engineering/examon-base-plugin.git
cd examon-base-plugin
pip install .
```

The base library installs the `examon.plugin` package, the `ExamonApp` entry point, and the worker/queue infrastructure shared by every SDK v3 publisher.

### Step 2: Install the Prometheus publisher

```bash
git clone https://github.com/E4-Computer-Engineering/prometheus_pub.git
cd prometheus_pub
pip install -r requirements.txt
```

### Step 3: Create a configuration file

The repository ships an example at `config/plugin.yaml`. Copy it and edit the copy:

```bash
cp config/plugin.yaml config/my_prometheus.yaml
```

The minimum edits for a working publisher are described in the next section.

## Configure

The configuration has three concerns: daemon lifecycle, ExaMon tagging, and the job pipeline. The example below is the minimum needed to scrape one Prometheus server and load into KairosDB.

```yaml
version: "0.4"

global:
  daemon:
    log_filename: prometheus_pub.log
    pid_filename: prometheus_pub.pid
    log_level: INFO
    log_max_bytes: 10485760
    monitor_interval: 60
    restart_backoff:
      initial: 10
      max: 60
      reset_alive: 60
    timeout: 120

  kairosdb:
    servers: kairosdb.example.com
    port: 8083
    username: ""
    password: ""

  examon:
    tags:
      org: examon
      cluster: production
      node:
        key: instance
        regex: "^[^:]*"
      plugin: prometheus_pub
      chnl: data

jobs:
  - name: prometheus_scraper
    extract:
      module: extract.prometheus_scraper
      class: PrometheusMetricsScraper
      type: loop
      interval: 60
      params:
        prometheus_url: http://prometheus.example.com:9090
        specific_metrics: []
        excluded_metrics: []
        query_timeout: 30
        exporter_name: default_exporter
    transform:
      module: transform.prometheus_transformer
      class: PrometheusToKairosDBTransformer
      params:
        timeout: 120
    load:
      module: load.kairosdb_loader
      class: KairosDBLoader
      params:
        timeout: 120
```

### Configuration sections at a glance

| Section | Purpose |
|---|---|
| `global.daemon` | Lifecycle: log file, PID file, log level, monitor interval, restart backoff. Tune `restart_backoff` for flaky upstreams. |
| `global.kairosdb` | KairosDB load target. Used when the load stage is `KairosDBLoader`. |
| `global.examon.tags` | The identifying tags attached to every metric. `org` / `cluster` / `plugin` are usually static; `node` is dynamic (extracted from a Prometheus label via the regex). |
| `jobs[]` | One or more ETL pipelines. Each job has its own extract / transform / load triplet and runs in its own worker pool. |
| `jobs[].extract` | What to scrape: the Prometheus URL, the metric filter, the polling interval. |
| `jobs[].transform` | How to convert Prometheus format to ExaMon format. The default `PrometheusToKairosDBTransformer` applies the tag mapping from `global.examon.tags`. |
| `jobs[].load` | Where to send the result. `KairosDBLoader` writes directly via the KairosDB HTTP API; the MQTT loader (below) ships through the broker instead. |

### Filtering metrics

The `specific_metrics` and `excluded_metrics` lists accept literal metric names or regex patterns wrapped in slashes:

```yaml
extract:
  params:
    specific_metrics:
      - "node_cpu_seconds_total"
      - "/^node_memory_/"
    excluded_metrics:
      - "/^(go|promhttp)_/"
```

Leaving both empty scrapes every metric the Prometheus server exposes.

### Scraping multiple Prometheus servers in parallel

A single job can fan out across a list of servers using the `foreach` block. The publisher creates one extract worker per list item:

```yaml
jobs:
  - name: prometheus_scraper
    extract:
      module: extract.prometheus_scraper
      class: PrometheusMetricsScraper
      type: loop
      interval: 60
      params:
        prometheus_url: http://localhost:9090
      foreach:
        type: list
        items:
          - prometheus_url: http://node-01:9090
            specific_metrics: ["node_cpu_seconds_total", "node_memory_MemAvailable_bytes"]
            interval: 10
            exporter_name: node_exporter
          - prometheus_url: http://node-02:9090
            specific_metrics: []
            interval: 60
            exporter_name: node_exporter
```

### Direct `/metrics` endpoint scraping

When the Prometheus query API is unavailable or restricted, the publisher can scrape exporters directly. Replace the extract class:

```yaml
extract:
  module: extract.prometheus_scraper
  class: PrometheusEndpointScraper
```

This bypasses Prometheus entirely and reads the exporter's `/metrics` endpoint in the Prometheus text format. Set `exporter_name` to identify the source; it is added as the `exp_name` label on every emitted metric (without overriding an existing `exp_name`).

### Load via MQTT instead of KairosDB

For deployments where publishers feed core through the broker (the standard SDK v3 pattern), swap the load stage:

```yaml
load:
  module: examon.load.mqtt_loader
  class: MQTTLoader
  params:
    inherit_mqtt: true
```

With `inherit_mqtt: true`, the loader reads MQTT broker connection details from the publisher's MQTT configuration block (host, port, credentials). The in-cluster `mqtt2kairosdb` bridge subscribes to the resulting topics and writes through to KairosDB.

## Run

### In the foreground (development)

```bash
python prometheus_pub.py -c config/my_prometheus.yaml run
```

The log output streams to the console; check the configured Prometheus server is reachable and that the tag extraction matches the expected node labels before promoting to daemon mode.

### As a daemon

```bash
python prometheus_pub.py -c config/my_prometheus.yaml start
python prometheus_pub.py -c config/my_prometheus.yaml stop
python prometheus_pub.py -c config/my_prometheus.yaml restart
```

The PID file location is set by `global.daemon.pid_filename`.

### As a systemd service

```ini
[Unit]
Description=ExaMon Prometheus Publisher
After=network.target

[Service]
Type=forking
User=examon
WorkingDirectory=/opt/examon/prometheus_pub
ExecStart=/usr/bin/python3 prometheus_pub.py -c /etc/examon/prometheus_pub.yaml run
KillSignal=SIGINT
PIDFile=/var/run/examon/prometheus_pub.pid
Restart=always

[Install]
WantedBy=multi-user.target
```

`SIGINT` is the signal the publisher's base library traps for graceful shutdown; the workers drain in-flight messages before the process exits.

## Verify

### Check the publisher is running

```bash
# Logs (foreground or systemd journal)
journalctl -u prometheus-pub -f

# Worker health (the publisher logs a heartbeat every `monitor_interval` seconds)
grep "monitor" /var/log/examon/prometheus_pub.log
```

### Check metrics arrive at the load target

For the KairosDB loader: the publisher logs successful POSTs at INFO level. Confirm metrics are queryable in KairosDB:

```bash
curl "http://kairosdb.example.com:8083/api/v1/metricnames" | jq .
```

For the MQTT loader: subscribe to the broker and watch the publisher's topics:

```bash
mosquitto_sub -h mqtt.example.com -p 1883 \
  -t 'examon/production/prometheus_pub/#' -v -C 10
```

The topic shape follows `<org>/<cluster>/<plugin>/<node>/<metric>` by default, derived from `global.examon.tags`.

## Troubleshoot

| Symptom | Likely cause | Action |
|---|---|---|
| Publisher starts but no data appears in KairosDB / MQTT | Tag extraction returns empty `node` | Verify the `node.key` matches a label on the scraped metrics and `node.regex` extracts a non-empty value. Run in the foreground at `log_level: DEBUG`. |
| Connection refused to Prometheus | Network policy or firewall | Verify the publisher host can reach `prometheus_url` from the publisher's network namespace. |
| KairosDB writes fail with 4xx | Auth misconfigured or wrong port | Confirm `global.kairosdb.username` / `password`. KairosDB listens on port 8083 by default (port 8080 is sometimes used in older configurations). |
| MQTT publishes hang | Broker authentication refused | Confirm `mqtt` credentials in the publisher config match the broker's password file or auth backend. The publisher will retry indefinitely per its restart backoff. |
| High memory growth | Unbounded label cache | Reduce `transform.tag_cache.size` and `extract.label_parse_cache.size`; both default to large values intended for static label sets. |
| Worker keeps restarting | Upstream Prometheus is unreachable or returning errors | Check the restart backoff in the log (`Restarting worker after Ns`). Inspect the underlying error; the worker will not back off forever if the cause is persistent. |

For the debug loader (writes to stdout instead of KairosDB or MQTT, useful for verifying the transform stage in isolation):

```yaml
load:
  module: examon.load.debug_loader
  class: DebugLoader
```

## Related pages

- The shared install pattern, fleet rollout considerations, and the publisher catalog are in [Publishers (overview)](index.md).
- The full configuration schema for SDK v3 publishers (every key, every default) is in [Reference → Configuration](../../reference/configuration.md).
- The architectural role of publishers (how they fit between the data sources and the broker) is in [Concepts → Architecture](../../concepts/architecture.md).

---

## Source

- Prometheus publisher repository: [`E4-Computer-Engineering/prometheus_pub`](https://github.com/E4-Computer-Engineering/prometheus_pub).
- SDK v3 base library: [`E4-Computer-Engineering/examon-base-plugin`](https://github.com/E4-Computer-Engineering/examon-base-plugin).
- Upstream Prometheus query API: [Prometheus HTTP API reference](https://prometheus.io/docs/prometheus/latest/querying/api/).
