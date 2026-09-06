# Writing Guide

Reference for creating content on levineuwirth.org. Covers file placement, all
frontmatter fields, and every authoring feature available in the Markdown source.

---

## File placement

| Type | Location | Output URL |
|------|----------|------------|
| Essay | `content/essays/my-essay.md` | `/essays/my-essay.html` |
| Essay (with co-located assets) | `content/essays/my-essay/index.md` | `/essays/my-essay/index.html` |
| Blog post | `content/blog/my-post.md` | `/blog/my-post.html` |
| Poetry | `content/poetry/my-poem.md` | `/poetry/my-poem.html` |
| Poetry collection | `content/poetry/collection-name/*.md` | `/poetry/collection-name/*.html` |
| Fiction | `content/fiction/my-story.md` | `/fiction/my-story.html` |
| Composition | `content/music/{slug}/index.md` | `/music/{slug}/` |
| Standalone page | `content/my-page.md` | `/my-page.html` |
| Standalone page (with co-located assets; needs a dedicated rule) | `content/me/index.md` | `/me.html` |
| Draft essay | `content/drafts/essays/my-draft.md` | `/drafts/essays/my-draft.html` (dev only) |

File names become URL slugs. Use lowercase, hyphen-separated words.

Flat `content/<page>.md` is the generic standalone form — any flat file dropped
into `content/` builds automatically. Directory-form standalone pages
(`content/my-page/index.md`) are **not** picked up by the generic rule; each one
requires its own dedicated `match` rule in `build/Site.hs`. The two existing
ones are `content/me/index.md` and `content/memento-mori/index.md` — follow
their pattern when adding another.

The directory form exists for pages that embed co-located SVG score fragments
or other relative assets: score fragment paths are resolved relative to the
source file's directory, and a flat `content/my-page.md` would resolve them
from `content/`, which is wrong.

---

## Drafts

In-progress essays go under `content/drafts/essays/`. Both flat files
(`content/drafts/essays/my-draft.md`) and directory-based essays
(`content/drafts/essays/my-draft/index.md`) are supported.

Drafts are **included** in `make watch` and `make dev` (which set `SITE_ENV=dev`)
and **excluded** from every production build (`make build`, `make deploy`).
They are also invisible to tags, author pages, backlinks, stats, and feeds.

To preview a draft:

```bash
make watch    # Hakyll live-reload with drafts visible
make dev      # clean build + Python HTTP server with drafts visible
```

When the draft is ready, move it into `content/essays/`.

---

## Frontmatter

Every file begins with a YAML block fenced by `---`. Keys are read by Hakyll
and passed to templates; unknown keys are silently ignored and can be used as
custom template variables.

### Essays

```yaml
---
title: "The Title of the Essay"
subtitle: "An Optional Secondary Line"  # optional; rendered below the title in the frontmatter header
date: 2026-03-15          # required; used for ordering, feed, and display
abstract: >               # optional; shown in the metadata block and link previews
  A one-paragraph description of the piece.
summary: |                # optional; rendered in a "Summary" box near the abstract
  A structured summary. **Markdown allowed** — bold, lists, multiple paragraphs.
tags:                     # optional; see Tags section
  - nonfiction
  - nonfiction/philosophy
keywords: [lattices, simd]  # optional; links to /bibliography/<keyword>/ pages (list or comma-separated string)
authors:                  # optional; overrides the default "Levi Neuwirth" link
  - "Levi Neuwirth | /me.html"
  - "Collaborator | https://their.site"
  - "Plain Name"          # URL optional; omit for plain-text credit
affiliation:              # optional; shown below author in metadata block
  - "Brown University | https://cs.brown.edu"
  - "Some Research Lab"   # URL optional; scalar string also accepted
further-reading:          # optional; see Citations section
  - someKey
  - anotherKey
bibliography: data/custom.bib   # optional; overrides data/bibliography.bib
csl: data/custom.csl            # optional; overrides Chicago Notes Bibliography
no-collapse: true               # optional; disables collapsible h2/h3 sections
repository: https://git.levineuwirth.org/levi/repo  # optional; "Repository" link in metadata
preprint: /papers/my-essay.pdf  # optional; "Preprint" link in metadata (typeset PDF version)
js: scripts/my-widget.js        # optional; per-page JS file (see Page scripts)
# js: [scripts/a.js, scripts/b.js]  # or a list

# Epistemic profile — all optional; the entire section is hidden unless `status` is set
status: "Working model"   # Draft | Working model | Durable | Refined | Superseded | Deprecated
confidence: 72            # 0–100 integer (%); also accepts the sentinel `proved` / `proven` for formal mathematical results
importance: 3             # 1–5 integer (rendered as filled/empty dots ●●●○○)
evidence: 2               # 1–5 integer (same)
scope: average            # personal | local | average | broad | civilizational
novelty: moderate         # conventional | moderate | idiosyncratic | innovative
practicality: moderate    # abstract | low | moderate | high | exceptional
confidence-history:       # list of integers; trend arrow derived from last two entries
  - 55
  - 63
  - 72
peer-status: under-review # optional; unreviewed (default) | under-review | peer-reviewed | published | retracted
result-shape: mixed       # optional; positive | negative | mixed | comparative | descriptive

# Version history — optional; falls back to git log, then to date frontmatter.
# Entries may be listed in any order — they are sorted by date at build time.
history:
  - date: 2026-03-14      # ISO date; unquoted is fine (the Haskell YAML parser keeps it as a string)
    note: Expanded typography section; added citations
  - date: 2026-03-01
    note: Initial draft

# Revision log — optional; drives the date shown on cards and list pages
# (see Revision dates section)
revised:
  - date: "2026-04-10"
    note: "expanded the section on typography"
  - date: "2026-03-20"    # note is optional per-entry
---
```

### Blog posts

Same fields as essays, with one exception: `tags:` doesn't apply. Blog posts
are excluded from `/<tag>/` pages — tags are a topical index for substantial
essays, and no blog post is ever "about" a topic the way an essay is. Setting
`tags:` on a blog post is a no-op, so don't. `keywords:` is unaffected and
still drives the separate embedding-based "Related" links.

`date` formats the `<time>` element in the post header and blog index. Posts
appear in `/feed.xml`.

### Poetry

