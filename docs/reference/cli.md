# CLI

!!! info "Status: Live (reproduced 2026-05-23)"
    Verified against examon-core v0.5.0 and [`examon-base-plugin`](https://github.com/E4-Computer-Engineering/examon-base-plugin) (SDK v3).

> The CLI surfaces shipped with ExaMon. These are the command-line entry points an operator or publisher author touches directly. The Trino CLI, `kubectl`, `helm`, and other upstream tools are not documented here; see the upstream references for those.

## Operator scripts (core repository)

These scripts live under [`scripts/`](https://github.com/ExamonHPC/examon/tree/release/v0.5.0/scripts) in the core repository and are the operator's day-1 CLI.

### `scripts/k8s-local-setup.sh`

The one-shot bring-up script for a complete local-development stack on K3d. Wraps cluster creation, registry setup, image build/push, cert-manager install, K8ssandra operator install, and the ExaMon Helm chart install into a single command.

```bash
./scripts/k8s-local-setup.sh
```

The script is idempotent: re-running it on an existing cluster upgrades the chart rather than re-creating the cluster. To fully reset, delete the cluster first:

```bash
k3d cluster delete examon-local
./scripts/k8s-local-setup.sh
```

The end-to-end walkthrough (what the script does, in what order, with what defaults) is in [Administrators → Local development](../administrators/deploy/local-development.md).

### `scripts/k8s-smoke-test.sh`

The end-to-end verification script. Confirms that:

- All pods in the `examon` namespace are `Running` and `Ready`.
- KairosDB is reachable and the random publisher's synthetic metric (`random_sensor`) is being ingested.
- Grafana is reachable, the auto-provisioned KairosDB datasource passes its test, and the bundled "Examon Test – Random Sensor" dashboard renders live data.

```bash
./scripts/k8s-smoke-test.sh
```

Exit code 0 means the stack is healthy end to end. Non-zero exit indicates which check failed. The script is the convention for "did the install work" beyond `kubectl get pods`.

### `scripts/build-and-push-images.sh`

Builds every ExaMon container image (Mosquitto, KairosDB, mqtt2kairosdb, random-pub, examon-server) and pushes them to a configurable registry.

```bash
./scripts/build-and-push-images.sh <registry>
```

| Registry pattern | Typical use |
|---|---|
| `examon-registry:5111` | K3d local registry (local-development bring-up). |
| `ghcr.io/examonhpc` | GitHub Container Registry (production / shared development). |

The image tag is determined by the script and the per-image `Dockerfile`; the convention is to update the corresponding `image.tag` in the Helm values overlay after a build.

## SDK v3 publisher CLI

Every SDK v3 publisher inherits the same CLI from `ExamonApp.parse_args()`. The publisher name varies (`prometheus_pub.py`, `ipmi_pub.py`, ...); the flags are identical.

### Synopsis

```
usage: <publisher>.py [-h] -c CONFIG [-l] [--threads] [--process-per-job]
                      {run,start,stop,restart}
```

### Positional argument

| Value | Behavior |
|---|---|
| `run` | Run the publisher in the foreground. Logs stream to the console. Used for development and verification. |
| `start` | Start the publisher as a background daemon. The PID file location is `global.daemon.pid_filename` from the configuration. |
| `stop` | Stop a running daemon (reads PID from the PID file). |
| `restart` | Stop and start the daemon. |

The default `run` mode is the right choice when running under systemd (with `Type=forking` set in the unit file the daemon modes are also used; see [Administrators → Publishers](../administrators/publishers/index.md#run-as-a-systemd-service)).

### Options

| Flag | Default | Behavior |
|---|---|---|
| `-c CONFIG`, `--config CONFIG` | (required) | Path to the publisher YAML configuration file. |
| `-l`, `--lib-version` | n/a | Print the `examon-base-plugin` version and exit. Useful for debugging environment skew. |
| `-h`, `--help` | n/a | Print help and exit. |
| `--threads` | (unset) | Run every pipeline stage as a Python thread inside the main process instead of as a separate process. Lower per-message latency; less crash isolation. |
| `--process-per-job` | (unset) | Combined with `--threads`: one OS process per job, with stages as threads inside each job process. Preserves crash isolation at the job boundary. |

The three modes (default process-per-stage, `--threads`, `--threads --process-per-job`) are explained in [Concepts → Plugin model → Concurrency: three modes](../concepts/plugin-model.md#concurrency-three-modes).

### Environment variables

The publisher reads `EXAMON_*` environment variables that the configuration file references via `${VAR}` interpolation. The interpolation set varies per publisher; the canonical names ExaMon AI uses (`EXAMON_META_CATALOG`, `EXAMON_TS_CATALOG`, ...) are documented at [Users → AI → Configure](../users/ai/index.md#environment-variables).

### Exit codes

| Exit code | Meaning |
|---|---|
| `0` | Clean shutdown (SIGINT or completed work for a finite job). |
| Non-zero | An unhandled exception during startup (typically a configuration error). The error is logged to `global.daemon.log_filename` and to stderr. |

A worker crash during steady-state operation does not exit the process; the framework restarts the worker per `restart_backoff`.

## ExaMon AI CLI

ExaMon AI ships two entry points after `pip install examon-ai` (or `pip install -e .` for development):

### `examon-ai init`

Scaffold the user configuration directory at `~/.config/examon-ai/` with bundled defaults.

```bash
examon-ai init
examon-ai init --force    # overwrite existing files (including .env)
```

Re-running without `--force` is safe: existing files are preserved. With `--force`, every file is overwritten.

### `run_examon.sh`

The HolmesGPT integration wrapper script. Resolves XDG paths, sets up the Trino / LLM endpoints from `~/.config/examon-ai/.env`, and invokes `holmes ask`.

```bash
./run_examon.sh                                 # interactive session
./run_examon.sh "what GPU jobs ran today?"      # one-shot question
./run_examon.sh --deep "analyze job failures"   # deep reasoning mode
EXAMON_MODEL=openai/qwen35-examon:latest ./run_examon.sh   # override the model
```

See [Users → AI](../users/ai/index.md) for the full setup and verification protocol.

## Planned: `examon-scheduler`

A fleet-rollout CLI that translates an [inventory schema](../concepts/architecture.md) entry into the per-node publisher install (which publishers run where, with what configuration). Currently in design; not yet shipped. The current substitute is Ansible plus per-node systemd units, as described in [Administrators → Publishers → Fleet rollout considerations](../administrators/publishers/index.md#fleet-rollout-considerations).

When `examon-scheduler` ships, its CLI surface will be documented here.

## Related CLIs (upstream, not documented here)

The ExaMon documentation assumes the operator is comfortable with:

| Tool | Used for |
|---|---|
| `kubectl` | Pod and service inspection, log streaming, secret reads. |
| `helm` | Install, upgrade, rollback, history of the ExaMon chart and the K8ssandra operator chart. |
| `k3d` | Local-development cluster lifecycle (create, delete, image import). |
| `docker` | Image build, push to the local or GHCR registry. |
| `trino` (the Trino CLI) | Ad-hoc queries against the federation endpoint. |
| `mosquitto_sub` / `mosquitto_pub` | Direct MQTT inspection and test publishes. |

Refer to each tool's upstream documentation for its full CLI surface. The ExaMon-specific use is shown inline in the relevant pages ([Administrators → On Kubernetes](../administrators/deploy/on-kubernetes.md), [Administrators → Troubleshoot](../administrators/operations/troubleshoot.md), [Users → Analyze](../users/analyze/index.md)).

---

## Source

- Operator scripts: [`scripts/`](https://github.com/ExamonHPC/examon/tree/release/v0.5.0/scripts) in the core repository.
- SDK v3 CLI implementation: `ExamonApp.parse_args()` in [`examon-base-plugin`](https://github.com/E4-Computer-Engineering/examon-base-plugin).
- ExaMon AI CLI: `examon-ai/cli.py` in the in-development ExaMon AI package.
