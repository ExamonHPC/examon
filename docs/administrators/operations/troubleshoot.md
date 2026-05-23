# Troubleshooting

This guide covers the systematic debugging approach for ExaMon Kubernetes
deployments, followed by specific issues encountered and their solutions.

## Systematic Debugging Methodology

When pods are not healthy, follow this top-down approach:

### Step 1: Get the Big Picture

```bash
kubectl get pods -n examon -o wide
```

Identify which pods are unhealthy and note their **Status** column:

| Status | Meaning | Next Step |
|--------|---------|-----------|
| `Pending` | Cannot be scheduled | Check node resources / PVC binding |
| `ImagePullBackOff` | Cannot pull container image | Check registry, image name/tag |
| `CrashLoopBackOff` | Container starts and exits | Check container logs |
| `RunContainerError` | Container cannot start at all | Check `kubectl describe pod` |
| `Init:0/1` | Init container not finished | Wait or check init container logs |
| `Running` but `0/1` Ready | Readiness probe failing | Check probe config and app health |

### Step 2: Read the Logs

```bash
kubectl logs <pod-name> -n examon
kubectl logs <pod-name> -n examon --previous   # if container already restarted
```

The logs tell you **why** the application crashed. Common patterns:

- **Connection refused / No host available** → wrong service name or target not ready
- **Authentication error** → missing or wrong credentials
- **Configuration error** → missing config key, wrong config format
- **OOM / Java heap errors** → resource limits vs JVM heap mismatch
- **Module access errors (Java)** → missing `--add-opens` JVM flags

### Step 3: Inspect the Pod Spec

```bash
kubectl describe pod <pod-name> -n examon
```

Look for:

- **Events section** at the bottom: scheduling failures, probe failures, image pull errors
- **Container State / Last State**: exit codes and error messages
- **Environment variables**: verify they have the expected values
- **Volume mounts**: verify ConfigMaps are mounted correctly

### Step 4: Verify What Helm Actually Deployed

```bash
# See the rendered manifest for a specific component
helm get manifest examon -n examon | grep -A30 "Source: examon/charts/<subchart>"

# Compare with what you expect from the templates
helm template examon ./deploy/helm/examon \
  -f ./deploy/helm/examon/values-local.yaml -n examon \
  -s charts/<subchart>/templates/deployment.yaml
```

This catches issues where:

- Template changes were not picked up (forgot `helm dependency update`)
- Umbrella chart `values.yaml` overrides subchart defaults unexpectedly
- The wrong values file was used

### Step 5: Test Connectivity from Inside the Cluster

```bash
# DNS resolution
kubectl run debug --rm -it --image=busybox -- nslookup <service-name>.examon.svc.cluster.local

# TCP connectivity
kubectl exec <any-running-pod> -n examon -- nc -zv <service-name> <port>

# HTTP endpoint
kubectl exec <any-running-pod> -n examon -- wget -qO- http://<service-name>:<port>/health
```

### Step 6: Fix, Rebuild, Redeploy

After fixing the root cause:

1. If you changed a **Dockerfile** or application code:
   ```bash
   docker build -t examon-registry:5111/examon/<service>:<new-tag> \
     -f deploy/docker/<service>/Dockerfile deploy/docker/<service>/
   docker push examon-registry:5111/examon/<service>:<new-tag>
   ```
   Update the tag in the values file, then upgrade.

2. If you changed a **subchart template** (anything under `subcharts/`):
   ```bash
   cd deploy/helm/examon && helm dependency update && cd ../../..
   ```

3. Upgrade:
   ```bash
   helm upgrade examon ./deploy/helm/examon \
     -f ./deploy/helm/examon/values-local.yaml -n examon --timeout 10m
   ```

4. If pods don't restart automatically (same image tag / unchanged pod spec):
   ```bash
   kubectl rollout restart deployment/<deployment-name> -n examon
   # For StatefulSets (like mosquitto):
   kubectl rollout restart statefulset/<statefulset-name> -n examon
   ```

5. If a Helm upgrade is stuck (`another operation is in progress`):
   ```bash
   helm history examon -n examon                    # find the last good revision
   helm rollback examon <last-good-revision> -n examon
   # Then retry the upgrade
   ```

## Specific Issues and Solutions

### 1. Mosquitto CrashLoopBackOff: "Address in use"

**Symptom:** Mosquitto pod crashes with:
```
Error: Address in use
```

