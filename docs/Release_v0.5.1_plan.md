# ExaMon v0.5.1 -- Technical Plan

This document captures the planned improvements for v0.5.1, building on the
v0.5.0 Kubernetes migration. It covers three main areas:

1. **Data persistence, backup, and migration strategy** -- filling the gaps
   identified in the v0.5.0 deployment.
2. **KairosDB HOCON ConfigMap overlay** -- replacing the current `sed`-patching
   entrypoint with a cleaner, Kubernetes-native configuration model.
3. **Documentation gap analysis (README parity)** -- ensuring every operation
   documented in the Docker Compose `README.md` has a complete K8s equivalent.

All items are documented here as a technical plan; implementation follows in a
subsequent phase.

---

## 1. Data Persistence, Backup, and Migration Strategy

### 1.1 Current State (v0.5.0)

The original Docker Compose deployment defines two named volumes:

```yaml
# docker-compose.yml
volumes:
  cassandra_volume:   # /var/lib/cassandra -- core time-series data
  grafana_volume:     # /var/lib/grafana   -- dashboards, users, preferences
```

The v0.5.0 Kubernetes deployment partially translates these into PVCs:

| Component | K8s Workload | Persistence | Local | Staging | Production |
|-----------|-------------|-------------|-------|---------|------------|
| Cassandra | K8ssandraCluster CR → StatefulSet | PVC via `cassandraDataVolumeClaimSpec` | 5Gi × 1 | 10Gi × 3 | 100Gi × 3 |
| Grafana | Deployment (upstream Helm chart) | PVC via `persistence.enabled` | **disabled** | 1Gi | 10Gi |
| Mosquitto | StatefulSet (custom subchart) | PVC via `volumeClaimTemplates` | **disabled** | 1Gi | 5Gi |
| KairosDB | Deployment | None (stateless proxy to Cassandra) | n/a | n/a | n/a |
| examon-server | Deployment | None (stateless) | n/a | n/a | n/a |
| mqtt2kairosdb | Deployment | None (stateless) | n/a | n/a | n/a |
| random-pub | Deployment | None (stateless) | n/a | n/a | n/a |

**What is correctly handled:**

- Cassandra PVCs are created automatically by K8ssandra with configurable
  `storageClass` and size per environment.
- Grafana persistence is enabled in staging/production.
- Mosquitto persistence is enabled in staging/production.
- Data survives pod restarts and `helm upgrade` in all three cases.

### 1.2 Identified Gaps

#### GAP 1: No Cassandra Backup Implementation (Medusa)

The `values-production.yaml` header mentions "Medusa backups" and the production
docs contain a two-line placeholder, but **no actual Medusa configuration exists**
in the `k8ssandra-cluster.yaml` template. The K8ssandraCluster CR has no `medusa`
section. This means:

- No automated Cassandra backups
- No point-in-time restore capability
- No disaster recovery plan for the primary data store

**Plan:** Add a `medusa` section to the K8ssandraCluster CR template with
configurable storage backend (S3-compatible, GCS, Azure Blob, or local).
Add corresponding values in `values.yaml`, `values-staging.yaml`, and
`values-production.yaml`. Create a `MedusaBackupSchedule` CR template for
automated periodic backups.

Required additions to `templates/k8ssandra-cluster.yaml`:

```yaml
spec:
  medusa:
    storageProperties:
      storageProvider: {{ .Values.cassandra.medusa.storageProvider }}
      bucketName: {{ .Values.cassandra.medusa.bucketName }}
      storageSecretRef:
        name: {{ .Values.cassandra.medusa.storageSecretName }}
      prefix: {{ .Values.cassandra.medusa.prefix | default "examon" }}
    containerImage:
      registry: docker.io
      repository: k8ssandra/medusa
      tag: {{ .Values.cassandra.medusa.imageTag | default "0.22.3" }}
```

Required values additions (production example):

```yaml
cassandra:
  medusa:
    enabled: true
    storageProvider: s3_compatible    # s3, s3_compatible, gcs, azure_blobs, local
    bucketName: examon-cassandra-backups
    storageSecretName: medusa-bucket-secret  # pre-created K8s Secret with credentials
    prefix: examon
    imageTag: "0.22.3"
    schedule: "0 2 * * *"           # daily at 02:00 UTC
    retentionDays: 30
```

Manual backup and restore commands:

```bash
# Trigger on-demand backup
kubectl apply -f - <<EOF
apiVersion: medusa.k8ssandra.io/v1alpha1
kind: MedusaBackupJob
metadata:
  name: backup-$(date +%Y%m%d-%H%M%S)
  namespace: examon
spec:
  cassandraDatacenter: dc1
EOF

# List backups
kubectl get medusabackupjob -n examon

# Restore from a backup
kubectl apply -f - <<EOF
apiVersion: medusa.k8ssandra.io/v1alpha1
kind: MedusaRestoreJob
metadata:
  name: restore-20260325
  namespace: examon
spec:
  cassandraDatacenter: dc1
  backup: backup-20260325-020000
EOF
```

#### GAP 2: No Grafana Backup Strategy

Grafana stores critical user-created content that must survive redeployments:

- **Dashboards** -- the primary user asset (significant development effort)
- **User accounts and org preferences**
- **Alert rules and notification channels**
- **Annotations**

Currently there is no Grafana backup automation, no dashboard-as-code
provisioning, and the upgrade guide only says "re-import Grafana dashboards."

