# ExaMon Kubernetes Deployment Review

## Scope

This review covers the v0.5.0 Kubernetes migration as documented under `docs/Deployment/` and implemented under `deploy/helm/examon/`, with comparison against the legacy Docker Compose deployment.

## Executive Summary

The migration is a meaningful improvement over the legacy monolithic Docker Compose setup. Breaking ExaMon into separate Kubernetes workloads, introducing environment-specific values files, and wiring in K8ssandra, Helm, and basic CI testing are all strong architectural steps.

The implementation is not yet production-grade by 2026 Kubernetes standards. The main gaps are around workload hardening, secure secret handling, image lifecycle management, Cassandra topology realism, network and observability controls, and scaling semantics. The current chart is best described as a solid functional baseline for local/staging validation, not a fully hardened production platform.

## What The Project Is Trying To Achieve

ExaMon is a HPC monitoring and telemetry platform built around:

- MQTT ingestion for collectors and publishers
- KairosDB for time-series storage
- Cassandra as the persistent backend
- Grafana for visualization and alerting
- `examon-server` as the HTTP API / scheduler integration layer

The legacy deployment bundles most runtime behavior into a single `examon` container managed by `supervisord`. The new Kubernetes design decomposes those processes into separate workloads, which is the right direction for resilience, independent scaling, and operability.

## What Is Good

### 1. The decomposition is correct

Splitting `mosquitto`, `random-pub`, `mqtt2kairosdb`, `kairosdb`, `examon-server`, and `grafana` into separate workloads is the right model for Kubernetes. It removes the monolithic failure domain of the old container and creates room for independent rollouts and tuning.

### 2. The environment split is sensible

The `values-local.yaml`, `values-staging.yaml`, and `values-production.yaml` approach is practical and readable. It makes the deployment intent visible and supports a path from laptop testing to production.

### 3. Cassandra is treated as a first-class stateful service

Using K8ssandra is a reasonable default for a Cassandra-backed platform. The staging and production documents correctly emphasize rack/zone awareness, anti-affinity, and backup thinking.

### 4. Basic health probes are present

`kairosdb`, `mosquitto`, and `examon-server` at least expose readiness/liveness probes, which is better than many first-pass Helm migrations.

### 5. The project added automated cluster validation

The local setup script and GitHub Actions workflow show intent to continuously validate the deployment, which is essential for a chart-driven platform.

## Major Findings

### 1. The chart is not hardened enough for production workloads

The templates do not yet apply the core Kubernetes security controls expected in 2026:

- No `securityContext` or `podSecurityContext`
- No `runAsNonRoot`
- No `readOnlyRootFilesystem`
- No `allowPrivilegeEscalation: false`
- No capability drop policy
- No `seccompProfile`
- No `fsGroup` handling for stateful volumes where needed

This is especially important for `mosquitto`, `examon-server`, and any container that consumes config or writes to mounted paths. Without these settings, the chart depends heavily on image defaults and cluster policy, which is fragile and increasingly non-compliant in hardened clusters.

### 2. Secrets are still handled too casually

The production docs explicitly suggest `--set grafana.adminPassword=...`, and `examon-server` can fall back to plain values in Helm config. The chart currently also exposes sensitive connection fields directly in values files.

This creates several problems:

- Secrets end up in Git history or CI logs
- Helm release metadata may retain sensitive values
- The pattern does not scale to real secret rotation
- It complicates external secret manager integration

For production, secret material should come from external secret sources or Kubernetes Secrets provisioned out-of-band, then referenced by name.

### 3. Image versioning is inconsistent

The chart mixes pinned versions and `latest` tags:

- `kairosdb` is pinned
- `mosquitto`, `mqtt2kairosdb`, `random-pub`, and `examon-server` use `latest` in several values files

This is a deployment risk because:

- rollouts become non-reproducible
- rollback safety is degraded
- image provenance and CVE triage become harder