Same fields as essays. Poetry uses a narrow-measure codex reading mode
(`reading.html`): 52ch measure, 1.85 line-height, stanza spacing, no drop cap.
`poetryCompiler` enables `Ext_hard_line_breaks` — each source newline becomes
a `<br>`, so verse lines render without trailing-space tricks.

**Poetry collections** — poems can be grouped into subdirectories:

```
content/poetry/shakespeare-sonnets/
├── index.md            ← collection landing page (uses pageCtx)
├── sonnet-1.md         ← individual poem
├── sonnet-2.md
└── …
```

Collection index pages (`content/poetry/*/index.md`) compile as standalone
pages. Poems inside collections (`content/poetry/*/*.md`, excluding
`index.md`) compile with `poetryCompiler` just like flat poems.

**External / non-original poems** — use `poet:` instead of `authors:` to credit
an external author without generating a (broken) author index page:

```yaml
---
title: Sonnet 60
date: 1609-05-20
poet: William Shakespeare
tags: [poetry]
---
```

`poet:` is a plain string. The metadata block shows "by William Shakespeare" as
plain text. Do not use `authors:` for poems you did not write; that would create
an `/authors/william-shakespeare/` index page linking to the poem.

### Fiction

Same fields as essays. Fiction uses the same codex reading mode as poetry:
62ch measure, chapter drop caps + smallcaps lead-in on `h2 + p`.

### Standalone pages

Only `title` is required. Pages use `pageCtx`: no TOC, no bibliography, no
reading-time, no epistemic footer.

```yaml
---
title: About
---
```

Add `js:` for any page-specific interactivity (see Page scripts).

### Music compositions

Compositions live in their own directory. See the Music section for full details.

```yaml
---
title: "Symphony No. 1"
date: 2026-01-15
abstract: >
  A four-movement work for large orchestra.
tags: [music]
instrumentation: "orchestra (2222/4231/timp+2perc/str)"
duration: "ca. 32'"
premiere: "2026-05-20"
commissioned-by: "—"              # optional
recording: audio/full-recording.mp3  # optional; full-piece audio player
pdf: scores/symphony.pdf          # optional; download link
category: orchestral              # orchestral | chamber | solo | vocal | choral | electronic
featured: true                    # optional; appears in Featured section of /music/
score-dir: scores/                # every *.svg in here becomes a page, in order
movements:                        # optional
  - name: "I. Allegro"
    page: 1                       # 1-indexed page in the reader (see below)
    duration: "10'"
    time: "0:00"                  # optional; offset into `recording`
    audio: audio/movement-1.mp3   # optional; per-movement player
  - name: "II. Adagio"
    page: 18
    duration: "12'"
    time: "10:24"
---
```

**Declaring the score.** Use either `score-dir` or `score-pages`; the reader
page at `/music/<slug>/score/` is generated only when one of them is present.

`score-dir` globs every `*.svg` in the named directory and orders them
numerically, so `page-2.svg` precedes `page-10.svg` whether or not you
zero-padded. This is the usual choice — hand-listing forty orchestral pages
is a chore, and a hand-list that drifts out of sync with the directory fails
silently.

```yaml
score-pages:                      # explicit override; wins over score-dir
  - scores/frontispiece.svg
  - scores/page-01.svg
```

Reach for `score-pages` only when the reading order is not the filename
order.

**Movement `page:` is the reader's index, not the printed folio.** The two
diverge as soon as a score has front matter. A `page:` past the end of the
score is reported at build time; one that is merely wrong is not, so check
the movement buttons after a re-export.

**Movement `time:`** accepts `H:MM:SS`, `M:SS`, or a plain number of
seconds, and is normalised to seconds at build time. It is parsed and
carried through the template context, but nothing renders it yet — it is
there so the schema is settled before compositions exist. A malformed
`time:` warns and is dropped; the movement itself is kept.

---

## Tags

Tags use slash-separated hierarchy. `nonfiction/philosophy` expands to both
`nonfiction` and `nonfiction/philosophy`, so the piece appears on both index
pages.

```yaml
tags:
  - nonfiction/philosophy
  - research/epistemology
```

The top-level segment maps to a **portal** in the nav:

| Portal | URL |
|--------|-----|
| AI | `/ai/` |
| Fiction | `/fiction/` |
| Miscellany | `/miscellany/` |
| Music | `/music/` |
| Nonfiction | `/nonfiction/` |
| Photography | `/photography/` |
| Poetry | `/poetry/` |
| Research | `/research/` |
| Tech | `/tech/` |

Tag index pages are paginated at 20 items and auto-generated on build.

### Tag-meta sidecars

Each portal and selected tag can carry a one-line tooltip rendered next to
the section heading. These live under `content/tag-meta/{portal}.md` and
use a tooltip-only schema — no `title:` and no body:

```yaml
---
tooltip: "formal and less formal inquiry"
---
```

The page title comes from the tag itself; the body is unused. Files in
`content/tag-meta/` are sidecars consumed by the Tags context, not
authored pages — they're the one place in `content/` where the standard
"every file has a `title:`" rule does not apply.

---

## Authors

The `authors` key controls the author line in the metadata block. When omitted,
it defaults to "Levi Neuwirth" linking to `/authors/levi-neuwirth/`.

Author pages are generated at `/authors/{slug}/` and list all attributed content.

Pipe syntax: `"Name | URL"` — name is the link text, URL is the `href`.
The URL part is optional.

---

## Citations

The citation pipeline uses Chicago Notes Bibliography style
(`data/chicago-notes.csl`). The bibliography lives at
`data/bibliography.bib` (BibLaTeX format) by default; override per-page with
`bibliography` and `csl`.

### Inline citations

```markdown
This claim is contested.[@smith2020]

Multiple sources agree.[@jones2019; @brown2021]
```

Inline citations render as numbered superscripts `[1]`, `[2]`, etc. The
bibliography section appears automatically in the page footer. `popups.js`
adds hover previews showing the full reference.

### Further reading

Keys under `further-reading` appear in a separate **Further Reading** section
in the page footer. These are not cited inline.

```yaml
further-reading:
  - keyNotCitedInline
  - anotherBackgroundSource
```

A key can appear both inline and in `further-reading`; it is numbered in the
bibliography and not duplicated.

---

## Footnotes → sidenotes

Standard Markdown footnotes are converted to sidenotes at build time.

```markdown
This sentence has a note.[^1]

[^1]: The note content, which may contain **bold**, *italic*, links, etc.
```