**Plan (multi-layered):**

1. **Dashboard provisioning from ConfigMaps (dashboard-as-code):** The Grafana
   Helm chart already has sidecar support (`sidecar.datasources.enabled: true`).
   Extend this to dashboards by enabling `sidecar.dashboards.enabled: true` and
   labeling ConfigMaps containing dashboard JSON. This makes core dashboards
   reproducible and version-controlled.

   ```yaml
   grafana:
     sidecar:
       datasources:
         enabled: true
       dashboards:
         enabled: true
         label: grafana_dashboard
         folder: /tmp/dashboards
   ```

2. **Grafana API export script:** Create a `scripts/grafana-backup.sh` script
   that uses the Grafana HTTP API to export all dashboards, datasources, and
   alert rules to JSON files. This handles user-created dashboards that are
   not in ConfigMaps.

   ```bash
   # Example: export all dashboards
   for uid in $(curl -s -H "Authorization: Bearer $TOKEN" \
     http://grafana:3000/api/search?type=dash-db | jq -r '.[].uid'); do
     curl -s -H "Authorization: Bearer $TOKEN" \
       "http://grafana:3000/api/dashboards/uid/$uid" > "dashboards/${uid}.json"
   done
   ```

3. **PVC snapshots** (if the storage provider supports CSI VolumeSnapshots):
   As a safety net for the Grafana SQLite database.

#### GAP 3: No PVC Backup/Snapshot Strategy

No `VolumeSnapshot` classes, schedules, or documentation exist for Cassandra,
Grafana, or Mosquitto PVCs.

**Plan:**

- Document CSI VolumeSnapshot usage for environments that support it.
- Create example VolumeSnapshot and VolumeSnapshotSchedule manifests.
- Add guidance for storage providers that support snapshot scheduling natively
  (e.g., Longhorn, Rook-Ceph, cloud CSI drivers).

#### GAP 4: No PV Reclaim Policy Guidance

When a PVC is deleted (e.g., during `helm uninstall`), the PV behavior depends on
the StorageClass `reclaimPolicy`. The default in most providers is `Delete`, which
**permanently destroys the data**.

**Plan:**

- Document the importance of `reclaimPolicy: Retain` for production Cassandra
  and Grafana StorageClasses.
- Add comments in `values-production.yaml` recommending explicit
  `storageClass` with `Retain` reclaim policy.
- Add a troubleshooting entry for accidental data loss on `helm uninstall`.

Example StorageClass:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: cassandra-ssd-retain
provisioner: <csi-driver>       # e.g., cinder.csi.openstack.org, ebs.csi.aws.com
reclaimPolicy: Retain
volumeBindingMode: WaitForFirstConsumer
parameters:
  type: ssd
```

#### GAP 5: Incomplete Migration/Restore Documentation

The `upgrading.md` Step 4 ("Restore Data") only says "consult the Apache
Cassandra upgrade documentation" for a 3.0.19 → 4.0.14 migration. This is a
major version jump requiring an SSTable upgrade path (3.0 → 3.11 → 4.0).

**Plan:**

- Expand `upgrading.md` with concrete SSTable migration steps.
- Document Grafana API export/import commands.
- Create a new `docs/Deployment/backup-restore.md` with a tested operational
  runbook covering: Medusa backup/restore for Cassandra, Grafana API
  backup/restore, PVC snapshot procedures, and disaster recovery scenarios.

#### GAP 6: Mosquitto Application-Level Persistence Mismatch

The Mosquitto subchart has two independent persistence toggles that are not
synchronized:

1. `persistence.enabled` -- controls PVC creation (Kubernetes volume)
2. `config.persistence` -- controls Mosquitto's own `persistence` directive
   in `mosquitto.conf` (whether retained messages/subscriptions are written
   to disk)

In staging and production, the PVC is created (`persistence.enabled: true`) but
the Mosquitto config still says `persistence false` (subchart default). This
means the PVC exists but Mosquitto never writes to it.

**Plan:** Synchronize the two toggles -- when `persistence.enabled` is `true`,
automatically set `persistence true` in the ConfigMap template, or at minimum
override `config.persistence: "true"` in `values-staging.yaml` and
`values-production.yaml`.

### 1.3 Implementation Priority

| Priority | Gap | Risk | Effort |
|----------|-----|------|--------|
| **P0** | Cassandra Medusa backups | Data loss on failure | Medium |
| **P0** | PV reclaim policy guidance | Data loss on helm uninstall | Low (docs) |
| **P1** | Grafana dashboard-as-code + API backup | Dashboard loss on redeploy | Medium |
| **P1** | Mosquitto persistence mismatch | Silent misconfiguration | Low |
| **P2** | PVC snapshot strategy | Defense-in-depth | Medium |
| **P2** | Migration documentation expansion | Upgrade friction | Medium |

---

## 2. KairosDB HOCON ConfigMap Overlay

### 2.1 Problem: sed-Patching at Runtime

The current KairosDB Docker image uses a shell entrypoint (`config-kairos.sh`)
that patches configuration files at container startup via `sed`:

```bash
# config-kairos.sh (current)
sed -i "s/^kairosdb.jetty.port.*$/kairosdb.jetty.port=$KAIROS_JETTY_PORT/" \
  /opt/kairosdb/conf/kairosdb.properties

