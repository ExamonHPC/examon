# Change Propagation Guide

This document explains **how configuration flows** through the ExaMon
deployment stack and **what you need to do** when you modify something at
each layer. Understanding this chain prevents the most common class of
deployment issues: making a change that silently fails to propagate.

## The Propagation Chain

Every configuration value in ExaMon flows through a layered pipeline before
it reaches the running container. Each layer can override the previous one.

```
┌────────────────────────────────────────────────────────────────────────┐
│                    Configuration Flow (top to bottom)                  │
│                                                                        │
│  ┌──────────────────────────────────────────────────────┐              │
│  │  1. Subchart values.yaml (subchart defaults)         │              │
│  │     deploy/helm/examon/subcharts/<svc>/values.yaml   │              │
│  └──────────────────┬───────────────────────────────────┘              │
│                     │ overridden by                                     │
│  ┌──────────────────▼───────────────────────────────────┐              │
│  │  2. Umbrella values.yaml (chart-wide defaults)       │              │
│  │     deploy/helm/examon/values.yaml                   │              │
│  └──────────────────┬───────────────────────────────────┘              │
│                     │ overridden by                                     │
│  ┌──────────────────▼───────────────────────────────────┐              │
│  │  3. Environment values file (final overrides)        │              │
│  │     deploy/helm/examon/values-{local,staging,prod}.yaml             │
│  └──────────────────┬───────────────────────────────────┘              │
│                     │ rendered into                                     │
│  ┌──────────────────▼───────────────────────────────────┐              │
│  │  4. Helm templates (Go templates → K8s manifests)    │              │
│  │     subcharts/<svc>/templates/deployment.yaml        │              │
│  │     subcharts/<svc>/templates/configmap.yaml         │              │
│  └──────────────────┬───────────────────────────────────┘              │
│                     │ applied to                                       │
│  ┌──────────────────▼───────────────────────────────────┐              │
│  │  5. Kubernetes resources (Deployments, ConfigMaps)   │              │
│  └──────────────────┬───────────────────────────────────┘              │
│                     │ creates                                          │
│  ┌──────────────────▼───────────────────────────────────┐              │
│  │  6. Container runtime (Docker image + env/mounts)    │              │
│  │     deploy/docker/<svc>/Dockerfile                   │              │
│  │     deploy/docker/<svc>/*.sh, *.conf                 │              │
│  └──────────────────────────────────────────────────────┘              │
└────────────────────────────────────────────────────────────────────────┘
```

## Where to Make Changes and What to Propagate

### Scenario 1: Changing a Configuration Value

**Example:** Change the Cassandra keyspace, MQTT broker address, JVM heap,
number of replicas, etc.

**Where the value lives:**

| Scope | File | When to use |
|-------|------|-------------|
| All environments | `values.yaml` (umbrella) | Default that applies everywhere |
| Single environment | `values-local.yaml` / `values-staging.yaml` / `values-production.yaml` | Override for a specific environment |
| Subchart fallback | `subcharts/<svc>/values.yaml` | Last-resort default (overridden by umbrella) |

**Propagation rule:** A value set in the environment file wins over the
umbrella file, which wins over the subchart default.

**What to propagate when you change a value:**

1. Decide if the change is environment-specific or universal.
2. If **universal**: edit `values.yaml`. The change automatically applies to
   all environments unless they override it.
3. If **environment-specific**: edit the relevant `values-<env>.yaml`.
4. **Check all three environment files** to verify they are consistent.
   Values files only override fields they explicitly set — if a file doesn't
   mention a field, it inherits from `values.yaml`.

**Checklist for value changes:**

```
□ Updated values.yaml (if the change is a new default)
□ Updated values-local.yaml (if local needs a specific override)
□ Updated values-staging.yaml (if staging needs a specific override)
□ Updated values-production.yaml (if production needs a specific override)
□ Verified subchart values.yaml is consistent (for documentation)
□ Updated docs/Deployment/configuration.md (if a parameter changed)
```

