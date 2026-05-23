---
title: Documentation Conventions
search:
  exclude: true
---

# Documentation Conventions

!!! info "Status: Live (reproduced 2026-05-23)"
    Distilled from the active method `Design_by_Documentation_Method_May_2026` in the architect's vault. This page is intentionally hidden from the published navigation: it is a contributor reference, not reader content.

> This page is for anyone editing or adding documentation to this repository. It records the small set of rules every ExaMon doc page must follow: the four feature-maturity labels, the admonition style, the mandatory page structure, the forbidden phrases, and the reproduction discipline.

## The two kinds of page

Every page in this site is one of two kinds. A reader cannot tell them apart by tone; only by the status label and the optional `Derived tasks` footer.

| Kind | What it describes | Source of truth | Has `Derived tasks` footer |
|---|---|---|---|
| **Consolidate** | A feature, install path, schema, or behaviour that exists today. | The implementation. The page describes reality. | No |
| **Specify** | A feature that does not yet exist, or exists only partially. | The page itself. The page is the contract the implementation conforms to. | Yes |

The prose voice is identical between the two. A Specify page is not a stub or a wishlist; it is a finished user-facing surface written in present-tense declarative voice, exactly like a Consolidate page. The only difference visible to a casual reader is the status admonition and the optional `Derived tasks` footer at the bottom.

## Feature-maturity labels

The status label attaches to the **feature**, not to the page. Every page is "finished" in the sense that it is ready for an external reader to consume; what varies is whether the described feature is built.

| Label | Meaning |
|---|---|
| **Live** | The feature works exactly as documented. The doc was reproduced (steps run, outputs verified) within the last 30 days, or is covered by an automated CI test. |
| **Beta** | The feature works but has documented caveats: known issues, missing edge cases, performance limits, or single-site validation only. Caveats are listed inline. |
| **Spec** | The page is the contract; the feature is not yet built. The `Derived tasks` footer lists the implementation work. |
| **Future** | The page describes intent beyond the current roadmap; not blocking the current release. The `Derived tasks` footer points to the ADR or year. |

## Admonition style

The status label is the first content under the page title, rendered as a MkDocs Material admonition. Use exactly these admonition types so the rendered colour matches the maturity:

```markdown
!!! info "Status: Live (reproduced 2026-05-19)"
    Verified against examon-core v0.5.0 on K3d.

!!! success "Status: Beta — single-site validation"
    Validated on Marconi 100 only. Tracked in #123.

!!! warning "Status: Spec — feature not yet built"
    This page is the contract. Implementation tasks are listed at the bottom.
    See [ADR: Inventory Abstraction](decisions/inventory-abstraction.md) for design rationale.

!!! abstract "Status: Future — beyond the 2026 roadmap"
    Tracked in [2027 planning](community/roadmap-status.md).
```

Other admonitions used across the site:

- `!!! note` — incidental notes, asides.
- `!!! warning "Known issue"` — Beta caveats. Must link to a tracked issue.
- `!!! danger` — destructive operations, data-loss risks.

Do not invent new admonition types. The four status admonitions and the three incidental admonitions above are the full set.

## Mandatory page structure

Every page follows this skeleton. Sections marked optional are omitted on pages where they do not apply.

```markdown
# <Title>

!!! <admonition> "Status: <Live|Beta|Spec|Future> (<reproduced YYYY-MM-DD | not yet implemented | beyond roadmap>)"
    <one-sentence context>

> <One-paragraph purpose: who this page is for and what they will achieve by reading it.>

## <Section 1>

...page body...

---

## Source

- <Authoritative source: link to the component README in its repo, or to the ADR>
- <Secondary sources: related vault notes, design docs, smoke-test scripts>

## Derived tasks

*(Spec / Future pages only — omit on Live / Beta pages.)*

- [ ] Task 1 — must be true for this page to become Live: <concrete, testable statement>
- [ ] Task 2 — ...

Tracked in: <link to GitHub issue, roadmap item, or "to be filed">
```

The `Source` section is **mandatory** on every page. A page with no `Source` section is not merged.

The `Derived tasks` section is **mandatory** on Spec and Future pages and **forbidden** on Live and Beta pages. Each derived task is concrete and testable: not "Implement `examon-scheduler apply`" but "Implement `examon-scheduler apply` such that running it twice on a converged fleet produces exit code 0 and zero changes".

## Forbidden phrases

The following phrases reveal a page as a draft and must be removed:

- "TODO", "WIP", "coming soon", "stay tuned"
- "In a future release", "planned for v0.6"
- "Note: this feature is not yet implemented"
- "We are currently working on..."
- Marketing superlatives: "best-in-class", "seamless", "powerful"

A Spec page conveys unbuiltness via the status admonition and the `Derived tasks` footer **only**. The prose itself stays declarative present tense: not "The `apply` command will deploy publishers", but "The `apply` command deploys publishers".

No em-dashes. Rephrase the sentence instead.

## Voice and tense

- Always present tense, third person where possible. Not "You will now install...", but "The next step installs...". When second person is needed for a procedure, use it sparingly and consistently within a page.
- Declarative, not promissory. "The connector exposes a virtual schema named `kairosdb`." Not "The connector will expose...".
- No first-person plural. "We recommend" becomes "The recommended option is...".

## Code examples

- Real for Consolidate pages, invented but self-consistent for Specify pages. Never half-and-half on a single page.
- All examples are copy-paste runnable. Do not mix untyped placeholders with concrete values inside the same block.
- Outputs are lightly trimmed but never invented. If a block is trimmed, mark the trim with `...` or `# truncated`.
- Use realistic values: `examon-core`, not `<my-app>`; `node-001`, not `host1`.

## Cross-linking

- Internal site links use relative paths: `../users/analyze/connect-jupyter.md`.
- Links to authoritative component READMEs use absolute GitHub URLs with a pinned ref where possible: `https://github.com/ExamonHPC/examon/blob/release/v0.5.0/...`.
- Links to vault material are **only** in `Source` sections, never inline in prose. The published site stands on its own without vault access.

## File naming

- All page files are `kebab-case.md`.
- All section directories are `kebab-case/`.
- The `index.md` of a section is the entry page. No other names are used for section landings.

## Reproduction discipline

A page marked **Live** carries a reproduction date in the status admonition (`reproduced 2026-MM-DD`). The page is reproduced when one of the following is true:

- The steps on the page were run end-to-end and the outputs verified within the last 30 days.
- The steps are covered by an automated CI test that runs on every commit.

A page that cannot be reproduced right now is demoted to **Beta** with the specific blocker as the inline caveat, until it can be reproduced again.

## Information architecture

The published navigation is **audience-shaped**: three macro guides (`administrators/`, `users/`, `developers/`) plus five universal sections (`get-started/`, `concepts/`, `reference/`, `community/`, `blog/`). The persona vocabulary (P0–P9) is the writer's design lens; it never appears in nav, URLs, page titles, or admonition text.

The top-level shape is authoritative for this site. Add pages by extending the existing sections; do not rename or restructure the top level without updating the active method document.

---

## Source

- Active method: `Design_by_Documentation_Method_May_2026.md` (architect vault, sections §4, §5, §10, §11).
- Page templates: same document, §8.1 (Consolidate) and §8.2 (Specify).
- Quality gates: same document, §10.
