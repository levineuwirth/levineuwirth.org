---
title: "Ozymandias: A Static Site Framework"
date: 2026-04-12
abstract: >
  Ozymandias is the static site framework underlying this website, now extracted and released under the MIT license. It
  is a full-featured Hakyll and Pandoc setup for long-form writing: sidenotes, epistemic profiles, backlinks,
  wikilinks, a swipeable score reader, a semantic search pipeline, and more — configurable from a single YAML file
  and deployable with a single make command.
tags: [meta, projects, releases]
status: "Working model"
confidence: 80
importance: 2
evidence: 3
scope: average
novelty: moderate
practicality: high
history:
  - date: "2026-04-12"

---

<figure class="poem-excerpt">
<blockquote>
<p>My name is Ozymandias, King of Kings;<br>
Look on my Works, ye Mighty, and despair!<br>
Nothing beside remains. Round the decay<br>
Of that colossal Wreck, boundless and bare<br>
The lone and level sands stretch far away.</p>
</blockquote>
<figcaption><a href="/poetry/ozymandias.html">Ozymandias</a> — Percy Bysshe Shelley</figcaption>
</figure>

The name is a joke. Every framework is a monument that its author believes will outlast the work produced in it. The name is also a warning: the writing you put in a framework might actually outlast the framework itself, which is why the framework should be small, coherent, and legible — not a cathedral built to impress.

