# Analyze

!!! warning "Status: Spec — section under development"
    Implementation tasks are listed at the bottom.

> The Analyze sub-section is for data scientists and analysts running queries against ExaMon. ExaMon exposes its data through a Trino SQL surface; any BI tool, notebook, or scripting language that speaks Trino can connect. This sub-section documents the SQL surface and the per-tool connection details.

The first concrete page available here is the existing ExamonQL notebook demo, reachable from the section navigation.

## In this section

- **Schema reference** — the tables, columns, and tags exposed by the connector.
- **Example queries** — common query patterns annotated.
- **Connect from Jupyter / Superset / Power BI / DBeaver / Python** — one page per tool.
- **Cookbooks** — recipe-style analyses for energy, jobs, and cluster utilization.

---

## Derived tasks

- [ ] Write `users/analyze/schema-reference.md` documenting the Trino schema exposed by the KairosDB connector.
- [ ] Write `users/analyze/example-queries.md` covering the canonical query patterns.
- [ ] Write one `users/analyze/connect-*.md` page per supported tool (Jupyter, Superset, Power BI, DBeaver, Python).
- [ ] Write the `users/analyze/cookbooks/` set: energy, jobs, cluster utilization.