On wide viewports the note floats into the right margin. On narrow viewports
it falls back to a standard footnote. Sidenotes are numbered automatically.

Avoid block-level elements (headings, lists) inside footnotes.

---

## Wikilinks

Internal links can be written as wikilinks. The title is slugified to produce
the URL.

```markdown
[[Page Title]]             → links to /page-title
[[Page Title|Link text]]   → links to /page-title with custom display text
```

Slug rules: lowercase, spaces → hyphens, non-alphanumeric characters removed.
`[[My Essay (2024)]]` → `/my-essay-2024`.

Use standard Markdown link syntax `[text](/path)` for any link whose path is
not derivable from the page title.

---

## Transclusion

Embed the rendered content of another page (or a section of it) inline using
`{{slug}}` directives. The directive must be on its own line.

```markdown
{{my-essay}}                 → embeds the full body of /my-essay.html
{{essays/deep-dive}}         → embeds /essays/deep-dive.html
{{my-essay#introduction}}    → embeds only the "introduction" section
```

At build time, `Filters.Transclusion` rewrites these to `<div class="transclude"
data-src="..." [data-section="..."]></div>` placeholders. At runtime,
`transclude.js` fetches the target page and injects the content.

Transclusions inside code blocks or inline prose are not replaced — only
block-level directives (sole content of a line) are processed.

---

## PDF Embeds

Embed a hosted PDF in a full PDF.js viewer (page navigation, zoom, text
selection) using the `{{pdf:...}}` directive on its own line:

```markdown
{{pdf:/papers/smith2023.pdf}}
{{pdf:/papers/smith2023.pdf#5}}        ← open at page 5 (bare integer)
{{pdf:/papers/smith2023.pdf#page=5}}   ← explicit form, same result
```

The directive produces an iframe pointing at the vendored PDF.js viewer at
`/pdfjs/web/viewer.html?file=...`.  The PDF must be served from the same
origin (i.e. it must be a file you host).

**Storing papers.** Drop PDFs in `static/papers/`; Hakyll's static rule copies
everything under `static/` to `_site/` unchanged.  Reference them as
`/papers/filename.pdf`.

**Graph-theory preprints.** Their editable LaTeX sources and demonstration code
live in `~/Repos/research/meyniel`. Build and explicitly export reviewed assets
from that checkout using its `docs/PUBLISHING.md`; `static/papers/` holds the
released copies. Reconcile the corresponding website articles when a theorem
or interpretation changes. See `paper/README.md` for the migration pointer.

**One-time vendor setup.** PDF.js is not included in the repo.  Install it once:

```bash
npm install pdfjs-dist
mkdir -p static/pdfjs
cp -r node_modules/pdfjs-dist/web   static/pdfjs/
cp -r node_modules/pdfjs-dist/build static/pdfjs/
rm -rf node_modules package-lock.json
```

Then commit `static/pdfjs/` (it is static and changes only when you want to
upgrade PDF.js).  Hakyll's existing `static/**` rule copies it through without
any new build rules.

**Optional: disable the "Open file" button** in the viewer.  Edit
`static/pdfjs/web/viewer.html` and set `AppOptions.set('disableOpenFile', true)`
in the `webViewerLoad` callback, or add a thin CSS rule to `viewer.css`:

```css
#openFile, #secondaryOpenFile { display: none !important; }
```

---

## Math

Pandoc parses LaTeX math and wraps it in `class="math inline"` / `class="math display"`
spans. KaTeX CSS is loaded conditionally on pages that contain math — this styles the
pre-rendered output. Client-side KaTeX JS rendering is not yet loaded; complex math
will appear as LaTeX source. Build-time server-side rendering is planned but not yet
implemented. Simple math currently renders through Pandoc's built-in KaTeX span output.

`math: true` is auto-set for all essays and blog posts. Standalone pages that use
math must set it explicitly in frontmatter to load the KaTeX CSS.

| Syntax | Usage |
|--------|-------|
| `$...$` | Inline math |
| `$$...$$` on its own line | Display math |

```markdown
The quadratic formula is $x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}$.

$$
\int_0^\infty e^{-x^2}\,dx = \frac{\sqrt{\pi}}{2}
$$
```

---

## Links

Internal links: standard Markdown or wikilinks. Internal links get a
`link-internal` class and an internal icon.

External links are classified automatically at build time:

- Opened in a new tab (`target="_blank" rel="noopener noreferrer"`)
- Decorated with a domain icon via CSS `mask-image`

Links to sibling subdomains (e.g. `git.levineuwirth.org`) are classified as
external — only `levineuwirth.org` and `www.levineuwirth.org` are treated as
the content host.

| Domain | Icon |
|--------|------|
| `wikipedia.org` | Wikipedia |
| `arxiv.org` | arXiv |
| `doi.org` | DOI |
| `worldcat.org` | WorldCat |
| `orcid.org` | ORCID |
| `archive.org` | Internet Archive |
| `github.com` | GitHub |
| `git.levineuwirth.org` | Forgejo |
| `tensorflow.org` | TensorFlow |
| `anthropic.com` | Anthropic |
| `openai.com` | OpenAI |
| `twitter.com` / `x.com` | Twitter/X |
| `reddit.com` | Reddit |
| `youtube.com` / `youtu.be` | YouTube |
| `tiktok.com` | TikTok |
| `substack.com` | Substack |
| `news.ycombinator.com` | Hacker News |
| `nytimes.com` | New York Times |
| `nasa.gov` | NASA |
| `apple.com` | Apple |
| Everything else | Generic external arrow |

### Link preview popups

Hovering over a link shows a context-aware popup. All automatic — no
markup needed.

| Target | Popup content |
|--------|--------------|
| Internal page | Title, abstract, authors, tags, word count, reading time |
| Citation marker (`[1]`) | Full bibliography reference (multi-cite groups supported) |
| Wikipedia | Lead section extract via MediaWiki API |
| arXiv | Title, authors, abstract via Atom API |
| DOI / CrossRef | Title, authors, journal, year, abstract |
| GitHub | Repo name, description, language, stars |
| Forgejo (`git.levineuwirth.org`) | Repo name, description, language, stars |
| Open Library | Book title, description |
| bioRxiv / medRxiv | Title, authors, abstract |
| YouTube | Video title, channel name (oEmbed) |
| Internet Archive | Title, creator, description |
| PubMed | Title, authors, journal, year |
| PDF link | First-page thumbnail (from build-time `pdftoppm`) |
| Epistemic jump link (`#epistemic`) | Clone of the full epistemic profile |
| Epistemic term label (`data-ep-term`) | Term definition from colophon |
| PGP signature link | ASCII armor of the `.sig` file |

