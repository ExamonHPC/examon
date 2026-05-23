# Administrators

!!! warning "Status: Spec — section under development"
    Implementation tasks are listed at the bottom. The Deploy, Publishers, and Operations sub-sections below already carry the v0.5.0 content; this landing page is the missing piece.

> The Administrators guide is for anyone making ExaMon run somewhere: DevOps engineers deploying core on a Kubernetes cluster, sysadmins installing publishers on individual nodes, fleet operators deploying across an inventory with Ansible. It covers deployment, publisher installation, and day-to-day operations.

## In this section

- **Deploy** — install ExaMon core on Kubernetes (Helm), Docker Compose, or across a cluster from an inventory.
- **Publishers** — install collectors on individual nodes via SDK v3 (pip, systemd, Ansible).
- **Operations** — configure, troubleshoot, propagate changes, back up.

---

## Derived tasks

- [ ] Rewrite this landing page as a "pick your scale" decision tree pointing readers at the right sub-section based on whether they are deploying to a single host, a cluster, or a fleet.