**Root cause:** In Mosquitto 2.x, if configuration directives like
`max_connections` appear before `listener`, Mosquitto creates a default
listener on port 1883. When the explicit `listener 1883 0.0.0.0` directive
is then processed, the port is already bound.

**Solution:** In the mosquitto ConfigMap template
(`subcharts/mosquitto/templates/configmap.yaml`), ensure `listener` is the
**first** directive:

```yaml
data:
  mosquitto.conf: |
    listener {{ .Values.service.mqttPort }} 0.0.0.0
    allow_anonymous {{ .Values.config.allowAnonymous }}
    persistence {{ .Values.config.persistence }}
    max_inflight_messages {{ .Values.config.maxInflightMessages }}
    max_queued_messages {{ .Values.config.maxQueuedMessages }}
    max_connections {{ .Values.config.maxConnections }}
```

**Files changed:** `deploy/helm/examon/subcharts/mosquitto/templates/configmap.yaml`

---

### 2. KairosDB CrashLoopBackOff: Java Module Access Error

**Symptom:** KairosDB crashes with:
```
java.lang.reflect.InaccessibleObjectException: Unable to make protected final
java.lang.Class java.lang.ClassLoader.defineClass(...) accessible: module
java.base does not "opens java.lang" to unnamed module
```

**Root cause:** KairosDB 1.3.0 uses Google Guice with cglib, which requires
reflective access to internal JDK classes. Java 17+ restricts this access by
default via the module system.

**Solution:** Add `--add-opens` flags to the JVM options in
`deploy/docker/kairosdb/kairosdb-env.sh`:

```bash
if [ -z "$JAVA_OPTS" ]; then
  JAVA_OPTS="-Xmx512m -Xms256m"
fi

JAVA_OPTS="$JAVA_OPTS --add-opens java.base/java.lang=ALL-UNNAMED"
JAVA_OPTS="$JAVA_OPTS --add-opens java.base/java.lang.reflect=ALL-UNNAMED"
JAVA_OPTS="$JAVA_OPTS --add-opens java.base/java.util=ALL-UNNAMED"
```

The `if` guard also ensures that `JAVA_OPTS` passed from Kubernetes environment
variables (via Helm values) are respected, rather than being overwritten by a
hardcoded heap size.

**Files changed:** `deploy/docker/kairosdb/kairosdb-env.sh`

---

### 3. KairosDB CrashLoopBackOff: OOM / Hardcoded 8G Heap

**Symptom:** KairosDB crashes or gets OOM-killed despite setting
`config.javaOpts: "-Xmx512m"` in Helm values.

**Root cause:** The original `kairosdb-env.sh` hardcoded
`JAVA_OPTS="-Xmx8G -Xms8G"`, unconditionally overwriting whatever was
passed via the `JAVA_OPTS` environment variable from the Kubernetes
Deployment spec.

**Solution:** Modified `kairosdb-env.sh` to only set defaults when `JAVA_OPTS`
is not already defined (see fix in issue #2 above; the `if [ -z "$JAVA_OPTS" ]`
guard serves both purposes).

**Files changed:** `deploy/docker/kairosdb/kairosdb-env.sh`

---

### 4. KairosDB CrashLoopBackOff: Connecting to localhost Instead of Cassandra Service

**Symptom:** KairosDB logs show:
```
Connecting to localhost:9042
NoHostAvailableException: All host(s) tried for query failed
(tried: localhost/127.0.0.1:9042)
```

despite `CASSANDRA_HOST_LIST` being set correctly in the pod env.

**Root cause:** KairosDB 1.3.0 introduced a new **HOCON-format** configuration
file (`kairosdb.conf`) that takes precedence over the legacy
`kairosdb.properties`. The `config-kairos.sh` entrypoint only patched the
`.properties` file via `sed`, but `kairosdb.conf` still had
`cql_host_list: ["localhost"]`.

**Solution:** Updated `config-kairos.sh` to patch **both** config files:

```bash
# Legacy .properties file
sed -i "s/^kairosdb.datastore.cassandra.cql_host_list.*$/kairosdb.datastore.cassandra.cql_host_list=$CASSANDRA_HOST_LIST/" \
  /opt/kairosdb/conf/kairosdb.properties

# HOCON .conf file (KairosDB 1.3.0+)
CASS_HOST=$(echo "$CASSANDRA_HOST_LIST" | sed 's/:.*$//')
sed -i "s|cql_host_list: \[\"localhost\"\]|cql_host_list: [\"${CASS_HOST}\"]|g" \
  /opt/kairosdb/conf/kairosdb.conf
```