For production, every runtime image should be pinned by immutable digest, or at minimum by explicit version tags with a documented promotion process.

### 4. The Cassandra topology is described better than it is implemented

The docs describe soft/hard zone affinity and three-node HA, but the actual chart template only conditionally emits `racks` when `podAntiAffinity` is enabled. In the default configuration, the chart does not clearly enforce:

- topology spread constraints
- anti-affinity at pod level
- disruption budgets
- zone-aware scheduling guardrails
- realistic storage class selection

In practice, Cassandra on Kubernetes needs explicit scheduling policy, storage quality, and disruption control. A 3-node cluster without carefully enforced anti-affinity and PDBs can still fail during node maintenance or cloud AZ disruption.

### 5. The docs overstate some production readiness claims

The documentation says “production,” “reliable,” and “scalable” in several places, but the implementation still lacks:

- PodDisruptionBudgets
- HorizontalPodAutoscaler definitions
- Cluster autoscaling guidance
- Resource requests/limits tuning per environment beyond simple defaults
- ServiceMonitor / PrometheusRule manifests
- backup and restore operational runbooks
- upgrade/rollback strategies for Cassandra and KairosDB

That means the documentation currently promises more operational maturity than the chart delivers.

### 6. Observability is incomplete

There is no clear first-class observability stack in the chart for:

- application metrics
- Kubernetes service discovery into Prometheus
- alerting rules
- tracing
- structured log shipping

Given the platform’s role as telemetry infrastructure, observability should be treated as a core product feature, not a later add-on.

### 7. Scaling semantics are weak for the data path

The current design can scale stateless components horizontally, but the data flow still has bottlenecks:

- `mqtt2kairosdb` may scale only if topic partitioning and consumer semantics are well defined
- KairosDB scaling is limited by Cassandra write throughput and query patterns
- Mosquitto is single-replica in default values, which creates a single ingress chokepoint
- `random-pub` is a test tool, but it is enabled by default in some environments, which can pollute production semantics

In other words, Kubernetes replication alone does not guarantee throughput scaling for this architecture.

### 8. Production ingress design is incomplete

The production values add Grafana ingress and set Mosquitto to `LoadBalancer`, but the overall exposure model is still fragmented:

- no consistent ingress strategy for all HTTP services
- no clear network edge policy for MQTT exposure
- no documented TLS posture for internal service-to-service traffic
- no reference to mTLS or service mesh, if that is expected later

This is acceptable for a baseline, but not for a mature production platform.

### 9. The CI test is useful but not sufficient

The GitHub Actions workflow is a good start, but it validates mostly startup and reachability. It does not verify:

- restart behavior
- disruption tolerance
- data persistence after pod deletion
- rollback behavior
- upgrade compatibility
- network policy enforcement
- secret injection correctness
- resource exhaustion behavior

For a stateful platform, those are the tests that matter most.

## Detailed Review By Area

### Legacy Docker Compose

The legacy setup is simple and useful as a reference. It remains valuable for quick testing, but the monolithic `supervisord` container is a technical debt anchor:

- it combines unrelated services into one blast radius
- it makes lifecycle management awkward
- it blurs resource ownership
- it prevents independent scaling

Keeping it as a legacy path is fine, but it should be treated as a compatibility mode, not a long-term target.

### Helm Chart Structure

The umbrella chart pattern is sensible for this stack because it provides one release boundary while still allowing workload-level separation.

However, the chart still needs stronger consistency:

- values schema validation
- reusable helper patterns for security and probes
- stronger contract between docs and actual values
- explicit support for image digests
- a safer secret model

### KairosDB

The chart gives KairosDB probes and resource requests, which is a good baseline. The main concerns are:

- it relies on a relatively old JVM-style configuration model
- no clear HPA strategy
- no workload anti-affinity
- no persistent storage because it is stateless, which is fine, but it means backend pressure lands entirely on Cassandra

KairosDB can be horizontally scaled, but only if Cassandra and the ingest path are tuned accordingly.

