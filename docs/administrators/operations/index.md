# Operations

!!! warning "Status: Spec — section under development"
    Implementation tasks are listed at the bottom. The Configure, Troubleshoot, and Change propagation pages below already carry the v0.5.0 content; this landing page is the missing piece.

> The Operations sub-section covers running ExaMon day to day: configuring the deployment, propagating changes across a fleet, troubleshooting common failures, monitoring ExaMon itself, and backing up data. It assumes the deployment is already up (see the Deploy sub-section) and the publishers are installed (see the Publishers sub-section).

## In this section

- **Configure** — change configuration after install.
- **Troubleshoot** — diagnose common failures.
- **Change propagation** — push configuration changes across a running deployment.
- **Monitor ExaMon** — meta-monitoring of the ExaMon services themselves.
- **Back up and restore** — protect time-series data and configuration.

---

## Derived tasks

- [ ] Rewrite this landing page as an entry point to the operations sub-pages.
- [ ] Write `administrators/operations/monitor-examon.md` documenting the Prometheus metrics ExaMon emits about itself.
- [ ] Write `administrators/operations/back-up-and-restore.md` documenting backup of KairosDB, Cassandra, and Grafana state.
