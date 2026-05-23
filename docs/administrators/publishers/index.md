# Publishers

!!! warning "Status: Spec — section under development"
    Implementation tasks are listed at the bottom.

> The Publishers sub-section is for sysadmins installing collectors on individual nodes: master nodes, compute nodes, BMC hosts. It covers the generic SDK v3 install pattern (pip, systemd, MQTT) and a thin landing page per available publisher that links to the publisher's component repository.

## In this section

- **Overview** — what publishers exist, what each one collects, and where each one belongs.
- **Install a publisher** — the generic SDK v3 install pattern.
- **Catalog** — one page per shipped publisher (Prometheus, IPMI, NVML, PMU, Slurm, GPU, MQTT bridge).

---

## Derived tasks

- [ ] Write `administrators/publishers/overview.md` listing every shipped publisher with its purpose and target host type.
- [ ] Write `administrators/publishers/install-a-publisher.md` covering the generic pip + systemd + MQTT install pattern used by SDK v3 publishers.
- [ ] Write one catalog page per publisher under `administrators/publishers/catalog/`, each linking to the publisher's component repository.