### Mosquitto

Mosquitto is deployed as a StatefulSet, which is a reasonable choice if you want stable identity or future persistence. Still, for a broker, the current model looks underdeveloped for production:

- no high-availability pair or cluster pattern
- default anonymous access is permissive
- TLS is optional and not clearly integrated into the full stack
- no network policy or ingress exposure model is shown in the templates reviewed

This is fine for local/staging, but it is not yet a robust production broker design.

### mqtt2kairosdb

This component is one of the most important scaling levers in the system because it sits directly on the ingest/write path.

Concerns:

- there is no explicit retry/backoff/queue durability policy in the chart
- worker sizing is static and environment-driven rather than load-driven
- no probe or startup gating is visible in the reviewed template
- config is injected through a ConfigMap, which is acceptable, but the operational contract needs more documentation

This component should eventually get strong telemetry, backpressure handling, and clear scaling guidance.

### ExaMon Server

`examon-server` is currently the weakest part of the chart from a production-hardening perspective:

- no visible readiness/liveness/startup probes in the reviewed template
- no secure secret wiring for Cassandra credentials
- configuration is injected through plain-text ConfigMap values
- no session/cache backend strategy is documented beyond `simple`

For a service that handles API access and scheduler integration, that is not enough for production.

### Grafana

The Grafana integration is structurally good, but there are still a few problems:

- `adminPassword` is handled too directly
- plugin list is extensive and may increase supply-chain and upgrade risk
- the chart does not clearly show persistence, ingress, and alerting as an integrated operational package across environments

Grafana should be treated as a secure, stateful control plane component, not just a UI.

## Performance And Scalability Assessment

### Good

- Stateless services can scale independently
- Cassandra is separated into a proper HA primitive
- The architecture allows service-level tuning
- Helm values create a path for environment-specific sizing

### Limits

- Kafka-like buffering is not present, so burst absorption is limited
- Mosquitto remains a single logical broker in the baseline config
- KairosDB throughput still depends heavily on Cassandra performance
- The default resource requests are modest and may underprovision real ingest loads

### Practical Scaling Verdict

This design is suitable for:

- development
- demo
- small-to-medium telemetry workloads
- controlled HPC environments with predictable topic partitioning

It is not yet suitable for:

- high-burst multi-tenant telemetry at large scale
- hard multi-AZ resilience without more scheduling and disruption controls
- strict enterprise production environments without additional security and observability layers

## Technical Debt Priorities

1. Replace `latest` tags with versioned or digest-pinned images.
2. Move secrets out of values files and Helm release metadata.
3. Add security contexts and hardening defaults to every workload.
4. Add PodDisruptionBudgets, topology spread constraints, and explicit anti-affinity.
5. Add ServiceMonitor, alert rules, and log/metric guidance.
6. Define scale-out and failure-recovery behavior for the ingest path.
7. Clarify the broker strategy if the platform is expected to grow.
8. Validate upgrades, rollbacks, and persistence recovery in CI.

## Documentation Gaps

The docs are already much better than the old state, but a few things should be added or tightened:

- a values schema table with required vs optional settings
- an explicit security model section
- secret management guidance for production
- a supported version matrix for Kubernetes, K3d, Helm, K8ssandra, Cassandra, KairosDB, and Grafana
- operational runbooks for backup, restore, upgrade, and failure recovery
- a realistic “known limitations” section

## Overall Verdict

The v0.5.0 Kubernetes migration is a strong foundation and clearly the right architectural direction. The repository now has a real Helm-based deployment model instead of a single-machine container bundle.

From a 2026 Kubernetes operations perspective, though, this is still an early-stage platform release. It is functional, but it needs another hardening pass before it can be considered production-grade in a conservative enterprise environment.

## Recommended Next Step

If you want, the next highest-value follow-up is a remediation plan that turns this review into a concrete backlog, prioritized by production risk and implementation effort.