**Deploy:**

```bash
helm upgrade examon ./deploy/helm/examon \
  -f ./deploy/helm/examon/values-<env>.yaml -n examon
```

---

### Scenario 2: Changing a Helm Template

**Example:** Add an environment variable to a Deployment, change a
readiness probe, add a volume mount, modify a ConfigMap template.

**Where the templates live:**

```
deploy/helm/examon/subcharts/<service>/templates/
    deployment.yaml     # Pod spec, containers, env vars, probes, mounts
    configmap.yaml      # Application config files (.conf)
    service.yaml        # Kubernetes Service
    _helpers.tpl        # Template helper functions
```

**Critical step — subchart packaging:**

Helm does **not** read templates directly from `subcharts/`. Instead, it uses
pre-packaged `.tgz` archives inside `deploy/helm/examon/charts/`. You must
rebuild these archives after every template change:

```bash
cd deploy/helm/examon
helm dependency update       # repackages subcharts/ → charts/*.tgz
cd ../../..
```

Without this step, `helm upgrade` silently uses the stale archive and your
template changes have no effect. This is the single most common pitfall.

**What to propagate when you change a template:**

1. Edit the template file under `subcharts/<service>/templates/`.
2. If the template references a new values field (e.g. `{{ .Values.config.newField }}`):
   - Add the field to `subcharts/<service>/values.yaml` with a sensible default.
   - Add it to `values.yaml` (umbrella) so all environments inherit it.
   - Add overrides to each `values-<env>.yaml` where needed.
3. Run `helm dependency update` in `deploy/helm/examon/`.
4. Verify the rendered output:
   ```bash
   helm template examon ./deploy/helm/examon \
     -f ./deploy/helm/examon/values-<env>.yaml -n examon \
     -s charts/<subchart>/templates/<template>.yaml
   ```
5. Upgrade.

**Checklist for template changes:**

```
□ Edited subcharts/<svc>/templates/<file>.yaml
□ Added new values fields to subcharts/<svc>/values.yaml
□ Added new values fields to values.yaml (umbrella defaults)
□ Added overrides in values-local.yaml / values-staging.yaml / values-production.yaml
□ Ran helm dependency update in deploy/helm/examon/
□ Verified rendered manifest with helm template
□ Ran helm upgrade
```

---

### Scenario 3: Changing a Dockerfile or Container Script

**Example:** Modify `kairosdb-env.sh`, `config-kairos.sh`, add a new
dependency to a Dockerfile, change the CMD/ENTRYPOINT.

**Where these files live:**

```
deploy/docker/<service>/
    Dockerfile           # Image definition
    *.sh                 # Entrypoint or config scripts
    *.conf               # Default config files (baked into image)
    *.properties         # Java properties (baked into image)
```

**What to propagate when you change a Dockerfile or script:**

1. Edit the file under `deploy/docker/<service>/`.
2. **Rebuild** the Docker image with a **new tag**:
   ```bash
   docker build -t <registry>/<image>:<new-tag> \
     -f deploy/docker/<service>/Dockerfile deploy/docker/<service>/
   docker push <registry>/<image>:<new-tag>
   ```
3. **Update the image tag** in the values files.
4. Upgrade.

**Why a new tag is required:**

Kubernetes nodes cache container images by tag. If you push a new image with
the same tag (e.g. `latest`), nodes with `imagePullPolicy: IfNotPresent`
(the default) continue using the cached version. A new tag forces a pull.

For production images on GHCR, use semantic versioning (e.g. `1.3.0`,
`1.3.1`). For development, use descriptive suffixes (e.g. `1.3.0-fix3`).

**What to propagate — image tag changes:**

| File | Update |
|------|--------|
| `values.yaml` | Update `image.tag` if this is the new default for all environments |
| `values-local.yaml` | Update `image.tag` with the local registry tag |
| `values-staging.yaml` | Update `image.tag` with the local registry tag |
| `values-production.yaml` | Update `image.tag` with the GHCR tag |

**Checklist for Docker image changes:**