**Custom annotations** — author-defined previews for any URL. Add entries
to `data/annotations.json`:

```json
{
  "https://example.com/article": {
    "title": "Article Title",
    "annotation": "A brief note about why this link is relevant."
  }
}
```

Annotation entries take priority over all other popup providers.

Popups are disabled on touch-primary devices and inside nav/TOC/footer
elements.

---

## Code

Fenced code blocks with a language identifier get syntax highlighting (JetBrains
Mono). The language annotation also enables the selection popup's docs-search
feature (maps to MDN, Hoogle, docs.python.org, etc.).

````markdown
```haskell
fib :: Int -> Int
fib 0 = 0
fib 1 = 1
fib n = fib (n-1) + fib (n-2)
```
````

Inline code: `` `like this` ``

---

## Images

Place images in `static/images/`. All images automatically get `loading="lazy"`.

```markdown
![Alt text](/images/my-image.png)
```

For a captioned figure, add a title string. Pandoc wraps it in `<figure>`/`<figcaption>`:

```markdown
![Alt text](/images/my-image.png "Caption shown below.")
```

**Lightbox:** standalone images automatically get `data-lightbox="true"`.
Clicking opens a fullscreen overlay; close with ×, click outside, or Escape.
Images inside hyperlinks get lazy loading only — no lightbox.

---

## Section collapsing

By default, every `h2` and `h3` heading in an essay gets a collapse toggle.
State persists in `localStorage`.

To disable on a specific page:

```yaml
no-collapse: true
```

---

## Exhibits and annotations

Pandoc fenced divs (`:::`) create structured callout blocks.

### Exhibits

Always-visible numbered blocks with overlay zoom on click. Use for equations or
proofs you want to reference structurally. Listed under their parent heading
in the TOC.

```markdown
::: {.exhibit .exhibit--equation}
$$E = mc^2$$
:::

::: {.exhibit .exhibit--proof}
*Proof.* Suppose for contradiction that …  ∎
:::
```

### Annotation callouts

Editorial sidebars — context, caveats, tangential detail.

```markdown
::: {.annotation .annotation--static}
Always visible. Use for important caveats or context.
:::

::: {.annotation .annotation--collapsible}
Collapsed by default. Use for tangential detail.
:::
```

---

## Score fragments

Inline SVG music notation, integrated with the gallery/exhibit system. Clicking
a fragment opens the shared overlay alongside any math exhibits on the page.

```markdown
::: {.score-fragment score-name="Main Theme, mm. 1–8" score-caption="The opening gesture."}
![](scores/main-theme.svg)
:::
```

Both attributes are optional, but `score-name` is strongly recommended — it
drives the overlay label and the TOC badge.

The image path is resolved **relative to the source file's directory**:

| Source file | SVG path | Reference as |
|---|---|---|
| `content/essays/my-essay.md` | `content/essays/scores/theme.svg` | `scores/theme.svg` |
| `content/music/symphony/index.md` | `content/music/symphony/scores/motif.svg` | `scores/motif.svg` |
| `content/me/index.md` | `content/me/scores/vln.svg` | `scores/vln.svg` |

SVGs are inlined at build time. Black `fill`/`stroke` values are replaced with
`currentColor` so notation renders correctly in dark mode.

---

## Excerpts

Pull-quotes from other works, displayed as indented blockquotes with a small
attribution line and a stretched invisible link covering the whole figure.

### Poem excerpt

Use when quoting verse that has a dedicated page on the site. The entire figure
becomes a click target pointing to the poem; the attribution line remains an
independent link.

```html
<figure class="poem-excerpt">
<blockquote>

Like as the waves make towards the pebbled shore,
So do our minutes hasten to their end;

</blockquote>
<figcaption><a href="/poetry/sonnet-60.html">William Shakespeare — <em>Sonnet 60</em></a></figcaption>
</figure>
```

The blockquote renders with the default dashed left border and italic muted text.
No box or background. The `figcaption` is small-caps and left-aligned.

### Prose excerpt

For quoting prose or for excerpts that do not have a page on the site:

```html
<figure class="prose-excerpt">
<blockquote>

The passage you want to quote goes here.

</blockquote>
<figcaption><a href="https://example.com">Author — <em>Source Title</em></a></figcaption>
</figure>
```

`prose-excerpt` is full-width (`width: auto; max-width: 100%`) rather than
`fit-content`-wide like `poem-excerpt`. Both reset the image-figure box styles
(no background, no border, no padding).

### Commonplace book

The `/commonplace` page is a YAML-driven quotation collection. Add entries to
`data/commonplace.yaml`; the page rebuilds automatically.

```yaml
- text: |-
    Like as the waves make towards the pebbled shore,
    So do our minutes hasten to their end;
    Each changing place with that which goes before,
    In sequent toil all forwards do contend.
  attribution: William Shakespeare
  source: Sonnet 60
  source-url: /poetry/sonnet-60.html
  tags: [time, mortality]
  commentary: >
    Optional note. Shown below the quote in muted italic. Omit entirely if
    not needed — most entries will not have one.
  date-added: 2026-03-17
```

| Field | Required | Notes |
|-------|----------|-------|
| `text` | yes | Use `|-` block scalar; newlines become `<br>` |
| `attribution` | yes | Author name, plain text |
| `source` | no | Title of the source work |
| `source-url` | no | Makes `source` a link |
| `tags` | no | Separate from content tags; used for "by theme" grouping |
| `commentary` | no | Your own remark on the passage |
| `date-added` | no | ISO date; used for chronological sort |

The page has a **by theme / chronological** toggle (state persists in
`localStorage`). Untagged entries appear under "miscellany" in the themed view.

---

## Music

### Catalog index (`/music/`)

`content/music/index.md` is the catalog homepage. Write prose about your
compositional work in the body; provide an `abstract` for the intro line.
The composition listing is auto-generated from all `content/music/*/index.md`
files — no manual list needed.

```yaml
---
title: Music
abstract: Compositions spanning orchestral, chamber, and solo writing.
tags: [music]
---

[Your prose here — influences, preoccupations, approach to the craft.]
```

### Composition pages