sed -i "s/^kairosdb.datastore.cassandra.cql_host_list.*$/kairosdb.datastore.cassandra.cql_host_list=$CASSANDRA_HOST_LIST/" \
  /opt/kairosdb/conf/kairosdb.properties

CASS_HOST=$(echo "$CASSANDRA_HOST_LIST" | sed 's/:.*$//')
sed -i "s|cql_host_list: \[\"localhost\"\]|cql_host_list: [\"${CASS_HOST}\"]|g" \
  /opt/kairosdb/conf/kairosdb.conf

if [[ -n "$CASSANDRA_USER" && -n "$CASSANDRA_PASSWORD" ]]; then
    sed -i "s|^kairosdb.datastore.cassandra.auth.user_name=.*|...|" ...
    sed -i "s|^kairosdb.datastore.cassandra.auth.password=.*|...|" ...
    sed -i "s|#auth.user_name=.*|auth.user_name=$CASSANDRA_USER|" ...
    sed -i "s|#auth.password=.*|auth.password=$CASSANDRA_PASSWORD|" ...
fi

/opt/kairosdb/bin/kairosdb.sh run
```

**Problems with this approach:**

1. **Fragile:** Sed patterns break if the upstream config file format changes
   (e.g., whitespace, comments, line ordering).
2. **Limited scope:** Only a handful of KairosDB settings are exposed.
   Adding a new setting requires editing the Dockerfile entrypoint, rebuilding
   the image, and pushing it to the registry.
3. **Dual-format maintenance:** KairosDB 1.3.0+ uses HOCON (`kairosdb.conf`)
   but retains the legacy `.properties` file. The entrypoint must patch both.
4. **Not Kubernetes-native:** The pattern does not leverage ConfigMaps for
   configuration management. Changes require image rebuilds rather than
   `helm upgrade`.
5. **Mutation at runtime:** The entrypoint mutates baked-in files, which
   conflicts with `readOnlyRootFilesystem` security contexts and makes
   debugging harder (the running config differs from the image's config).

### 2.2 Proposed Solution: HOCON Overrides via ConfigMap

KairosDB 1.3.0+ supports HOCON configuration with an include-based override
mechanism. The upstream KairosDB Helm chart (from the `kairosdb/kairosdb`
repository) demonstrates this pattern: mount an `overrides.conf` file via
ConfigMap that is included by the main `kairosdb.conf`.

The key insight is that HOCON supports **late-binding overrides**: a property
defined later in the include chain wins. This means we can keep the default
`kairosdb.conf` baked into the image and mount a small `overrides.conf` via
ConfigMap that sets only the values we care about.

**Target architecture:**

```
┌──────────────────────────────────────────────────────────┐
│  KairosDB Container                                       │
│                                                           │
│  /opt/kairosdb/conf/kairosdb.conf      (baked in image)   │
│    └── include "overrides.conf"        (last line)        │
│                                                           │
│  /opt/kairosdb/conf/overrides.conf     (ConfigMap mount)  │
│    ├── kairosdb.datastore.cassandra {                     │
│    │     cql_host_list: ["cassandra-dc1-service"]         │
│    │     auth { user_name: ..., password: ... }           │
│    │   }                                                  │
│    ├── kairosdb.jetty.port = 8083                         │
│    └── (any other override)                               │
│                                                           │
│  /opt/kairosdb/bin/kairosdb.sh run     (direct CMD)       │
│    No sed-patching entrypoint needed                      │
└──────────────────────────────────────────────────────────┘
```

### 2.3 Implementation Steps

#### Step 1: Modify the KairosDB Docker Image

1. **Edit `kairosdb.conf`** (baked into the image) to add at the end:

   ```hocon
   # Include overrides from mounted ConfigMap (if present)
   include "overrides"
   ```

   HOCON's `include` silently ignores missing files, so the image remains
   usable standalone without a mounted ConfigMap.

2. **Replace the entrypoint:** Change the `CMD` from
   `/usr/bin/config-kairos.sh` to `/opt/kairosdb/bin/kairosdb.sh run`
   directly, or use a minimal entrypoint that only handles graceful shutdown
   signals (no sed). The `config-kairos.sh` script can be kept for backward
   compatibility with non-Kubernetes deployments but is no longer the default
   entrypoint.

3. **Updated Dockerfile:**

   ```dockerfile
   FROM eclipse-temurin:17-jre

   ENV KAIROSDB_VERSION=1.3.0

   RUN apt-get update && apt-get install -y --no-install-recommends \
           wget curl \
       && rm -rf /var/lib/apt/lists/*

   RUN wget -q "https://github.com/kairosdb/kairosdb/releases/download/v${KAIROSDB_VERSION}/kairosdb_${KAIROSDB_VERSION}-1_all.deb" \
       && dpkg -i "kairosdb_${KAIROSDB_VERSION}-1_all.deb" \
       && rm "kairosdb_${KAIROSDB_VERSION}-1_all.deb"

   COPY kairosdb.properties /opt/kairosdb/conf/kairosdb.properties
   COPY kairosdb-env.sh /opt/kairosdb/bin/kairosdb-env.sh

   # Append HOCON include directive for ConfigMap overrides
   RUN echo '' >> /opt/kairosdb/conf/kairosdb.conf && \
       echo 'include "overrides"' >> /opt/kairosdb/conf/kairosdb.conf

   EXPOSE 4242 8083 2003

   CMD ["/opt/kairosdb/bin/kairosdb.sh", "run"]
   ```

#### Step 2: Create a HOCON ConfigMap Template

Replace the current env-var-based deployment template with a ConfigMap that
renders an `overrides.conf` file from Helm values:

```yaml
# subcharts/kairosdb/templates/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ include "kairosdb.fullname" . }}-config
  labels:
    {{- include "kairosdb.labels" . | nindent 4 }}
data:
  overrides.conf: |
    kairosdb {
      jetty {
        port = {{ .Values.config.jettyPort }}
        address = "0.0.0.0"
      }

      datastore.cassandra {
        cql_host_list: [{{ .Values.config.cassandraHostList | quote }}]
        keyspace = {{ .Values.config.cassandraKeyspace | default "kairosdb" | quote }}

        {{- if .Values.config.cassandraAuth.enabled }}
        auth {
          user_name = ${?CASSANDRA_USER}
          password = ${?CASSANDRA_PASSWORD}
        }
        {{- end }}

        read_consistency_level = {{ .Values.config.readConsistency | default "ONE" | quote }}
        write_consistency_level = {{ .Values.config.writeConsistency | default "QUORUM" | quote }}

        {{- if .Values.config.localDatacenter }}
        local_datacenter = {{ .Values.config.localDatacenter | quote }}
        {{- end }}

        replication = {{ .Values.config.replication | default "{'class': 'SimpleStrategy','replication_factor' : 1}" | quote }}
      }

      queue_processor {
        batch_size = {{ .Values.config.queueProcessor.batchSize | default 200 }}
        min_batch_size = {{ .Values.config.queueProcessor.minBatchSize | default 100 }}
        memory_queue_size = {{ .Values.config.queueProcessor.memoryQueueSize | default 100000 }}
      }

      {{- with .Values.config.extraHocon }}
      {{ . | nindent 6 }}
      {{- end }}
    }
```

The `extraHocon` field is a free-form escape hatch that lets operators inject
any KairosDB HOCON setting without modifying templates or Dockerfiles.

#### Step 3: Update the Deployment Template

Mount the ConfigMap as a volume at `/opt/kairosdb/conf/overrides.conf`:

```yaml
# subcharts/kairosdb/templates/deployment.yaml (relevant changes)
spec:
  template:
    spec:
      containers:
        - name: kairosdb
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          command: ["/opt/kairosdb/bin/kairosdb.sh", "run"]
          env:
            - name: JAVA_OPTS
              value: {{ .Values.config.javaOpts | quote }}
            {{- if .Values.config.cassandraAuth.secretName }}
            - name: CASSANDRA_USER
              valueFrom:
                secretKeyRef:
                  name: {{ .Values.config.cassandraAuth.secretName }}
                  key: username
            - name: CASSANDRA_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: {{ .Values.config.cassandraAuth.secretName }}
                  key: password
            {{- end }}
          volumeMounts:
            - name: config-override
              mountPath: /opt/kairosdb/conf/overrides.conf
              subPath: overrides.conf
              readOnly: true
      volumes:
        - name: config-override
          configMap:
            name: {{ include "kairosdb.fullname" . }}-config
```

Cassandra credentials continue to be injected via `secretKeyRef` environment
variables. The HOCON `overrides.conf` references them using HOCON's environment
variable substitution syntax (`${?CASSANDRA_USER}`, `${?CASSANDRA_PASSWORD}`),
which resolves at KairosDB startup.

#### Step 4: Expand values.yaml

The KairosDB subchart `values.yaml` gains richer configuration:

```yaml
config:
  cassandraHostList: "examon-cassandra-dc1-service:9042"
  cassandraKeyspace: kairosdb
  jettyPort: 8083
  javaOpts: "-Xmx2g -Xms2g"

  cassandraAuth:
    enabled: true
    secretName: "examon-cassandra-superuser"

  readConsistency: "ONE"
  writeConsistency: "QUORUM"
  localDatacenter: ""
  replication: "{'class': 'SimpleStrategy','replication_factor' : 1}"

  queueProcessor:
    batchSize: 200
    minBatchSize: 100
    memoryQueueSize: 100000

  # Free-form HOCON block injected at the end of overrides.conf.
  # Use this to override any KairosDB setting without modifying templates.
  # Example:
  #   extraHocon: |
  #     kairosdb.datastore.cassandra.connections_per_host.local.max = 200
  #     kairosdb.log.queries.enable = true
  extraHocon: ""
```

### 2.4 Benefits

| Aspect | Current (sed-patching) | Proposed (HOCON ConfigMap) |
|--------|----------------------|--------------------------|
| Adding a new KairosDB setting | Edit entrypoint script → rebuild image → push → upgrade | Add to `values.yaml` → `helm upgrade` |
| Configuration visibility | Hidden in runtime sed mutations | Visible in ConfigMap (`kubectl get cm`) |
| Debugging | Must exec into pod to see patched files | ConfigMap is the source of truth |
| Security context | Incompatible with `readOnlyRootFilesystem` | Compatible (ConfigMap mounted read-only) |
| Upstream compatibility | Breaks if KairosDB config format changes | HOCON include is a stable contract |
| Dual-format maintenance | Must patch both `.properties` and `.conf` | Only `.conf` (HOCON) |
| Free-form overrides | Not possible without image rebuild | `extraHocon` field in values |
| Backward compatibility | n/a | Old entrypoint kept in image for non-K8s use |

### 2.5 Migration Path

This is a **breaking change** for the KairosDB Docker image entrypoint. The
migration path is:

1. Build a new KairosDB image with the HOCON include and direct `CMD`.
2. Tag it with a new version (e.g., `1.3.0-hocon` or `1.3.1`).
3. Update `values.yaml` and all environment values files to use the new tag.
4. The old `config-kairos.sh` entrypoint remains in the image for users who
   run KairosDB outside Kubernetes (e.g., Docker Compose), but it is no
   longer the default `CMD`.

### 2.6 Scope and Effort

This refactor touches:

| File | Change |
|------|--------|
| `deploy/docker/kairosdb/Dockerfile` | Replace CMD, append `include "overrides"` to kairosdb.conf |
| `deploy/docker/kairosdb/config-kairos.sh` | Keep for backward compat, no longer default entrypoint |
| `deploy/helm/examon/subcharts/kairosdb/templates/configmap.yaml` | **New file** -- HOCON overrides template |
| `deploy/helm/examon/subcharts/kairosdb/templates/deployment.yaml` | Add ConfigMap volumeMount, remove some env vars |
| `deploy/helm/examon/subcharts/kairosdb/values.yaml` | Expand config section |
| `deploy/helm/examon/values.yaml` | Expand kairosdb config section |
| `deploy/helm/examon/values-local.yaml` | Update kairosdb config if needed |
| `deploy/helm/examon/values-staging.yaml` | Update kairosdb config if needed |
| `deploy/helm/examon/values-production.yaml` | Update kairosdb config, set replication strategy |
| `scripts/build-and-push-images.sh` | No change (already builds kairosdb) |
| `.github/workflows/k8s-test.yml` | No change (already tests kairosdb) |
| Documentation | Update configuration.md, change-propagation.md |

**Estimated effort:** Medium. The refactor itself is straightforward, but
requires careful testing of the HOCON include mechanism, validation that
credentials are still correctly injected, and regression testing of all three
environments.

---

## 3. Additional Improvements from v0.5.0 Review

The [kubernetes-review-report.md](kubernetes-review-report.md) identified several
additional technical debt items. The following are candidates for v0.5.1 or later
releases, listed here for tracking:

### 3.1 Workload Hardening (P1)

Add `securityContext` and `podSecurityContext` to all custom subchart templates:

```yaml
securityContext:
  runAsNonRoot: true
  readOnlyRootFilesystem: true    # feasible after HOCON ConfigMap refactor
  allowPrivilegeEscalation: false
  capabilities:
    drop: [ALL]
  seccompProfile:
    type: RuntimeDefault
```

The KairosDB HOCON ConfigMap refactor (section 2) is a prerequisite for
`readOnlyRootFilesystem` on the KairosDB pod, since the current sed-patching
requires a writable filesystem.

### 3.2 PodDisruptionBudgets (P1)

Add PDBs for stateful and critical-path services:

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: kairosdb-pdb
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: kairosdb
```

Candidates: Cassandra (managed by K8ssandra), KairosDB, examon-server,
Mosquitto.

### 3.3 Image Versioning (P1)

Replace all `latest` tags in production values with pinned semantic versions
or SHA digests. Establish a documented image promotion process:

```
local (latest) → staging (version tag) → production (version tag or digest)
```

### 3.4 Observability Stack (P2)

- Add ServiceMonitor manifests for Prometheus scraping.
- Add PrometheusRule manifests for alerting.
- Create self-monitoring Grafana dashboards as ConfigMap-provisioned dashboards.

### 3.5 Horizontal Pod Autoscaling (P2)

Add HPA definitions for stateless services:

- `examon-server`: scale on CPU/memory
- `mqtt2kairosdb`: scale on CPU (requires topic partitioning analysis)
- `kairosdb`: scale on CPU (limited by Cassandra write throughput)

### 3.6 Network Policies (P2)

Add NetworkPolicy manifests restricting inter-service traffic to the minimum
required:

```
random-pub     → mosquitto (1883)
mqtt2kairosdb  → mosquitto (1883), kairosdb (8083)
kairosdb       → cassandra (9042)
examon-server  → cassandra (9042), grafana (3000)
grafana        → kairosdb (8083)
ingress        → grafana (3000), examon-server (5000)
```

---

## 4. Implementation Phases (Original)

See [section 7](#7-implementation-phases-updated) for the updated phase plan
that includes documentation gap items from section 6.

---

## 5. Reference

- [v0.5.0 Technical Plan](Release_v0.5.0_plan.md) -- original Kubernetes
  migration plan
- [v0.5.0 Release Notes](Release_v0.5.0.md) -- release notes and goals
- [Kubernetes Review Report](kubernetes-review-report.md) -- independent review
  of v0.5.0 deployment quality
- [KairosDB upstream Helm chart](https://github.com/kairosdb/kairosdb/tree/master/deployment/helm) --
  reference implementation using HOCON ConfigMap overlay pattern
- [K8ssandra Medusa documentation](https://docs.k8ssandra.io/components/medusa/) --
  backup/restore operator for Cassandra
- [Grafana sidecar provisioning](https://github.com/grafana/helm-charts/tree/main/charts/grafana#sidecar-for-dashboards) --
  dashboard-as-code via ConfigMap sidecar

---

## 6. Documentation Gap Analysis (README vs. K8s Docs)

A systematic comparison of the Docker Compose `README.md` against the full
Kubernetes documentation identified six areas where the K8s docs do not cover
functionality that users expect based on the README. These must be addressed
so that every operation documented for Docker Compose has a clear, complete
K8s equivalent.

### 6.1 Gap Overview

| # | README Feature | K8s Coverage | Severity | Environments |
|---|----------------|-------------|----------|--------------|
| D1 | Grafana dashboard import/provisioning | Not covered | **HIGH** | All |
| D2 | Plugin management (start/stop/restart/status/logs) | Partially covered | **MEDIUM** | All |
| D3 | Grafana first login & datasource setup walkthrough | Auto-provisioned but undocumented | **MEDIUM** | Mostly local |
| D4 | Plugin `.conf` files replaced by Helm values | Not explained | **LOW** | All |
| D5 | Custom volume paths / data persistence model | Partially covered | **LOW** | Production |
| D6 | Log rotation and retention configuration | Not covered | **LOW** | Production |

### 6.2 D1 — Grafana Dashboard Import and Provisioning

**README reference:**

> "To import the dashboards stored in the `dashboards/` folder:
> [Import dashboard](https://grafana.com/docs/grafana/latest/dashboards/export-import/#import-dashboard)
> To test the installation, you can import the `Examon Test - Random Sensor.json` dashboard."

**Current K8s state:**

- The `values.yaml` auto-provisions the KairosDB **datasource** via
  `grafana.datasources.datasources.yaml`, which is correctly handled.
- The `dashboards/Examon Test - Random Sensor.json` file exists in the repo
  but is never referenced by any K8s template or documentation.
- The upgrading guide (`upgrading.md` Step 4) only says "Re-import Grafana
  dashboards through the Grafana UI or API" with no further instructions.
- The v0.5.1 plan (section 1.2 GAP 2) already describes the Grafana sidecar
  dashboard-as-code strategy but only as a future plan, not documentation.

**TODO — Documentation additions:**

- [ ] **D1a:** Add a "Grafana Dashboards" section to `kubernetes.md` covering:
  - Manual dashboard import via Grafana UI (same procedure as README, with
    K8s-specific URL — `http://localhost:3000` for local, or the Ingress URL
    for production).
  - API-based import (useful for scripting):
    ```bash
    # Port-forward to Grafana (if not using NodePort/Ingress)
    kubectl port-forward svc/examon-grafana 3000:80 -n examon &

    # Import dashboard JSON
    curl -X POST -H "Content-Type: application/json" \
      -H "Authorization: Basic $(echo -n admin:<password> | base64)" \
      -d @dashboards/Examon\ Test\ -\ Random\ Sensor.json \
      http://localhost:3000/api/dashboards/db
    ```
  - A note that the bundled `dashboards/Examon Test - Random Sensor.json`
    can be used to verify the full data pipeline after installation.

- [ ] **D1b:** (Implementation item, already tracked in section 1.2 GAP 2)
  Enable Grafana sidecar dashboard provisioning so that bundled dashboards
  are automatically loaded from ConfigMaps on deploy. This eliminates the
  manual import step for core dashboards. Required changes:
  - Set `grafana.sidecar.dashboards.enabled: true` and
    `grafana.sidecar.dashboards.label: grafana_dashboard` in `values.yaml`.
  - Create a ConfigMap template in the umbrella chart's `templates/` that
    loads `dashboards/*.json` files with the `grafana_dashboard` label.
  - Document: "Core dashboards are auto-provisioned on deploy. User-created
    dashboards must be imported manually or backed up via the API."

- [ ] **D1c:** Add environment-specific guidance:
  - **Local/Staging:** Manual UI import is acceptable for testing. The
    auto-provisioned test dashboard (after D1b) provides an out-of-the-box
    verification experience.
  - **Production:** Dashboard-as-code is recommended. User-created dashboards
    should be exported via the Grafana API and stored in version control.

### 6.3 D2 — Plugin Management (Start/Stop/Restart/Status/Logs)

**README reference:**

The README has a large section on `supervisorctl` commands:
- `docker exec -it <container> supervisorctl start/stop/restart/status/tail <plugin>`
- Opening the supervisor shell for interactive management.
- Editing `supervisor.conf` for `autostart=True` to persist enable/disable.

**Current K8s state:**

- `kubernetes.md` has a brief "Managing Plugins" section showing
  `--set random-pub.enabled=false` and `kubectl scale`.
- The `kubernetes.md` "Logs" section shows `kubectl logs` commands.
- No mapping table exists to help Docker Compose users translate their
  existing workflows.

**TODO — Documentation additions:**

- [ ] **D2a:** Expand the "Managing Plugins" section in `kubernetes.md` with a
  complete mapping table between Docker Compose `supervisorctl` operations and
  their Kubernetes equivalents:

  | Operation | Docker Compose | Kubernetes |
  |-----------|---------------|------------|
  | **Start** a plugin | `docker exec -it examon supervisorctl start plugins:random_pub` | `kubectl scale deployment examon-random-pub --replicas=1 -n examon` |
  | **Stop** a plugin | `docker exec -it examon supervisorctl stop plugins:random_pub` | `kubectl scale deployment examon-random-pub --replicas=0 -n examon` |
  | **Restart** a plugin | `docker exec -it examon supervisorctl restart plugins:random_pub` | `kubectl rollout restart deployment/examon-random-pub -n examon` |
  | **Status** of all plugins | `docker exec -it examon supervisorctl status` | `kubectl get pods -n examon` |
  | **Tail logs** of a plugin | `docker exec -it examon supervisorctl tail -f random_pub` | `kubectl logs -f deployment/examon-random-pub -n examon` |
  | **Permanent enable** | Edit `supervisor.conf`, set `autostart=True` | Set `random-pub.enabled: true` in `values-<env>.yaml` + `helm upgrade` |
  | **Permanent disable** | Edit `supervisor.conf`, set `autostart=False` | Set `random-pub.enabled: false` in `values-<env>.yaml` + `helm upgrade` |
  | **Scale** a plugin | Not supported (single container) | `kubectl scale deployment examon-mqtt2kairosdb --replicas=3 -n examon` |

- [ ] **D2b:** Add a note explaining the architectural difference: in Docker
  Compose, all plugins run inside a single container managed by `supervisord`;
  in Kubernetes, each plugin is an independent Deployment with its own pod(s),
  enabling independent scaling, restarts, and resource limits.

- [ ] **D2c:** Document how to get a shell inside a plugin pod for debugging:
  ```bash
  kubectl exec -it deployment/examon-examon-server -n examon -- /bin/bash
  ```
  This is the K8s equivalent of `docker exec -it <container> bash`.

### 6.4 D3 — Grafana First Login and Datasource Setup Walkthrough

**README reference:**

> "Log in to the Grafana server using your browser and the default credentials...
> http://localhost:3000 ... add a new data source and select `KairosDB`.
> Fill out the form with: Name: kairosdb, Url: http://kairosdb:8083, Access: Server"

**Current K8s state:**

- The KairosDB datasource is **auto-provisioned** via
  `grafana.datasources.datasources.yaml` in `values.yaml`. Users do NOT need
  to add it manually — but this is never stated.
- Grafana plugins (KairosDB, plotly, piechart, etc.) are auto-installed via
  `grafana.plugins` in `values.yaml` — also not documented as a feature.
- The `GF_PANELS_DISABLE_SANITIZE_HTML` setting is auto-configured via
  `grafana.env` — not documented.
- No "first login" walkthrough exists for K8s users.
- The production guide briefly mentions auto-provisioning and has a manual
  fallback, but local/staging docs skip this entirely.

**TODO — Documentation additions:**

- [ ] **D3a:** Add a "Grafana First Login" subsection to `kubernetes-local.md`
  (after the data pipeline verification step), covering:
  1. Open `http://localhost:3000` (for K3d) or the Ingress URL (production).
  2. Log in as `admin` with the password set via `--set grafana.adminPassword`
     (default: `Password` if not overridden).
  3. Note: the KairosDB datasource is **already configured** — no manual setup
     needed (unlike Docker Compose).
  4. Note: the KairosDB Grafana plugin and other required plugins are
     **auto-installed** during pod startup via the `grafana.plugins` list.
  5. Link to the dashboard import section (D1a) for importing test dashboards.

- [ ] **D3b:** Add a "What is auto-configured" callout in `kubernetes.md` listing
  all the things that are automatically set up (datasources, plugins, HTML
  sanitization) so users understand they don't need to replicate the README's
  manual configuration steps.

### 6.5 D4 — Plugin Configuration Files Replaced by Helm Values

**README reference:**

> "It is necessary to define all the properties of the `.conf` configuration file
> of the plugins with the appropriate values related to the server hosting the
> framework. In particular, it is necessary to define the IP addresses and ports
> of the server where the KairosDB and/or MQTT broker services run..."

Points users to `publishers/random_pub/random_pub.conf` and per-plugin READMEs.

**Current K8s state:**

- The `change-propagation.md` explains that `.conf` files are generated from
  Helm values via ConfigMap templates, and `configuration.md` lists all
  parameters. However, nowhere does the documentation explicitly say: "the
  old `.conf` files in `publishers/` and `web/examon-server/` are **not used**
  in K8s. All configuration is driven by Helm `values.yaml`."
- A user coming from Docker Compose would naturally look for `.conf` files
  to edit and would be confused.

**TODO — Documentation additions:**

- [ ] **D4a:** Add a paragraph to `kubernetes.md` (in the "Configuration" or
  a new "Configuration Model" section) explicitly stating:

  > In the Kubernetes deployment, plugin configuration files (`.conf`) are
  > **generated automatically** from Helm values and mounted as ConfigMaps.
  > Do not edit the `.conf` files in `publishers/` or `web/examon-server/`
  > directly — those files are only used by the Docker Compose deployment.
  > All configuration is managed via `values.yaml` and environment-specific
  > override files.

- [ ] **D4b:** Add a mapping reference of key old `.conf` fields to new Helm
  values, either in `configuration.md` or `upgrading.md`:

  | Old field (`random_pub.conf`) | New Helm value |
  |-------------------------------|---------------|
  | `MQTT_BROKER` | `random-pub.config.mqttBroker` |
  | `MQTT_PORT` | `random-pub.config.mqttPort` |
  | `MQTT_TOPIC` | `random-pub.config.mqttTopic` |
  | `MQTT_USER` | `random-pub.config.mqttUser` |
  | `MQTT_PASSWORD` | `random-pub.config.mqttPassword` |
  | `NUM_SENSORS` | `random-pub.config.numSensors` |
  | `TS` (sample interval) | `random-pub.config.sampleInterval` |

  Similar tables for `mqtt2kairosdb.conf` and `server.conf`.

### 6.6 D5 — Data Persistence Model and Custom Volume Paths

**README reference:**

> "Two Docker volumes are created... `examon_cassandra_volume`, `examon_grafana_volume`.
> To set a custom volume path, use `driver_opts` with `type: none`, `device: /path/...`"

**Current K8s state:**

- `configuration.md` documents `cassandra.datacenters.dc1.storageClass`,
  `grafana.persistence.enabled/size`, and `mosquitto.persistence.enabled/size`.
- The production guide has a "Storage" section for Cassandra StorageClass.
- Section 1 of this plan document covers backup/snapshot gaps.
- However, there is no unified "Data Persistence" section explaining how K8s
  PVCs replace Docker volumes, what happens to data on pod restart vs.
  `helm uninstall` vs. cluster deletion, or how to specify custom storage
  paths.

**TODO — Documentation additions:**

- [ ] **D5a:** Add a "Data Persistence" section to `kubernetes.md` covering:
  - How PVCs replace Docker volumes (the K8s equivalent).
  - What data survives what operations:

    | Event | Cassandra data | Grafana data |
    |-------|:---:|:---:|
    | Pod restart | Survives | Survives |
    | `helm upgrade` | Survives | Survives |
    | `helm uninstall` | Depends on reclaim policy | Depends on reclaim policy |
    | K3d cluster delete | **Lost** (local only) | **Lost** (local only) |
    | Node failure (production) | Survives (replicas) | Survives (if PVC on shared storage) |

  - Environment-specific behavior:
    - **Local (K3d):** Uses `local-path` provisioner. Data persists across
      pod restarts but is lost when the K3d cluster is deleted.
    - **Staging (K3d):** Same as local; data is ephemeral to the cluster.
    - **Production:** Set `storageClass` to match infrastructure
      (e.g., `cinder-ssd`, `gp3`, `longhorn`). Use `reclaimPolicy: Retain`
      for critical data (see section 1.2 GAP 4).

- [ ] **D5b:** Add the K8s equivalent of "custom volume path": explain how to
  use a `hostPath` PersistentVolume or a `local` StorageClass for bare-metal
  deployments where data must reside on a specific disk/partition.

### 6.7 D6 — Log Rotation and Retention

**README reference (via docker-compose.yml):**

Each service in `docker-compose.yml` specifies logging configuration:
```yaml
logging:
  driver: json-file
  options:
    max-size: "10m"
    max-file: "1"
```

**Current K8s state:**

- The `kubernetes.md` "Logs" section shows `kubectl logs` commands but says
  nothing about log rotation, retention, or aggregation.

**TODO — Documentation additions:**

- [ ] **D6a:** Add a note to the "Logs" section of `kubernetes.md` explaining:
  - In Kubernetes, container log rotation is handled by the **container
    runtime** (containerd/CRI-O), not by individual services. The Docker
    Compose `json-file` settings have no direct K8s equivalent — containerd
    handles rotation automatically.
  - K3d default: containerd keeps ~10MB per container before rotation.
  - Production recommendation: the default containerd rotation is sufficient
    for cluster-level operations, but for persistent, searchable logs,
    deploy a **log aggregation stack**:
    - **Loki + Promtail + Grafana** (lightweight, integrates with existing
      Grafana — recommended for ExaMon)
    - **EFK** (Elasticsearch + Fluentd + Kibana) — heavier but more mature
    - **Cloud-native** (CloudWatch, GCP Logging, Azure Monitor) — if on
      managed K8s

- [ ] **D6b:** For production, add a brief note in `kubernetes-production.md`
  recommending a log retention strategy and linking to the Logs section.

### 6.8 Implementation Priority

| Priority | TODO | Effort | Depends On |
|----------|------|--------|-----------|
| **P0** | D1a (dashboard import docs) | Low | — |
| **P0** | D2a (plugin management mapping table) | Low | — |
| **P0** | D3a (Grafana first login) | Low | — |
| **P1** | D1b (dashboard-as-code provisioning) | Medium | Grafana sidecar config |
| **P1** | D4a, D4b (conf file replacement docs) | Low | — |
| **P1** | D5a (persistence model docs) | Low | — |
| **P2** | D1c (per-environment dashboard guidance) | Low | D1a |
| **P2** | D2b, D2c (architecture note, exec shell) | Low | — |
| **P2** | D3b (auto-configured callout) | Low | — |
| **P2** | D5b (custom volume paths for bare metal) | Low | — |
| **P2** | D6a, D6b (logging docs) | Low | — |

---

## 7. Implementation Phases (Updated)

| Phase | Items | Depends On | Effort |
|-------|-------|-----------|--------|
| **Phase 1** | Cassandra Medusa backups, PV reclaim policy docs, Mosquitto persistence fix | — | Medium |
| **Phase 2** | KairosDB HOCON ConfigMap overlay, updated Dockerfile | — | Medium |
| **Phase 3** | Grafana dashboard-as-code + API backup script | — | Medium |
| **Phase 4** | Documentation gaps D1–D6 (README parity) | D1b depends on Phase 3 | Low-Medium |
| **Phase 5** | Security contexts on all workloads | Phase 2 (readOnlyRootFilesystem) | Medium |
| **Phase 6** | PDBs, image versioning, expanded migration docs | — | Low-Medium |
| **Phase 7** | Observability (ServiceMonitors, alert rules, dashboards) | Phase 3 (Grafana provisioning) | Medium |
| **Phase 8** | HPAs, NetworkPolicies | Phase 7 (metrics for HPA decisions) | Medium |
