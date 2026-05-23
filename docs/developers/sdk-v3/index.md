# SDK v3

!!! warning "Status: Spec — section under development"
    Implementation tasks are listed at the bottom. A worked example for the legacy `examon_pub` notebook is already reachable from the section navigation as a starting point.

> The SDK v3 sub-section documents the publisher framework used to write a new ExaMon collector. The framework provides workers (extractors, transformers, loaders), a lifecycle, and a YAML configuration model; a typical publisher is a few lines of Python wiring those pieces together.

## In this section

- **Quickstart** — a few lines of Python that produce a working publisher.
- **Concepts** — the ETL model, the worker lifecycle, the configuration model.
- **Workers reference** — every built-in extractor, transformer, and loader.
- **Configuration** — the publisher YAML schema.
- **Examples** — worked walkthroughs of shipped publishers.

---

## Derived tasks

- [ ] Write `developers/sdk-v3/quickstart.md` covering a minimal publisher in a few lines of Python.
- [ ] Write `developers/sdk-v3/concepts.md` documenting the ETL model and worker lifecycle.
- [ ] Write `developers/sdk-v3/workers-reference.md` listing every built-in worker.
- [ ] Write `developers/sdk-v3/configuration.md` documenting the publisher YAML schema.
- [ ] Add additional worked examples under `developers/sdk-v3/examples/`.