**Files changed:** `deploy/docker/kairosdb/config-kairos.sh`

---

### 5. KairosDB CrashLoopBackOff: Cassandra Authentication Required

**Symptom:** KairosDB logs show:
```
AuthenticationException: Authentication error on host ...:
Host ... requires authentication, but no authenticator found
in Cluster configuration
```

**Root cause:** K8ssandra deploys Cassandra with authentication enabled by
default. KairosDB was not configured with credentials.

**Solution:**

1. The kairosdb Helm subchart now supports reading credentials from a
   Kubernetes Secret via `config.cassandraAuth.secretName`:

   ```yaml
   kairosdb:
     config:
       cassandraAuth:
         secretName: "examon-cassandra-superuser"
   ```

2. `config-kairos.sh` was updated to set the auth properties in both
   config files when `CASSANDRA_USER` and `CASSANDRA_PASSWORD` env vars
   are present.

**Files changed:**
- `deploy/docker/kairosdb/config-kairos.sh`
- `deploy/helm/examon/subcharts/kairosdb/templates/deployment.yaml`
- `deploy/helm/examon/subcharts/kairosdb/values.yaml`

---

### 6. examon-server CrashLoopBackOff: "CASSANDRA_KEY_SPACE is not defined"

**Symptom:** examon-server crashes at startup with:
```
ERROR - CASSANDRA_KEY_SPACE is not defined in the configuration file.
```

**Root cause:** The `cassandraKeySpace` field in the umbrella chart's
`values.yaml` was empty (`""`). The examon-server application requires a
non-empty keyspace name.

**Solution:** Set `cassandraKeySpace: "kairosdb"` in the umbrella chart's
default values and in the environment-specific values files. The keyspace
`kairosdb` is the default keyspace created by KairosDB when it first connects
to Cassandra.

**Files changed:**
- `deploy/helm/examon/values.yaml`
- `deploy/helm/examon/subcharts/examon-server/values.yaml`

---

### 7. examon-server CrashLoopBackOff: Cassandra "Password must not be null"

**Symptom:** examon-server logs show:
```
AuthenticationFailed: Failed to authenticate to ...:
Error from server: code=0100 [Bad credentials] message="Password must not be null"
```

**Root cause:** K8ssandra enables Cassandra authentication by default.
The examon-server pod needs Cassandra credentials to connect.

**Solution (current):** This is now handled automatically. The deployment
template injects `CASSANDRA_USER` and `CASSANDRA_PASSWORD` environment
variables from the K8ssandra-generated secret (`examon-cassandra-superuser`)
via `secretKeyRef`. The `server.py` application checks these env vars first,
falling back to `server.conf` values.

Verify the `cassandraAuth.secretName` is set in your values file:

```yaml
examon-server:
  config:
    cassandraAuth:
      secretName: "examon-cassandra-superuser"
```

If the error persists on a fresh install, it's likely a bootstrap timing
issue: `examon-server` starts before the K8ssandra secret is created.
Wait for Kubernetes to restart the pod automatically (it will succeed once
the secret exists).

**Files involved:** `deploy/helm/examon/subcharts/examon-server/templates/deployment.yaml`, `web/examon-server/server.py`

---

### 8. examon-server CrashLoopBackOff: Cannot Connect to Grafana on Port 3000

**Symptom:** examon-server logs show:
```
ConnectionError: HTTPConnectionPool(host='examon-grafana', port=3000):
Max retries exceeded ... [Errno 111] Connection refused
```

**Root cause:** The Grafana Helm chart exposes its Kubernetes service on
port **80** (proxying to container port 3000). The `authUrl` was configured
with `http://examon-grafana:3000/...`, which hits a non-listening port.

**Solution:** Remove the port from the auth URL:

```yaml
examon-server:
  config:
    authUrl: "http://examon-grafana/api/datasources/id/kairosdb"
```

**Files changed:**
- `deploy/helm/examon/values.yaml`
- `deploy/helm/examon/subcharts/examon-server/values.yaml`

---

### 9. examon-server Not Ready: Readiness Probe Returns 401

**Symptom:** examon-server is `Running` but shows `0/1 Ready`. Events show:
```
Readiness probe failed: HTTP probe failed with statuscode: 401
```