```
□ Edited deploy/docker/<svc>/Dockerfile (or scripts/conf within)
□ Built image with a NEW tag
□ Pushed to the correct registry (examon-registry:5111 or ghcr.io)
□ Updated image tag in values-local.yaml
□ Updated image tag in values-staging.yaml
□ Updated image tag in values-production.yaml
□ Updated default tag in values.yaml (if appropriate)
□ Ran helm upgrade
□ Verified pod is using the new image:
  kubectl get pod <pod> -n examon -o jsonpath='{.spec.containers[0].image}'
```

---

### Scenario 4: Adding a New Configuration Field End-to-End

**Example:** Adding a new `CASSANDRA_TIMEOUT` parameter to examon-server.

This is the most complex scenario because it touches every layer:

**Step 1 — Subchart template:**
Edit `subcharts/examon-server/templates/configmap.yaml` to render the new
field:

```yaml
CASSANDRA_TIMEOUT = {{ .Values.config.cassandraTimeout }}
```

**Step 2 — Subchart default:**
Edit `subcharts/examon-server/values.yaml`:

```yaml
config:
  cassandraTimeout: 30
```

**Step 3 — Umbrella default:**
Edit `values.yaml`:

```yaml
examon-server:
  config:
    cassandraTimeout: 30
```

**Step 4 — Environment overrides (if needed):**
Edit `values-production.yaml`:

```yaml
examon-server:
  config:
    cassandraTimeout: 120
```

**Step 5 — Rebuild and deploy:**

```bash
cd deploy/helm/examon && helm dependency update && cd ../../..
helm upgrade examon ./deploy/helm/examon \
  -f ./deploy/helm/examon/values-<env>.yaml -n examon
```

**Step 6 — Verify:**

```bash
helm get manifest examon -n examon | grep CASSANDRA_TIMEOUT
```

**Step 7 — Documentation:**
Update `docs/Deployment/configuration.md` with the new parameter.

---

## Summary: What Changes Require What Actions

| What you changed | Rebuild image | `helm dependency update` | `helm upgrade` | Update values files |
|------------------|:---:|:---:|:---:|:---:|
| Value in `values-<env>.yaml` only | | | Yes | — |
| Value in umbrella `values.yaml` | | | Yes | Check env files |
| Subchart template (`subcharts/*/templates/`) | | **Yes** | Yes | If new field |
| Subchart `values.yaml` (defaults) | | **Yes** | Yes | Check umbrella + env files |
| Dockerfile or container scripts | **Yes** | | Yes | Update image tags |
| K3d/K8s cluster config (`deploy/k3d/`) | — | — | Recreate cluster | — |
| External chart version (`Chart.yaml`) | | **Yes** | Yes | — |

## Values Inheritance Diagram

For a specific field like `kairosdb.config.cassandraHostList`:

```
subcharts/kairosdb/values.yaml
  cassandraHostList: "examon-cassandra-dc1-service:9042"    ← subchart default
        │
        │  overridden by umbrella values.yaml (kairosdb section):
        ▼
values.yaml
  kairosdb:
    config:
      cassandraHostList: "examon-cassandra-dc1-service:9042"  ← chart-wide default
        │
        │  overridden by environment file (if field is present):
        ▼
values-production.yaml
  kairosdb:
    config:
      cassandraHostList: "prod-cassandra.example.com:9042"    ← env override
        │
        │  rendered by template:
        ▼
subcharts/kairosdb/templates/deployment.yaml
  env:
    - name: CASSANDRA_HOST_LIST
      value: {{ .Values.config.cassandraHostList | quote }}
        │
        │  injected into container:
        ▼
config-kairos.sh
  sed -i "s/.../$CASSANDRA_HOST_LIST/" kairosdb.properties
  sed -i "s/.../$CASS_HOST/" kairosdb.conf
```

If a field is **not** present in the environment values file, Helm uses the
umbrella `values.yaml` default. If it's also absent from the umbrella file,
Helm falls back to the subchart's own `values.yaml`.

