# Contributing

!!! info "Status: Beta — the open-source contribution flow is still maturing"
    The flow described below is the one currently used for [ExamonHPC/examon](https://github.com/ExamonHPC/examon) and is the model the other ExaMon-org repositories are converging on. The E4-Computer-Engineering repositories (SDK v3 publishers and base library) currently use a similar but slightly different release cadence; the differences are noted where relevant.

> ExaMon is a federation of independent repositories. A contribution typically targets one repository; the contribution flow below applies per-repository. The core repository ([`ExamonHPC/examon`](https://github.com/ExamonHPC/examon)) is the most active one and the best entry point for first-time contributors.

## Which repository to target

| The change is to ... | Repository |
|---|---|
| Helm chart, mqtt2kairosdb bridge, examon-server, Docker images, k3d setup scripts | [ExamonHPC/examon](https://github.com/ExamonHPC/examon) |
| SDK v3 base library (`examon-base-plugin`) | [E4-Computer-Engineering/examon-base-plugin](https://github.com/E4-Computer-Engineering/examon-base-plugin) |
| A specific publisher (`prometheus_pub`, `ipmi_pub`, `nvml_pub`, `pmu_pub`, `slurm_pub`) | One repository each under [E4-Computer-Engineering](https://github.com/E4-Computer-Engineering) |
| Trino-KairosDB connector | [ExamonHPC/trino-kairosdb-connector](https://github.com/ExamonHPC/trino-kairosdb-connector) |
| Documentation (this site) | [ExamonHPC/examon](https://github.com/ExamonHPC/examon) — the `docs/` directory and `mkdocs.yml` |

The full inventory is in [Reference → Component catalog](../reference/component-catalog.md).

## File an issue

Before opening a pull request, an issue is the right starting point for any non-trivial change: it lets maintainers acknowledge the direction before the implementation cost is spent. Trivial changes (typo fixes, single-line bug fixes, documentation clarifications) can skip straight to a pull request.

Open issues at the repository's GitHub issue tracker:

- [ExamonHPC/examon issues](https://github.com/ExamonHPC/examon/issues)
- [ExamonHPC/trino-kairosdb-connector issues](https://github.com/ExamonHPC/trino-kairosdb-connector/issues)
- Each E4 publisher repository has its own tracker.

### Bug reports

A useful bug report includes:

- A clear, descriptive title.
- The exact steps that reproduce the problem.
- The observed behavior, what was expected instead, and the difference between them.
- Versions: ExaMon component versions (Helm chart, base library, publisher), upstream versions (Kubernetes, Cassandra, KairosDB, Trino as relevant), and host OS / Python version when relevant.
- Logs, kubectl output, screenshots — whatever shortens the maintainer's reproduction time.

### Enhancement proposals

For non-trivial enhancements:

- A clear explanation of the proposed feature.
- The motivation: what use case is currently awkward or impossible.
- Alternative solutions that were considered and why they were rejected.
- If applicable, prior art: how related projects approach the same problem.

## Branch and release model

The core repository uses a `release/v0.5.0`-style branch model. The general shape is:

| Branch | Purpose |
|---|---|
| `main` | The current released stable line. Tags on `main` correspond to GitHub Releases. |
| `release/v<minor>` | The active development line for the next release (currently `release/v0.5.0`). All feature work and most bug fixes target this branch. |
| `feature/*`, `fix/*` | Short-lived branches off the relevant `release/*` branch. Merged via pull request. |

A pull request targets the relevant `release/*` branch (not `main`). When the release is cut, `release/v0.5.0` is fast-forward merged to `main` and tagged.

The E4-Computer-Engineering publisher repositories use a simpler model (`main`-based development, GitHub Releases) without the `release/*` branch; the pull-request and commit-message conventions below still apply.

## Pull request process

1. **Fork the target repository** on GitHub.
2. **Clone the fork** and add the upstream as a second remote so feature branches can be kept in sync:
   ```bash
   git clone git@github.com:<your-user>/examon.git
   cd examon
   git remote add upstream git@github.com:ExamonHPC/examon.git
   ```
3. **Branch off the relevant base branch**:
   ```bash
   git fetch upstream
   git checkout -b fix/short-description upstream/release/v0.5.0
   ```
4. **Make the change.** Keep the change focused: one logical concern per pull request. Multi-concern pull requests are commonly asked to be split before review.
5. **Test locally.** For core changes, the local-development bring-up (`./scripts/k8s-local-setup.sh`) followed by the smoke test (`./scripts/k8s-smoke-test.sh`) is the minimum gate. For SDK v3 publisher changes, the publisher's own test suite plus a manual run against a reference Prometheus / IPMI / KairosDB instance.
6. **Document the change.** If the change affects user-facing behavior, configuration, or installation, update the relevant page on this site. Documentation lives at `docs/` in the core repository.
7. **Commit using the convention below.**
8. **Push and open a pull request** against the upstream base branch. Reference the issue number in the description if one exists. Describe the user-visible effect of the change, not just the implementation.
9. **Address review feedback.** Force-pushes to the pull-request branch are acceptable and often preferred for rewriting commits during review; preserve the linear history.
10. **Maintainer merges.** Pull requests are squashed or fast-forwarded on merge depending on the repository's policy and the contribution's shape.

## Commit message convention

The core repository uses a lightweight Conventional Commits style:

```
<type>(<scope>): <subject>

<optional body>

<optional footer>
```

The recognized `type` values:

| Type | Use for |
|---|---|
| `add` | A new feature or capability. |
| `fix` | A bug fix. |
| `change` | A modification of existing behavior that is neither a new feature nor a bug fix (refactor, rename, signature change). |
| `remove` | A deletion or deprecation. |
| `docs` | A documentation-only change. |
| `merge` | A merge commit (rare; the convention is fast-forward where possible). |

The `<scope>` is the affected area: `helm`, `mqtt2kairosdb`, `examon-server`, `docker`, `scripts`, `docs(phase3)`, etc. Subject is in imperative mood, no trailing period.

Example:

```
fix(helm): set Grafana service port to 80, not 3000

The Helm subchart's `authUrl` referenced port 3000, which is the
container port, not the service port. This caused examon-server's
auth check to fail in every environment where the chart shipped
without an explicit port override.

Refs: #42
```

## Coding standards

Per repository, the existing code style is the contract. Cross-repository conventions:

- Python: PEP 8 with the line-length conventions already in place per repository (typically 88 or 100 characters). Black is used in some repositories; running it before committing is safe.
- Helm templates: two-space indent, `{{ }}` with single-space padding inside braces, helper functions extracted into `_helpers.tpl` when reused.
- Shell scripts (`scripts/*.sh`): bash, `set -euo pipefail` at the top, ShellCheck-clean.
- Container Dockerfiles: pin the base image tag (no `:latest`), prefer multi-stage builds for non-trivial images, document non-obvious `JAVA_OPTS` or environment-variable handling inline.

## Tests

Each repository carries its own test conventions. The core repository's day-1 verification is the `scripts/k8s-smoke-test.sh` end-to-end test that brings up the local-development stack and checks the bundled dashboard renders live data. New core features should either pass the smoke test unchanged or extend the smoke test accordingly.

For SDK v3 publishers, unit tests live alongside the publisher source; the conventional path is `pytest` from the repository root.

## Documentation contributions

This site (the ExaMon documentation) is part of the core repository under `docs/`, built with MkDocs Material and deployed via `mike`. To preview a documentation change locally:

```bash
pip install -r docs-requirements.txt
mkdocs serve
```

The site is then reachable at [http://localhost:8000](http://localhost:8000). The build is configured in `mkdocs.yml`; the navigation is the `nav:` block there. Adding a new page is two steps: create the Markdown file under `docs/` and add it to the relevant entry in `mkdocs.yml`.

The site uses an audience-shaped information architecture (Get Started, Administrators, Users, Developers, Concepts, Reference, Community). Documentation contributions should fit the existing audience structure rather than create a parallel tree.

## First-time contributors

Issues labeled `good first issue` or `help wanted` on the [core issue tracker](https://github.com/ExamonHPC/examon/issues) are scoped to be approachable without deep prior knowledge of the codebase. Asking a clarifying question on the issue before starting is welcomed and accelerates the eventual review.

## License

By contributing, the contributor agrees that the contribution is licensed under the same license that covers the target repository. The core repository ([`ExamonHPC/examon`](https://github.com/ExamonHPC/examon)) is licensed under BSD-3-Clause; individual component repositories carry their own licenses, all of which are OSI-approved (BSD-3-Clause, Apache-2.0, or MIT).

## Questions

The clearest channels for questions about the contribution flow itself, rather than a specific issue or pull request, are listed in [Community → Contact](../community/contact.md).

---

## Source

- Core repository: [ExamonHPC/examon](https://github.com/ExamonHPC/examon) (release/v0.5.0).
- Issue tracker: [ExamonHPC/examon/issues](https://github.com/ExamonHPC/examon/issues).
- Component repositories: [Reference → Component catalog](../reference/component-catalog.md).
- Upstream commit-message reference: [Conventional Commits](https://www.conventionalcommits.org/).