Each composition lives in its own subdirectory:

```
content/music/symphony-no-1/
├── index.md            ← frontmatter + program notes prose
├── scores/
│   ├── page-01.svg     ← one file per score page
│   └── symphony.pdf    ← optional PDF download
└── audio/
    ├── full.mp3        ← optional full-piece recording
    └── movement-1.mp3  ← optional per-movement recordings
```

**Turn LilyPond's point-and-click off before exporting.** It is on by
default, and it wraps every notehead in an anchor holding the *absolute path
of your source file*:

```
<a xlink:href="textedit:///home/you/scores/symphony.ly:106:75:76">
```

That is several hundred anchors per page, and publishing them puts your local
filesystem layout on the public site. Export with `-dpoint-and-click=#f`, or
put `\pointAndClickOff` at the top of the `.ly`:

```bash
lilypond -dbackend=svg -dpoint-and-click=#f -o symphony symphony.ly
```

The reader strips non-web hrefs when it inlines a page, so a score exported
the wrong way is not *served* with them — but the paths are still sitting in
the SVG files in the repository, and anyone fetching one directly reads them.
Fix it at export.

**Exporting pages.** One SVG per page, from any engraver — MuseScore,
LilyPond, and Epiphany are all handled without configuration. The reader
fetches each page and inlines it, then recolours it through CSS: a
presentation attribute such as `fill="#000000"` carries specificity zero, so
the stylesheet wins, and the notation draws in the theme's ink on every
theme. Nothing needs stripping or rewriting before export, and `fill="none"`
(slurs, ties, beams) is preserved.

Page weight is not worth optimising. MuseScore repeats identical glyph
outlines rather than referencing them, which looks alarming — a full letter
page runs ~145 KB — but that redundancy is exactly what compresses: the same
file is 17 KB brotli, and `compress-assets.sh` already emits the sidecars.
Pages load one at a time, with neighbours prefetched.

Two URLs are generated automatically from one source:
- `/music/symphony-no-1/` — prose landing page with metadata, audio players, movements
- `/music/symphony-no-1/score/` — minimal page-turn score reader

The score reader is generated only when `score-dir` or `score-pages` is
present. It fits the page to the window by default; `Fit`/`Width` toggles the
mode and `+`/`−` zoom from there, panning by ordinary scroll. Arrow keys,
`PageUp`/`PageDown`, `Home`/`End` and swipe turn pages; `?p=N` deep-links one.
With scripting off, page 1 still renders at the right size — the build reads
its dimensions and the stylesheet fits it without help.

**Catalog indicators** — the `/music/` catalog auto-derives:
- ◼ (score available): the composition resolves to at least one page
- ♫ (recording available): `recording` key is present, or any movement has `audio`

**Catalog grouping** — `category` controls which section the work appears in.
Valid values: `orchestral`, `chamber`, `solo`, `vocal`, `choral`, `electronic`.
Anything else appears under "Other". Omitting `category` defaults to "other".

**Featured works** — set `featured: true` to also appear in the Featured section
at the top of the catalog.

---

## Page scripts

For pages that need custom JavaScript (interactive widgets, visualisations, etc.),
reference the JS file via the `js:` frontmatter key. The file is injected as a
deferred `<script>` at the bottom of `<body>`.

```yaml
js: scripts/memento-mori.js          # single file
```

or a list:

```yaml
js:
  - scripts/widget-a.js
  - scripts/widget-b.js
```

Paths are **site-root-relative**, not relative to the content file: the template
emits the value verbatim with a leading `/` prepended. Write the path without a
leading slash. `js: scripts/widget.js` loads `/scripts/widget.js` regardless of
where the page lives — a composition at `content/music/symphony/index.md` with
that value does *not* get `/music/symphony/scripts/widget.js`.

The script file must live where the build serves that URL. The `content/**/*.js`
glob rule copies JS files to `_site/` with the `content/` prefix stripped, so
`content/scripts/widget.js` is served at `/scripts/widget.js` — this is the
current convention (the memento-mori page keeps its script at
`content/scripts/memento-mori.js` and references it as
`js: scripts/memento-mori.js`).

---

## Epistemic profile

The epistemic footer section appears when `status` is set. All other fields
are optional and are shown or hidden independently.

| Field | Compact rows | Expanded `<dl>` |
|-------|-------------|------------------|
| *(trust score)* | bordered chip + small-caps "trust" label on the primary row | — |
| `status` | small-caps chip on the primary row, alongside the trust chip | — |
| `confidence` | `· 72% confidence` | — |
| `importance` | `· ●●●○○ importance` | — |
| `evidence` | `· ●●○○○ evidence quality` | — |
| `scope` | `· average scope` (if set) | — |
| `novelty` | `· moderate novelty` (if set) | — |
| `practicality` | `· moderate practicality` (if set) | — |
| `stability` | — | auto-computed from git history |
| `last-reviewed` | — | most recent commit date |
| `confidence-trend` | — | ↑/↓/→ from last two `confidence-history` entries |

The **trust score** is auto-computed as `confidence × 0.6 + ((evidence − 1) / 4) × 0.4`,
clamped 0–100. It is deliberately narrow: it answers "how much should you trust the
central claim?" and nothing else. Importance, scope, novelty, and practicality are
*not* folded in — they are orientation signals shown alongside the chip so a high
trust score on a personal essay cannot be misread as broad significance.

**Stability** is auto-computed from `git log --follow` at every build. The
heuristic: ≤1 commits or age <14 days → *volatile*; ≤5 commits and age <90
days → *revising*; ≤15 commits or age <365 days → *fairly stable*; ≤30
commits or age <730 days → *stable*; otherwise → *established*.

To pin a manual stability label for one build, add the file path to `IGNORE.txt`
(one path per line). The file is cleared automatically by `make build`.

### `peer-status`, `result-shape`, and `confidence: proved`

Three optional extensions to the epistemic vocabulary, introduced
alongside the epistemic figure (`MARKS.md` for the full spec).