**Root cause:** The readiness and liveness probes were configured as HTTP GET
on `/`, but the examon-server root endpoint requires Grafana-based
authentication and returns 401 for unauthenticated requests. Kubernetes only
considers HTTP 200-399 as healthy.

**Solution:** Changed the probes from `httpGet` to `tcpSocket`, which simply
checks that the port is accepting connections:

```yaml
readinessProbe:
  tcpSocket:
    port: http
  initialDelaySeconds: 10
  periodSeconds: 10
livenessProbe:
  tcpSocket:
    port: http
  initialDelaySeconds: 15
  periodSeconds: 20
```

**Files changed:** `deploy/helm/examon/subcharts/examon-server/templates/deployment.yaml`

---

### 10. random-pub RunContainerError: "executable file not found"

**Symptom:** random-pub pod shows `RunContainerError` with:
```
exec: "-b": executable file not found in $PATH
```

**Root cause:** The random-pub Deployment template specified CLI `args`
(`["-b", "examon-mosquitto", "-p", "1883", ...]`) without an explicit
`command`. The Python base image's default entrypoint tried to execute `"-b"`
as a command. Additionally, `random_pub.py` is an `ExamonApp`-based
application that reads configuration from a `random_pub.conf` file, not CLI
arguments.

**Solution:**

1. Removed the `args` from the Deployment template
2. Created a ConfigMap template to generate `random_pub.conf` from Helm values
3. Added a volume mount to provide the config file to the container

The ConfigMap generates the correct INI-format config file:

```ini
[MQTT]
MQTT_BROKER = examon-mosquitto
MQTT_PORT = 1883
...

[Daemon]
NUM_SENSORS = 10
TS = 2
```

**Files changed:**
- `deploy/helm/examon/subcharts/random-pub/templates/deployment.yaml`
- `deploy/helm/examon/subcharts/random-pub/templates/configmap.yaml` (new)
- `deploy/helm/examon/subcharts/random-pub/values.yaml`

---

### 11. Cassandra Service Name Mismatch

**Symptom:** KairosDB or examon-server cannot connect to Cassandra, despite
Cassandra pods being healthy.

**Root cause:** The default `cassandraHostList` and `cassandraIp` values
referenced `examon-k8ssandra-operator-dc1-service`, but the actual Kubernetes
service created by K8ssandra is `examon-cassandra-dc1-service`.

**How to find the correct name:**
```bash
kubectl get svc -n examon | grep cass
```

**Solution:** Updated all references in `values.yaml` and subchart defaults
to use `examon-cassandra-dc1-service`.

**Files changed:**
- `deploy/helm/examon/values.yaml`
- `deploy/helm/examon/subcharts/kairosdb/values.yaml`
- `deploy/helm/examon/subcharts/examon-server/values.yaml`

---

### 12. K3d Image Caching: Updated Image Not Used

**Symptom:** After rebuilding and pushing a Docker image with the same tag,
the new pod still runs the old image.

**Root cause:** K3d nodes run containerd, which caches images independently
from the host Docker daemon. With `imagePullPolicy: IfNotPresent` (the
subchart default), containerd resolves the tag from its local cache and
never re-pulls from the registry, even if the registry has a newer image
with the same tag.