## Configuration Delivery Mechanisms

Different services receive their configuration in different ways:

| Service | Config Mechanism | Template | How App Reads It |
|---------|-----------------|----------|-----------------|
| **kairosdb** | Env vars → `config-kairos.sh` patches config files at startup | `deployment.yaml` (env section) | `kairosdb.properties` + `kairosdb.conf` (HOCON) |
| **examon-server** | ConfigMap mounted as `server.conf` | `configmap.yaml` → `deployment.yaml` (volumeMount) | Python `configparser` (INI format) |
| **random-pub** | ConfigMap mounted as `random_pub.conf` | `configmap.yaml` → `deployment.yaml` (volumeMount) | Python `ExamonApp` (INI format) |
| **mqtt2kairosdb** | ConfigMap mounted as `mqtt2kairosdb.conf` | `configmap.yaml` → `deployment.yaml` (volumeMount) | Python `ExamonApp` (INI format) |
| **mosquitto** | ConfigMap mounted as `mosquitto.conf` | `configmap.yaml` → `statefulset.yaml` (volumeMount) | Mosquitto reads conf on startup |
| **Cassandra** | K8ssandraCluster CRD (managed by operator) | `templates/k8ssandra.yaml` | Operator manages `cassandra.yaml` |
| **Grafana** | Helm subchart values (upstream chart) | Upstream templates | Grafana reads env vars + provisioning |

## Secrets Management

Secret values (passwords, API keys) must **never** be committed in plain text
to any values file. All secret fields in the checked-in values files contain
empty strings.

### Automatic Cassandra credential injection

Both **KairosDB** and **examon-server** read Cassandra credentials
automatically from the K8ssandra-generated secret (`examon-cassandra-superuser`)
via `secretKeyRef` environment variables. No `--set` flags are needed for
Cassandra passwords. This is configured via:

```yaml
examon-server:
  config:
    cassandraAuth:
      secretName: "examon-cassandra-superuser"
```

### How to pass remaining secrets at deploy time

The only secret that still requires `--set` is the **Grafana admin password**:

1. **`--set` flags** (recommended for local/staging):

    ```bash
    helm upgrade examon ./deploy/helm/examon \
      -f ./deploy/helm/examon/values-local.yaml \
      --set grafana.adminPassword="my-grafana-password" \
      -n examon
    ```

2. **Secret override files** (gitignored):

    Create `values-<env>.secret.yaml` (e.g. `values-local.secret.yaml`) in
    `deploy/helm/examon/`. These files match the `.gitignore` pattern
    `deploy/helm/examon/values-*.secret.yaml` and will never be committed:

    ```yaml
    # values-local.secret.yaml — DO NOT COMMIT
    grafana:
      adminPassword: "my-grafana-password"
    ```

    Pass both files to Helm:

    ```bash
    helm upgrade examon ./deploy/helm/examon \
      -f values-local.yaml -f values-local.secret.yaml -n examon
    ```

3. **External secrets operator** (recommended for production): Sync secrets
   from Vault, AWS Secrets Manager, etc. into Kubernetes Secrets.

### Which fields are secrets?

| Field | Service | How injected |
|-------|---------|-------------|
| `grafana.adminPassword` | Grafana | `--set` flag |
| `examon-server.config.cassandraAuth.secretName` | examon-server | Auto via K8s `secretKeyRef` |
| `kairosdb.config.cassandraAuth.secretName` | KairosDB | Auto via K8s `secretKeyRef` |
| `random-pub.config.mqttPassword` | random-pub | `--set` flag |
| `mqtt2kairosdb.config.kairosdb.password` | mqtt2kairosdb | `--set` flag |

## Common Mistakes and How to Avoid Them

### 1. "I changed a template but nothing happened"

You forgot `helm dependency update`. Helm uses packaged `.tgz` archives from
`deploy/helm/examon/charts/`, not the source files in `subcharts/`.

### 2. "I pushed a new image but the pod runs the old one"