**`peer-status`** — the *external* review state, factored out of `status`
(which captures the author's internal position). Values:

| Value | Meaning |
|-------|---------|
| `unreviewed` | Default. No external review has taken place. |
| `under-review` | In submission or peer review. |
| `peer-reviewed` | Reviewed but not yet formally published. |
| `published` | Appeared in a peer-reviewed venue. |
| `retracted` | Formally retracted; renders with a strikethrough. |

A non-`unreviewed` value adds a chip (`under review`, `peer-reviewed`, …)
to the compact epistemic strip and modulates the outer-ring tick *style*
on the epistemic figure.

**`result-shape`** — the shape of the central claim:

| Value | Meaning |
|-------|---------|
| `positive` | Argues for / proves something works. |
| `negative` | Argues against / proves a barrier. |
| `mixed` | Both, e.g. a double-pincer barrier paper. |
| `comparative` | Compares two or more approaches. |
| `descriptive` | Describes without arguing for or against. |

Renders as a small glyph (`+`, `−`, `±`, `∼`, `□`) beside the trust score
on the epistemic figure. Adds nothing to the compact row.

**`confidence: proved`** (or `proven`) — the formal-proof carve-out. A
theorem with a complete proof has confidence ≈ 100 modulo soundness, and
writing `confidence: 95` invites a false-precision reading. The sentinel:

  * Substitutes 100 in the trust-score formula (evidence still varies, so
    a complete proof with thin supporting apparatus does not pin trust to
    100).
  * Renders the compact-row chip as `proved confidence` instead of
    `XX% confidence`.
  * Draws the confidence axis on the epistemic figure full-length, with a
    3×3 px filled square at the vertex (the "proof cap" marker) instead
    of the usual 2 px circle.
  * Suppresses the inline trend arrow. Setting both
    `confidence: proved` and `confidence-history` emits a build warning
    and the history is ignored.

This is the only genre-specific carve-out in the schema. All other
fields read across genres without modification.

### Frontmatter marks (monogram + epistemic figure)

Each piece may carry a hand-authored monogram — a small SVG glyph
abstracted from its central concept — that renders in the left column of
the frontmatter header. Drop a `mark.svg` next to the source file; the
build picks it up automatically. No frontmatter key is required to opt
in.

| Source path | Mark path |
|-------------|-----------|
| `content/essays/foo.md` | `content/essays/foo.mark.svg` |
| `content/essays/foo/index.md` | `content/essays/foo/mark.svg` |
| `content/blog/post.md` | `content/blog/post.mark.svg` |
| `content/{slug}.md` | `content/{slug}.mark.svg` |

The right column of the header carries the **epistemic figure** — a
build-time SVG generated deterministically from the existing epistemic
fields. It renders only when `status:` is set, matching the existing
visibility rule for the epistemic block. See `MARKS.md` for the full
specification (visual contract, accessibility, geometry).

A reference monogram template lives at
`static/templates/mark-template.svg`. Authors hand-rolling a monogram
should copy and adapt it; the file documents the §2.2 visual contract
(currentColor strokes, no embedded text, ≤ 8 KiB, etc.).

---

## Version history

The version history footer section uses a three-tier fallback:

1. **`history:` frontmatter** — your authored notes. Entries may be listed in
   any order — they are sorted by date at build time.
2. **Git log** — if no `history:` key, dates are extracted from `git log --follow`.
   Entries have no message (date only).
3. **`date:` frontmatter** — if git has no commits for the file, falls back to
   the `date` field as a single "Created" entry.

`make build` auto-commits `content/` before running the Hakyll build, so the
git log stays current without manual commits.

Write authored notes when the git log would be too noisy or insufficiently
descriptive:

```yaml
history:
  - date: 2026-03-14
    note: Expanded section 3; incorporated feedback from peer review
  - date: 2026-03-01
    note: Initial draft
```

---

## Revision dates

The `revised:` key records substantive revisions and drives the date shown on
item cards and list pages. Two accepted shapes:

```yaml
revised: "2026-04-10"     # scalar shorthand — one revision, no note

revised:                  # canonical list of objects
  - date: "2026-04-10"
    note: "expanded the section on Shestov"
  - date: "2025-12-03"    # note is optional per-entry
```

Dates are ISO `YYYY-MM-DD` strings. Entries may be listed in any order — they
are sorted by date at build time, most recent first. Entries missing `date:`
or carrying non-string values are silently dropped; the build never fails on
a malformed `revised:` block.

Effects:

- **`$date-display$` / `$date-iso$`** — cards and list pages show the
  most-recent revision date instead of the creation date.
- **Sort order** — revision-aware lists (`/new.html`, tag pages, the library)
  sort by the display date, so a freshly revised piece moves to the top.
- **`$date-original$`** — when the latest revision date differs from the
  creation date, the card adds a "revised from …" annotation showing the
  original date.
- **`$revision-note$`** — the note on the most-recent entry renders as an
  italicized line under the abstract on the card.

`revised:` is independent of `history:` (the version-history footer above);
add a matching `history:` entry if the revision should appear there too.

---

## Typography features

Applied automatically at build time; no markup needed.

| Feature | What it does |
|---------|-------------|
| Smart quotes | `"foo"` / `'bar'` → curly quotes |
| Em dashes | `---` → — |
| En dashes | `--` → – |
| Smallcaps | `[TEXT]{.smallcaps}` → `font-variant-caps: small-caps` |
| Drop cap | First letter of the first `<p>` gets a decorative large initial |
| Explicit drop cap | `::: dropcap` fenced div applies drop cap to any paragraph |
| Ligatures | Spectral `liga`, `dlig` OT features active for body text |
| Old-style figures | Spectral `onum` active; use `.lining-nums` class to override |

To mark a phrase as small caps explicitly:

```markdown
The [CPU]{.smallcaps} handles this.
```

### Explicit drop cap

Wrap any paragraph in a `::: dropcap` fenced div to get a drop cap regardless
of its position in the document. The first line is automatically rendered in
small caps via `::first-line { font-variant-caps: small-caps }`.

```markdown
::: dropcap
A personal website is not a publication. It is a position — something you
inhabit, argue from, and occasionally revise in public.
:::
```

Write in normal mixed case. The CSS applies `font-variant-caps: small-caps` to
the entire first rendered line, converting lowercase letters to small-cap glyphs.
Use `[WORD]{.smallcaps}` spans to force specific words into small-caps anywhere
in the paragraph.

A paragraph that immediately follows a `::: dropcap` block will be indented
correctly (`text-indent: 1.5em`), matching the paragraph-after-paragraph rule.

---

## Text selection popup

Selecting any text (≥ 2 characters) shows a context-aware toolbar after 450 ms.

| Context | Buttons |
|---------|---------|
| Prose (multi-word) | Annotate · BibTeX · Copy · DuckDuckGo · Here · \[Translate\] · Wikipedia |
| Prose (single word) | Annotate · BibTeX · Copy · Define · DuckDuckGo · Here · \[Translate\] · Wikipedia |
| Math | Copy · nLab · OEIS · Wolfram |
| Code (known language) | Copy · \<MDN / Hoogle / Docs…\> |
| Code (unknown) | Copy |

**BibTeX** generates a `@online{...}` BibLaTeX entry with the selected text in
`note={\enquote{...}}` and copies it to the clipboard. **Define** opens English
Wiktionary. **Here** opens the Pagefind search page pre-filled with the selection.
**Translate** appears only for selections inside a non-English `[lang]` subtree
(see below) and opens DeepL with the source lang pre-set and the target as English.

---

## Non-English passages

Wrap non-English text in a Pandoc fenced div with a `lang` attribute. The
primary subtag is a BCP-47 code (`es`, `fr`, `la`, `de`, `zh`, …):

```markdown
::: {lang="es"}
> *El universo (que otros llaman la Biblioteca) se compone de un número
>  indefinido, y tal vez infinito, de galerías hexagonales…*
:::
```

Pandoc emits `<div lang="es">…</div>`. For inline passages inside an
otherwise-English paragraph, use the span form:

```markdown
He opened with a cheerful [bonjour, mon ami]{lang="fr"} and kept going.
```

which produces `<span lang="fr">…</span>`.

The page root is `<html lang="en">`, so any subtree with a different primary
lang subtag activates the **Translate** button in the selection popup —
clicking it opens DeepL with the detected source language and English as the
target. Languages DeepL does not support (e.g. Latin) fall back to DeepL's
auto-detect. Matching the page root (`lang="en"`) does nothing — there is no
point translating English into English.

---

## Visualizations

Two types of figure are supported, authored as fenced divs. The Python script
runs at build time via the Pandoc filter; no client-side computation is needed
for static figures.

### Static figures (matplotlib)

```markdown
::: {.figure script="figures/my-plot.py" caption="Caption text."}
:::
```

The script path is resolved relative to the source file's directory. It should
import `viz_theme` from `tools/` and write SVG to stdout:

```python
import sys
sys.path.insert(0, 'tools')
from viz_theme import apply_monochrome, save_svg, load_csv
import matplotlib.pyplot as plt

apply_monochrome()
rows = load_csv("speedups.csv")          # figures/data/speedups.csv
fig, ax = plt.subplots()
ax.plot([r["n"] for r in rows], [r["t"] for r in rows])
save_svg(
    fig,
    alt="Line chart of runtime against input size.",
    desc="Runtime grows linearly to about n=1000 and then flattens.",
)
```

`load_csv` resolves against the script's own directory, so a figure keeps
working if the essay is renamed or moved. `alt` is the accessible name a
screen reader announces in place of the chart, and `desc` the longer
description; omitting `alt` warns during the build, and `make audit-viz`
reports it.

`apply_monochrome()` sets transparent backgrounds and pure black elements so
the figure inherits the page's dark/light mode via CSS `currentColor`.

Only *pure* black is rewritten. A colour chosen deliberately — a white label
on a dark heatmap cell, a mid-grey bar fill — is passed through untouched, so
pick greys that stay legible against both `#faf8f4` and `#121212`. Text that
is left at the default colour carries no fill at all in matplotlib's SVG, and
picks up `currentColor` from `viz.css` by inheritance.

Multi-series charts should use `LINESTYLE_CYCLE` instead of color:

```python
from viz_theme import apply_monochrome, save_svg, LINESTYLE_CYCLE
apply_monochrome()
fig, ax = plt.subplots()
for i, style in enumerate(LINESTYLE_CYCLE[:3]):
    ax.plot(x, data[i], **style, label=f"Series {i+1}")
save_svg(fig)
```

### Interactive figures (Altair / Vega-Lite)

```markdown
::: {.visualization script="figures/my-chart.py" caption="Caption text."}
:::
```

The script outputs Vega-Lite JSON to stdout:

```python
import sys, json
import altair as alt
import pandas as pd

df = pd.read_csv('figures/data.csv')
chart = alt.Chart(df).mark_line().encode(x='year:O', y='value:Q')
print(json.dumps(chart.to_dict()))
```

The site's monochrome Vega config is applied automatically, overriding the
spec's own `config`. Dark mode re-renders automatically.

Add `viz: true` to the frontmatter of any page using `.visualization` divs —
this loads the Vega CDN scripts:

```yaml

viz: true
```

Pages with only static `.figure` divs do not need `viz: true`.

### Captions

`caption=` is parsed as Markdown on both figure types, with the same reader
the body uses — code spans, emphasis, links, smart quotes and `$…$` math all
work:

```markdown
::: {.figure script="figures/speedup.py" caption="Speedup of `ref` $\to$ `avx2`. Log $y$-axis."}
:::
```

Keep it to inline content: a caption is rendered into a `<figcaption>`, so
block constructs (lists, headings) have nowhere sensible to go.

### Rebuilds

An essay depends on everything under its `figures/` directory, plus
`tools/viz_theme.py`. Editing a script, a CSV, or the shared theme rebuilds
the pages that draw from it — you do not need to touch `index.md` or run
`make clean`.

This is declared in `build/Site.hs` (`figureDep`) because Hakyll cannot see
it otherwise: figure scripts are executed by a Pandoc filter, so nothing in
the dependency graph connects a page to the data its charts read. Without
it, editing a CSV republished the *data file* while leaving the chart drawn
from it untouched.

### Figure width and small screens

Matplotlib bakes label text at a fixed size in figure units, so a wide figure
scaled down to a narrow column takes its text down with it. Each figure is
therefore wrapped in a scroll container carrying its natural width: below that
width it pans sideways instead of shrinking, keeping a 10pt label at about
10px. Nothing to do as an author — but two things follow.

`figsize` is a real budget. The body column is 800px, so a figure wider than
roughly `figsize=(8, …)` will show a horizontal scrollbar even on a desktop.
That is the honest outcome for a genuinely oversized figure, but prefer
stacking panels vertically, or splitting into two figures, over a very wide
row of facets.

Escape backslashes in mathtext labels, or use a raw string:

```python
ax.set_ylabel(r"Speedup ($\times$)")     # fine
ax.set_ylabel("Speedup ($\\times$)")     # also fine
ax.set_ylabel("Speedup ($\times$)")      # WRONG: \t is a tab, renders "imes"
```

`make test` checks for this — it reads the text runs matplotlib records in the
SVG and fails on any control character in one.

### Figure numbering and cross-references

Opt in per page:

```yaml
figure-numbering: true
```

Every captioned figure on that page — `.figure` and `.visualization` divs
and captioned Markdown images alike — is then numbered in document order and
its caption prefixed with `Figure N.` Uncaptioned figures are skipped rather
than given an invisible number.

Give a figure an anchor and reference it with an **empty link**:

```markdown
::: {.figure #fig-decomp script="figures/fig_decomp.py" caption="…"}
:::

![Caption text.](figures/plot.png){#fig-dist}

The decomposition in [](#fig-decomp) shows … and [](#fig-dist) confirms it.
```

The empty link fills in as `Figure 1`, `Figure 2`, … A link that already has
text is left alone, so `[the decomposition](#fig-decomp)` still reads as
written. A reference to a missing anchor renders `Figure ?` rather than
vanishing, so typos are visible.

Anchors must start with `fig-` or `fig:`. Without an explicit id a figure is
still numbered and gets a generated `fig-N` anchor.

Note the syntax is `[](#anchor)`, not pandoc-crossref's `[@fig:x]` — citeproc
runs first on this site and would try to resolve `@fig:x` against the
bibliography.

**Opting in is deliberate.** `beyond-comorbidity-indices` and
`specification-dilemma` number by hand today; turning this on for them would
double-number every figure. Convert a page when you are ready to strip its
manual labels, not before. Tables are out of scope either way.

### Checking figures

Two complementary commands, because the failures come in two kinds.

`make test` checks the **pipeline contract** — that the black the scripts
emit is in a form `processColors` can match, that repeated runs are
byte-identical, that ids do not collide across figures on a page, that
captions are Markdown and figures carry `role="img"` and a description.

`make audit-viz` checks **what a reader would see**. It renders each figure
and reports marks with no variation in them (a heatmap drawn from constant
data is a solid rectangle), text that cannot be read against what sits behind
it in either theme, labels too small at the body column, and missing `alt`.
Every visualization bug found in this repo so far was invisible in the source
and obvious in the render, which is what this is for. It exits 0 by default;
`make audit-viz STRICT=1` fails instead.

`make viz-provenance` checksums the CSVs behind each figure into
`figures/data/PROVENANCE.json` so a reader who downloads the data can tell it
is what the chart was drawn from. Fill in each file's `source` field with the
run that produced it — the tool seeds a TODO and never overwrites what you
write. `make viz-provenance-check` verifies the checksums still match.

---

## Page footer sections

Essays get a structured footer. Sections with no data are hidden.

| Section | Shown when |
|---------|-----------|
| Version history | Always (falls back through three-tier system) |
| Epistemic | `status` frontmatter key is present |
| Bibliography | At least one inline citation |
| Further Reading | `further-reading` key is present |
| Backlinks | Other pages link to this page |
| Related | Similar pages exist (embedding-based; computed at build time) |

Backlinks are auto-generated at build time. No markup needed — any internal
link from another page creates an entry here, showing the source title and the
surrounding paragraph as context.

Related pages are computed by `tools/embed.py` using semantic embeddings
(`nomic-embed-text-v1.5` + FAISS). Runs automatically during `make build`
when the Python environment is set up (`uv sync`). No markup needed.

---

## Auto-generated pages

These pages are built automatically and require no content files or markup:

| Page | URL | Description |
|------|-----|-------------|
| Essay index | `/essays/` | All essays, newest first |
| Blog index | `/blog/` | Paginated blog posts |
| New | `/new.html` | All content types sorted by date, newest first |
| Library | `/library.html` | All content grouped by portal (AI, Fiction, Music, etc.) |
| Build telemetry | `/build/` | Corpus stats, word-length distribution, tag frequencies, link analysis, epistemic coverage, output metrics, repository overview, build timing, and a 52-week writing activity heatmap |
| Tag indexes | `/<tag>/` | Paginated pages per tag, auto-generated |
| Author indexes | `/authors/<slug>/` | All content attributed to an author |
| Random manifest | `/random-pages.json` | JSON array of page URLs for the random-page button |
| Atom feeds | `/feed.xml`, `/music/feed.xml` | All content feed + music-only feed |
| Search | `/search.html` | Pagefind full-text search + client-side semantic search (`all-MiniLM-L6-v2` ONNX model) |

---

## Build

```bash
make build    # auto-commit content/, convert images, PDF thumbs, compile,
              #   run pagefind + embeddings, clear IGNORE.txt
make sign     # GPG detach-sign every _site/**/*.html → .html.sig
make deploy   # clean + build + sign + rsync to VPS + git push
make watch    # Hakyll live-reload dev server (SITE_ENV=dev — includes drafts)
make dev      # clean build + Python HTTP server (SITE_ENV=dev — includes drafts)
make clean    # wipe _site/ and _cache/
```

`make watch` and `make dev` set `SITE_ENV=dev`, which includes drafts under
`content/drafts/essays/` in the build. All other targets exclude drafts.

`make watch` hot-reloads changes to Markdown, CSS, JS, and templates.
**After any change to a `.hs` file, always run `make clean && make build`** —
Hakyll's cache is keyed to source file mtimes and will serve stale output after
Haskell-side changes.

`make deploy` requires `VPS_USER`, `VPS_HOST`, and `VPS_PATH` to be set in
`.env` (see `.env.example`). It runs `clean → build → sign`, sends a desktop
notification, rsyncs `_site/` to the VPS, and pushes to `origin main`.

**GPG signing:** `make sign` and `make deploy` require the signing subkey
passphrase to be cached. Run once per boot (or per 24h expiry):

```bash
./tools/preset-signing-passphrase.sh
```

**Image conversion:** `make build` automatically runs `tools/convert-images.sh`
to generate WebP companions for JPEG/PNG images (requires `cwebp`). It also
generates first-page PDF thumbnails via `pdftoppm` (requires `poppler`).
Both are skipped silently when the tools are not installed.

**Python environment:** the embedding pipeline requires `uv sync` to be run
once. After that, `make build` invokes `uv run python tools/embed.py`
automatically. If `.venv` is absent, the step is skipped with a warning and
the build continues normally.