**Prevention:** `values-local.yaml` now sets `pullPolicy: Always` for all
custom images. With this setting, the standard build-push-restart workflow
works correctly because containerd re-pulls from the registry every time.
See the [Local Development Workflow](kubernetes-local.md#local-development-workflow)
for the full recommended cycle.

**Fix (if `pullPolicy` is `IfNotPresent`):** Use `k3d image import` to
load the rebuilt image directly into the K3d containerd cache:

```bash
docker build -t examon-registry:5111/examon/<service>:latest \
  -f deploy/docker/<service>/Dockerfile .
docker push examon-registry:5111/examon/<service>:latest

# Import into K3d so containerd sees the new layers
k3d image import examon-registry:5111/examon/<service>:latest -c examon-local

# Force the pod to restart with the new image
kubectl rollout restart deployment/examon-<service> -n examon
```

**Other alternatives:**

- **Unique tag per rebuild** (`git rev-parse --short HEAD`): Avoids the
  caching problem entirely. Update the tag in values and run `helm upgrade`.
- **`imagePullPolicy: Always`**: Set in values for development. This is
  already the default in `values-local.yaml`.

---

### 13. Helm Subchart Template Changes Not Applied

**Symptom:** After editing a file under `deploy/helm/examon/subcharts/`,
`helm upgrade` succeeds but the deployed manifest still contains the old
template content.

**Root cause:** Helm packages subcharts into `.tgz` archives inside
`deploy/helm/examon/charts/`. The `helm upgrade` command uses these archives,
not the `subcharts/` source directory. If you don't rebuild the archives,
your changes are invisible.

**Solution:**

```bash
cd deploy/helm/examon
helm dependency update    # rebuilds the .tgz archives from subcharts/
cd ../../..

helm upgrade examon ./deploy/helm/examon \
  -f ./deploy/helm/examon/values-local.yaml -n examon
```

---

### 14. Helm Upgrade Fails: "another operation is in progress"

**Symptom:**
```
Error: UPGRADE FAILED: another operation (install/upgrade/rollback) is in progress
```

**Root cause:** A previous Helm operation timed out or was interrupted,
leaving the release in a `pending-upgrade` or `pending-install` state.

**Solution:**

```bash
# Check release history
helm history examon -n examon

# Rollback to the last successful revision
helm rollback examon <revision-number> -n examon

# Then retry the upgrade
helm upgrade examon ./deploy/helm/examon ...
```

---

### 15. K8ssandra Operator Webhook Not Ready

**Symptom:**
```
failed calling webhook "vk8ssandracluster.kb.io":
no endpoints available for service "k8ssandra-operator-webhook-service"
```

**Root cause:** The `K8ssandraCluster` CR was submitted before the operator's
webhook endpoint was ready. This happens when the operator and the CR are
deployed in the same Helm release: Helm cannot guarantee ordering between
a subchart's Deployment and the parent chart's custom resource.

**Solution:**

The K8ssandra operator is installed as a **separate Helm release** with
`--wait`, which ensures the webhook is fully ready before returning. The
ExaMon chart is then installed in a second `helm install`. This is the
default behavior of `k8s-local-setup.sh` and the CI pipeline.

If you hit this error, verify the operator is running:

```bash
helm list -n examon | grep k8ssandra-operator
kubectl get pods -n examon -l app.kubernetes.io/name=k8ssandra-operator
```

If the operator release is missing, install it:

```bash
helm install k8ssandra-operator k8ssandra/k8ssandra-operator \
  -n examon --wait --timeout 5m
```

Then retry the ExaMon chart install/upgrade.

### 15b. K8ssandra Operator Webhook Certificate Conflict

**Symptom:**
```
tls: failed to verify certificate: x509: certificate is valid for
examon-k8ssandra-operator-webhook-service.examon.svc, not
k8ssandra-operator-webhook-service.examon.svc
```

**Root cause:** Two K8ssandra operator installations exist: one standalone
and one from a previous umbrella chart dependency. They create webhook
services with different names but the same CRD validators.

**Solution:**

1. Check for duplicate releases:
   ```bash
   helm list -n examon | grep k8ssandra
   ```

2. Uninstall the duplicate:
   ```bash
   helm uninstall <duplicate-release-name> -n examon
   ```

3. Keep only the standalone `k8ssandra-operator` release.

**Files changed:** `deploy/helm/examon/Chart.yaml`, `scripts/k8s-local-setup.sh`

---

### 16. Registry Hostname Not Resolved (K3d)

**Symptom:** `docker push` fails with:
```
dial tcp: lookup examon-registry: no such host
```

**Root cause:** K3d creates the registry as a Docker container named
`examon-registry`. The host machine cannot resolve this hostname without
an explicit `/etc/hosts` entry.

**Solution:**

```bash
echo "127.0.0.1 examon-registry" | sudo tee -a /etc/hosts
```

The automated setup script handles this automatically. See the
[local deployment guide](kubernetes-local.md#step-2-register-the-k3d-registry-hostname).

---

### 17. Fresh Install: examon-server and KairosDB CrashLoop During Bootstrap

**Symptom:** On a fresh `helm install`, `examon-server` and `kairosdb` pods
enter `CrashLoopBackOff` with connection errors to Cassandra. After several
minutes, they recover and become `Running` / `Ready`.

**Root cause:** This is **expected behavior**, not a bug. Helm deploys all
components simultaneously, but Cassandra takes 2-5 minutes to initialize
(schema creation, superuser secret generation). KairosDB and examon-server
start before Cassandra is ready and fail their initial connection attempts.

**Why it resolves itself:**

- Both KairosDB and examon-server have retry logic with exponential backoff.
- Kubernetes restarts crashed pods automatically.
- Once Cassandra is ready and the `examon-cassandra-superuser` secret exists,
  the pods connect successfully on the next restart.
- Cassandra credentials are injected via `secretKeyRef` environment variables,
  so no manual `helm upgrade --set` is needed.

**When to worry:** If the pods are still in `CrashLoopBackOff` after
**10 minutes**, check:

1. Cassandra pod status: `kubectl get pods -l app.kubernetes.io/name=cassandra -n examon`
2. Cassandra logs: `kubectl logs examon-cassandra-dc1-default-sts-0 -c cassandra -n examon`
3. Whether the superuser secret exists: `kubectl get secret examon-cassandra-superuser -n examon`

---

### 18. Grafana: KairosDB Data Source Fails or Dashboards Show "No Data"

**Symptom:** On a freshly installed v0.5.0 chart, the Grafana KairosDB
data source either does not appear, fails the **Test** action, or panels
show "No data" / `Datasource not found` errors. The browser console
typically reports a plugin loading or AngularJS-related failure.

**Root cause:** The original `grafana-kairosdb-datasource` plugin is
AngularJS-based and is no longer compatible with Grafana 11+ (AngularJS
support has been removed). The v0.5.0 chart switches to the React-based
[ArpNetworking
fork](https://github.com/ArpNetworking/kairosdb-datasource), which is
unsigned and must be explicitly whitelisted in the Grafana config. The
auto-provisioned data source must also reference the plugin by its new
`type`. This is tracked as [Issue #25](https://github.com/ExamonHPC/examon/issues/25).

**Resolution.** Re-`helm upgrade` with the chart's defaults; they
already encode all three pieces:

1. Plugin install in `grafana.plugins`:
   ```yaml
   grafana:
     plugins:
       - https://github.com/ArpNetworking/kairosdb-datasource/releases/download/v1.4.0/arpnetworking-kairosdb-datasource-1.4.0.zip;arpnetworking-kairosdb-datasource
   ```
2. Unsigned-plugin allowlist in `grafana.grafana.ini`:
   ```yaml
   grafana:
     grafana.ini:
       plugins:
         allow_loading_unsigned_plugins: arpnetworking-kairosdb-datasource
   ```
3. Data source provisioning in `grafana.datasources`:
   ```yaml
   grafana:
     datasources:
       datasources.yaml:
         apiVersion: 1
         datasources:
           - name: kairosdb
             type: arpnetworking-kairosdb-datasource
             uid: examon-kairosdb
             url: http://examon-kairosdb:8083
             access: proxy
             isDefault: true
   ```

**Verification:**

```bash
kubectl exec -n examon deploy/examon-grafana -c grafana -- \
  curl -s -u admin:<password> http://localhost:3000/api/datasources \
  | jq '.[] | {name, type, uid}'
```

Expect `type: arpnetworking-kairosdb-datasource` and `uid: examon-kairosdb`.
If you see `grafana-kairosdb-datasource` instead, you are still on the
legacy plugin: re-run `helm upgrade` against the v0.5.0 chart and
restart the Grafana pod so the plugin install init container re-runs.

**Note for legacy Docker Compose v0.4.0:** the Docker Compose stack still
runs Grafana 7.3.10 with the AngularJS plugin and keeps working. The
matching v0.4.0 snapshot of the test dashboard is preserved under
`dashboards/legacy/`.

---

## General Debugging Commands

```bash
# Pod status overview
kubectl get pods -n examon -o wide

# Recent events (sorted by time)
kubectl get events -n examon --sort-by='.lastTimestamp'

# Pod details and events
kubectl describe pod <pod-name> -n examon

# Container logs
kubectl logs <pod-name> -n examon
kubectl logs <pod-name> -n examon --previous

# Exec into a running container
kubectl exec -it <pod-name> -n examon -- bash

# Check what Helm deployed
helm get manifest examon -n examon
helm get values examon -n examon

# Cassandra health
kubectl exec -it examon-cassandra-dc1-default-sts-0 -c cassandra -n examon \
  -- nodetool status

# Registry contents
curl http://examon-registry:5111/v2/_catalog
curl http://examon-registry:5111/v2/examon/<image>/tags/list
```

## Resetting the Environment

### Local

```bash
k3d cluster delete examon-local
./scripts/k8s-local-setup.sh
```

### Staging

```bash
k3d cluster delete examon-staging
k3d cluster create --config deploy/k3d/staging-cluster.yaml
```