You reused the same tag. K3d/K8s nodes cache images by tag with
`imagePullPolicy: IfNotPresent`. Use a new tag or set
`imagePullPolicy: Always`.

### 3. "I set a value in the subchart's values.yaml but it was ignored"

The umbrella `values.yaml` overrides subchart defaults. If the umbrella file
has the same field set to a different value, the umbrella wins. Always update
both, or rely solely on the umbrella file.

### 4. "My change works in local but not staging/production"

The environment values files are independent. A fix in `values-local.yaml`
is not automatically reflected in `values-staging.yaml` or
`values-production.yaml`. Check all three files when making fixes.

### 5. "helm upgrade succeeded but pods didn't restart"

Helm only restarts pods when the pod spec changes. If you changed a
ConfigMap but the Deployment template doesn't include a checksum annotation,
the Deployment spec is unchanged and pods keep running the old config.

For services that use ConfigMap-mounted config files, the Deployment templates
include a `checksum/config` annotation that forces a rollout when the
ConfigMap content changes:

```yaml
template:
  metadata:
    annotations:
      checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
```

If a service uses only env vars (like kairosdb), changing env var values in
the template will trigger a rollout automatically. If it doesn't, force one:

```bash
kubectl rollout restart deployment/<name> -n examon
```

## Quick Reference: Files to Check for Each Service

### kairosdb

```
deploy/docker/kairosdb/
    Dockerfile              # Image definition
    kairosdb-env.sh         # JVM options (--add-opens, heap)
    config-kairos.sh        # Entrypoint: patches .properties + .conf
    kairosdb.properties     # Legacy config (baked in image)

deploy/helm/examon/
    subcharts/kairosdb/
        values.yaml                     # Subchart defaults
        templates/deployment.yaml       # Pod spec, env vars, probes
        templates/service.yaml          # K8s Service
    values.yaml                         # Umbrella defaults (kairosdb section)
    values-local.yaml                   # Local overrides
    values-staging.yaml                 # Staging overrides
    values-production.yaml              # Production overrides
```

### examon-server

```
deploy/docker/examon-server/
    Dockerfile              # Image definition

deploy/helm/examon/
    subcharts/examon-server/
        values.yaml                     # Subchart defaults
        templates/deployment.yaml       # Pod spec, probes, volumeMounts
        templates/configmap.yaml        # server.conf generation
        templates/service.yaml          # K8s Service
    values.yaml                         # Umbrella defaults
    values-{local,staging,production}.yaml
```

### random-pub

```
deploy/docker/random-pub/
    Dockerfile              # Image definition

deploy/helm/examon/
    subcharts/random-pub/
        values.yaml                     # Subchart defaults
        templates/deployment.yaml       # Pod spec, volumeMounts
        templates/configmap.yaml        # random_pub.conf generation
    values.yaml                         # Umbrella defaults
    values-{local,staging,production}.yaml
```

### mosquitto

```
deploy/docker/mosquitto/
    Dockerfile              # Image definition
    mosquitto.conf          # Default config (baked in image, overridden by ConfigMap)

deploy/helm/examon/
    subcharts/mosquitto/
        values.yaml                     # Subchart defaults
        templates/statefulset.yaml      # Pod spec
        templates/configmap.yaml        # mosquitto.conf generation
        templates/service.yaml          # K8s Service
    values.yaml                         # Umbrella defaults
    values-{local,staging,production}.yaml
```

### mqtt2kairosdb

```
deploy/docker/mqtt2kairosdb/
    Dockerfile              # Image definition (git clones source from examon-container repo)
    mqtt2kairosdb.conf      # Default config (overridden by ConfigMap)

deploy/helm/examon/
    subcharts/mqtt2kairosdb/
        values.yaml                     # Subchart defaults
        templates/deployment.yaml       # Pod spec, volumeMounts
        templates/configmap.yaml        # mqtt2kairosdb.conf generation
    values.yaml                         # Umbrella defaults
    values-{local,staging,production}.yaml
```