The core of this website has been extracted and released as [Ozymandias](https://git.levineuwirth.org/neuwirth/ozymandias), a static site framework under the MIT license. It is the full pipeline: the Haskell build system, the Pandoc filter stack, all templates, all stylesheets, all client-side JavaScript — minus my personal content. If you want a website that works like this one and want to understand exactly how it works, Ozymandias is where to start.

This page describes what Ozymandias is, how it diverged from this site during extraction, and how to use it.

---

## What It Is

Ozymandias is a static site generator for long-form writing. It is built on two mature Haskell tools: [Hakyll](https://jaspervdj.be/hakyll/) for build orchestration and [Pandoc](https://pandoc.org/) for document processing. The framework handles routing, templating, and pagination through Hakyll, and applies a custom sequence of Pandoc [AST]{.smallcaps} transforms during compilation. The output is a directory of plain [HTML]{.smallcaps} files that can be served by any web server.

The short version of what comes with it:

- **Sidenotes** — Pandoc footnotes render as margin notes on wide screens; on narrow screens they collapse to a numbered footnotes section at the bottom.
- **Epistemic profiles** — essays can declare confidence, evidence quality, importance, scope, novelty, and practicality; these appear as a structured footer before the reader commits to the full text.
- **Backlinks** — every page accumulates a list of other pages that link to it, with surrounding paragraph context, via a two-pass compilation strategy.
- **Wikilinks** — `[[Page Title]]` and `[[Page Title|display text]]` syntax resolved at build time.
- **Citations** — Pandoc citeproc with Chicago Notes; footnote-style in-text markers with a bibliography section and a separate "further reading" block.
- **Score reader** — a swipeable [SVG]{.smallcaps} viewer for music compositions with dark-mode-compatible notation.
- **Typography** — dropcaps, automatic smallcaps detection for abbreviations, Latin abbreviation tooltips, old-style figures via the `onum` OpenType feature.
- **Mathematics** — [KaTeX]{.smallcaps} rendering at build time; no math rendering in the browser.
- **Full-text search** — Pagefind, client-side, no external service.
- **Semantic search** — an optional embedding pipeline using `sentence-transformers` and [FAISS]{.smallcaps} for a "similar pages" section and semantic query matching.
- **Hierarchical tags** — `research/mathematics` expands to both `research` and `research/mathematics`; tag pages are generated and paginated automatically.
- **Library portal** — a configurable taxonomy page that groups all content by tag hierarchy.
- **Dark mode, reading mode, settings** — client-side, persisted in `localStorage`.
- **GPG signing** — optional per-page detached signatures, with pubkey linked from the footer.
- **Atom feeds** — site-wide and per-section (music gets its own feed by default).

The prerequisite list is short: [GHC]{.smallcaps} 9.6+, cabal-install, and Pagefind. Image conversion and the embedding pipeline are both optional and add their own dependencies (`cwebp` and Python with `uv`, respectively).

---

## How It Diverged From This Site

When I extracted Ozymandias, the primary engineering work was disentangling site-specific configuration from the framework machinery. In levineuwirth.org, several values — the site [URL]{.smallcaps}, the author name, the navigation structure, the feed title — were compiled directly into the Haskell source. That is fine for a personal site and irritating for a reusable framework. The extraction introduced a `Config.hs` module and a `site.yaml` file that together hold all identity and navigation configuration. The rest of the build system reads from these at startup and never hardcodes a domain or author name.

The result is that you can fork the repository, edit one file, and have a working site with a completely different identity. The Haskell source does not need to be touched unless you want to extend or modify the framework itself.

Beyond configuration, the content in `content/` was replaced with a small set of demo pages that exercise the filter pipeline without constituting a personal corpus. The `data/bibliography.bib` file was emptied and replaced with a placeholder. Everything in `static/` — the fonts, stylesheets, scripts, and link icons — shipped intact. No features were removed during the extraction. Ozymandias has the full pipeline.

### What Remains Shared

The two repositories share the same filter modules, the same templates (minus identity strings), and the same static assets. Changes to the filter pipeline in one are intended to be ported to the other. The practical result is that this site is an Ozymandias instance — it runs on the same engine, only with the configuration file pointing at `levineuwirth.org` rather than `example.com`. This page is compiled by the same code that compiles an Ozymandias site built from the framework.

### What Diverges Intentionally

Several features of this site are too specific to my personal corpus to include in the framework defaults. The similarity embedding index — which requires running a neural model over all page content — is present in Ozymandias as an optional pipeline but ships with an empty index. The music catalog, the commonplace book, and the statistics page are included in the framework because they are useful to authors in general, but they contain no data by default. The semantic search [ONNX]{.smallcaps} model weights are downloaded by a separate `make download-model` target rather than committed to the repository.

---

## The Filter Pipeline

The filters are the heart of the framework. Pandoc compiles Markdown to an abstract syntax tree, and the filters walk and transform that tree before Pandoc serializes it to [HTML]{.smallcaps}. They are applied in a fixed sequence; the order matters.

**Source-level preprocessors** run before Pandoc sees the file. They transform raw Markdown strings:

- **Wikilinks** — converts `[[Page Name]]` and `[[Page Name|display text]]` to standard Markdown links using slugification: lowercase, spaces to hyphens, punctuation stripped. The destination path follows the same routing rules as the content item it targets.
- **EmbedPdf** — converts `{{pdf:/path/to/file.pdf}}` syntax (optionally with a page anchor) to an iframe pointed at the vendored PDF.js viewer, preserving the original path in a `data-pdf-src` attribute for the popup thumbnail system.
- **Transclusion** — converts `{{essay-slug}}` or `{{essay-slug#section}}` to placeholder divs that the client-side `transclude.js` script resolves at page load. This allows shared content to be authored once and embedded anywhere without duplicating the source.

**[AST]{.smallcaps}-level filters** run after parsing. They are pure functions over the Pandoc [AST]{.smallcaps}:

- **Images** — wraps each image in a `<picture>` element with a [WebP]{.smallcaps} source if a `.webp` companion file exists alongside the original. Adds `loading="lazy"` to images below the fold and marks them for the lightbox system.
- **Sidenotes** — transforms Pandoc's footnote syntax (`[^1]: note text`) into inline `<span class="sidenote">` elements with alphabetic labels (a, b, c, … z, aa, ab, …). A `<section class="footnotes">` fallback is preserved at document end for narrow screens where margin placement is impractical.
- **Typography** — matches exact Pandoc `Str` tokens against a table of Latin abbreviations and wraps them in `<abbr title="…">` elements. The table covers *e.g.*, *i.e.*, *cf.*, *viz.*, *NB*, *et al.*, and the rest of the common scholarly shorthand.
- **Links** — classifies external links (any `http`/`https` [URL]{.smallcaps} not on the site's own domain) and adds `class="link-external"`, `target="_blank"`, `rel="noopener noreferrer"`, and a `data-link-icon` attribute that the [CSS]{.smallcaps} uses to render a per-domain icon. A separate pass rewrites root-relative [PDF]{.smallcaps} links to the viewer [URL]{.smallcaps}. Domain classification is by exact hostname match, not substring, so lookalike domains are correctly identified as external.
- **Smallcaps** — detects runs of three or more uppercase letters and wraps them in `<abbr class="smallcaps">`. Trailing punctuation is stripped before matching so `HTML,` and `API.` are caught correctly. Short all-caps tokens (`OK`, `I`) and mixed-case tokens (`JavaScript`) are not converted.
- **Dropcaps** — the filter itself is an identity transform; the real work is done by the [CSS]{.smallcaps} `.dropcap` class applied via fenced div syntax (`::: dropcap`). The filter's presence in the pipeline documents the intent.
- **Math** — another near-identity transform; inline and display math is passed through as-is for [KaTeX]{.smallcaps} to process at render time.
- **Code** — prepends `language-` to code block class names so Prism.js can pick up the language for syntax highlighting without each author needing to write `language-haskell` instead of just `haskell`.
- **Score** (music-specific) — reads [SVG]{.smallcaps} score fragment files from disk and inlines them into the document, replacing `#000000` and `black` fills and strokes with `currentColor` so notation renders correctly in both light and dark mode.
- **Viz** (visualization-specific) — executes Python scripts referenced in fenced code blocks and captures stdout. A Matplotlib script produces an [SVG]{.smallcaps} that is inlined directly; a Vega-Lite script produces a [JSON]{.smallcaps} spec that is embedded for Vega-Embed to render client-side.

The IO-performing filters (Score, Viz, Images) run before the pure ones. This ordering ensures that downstream filters see a stable [AST]{.smallcaps} without pending file reads.

---

## Epistemic Profiles

The epistemic profile is a structured block that appears in the footer of any essay or post whose frontmatter includes a `status` field. It is the most distinctive feature of the framework philosophically, and the one most worth understanding before deploying it.

The fields:

- **Status** — a controlled vocabulary: *Draft*, *Working model*, *Durable*, *Refined*, *Superseded*, *Deprecated*. The distinction between *Working model* and *Durable* matters: the former is a position I currently hold but would not stake much on; the latter is something I expect to hold up under scrutiny.
- **Confidence** — an integer from 0 to 100 representing credence in the central thesis. When a `confidence-history` list is present in the frontmatter, the framework derives a trend arrow (↑ ↓ →) from the last two entries automatically.
- **Importance** — a 1–5 dot scale for how much the work matters.
- **Evidence** — a 1–5 dot scale for how well-evidenced the claims are. An essay with high importance and low evidence is a speculative position and should be read accordingly.
- **Trust score** — derived automatically as (confidence × 0.6) + (rescaled evidence × 0.4). It is a narrow answer to "how much should you trust the central claim?" and deliberately does not incorporate importance, scope, novelty, or practicality, which are separate axes intentionally not blended into a composite.
- **Scope, Novelty, Practicality** — orientation fields, not ratings. *Scope* ranges from *personal* to *civilizational*; *novelty* from *conventional* to *innovative*; *practicality* from *abstract* to *exceptional*. They appear in the footer alongside the numeric fields.
- **Stability** — auto-computed from `git log --follow` at every build. The heuristic: a very new or barely-touched document is *volatile*; an actively-revised document is *revising*; older documents with more commits settle into *fairly stable*, *stable*, or *established*. This requires no manual maintenance.

The version history block, just above the epistemic footer, uses a three-tier fallback: authored `history:` notes in the frontmatter, then the raw git log, then the `date:` field as a creation record.

The point is not precision — a 72% confidence rating is not false exactness. It is an attempt to make explicit what most writing leaves implicit: where the author actually stands, and whether that position is stable or still shifting.

---

## Backlinks

Backlinks require a two-pass architecture, because a page cannot know which pages will link to it until all pages have been compiled.

Pass one compiles every content item in a special "links" version that extracts all internal links together with the surrounding paragraph [HTML]{.smallcaps}. Pass two inverts this map — grouping sources by their targets — and produces `data/backlinks.json`. The final compilation pass loads this file as a dependency and injects the backlinks section into each page's template context.

The practical consequence for authors is that internal links automatically generate backlink sections with source titles and context snippets, without any manual cross-referencing. The `[[Wikilinks]]` syntax makes it natural to link between pages; the backlinks system makes those connections visible to readers moving in either direction.

---

## Semantic Search and Similar Links

Both features are optional and require Python with `uv`:

```sh
uv sync            # install dependencies from pyproject.toml
make download-model  # fetch ONNX weights for client-side search
```

**Full-text search** uses Pagefind, which indexes the compiled [HTML]{.smallcaps} and produces a static search index that runs entirely in the browser. No external service is involved.

**Semantic search** runs a `sentence-transformers` model (`all-MiniLM-L6-v2`, 384 dimensions) over extracted page text, builds a [FAISS]{.smallcaps} similarity index, and stores page-level neighbors in `data/similar-links.json`. At render time, this file is loaded as a Hakyll dependency and the top similar pages are injected into each essay's template context as a "Related" section. The same model can be run client-side in the browser via [ONNX]{.smallcaps} Runtime Web for semantic query matching — the weights are served from the same origin, which means no external [API]{.smallcaps} calls.^[This is the design decision I care most about. Bolting semantic search onto a static site usually means sending queries to a third-party service. Serving the model weights from the same origin means the feature works without any network request beyond what is needed to load the page.]

---

## Content Types

Ozymandias supports six content types, each with its own template and routing convention:

| Type | Path | Route | Template |
|:-----|:-----|:------|:---------|
| Essay | `content/essays/*.md` | `/essays/{slug}.html` | `essay.html` |
| Blog post | `content/blog/*.md` | `/blog/YYYY-MM-DD-{slug}.html` | `blog-post.html` |
| Poetry | `content/poetry/*.md` | `/poetry/{slug}.html` | `reading.html` |
| Fiction | `content/fiction/*.md` | `/fiction/{slug}.html` | `reading.html` |
| Composition | `content/music/{slug}/index.md` | `/music/{slug}/index.html` | `composition.html` |
| Page | `content/*.md` | `/{slug}.html` | `page.html` |

Essays and blog posts support the full feature set: [TOC]{.smallcaps}, epistemic profiles, backlinks, similar links, citations, version history. Poetry and fiction use a `reading` [CSS]{.smallcaps} class that adjusts line spacing and disables indentation, making stanza structure visible. Music compositions get a separate score-reader view at `/music/{slug}/score/` — a minimal interface with swipe navigation through [SVG]{.smallcaps} score pages.

Several pages are generated automatically without source files: `/essays/index.html`, `/blog/index.html` (paginated, 20 per page), `/new.html` (all content sorted by creation date), `/library.html` (portal taxonomy), tag index pages at `/{tag}/index.html`, author pages at `/authors/{slug}/index.html`, and `/feed.xml`.

Drafts live in `content/drafts/essays/` and are only visible when the `SITE_ENV=dev` environment variable is set. Production builds exclude them entirely — they do not appear in feeds, tag pages, backlinks, or the library.

---

## Configuration

All site identity and navigation lives in `site.yaml`. The full schema:

```yaml
site-name:        "My Site"
site-url:         "https://example.com"
site-description: "A personal site built with Ozymandias"
site-language:    "en"

author-name:  "Your Name"
author-email: "you@example.com"

feed-title:       "My Site"
feed-description: "Essays, notes, and creative work"

license:    "CC BY-SA 4.0"
source-url: ""              # optional link to git repository

gpg-fingerprint: ""         # leave empty to omit sig links
gpg-pubkey-url:  "/gpg/pubkey.asc"

nav:
  - { href: "/",             label: "Home"    }
  - { href: "/library.html", label: "Library" }
  - { href: "/new.html",     label: "New"     }
  - { href: "/search.html",  label: "Search"  }

portals:
  - { slug: "writing", name: "Writing" }
  - { slug: "code",    name: "Code"    }
  - { slug: "notes",   name: "Notes"   }
```

Portals are the library taxonomy. Each portal collects all content whose tags include the portal's slug or any tag with that slug as a prefix. Content tagged `writing/essays` and `writing/fiction` both appear under the `writing` portal.

---

## Getting Started

```sh
git clone https://git.levineuwirth.org/neuwirth/ozymandias my-site
cd my-site
$EDITOR site.yaml    # set site-name, site-url, author-name, author-email
make dev             # build with drafts visible; serve on :8000
```

`make dev` builds with `SITE_ENV=dev` (so drafts are included) and starts a local server. `make build` produces the production output in `_site/`. `make watch` adds incremental rebuilds on file changes.

For deployment, the included `make deploy` target runs `make clean && make build`, optionally signs each page with [GPG]{.smallcaps}, rsyncs `_site/` to a [VPS]{.smallcaps} configured via `.env`, and pushes to the git remote. Set `VPS_USER`, `VPS_HOST`, and `VPS_PATH` in `.env` to configure the destination.^[The `make deploy` target always begins with `make clean` to avoid stale build artifacts. Incremental Hakyll rebuilds are safe for development but can produce subtly incorrect output — particularly for pages whose template context depends on the full backlink graph — if the dependency graph is not fully consistent. The clean ensures the graph is always recomputed from scratch for production.]

---

## Writing Content

An essay with the full feature set looks like this:

```yaml
---
title: "On the Virtues of Careful Writing"
date: 2026-04-12
abstract: >
  A brief description that appears on index pages and in the epistemic header.
tags: [writing, research/rhetoric]
authors: ["Your Name", "Collaborator | https://example.com"]
affiliation: "Institution | https://institution.edu"

status: "Working model"
confidence: 65
importance: 4
evidence: 3
scope: average
novelty: moderate
practicality: high
confidence-history: [50, 65]

history:
  - date: "2026-04-12"
    note: Initial draft

bibliography: data/bibliography.bib
further-reading: [key1, key2]
---

::: dropcap
Opening paragraph here. Sidenotes use the standard Pandoc footnote syntax.^[Like this.]
:::

## First Section

Wikilinks to other pages: [[About This Site]]. External links work normally.
Citations use Pandoc's citeproc syntax: [@author2024].
```

The `authors` field defaults to the `author-name` in `site.yaml` when absent. The `affiliation` field takes a `Name | URL` format. The `history:` block overrides git-derived version history when the git log alone would not convey what changed.

---

## License

The framework code — everything in `build/`, `templates/`, `static/`, `tools/`, and the configuration files — is [MIT]{.smallcaps} licensed. The demo content under `content/` is public domain. Your content is yours; add whatever license you choose.

The [MIT]{.smallcaps} license was chosen deliberately: it imposes no obligations, carries no viral clauses, and makes no claims on the writing produced with it. Frameworks should not take a stake in the work they compile.

---

## The Relationship Between Ozymandias and This Site

This site is Ozymandias with my configuration and my content. Changes flow in both directions, with the understanding that the framework is the more conservative of the two repositories: features that turn out to be site-specific stay in levineuwirth.org; features that generalize get ported to Ozymandias. The filter pipeline and the template system are intended to stay in sync.

The divergence is, in a sense, the point. A personal website is a *position*, as I elaborate upon in the [[Colophon]]. Ozymandias is the mechanism; the position is what you put in it.
