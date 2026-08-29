# Frontmatter Marks: Specification

A two-part visual identity for essay and research frontmatter, designed
to extend (not replace) the existing epistemic profile system.

The mark system has two pieces:

  1. **Monogram** — a hand-authored SVG glyph per piece, abstracted from
     the work's central concept. The author's statement of *what* the
     piece is about.
  2. **Epistemic figure** — a build-time SVG generated deterministically
     from existing frontmatter fields. The site's statement of *where
     the piece stands*.

The two are paired in the frontmatter: monogram on the left, title and
abstract in the middle, epistemic figure on the right. Either can be
present alone; both can be absent. When a field that drives the
epistemic figure is missing, the figure is omitted entirely rather
than rendered with empty axes.

This document specifies the authoring interface, the field schema
(extending the existing one in `WRITING.md`), the visual contract,
the build-time rendering pipeline, and the migration plan.

It is written to slot in alongside `WRITING.md` as a sibling reference,
and to live as a section in the colophon once shipped.

---

## 1. Scope and non-goals

### In scope

- A monogram convention (location, dimensions, line-weight, palette)
  that any author or generator can produce SVGs for.
- Two new optional frontmatter fields (`peer-status`, `result-shape`)
  that surface useful information for both essays and formal research,
  with a colophon-glossed interpretation that adapts to genre.
- One narrow exception (`confidence: proved`) that lets formal proofs
  honestly opt out of a numeric credence without forcing false precision.
- A new Pandoc filter (`Filters/Mark.hs`) that emits the epistemic
  figure SVG inline in the essay header at build time.
- Template changes in `templates/essay.html` and `templates/blog-post.html`
  to provide three-column frontmatter slots (monogram | title | figure).
- A `make audit-marks` build target and an addition to `/build/`
  surfacing which essays are missing one or both marks.

### Out of scope

- A separate "research badge" figure type. The single radial figure
  handles both essays and formal research; see §3.4.
- A unified mode-switched figure with axes that change meaning based on
  a `claim-mode` flag. Visual grammar should be unambiguous; one figure
  type, stable axis semantics. See §11 for the rejected alternatives.
- Per-portal iconographic systems (the Approach 5 idea from earlier
  exploration). Not ruled out for the future, but not specified here.
- Author UI for generating monograms. Authors may use any tool —
  hand-drawn, prompt-driven, traced from references — provided the
  output meets §2.

---

## 2. The monogram

### 2.1 Authoring contract

A monogram is a single SVG file at:

    content/essays/{slug}/mark.svg                  ← directory-form essays
    content/essays/{slug}.mark.svg                  ← flat-file essays
    content/blog/{slug}.mark.svg
    content/poetry/{slug}.mark.svg
    content/fiction/{slug}.mark.svg
    content/music/{slug}/mark.svg
    content/{slug}.mark.svg                         ← standalone pages
    content/drafts/essays/{slug}.mark.svg           ← drafts

The build picks up the file by the same slug-resolution rules already
used for score fragments and page-local JS. No frontmatter key is
required to opt in; the file's presence is the opt-in. To opt out
(suppress an inherited or stale mark), delete the file.

### 2.2 Visual contract

Monograms must satisfy the following constraints. These are enforced
by `tools/audit-marks.py` and by `make audit-marks` (§9), not at
build-fail level — violations warn but do not break the build.

| # | Constraint | Rationale |
|---|---|---|
| M1 | `viewBox="0 0 280 280"` (or proportional, square) | Renders at 130–280 px equally. |
| M2 | All strokes use `stroke="currentColor"`; all fills use `fill="none"` except small filled point-marks which use `fill="currentColor"` | Inverts cleanly under Light, Dark, Cappuccino without per-theme assets. The score-fragment filter already does this substitution; monograms must be authored this way from the start. |
| M3 | Outer roundel: `<circle cx="140" cy="140" r="128" stroke-width="0.6"/>` | The unifying frame. Without it, marks read as illustrations, not as a system. |
| M4 | Stroke widths within {0.3, 0.5, 0.6, 0.8, 1.0, 1.2, 1.4} | Limits visual rhythm to a small palette. |
| M5 | `stroke-linecap="round"` and `stroke-linejoin="round"` everywhere | Spectral-compatible terminals. |
| M6 | No `<text>`, no `<image>`, no gradients, no filters, no embedded fonts, no rasters | Letterforms and color belong to the page, not the mark. Note: `<title>` and `<desc>` for accessibility are required (§2.3), not forbidden. |
| M7 | No XML prologue, no `<?xml` declaration, no DOCTYPE | The file is inlined; a prologue would land mid-body. |
| M8 | File size ≤ 8 KiB | A working corpus of 200 marks at this ceiling is 1.6 MiB total; larger is overkill for a 280-px frontispiece. |
| M9 | Validates as well-formed XML (round-trips through `xmllint --noout`) | Inlining a malformed SVG breaks the surrounding page. |

A reference monogram template lives at `static/templates/mark-template.svg`
and is the recommended starting point for hand-authoring.

### 2.3 Accessibility

Each monogram must include a `<title>` element as the first child of
`<svg>` and may include a `<desc>`:

    <svg viewBox="0 0 280 280" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="mark-title">
      <title id="mark-title">Half-buried column on a low desert horizon</title>
      <desc>A frontispiece mark for the essay "Ozymandias: A Static Site Framework".</desc>
      ...
    </svg>

The author writes the visible-content description in `<title>`. The
`role="img"` and `aria-labelledby` attributes are required by M9.
Screen readers announce the title; the desc is supplementary.

### 2.4 Inlining and theming

Monograms are inlined into the page HTML at build time by the same
mechanism `Filters/Score.hs` uses for score fragments. The build step:

  1. Reads the SVG file.
  2. Strips any `width=` and `height=` attributes from the `<svg>` root
     (presentation is controlled by CSS).
  3. Replaces any `fill="#000000"`, `fill="black"`, `stroke="#000000"`,
     `stroke="black"` with `currentColor` (defensive: lets authors
     produce SVGs from generators that hardcode black without breaking
     the contract).
  4. Wraps the SVG in `<figure class="frontmatter-mark frontmatter-mark--monogram">…</figure>`.

The CSS rule `.frontmatter-mark svg { color: var(--text); }` propagates
the page color to the SVG strokes. No theme-switching JS is required.

### 2.5 Print and reduce-motion

Monograms render in print (they are inert SVG; there is nothing to
suppress). They are unaffected by `prefers-reduced-motion` because
they do not animate. The Display panel's "Focus Mode" hides them via
`.focus-mode .frontmatter-mark { display: none; }`.

---

## 3. The epistemic figure

### 3.1 Visibility rule

The epistemic figure is rendered for a piece if, and only if, the
existing visibility rule for the epistemic block is met:

> The epistemic figure renders when `status:` is set in frontmatter.

This matches the existing rule in `WRITING.md` ("The epistemic footer
section appears when `status` is set"). No new gating field is
introduced. A piece without `status:` gets no figure — the same as it
gets no epistemic block today.

This is deliberate. A figure showing five missing axes and one filled
axis would look like a build bug, not a deliberate position. Either
the piece has taken a position (and therefore renders the figure), or
it has not (and therefore renders only the monogram). The audit job
in §9 lists pieces in `research/` or with `peer-status:` that lack
`status:`, so the absence is visible without being silently broken.

### 3.2 Inputs

The figure consumes only fields already in the schema (per `WRITING.md`),
plus the two new optional fields specified in §4:

| Field | Existing? | Maps to |
|---|---|---|
| `confidence` | yes (0–100) | confidence axis length |
| `importance` | yes (1–5) | importance axis length |
| `evidence` | yes (1–5) | evidence axis length |
| `scope` | yes (5-step ordinal) | scope axis length |
| `novelty` | yes (4-step ordinal) | novelty axis length |
| `practicality` | yes (5-step ordinal) | practicality axis length |
| *(stability)* | auto from git | outer-ring tick count |
| *(trust score)* | auto from formula | center number |
| `peer-status` | **new** (§4.1) | outer-ring tick *style* |
| `result-shape` | **new** (§4.2) | center glyph beside trust |
| `confidence: proved` | **new exception** (§4.3) | confidence axis renders as proof-cap |

Ordinal-to-numeric mapping is exactly what `Contexts.hs` already does
for the dot-rendering of these fields:

| `scope` value | Numeric |
|---|---|
| `personal` | 1 |
| `local` | 2 |
| `average` | 3 |
| `broad` | 4 |
| `civilizational` | 5 |

| `novelty` value | Numeric |
|---|---|
| `conventional` | 1 |
| `moderate` | 2 |
| `idiosyncratic` | 3 |
| `innovative` | 4 |

(Note: `novelty` is a 4-step scale in the existing schema, not 5. The
figure normalizes to a 0–1 axis length the same way the dots do —
`(value - 1) / (max - 1)` — so a 4-step scale renders one step shorter
at maximum than a 5-step scale. This is honest and matches existing
behavior; do not silently widen the scale to 5.)

| `practicality` value | Numeric |
|---|---|
| `abstract` | 1 |
| `low` | 2 |
| `moderate` | 3 |
| `high` | 4 |
| `exceptional` | 5 |

The `confidence` axis is 0–100; it normalizes as `confidence / 100`.

### 3.3 Geometry

The figure is a 200×200 SVG rendered at frontmatter scale (170 px on
desktop, 130 px on mobile). It consists of:

- An outer roundel (two thin concentric circles, `r=88` and `r=90`,
  both `stroke-width="0.5"`).
- Six radial axes at 60° spacing, in this fixed clockwise order
  starting from 12 o'clock:
    1. confidence (top, 0°)
    2. novelty (60°)
    3. practicality (120°)
    4. scope (180°, bottom)
    5. evidence (240°)
    6. importance (300°)
  Axis stroke `0.3`, opacity `0.55`. Visible at all times whether or
  not the corresponding field is set; a missing field renders the
  axis without a polygon vertex (see below).
- Four inner concentric guide circles at `0.2, 0.4, 0.6, 0.8` of the
  axis radius. Stroke `0.25`, opacity `0.4`.
- A polygon connecting the field values along their axes.
  Stroke `1.1`, fill `currentColor` at `fill-opacity="0.08"`. The
  polygon is closed only if all six fields are present; otherwise it
  is rendered as an open polyline through the present vertices in
  axis order, and missing axes contribute no vertex (the line jumps
  the missing axis). This is the only mode where partial fields are
  rendered; in practice §3.1 ensures all six are present whenever the
  figure renders at all.
- Vertex point marks at each present field's position
  (`r=2`, `fill="currentColor"`).
- The center number: trust score, in Spectral 500 weight, font-size 16,
  centered on the geometric center.
- Below the trust number, in 5 pt Fira Sans with letter-spacing 0.18em,
  the literal text `TRUST`.
- Stability ticks on the outer ring at 12 o'clock (see §3.5).
- A result-shape glyph immediately to the right of the trust number
  (rendered only when `result-shape:` is set; see §4.2).

The figure deliberately omits the confidence-trend arrow; the trend is
rendered inline in the compact epistemic strip instead (see §3.4). The
figure carries only the geometry, the trust score, and the result-shape
glyph.

A reference renderer in pure SVG, with annotated coordinates, is
checked in at `static/templates/epistemic-figure-reference.svg` for
visual regression testing.

### 3.4 Confidence trend

The trend arrow is rendered inline in the compact epistemic strip,
immediately after the confidence percentage (e.g. `conf 80%↑`). It
indicates the direction of the *last* step in `confidence-history`:

| Last step | Glyph |
|---|---|
| Increase (∆ > 5) | ↑ |
| Decrease (∆ < −5) | ↓ |
| Equal (within ±5) | → |

When `confidence-history` is absent or has fewer than two entries, the
arrow is not drawn. The arrow uses the same parsing and ±5 threshold
the existing epistemic block uses; no new heuristic is introduced.

The arrow lives in the strip rather than on the figure for two reasons:
the figure stays visually clean, and the arrow sits next to the value
it modifies. This is a deliberate departure from earlier drafts that
placed the arrow at the confidence vertex.

### 3.5 Stability ticks

The existing `Stability.hs` heuristic produces one of five labels:
`volatile`, `revising`, `fairly stable`, `stable`, `established`.
These map to outer-ring ticks at 12 o'clock:

| Stability | Tick count | Tick positions (visible / dim) |
|---|---|---|
| volatile | 1 | center only |
| revising | 2 | center + left |
| fairly stable | 3 | center + left + right |
| stable | 4 | center + left + right + far-left |
| established | 5 | all five |

Ticks are short radial line segments just outside the outer roundel,
1–1.5 px in length, `stroke-width="1"`. Inactive ticks are drawn at
`opacity="0.4"` so the full set is always visible; this gives the
reader a constant five-step scale to anchor against.

The manual override mechanism (`IGNORE.txt`) documented in WRITING.md
applies unchanged: a path listed there pins stability for one build
and is cleared by `make build`. The figure honors the override.

### 3.6 Visibility under reduce-motion and print

The figure does not animate, so reduce-motion has no effect.

In print, the figure renders at fixed size and inverts to black-on-white
via the existing `@media print` rules in `static/css/print.css`. No
new print rules are required.

### 3.7 Theming

The figure uses `currentColor` exclusively. The `<text>` elements
explicitly set `fill="currentColor" stroke="none"` to prevent text
nodes from inheriting the strokes used for geometry.

### 3.8 Tooltip and link

The figure is wrapped in `<a href="#epistemic">…</a>`. Hovering it
triggers the existing epistemic-jump-link popup (per WRITING.md:
"Epistemic jump link (`#epistemic`) — Clone of the full epistemic
profile"). Clicking jumps to the epistemic block at the page footer.

This means the figure does double duty: it is a glance-readable
summary at the top, and a clickable handle for the full block at the
bottom. The popup logic is already implemented; this is a free pickup.

---

## 4. New optional frontmatter fields

Two new fields and one new value of an existing field. All optional;
all backward-compatible; existing essays continue to render
identically until the author opts in.

### 4.1 `peer-status`

Captures the *external* review state of a piece, distinct from
`status` (which captures the author's internal position).

| Value | Meaning |
|---|---|
| `unreviewed` | No external review has taken place. Default if omitted. |
| `under-review` | Currently in submission or peer review. |
| `peer-reviewed` | Has been peer-reviewed (e.g. preprint with referee reports addressed) but not yet formally published. |
| `published` | Appeared in a peer-reviewed venue. Treat as canonical. |
| `retracted` | Formally retracted. Renders with a strikethrough on the field name in the epistemic block. |

This is genre-agnostic. An essay can be `under-review` at a magazine;
a paper can be `peer-reviewed` at a journal. The vocabulary doesn't
change.

#### Visual encoding

`peer-status` modulates the *style* of the stability ticks (§3.5),
not their count. Stability and peer-status are factored: stability
remains git-derived and counts ticks; peer-status changes how those
ticks are drawn:

| `peer-status` | Tick style |
|---|---|
| `unreviewed` (default) | Plain solid ticks. |
| `under-review` | Solid ticks with a small unfilled circle (`r=1`) just outside the outermost tick — "in flight" mark. |
| `peer-reviewed` | Solid ticks with a single horizontal bar above the outer roundel arc. |
| `published` | Solid ticks bracketed by two short vertical marks at ±15° on the outer roundel — a printer's bracket. |
| `retracted` | Solid ticks struck through with a horizontal line `stroke-width="1.5"` across the tick group. |

The reading order on the figure thus becomes: outer ring (stability +
peer-status) communicates *external* standing; inner shape
(polygon + trust + result-shape) communicates *internal* claim.
Cleanly factored.

#### Compact-row rendering

In addition to modulating the figure, `peer-status` adds a compact
chip to the existing epistemic-block primary row, alongside `status`
and the trust chip:

    88% trust · Durable · under review · 80% confidence · ●●●○○ importance · …

Rendered for any non-`unreviewed` value. The label uses the
hyphen-stripped form (`under review`, `peer-reviewed`, `published`,
`retracted`).

### 4.2 `result-shape`

Captures the *shape* of the piece's central claim. This is missing
from the current vocabulary and surfaces information that's currently
buried in the abstract.

| Value | Meaning | Center glyph |
|---|---|---|
| `positive` | Argues for or proves something works. | `+` |
| `negative` | Argues against or proves a barrier. | `−` |
| `mixed` | Both positive and negative results coexist (e.g. *Branch-Based Local Capture*'s "double pincer"). | `±` |
| `comparative` | Compares two or more approaches. | `∼` |
| `descriptive` | Describes a system, observation, or position without arguing for or against. | `□` |

The glyph appears immediately to the right of the trust score, in
Spectral, font-size 16, vertically centered on the trust number. When
omitted, no glyph is drawn (the trust number sits alone).

#### Compact-row rendering

`result-shape` adds nothing to the compact row. The character is small
enough that the figure carries it without competing with the chip
sequence. If omitted, the figure simply renders the trust number alone.

### 4.3 `confidence: proved` (and `proven`)

Formal mathematical results don't have credences in the same sense
that essays do. A theorem with a complete proof has confidence
~100 modulo soundness, but writing `confidence: 95` invites a
false-precision reading. The colophon's commitment to honest
epistemic accounting requires a way to opt out.

The exception:

    confidence: proved

(or the equivalent `proven` — both forms accepted) does three things:

1. The trust score is computed as `100 × 0.6 + ((evidence-1)/4) × 100 × 0.4`,
   i.e. as if `confidence` were 100. Evidence still varies; trust is
   not pinned to 100.
2. The confidence axis on the figure is drawn full-length, with a
   small distinct cap at the vertex: a 3×3-px filled square (instead
   of the usual 2-px circle). The square is the visual marker that
   reads "this is not a credence, it is a proof-completeness flag."
3. The compact row renders `proved confidence` instead of the
   `XX% confidence` form.

`confidence-history` is incompatible with `confidence: proved`. If
both are set, the build emits a warning and `confidence-history` is
ignored (a proof either is or is not; tracking history of a
binary-after-the-fact value is incoherent).

This is the *only* genre-specific carve-out in the schema. All other
fields read across genres without modification, with the colophon
gloss in §6 explaining the cross-genre interpretation.

### 4.4 `subtitle`

Captures a short secondary title shown below the main `title` in the
center column of the new three-column header (§7.2). The field is
optional and free-form.

    subtitle: "A Static Site Framework"

When omitted, no subtitle line is rendered and the byline collapses
upward against the title. The subtitle is *not* an abstract; abstracts
remain in the existing `abstract:` field and render below the byline.

Subtitles do not feed the epistemic figure or any audit metric; they
are purely a presentation field. They render in print and do not
participate in any focus-mode hiding.

---

## 5. Frontmatter layout

The combined frontmatter for an essay using all features:

    ---
    title: "The Title"
    subtitle: "An Optional Secondary Line"
    date: 2026-05-07
    abstract: >
      One-paragraph description.
    tags:
      - research/mathematics

    # existing epistemic
    status: "Durable"
    confidence: 80
    importance: 3
    evidence: 5
    scope: average
    novelty: moderate
    practicality: moderate
    confidence-history: [60, 70, 80]

    # new
    peer-status: under-review
    result-shape: mixed
    ---

For a formal-mathematics piece using `confidence: proved`:

    ---
    title: "Branch-Based Local Capture in Tree-Ball Geometry"
    status: "Durable"
    confidence: proved
    importance: 3
    evidence: 5
    scope: average
    novelty: idiosyncratic
    practicality: low
    peer-status: under-review
    result-shape: mixed
    ---

The monogram lives outside frontmatter, in
`content/essays/branch-based-local-capture-in-tree-balls/mark.svg`.

---

## 6. Colophon gloss

The colophon's *Living Documents* section is updated to add a
paragraph documenting genre-specific reading of the existing
fields. Proposed text (to be inserted before the field list):

> The epistemic vocabulary above is genre-general but reads
> differently across genres. For a personal essay, `confidence`
> reflects credence in a thesis — "I might change my mind." For an
> empirical research paper, it reflects expected generalization —
> "this would replicate." For formal mathematics, it reflects
> credence in proof correctness, with a special value `proved`
> available for theorems with complete proofs (where any numeric
> value would be false precision). `evidence` reads analogously: the
> strength of arguments and supporting writing in essays, the
> empirical base in research, the structure of the proof in
> mathematics. The fields are the same; the interpretive frame
> shifts with the work.

Two new field rows are appended to the existing field list:

> **Peer status** — the external review state, distinct from
> `status` (which is the author's internal position). Values:
> *unreviewed* (default), *under review*, *peer reviewed*,
> *published*, *retracted*. This information modulates the outer
> ring of the epistemic figure; a *retracted* piece is also rendered
> with the field name struck through.
>
> **Result shape** — the shape of the central claim: *positive*
> (argues something works), *negative* (argues something does not),
> *mixed* (both, as in a double-pincer barrier paper), *comparative*
> (compares approaches), or *descriptive* (describes without arguing
> for or against). Encoded as a small glyph beside the trust score
> on the epistemic figure.

---

## 7. Pandoc filter and template integration

### 7.1 New Haskell module

A new module `build/Filters/Mark.hs` exports two functions:

    -- | Render the monogram inline. Reads from disk; substitutes
    --   black/#000000 fills and strokes with currentColor; strips
    --   width/height attributes from <svg>; wraps in <figure>.
    --   Returns an empty document fragment if the file is absent.
    renderMonogram :: FilePath -> Compiler Html

    -- | Build the epistemic figure SVG from a Context.
    --   Reads exactly the fields listed in §3.2.
    --   Returns Nothing when `status` is absent.
    renderEpistemicFigure :: EpistemicFields -> Maybe Html

`EpistemicFields` is a small record type that reuses the parsing
logic already in `Contexts.hs` for the existing block. The figure
generator is a pure function from this record to SVG markup.

The filter is wired into `build/Compilers.hs` as the last step of
the AST transformation, so it runs after the existing image,
sidenote, and citation passes. It produces no AST mutation; instead,
the rendered SVG is added to the page Context as two new fields:

    monogramSvg     -- inline SVG or empty
    epistemicSvg    -- inline SVG or empty

These are referenced in templates as `$monogramSvg$` and
`$epistemicSvg$`.

### 7.2 Template change

The current `templates/partials/metadata.html` carries everything
between the title and the cursive-L divider: tags, keywords, abstract,
byline, affiliation, the compact epistemic strip, and the page-nav
links. To make room for the three-column header without losing the
ordering or the divider, the partial is split in two:

  - `templates/partials/metadata-header.html` — byline, abstract, and
    the compact epistemic strip. Renders inside the center column of
    the new header.
  - `templates/partials/metadata-tail.html` — tags, keywords,
    affiliation, page-nav, in that exact order (matching the current
    `metadata.html` rendering order). Renders as a row beneath the
    three-column header, above the cursive-L divider.

`templates/essay.html` and `templates/blog-post.html` then become:

    <header class="essay-frontmatter">
      <div class="frontmatter-mark frontmatter-mark--monogram">$monogramSvg$</div>
      <div class="frontmatter-title">
        <h1 class="page-title">$title$</h1>
        $if(subtitle)$<p class="essay-subtitle">$subtitle$</p>$endif$
        $partial("templates/partials/metadata-header.html")$
      </div>
      <div class="frontmatter-mark frontmatter-mark--epistemic">
        <a href="#epistemic" aria-label="Jump to epistemic profile">$epistemicSvg$</a>
      </div>
    </header>
    $partial("templates/partials/metadata-tail.html")$
    <div class="content-divider" aria-hidden="true">
      <a href="/new.html" class="content-divider-logo" aria-label="New"></a>
    </div>

The cursive-L `content-divider-logo` is preserved exactly as it is
today; nothing about the frontmatter↔body separator changes. Only the
material *above* the divider is reorganized.

When either SVG is empty, the corresponding column collapses (CSS
grid, `auto` sizing). When both are absent, the header degrades to a
single-column layout that visually matches the existing one
(title + subtitle + metadata-header), so existing pages render
identically until they opt in.

`reading.html` (poetry/fiction) does NOT receive the figure column,
since these content types omit the epistemic block by design. They
do receive the monogram column when a `mark.svg` is present, plus the
`subtitle` field if set.

`pageCtx` (standalone pages) receives neither column but does honor
`subtitle` if set.

### 7.3 CSS

A new file `static/css/marks.css` defines the grid layout, the
collapse behavior, the print rules, the focus-mode hiding, and the
two `.frontmatter-mark` modifiers. It loads with the rest of the
stylesheet bundle; no new HTTP request.

The breakpoint at which the figure column drops below the title
(rather than sitting beside it) is the existing narrow-screen
breakpoint where sidenotes collapse to footnotes. A reader on
mobile sees: monogram → title → figure, stacked.

---

## 8. Build behavior

### 8.1 Determinism

Both monograms and epistemic figures must be deterministic at build
time. The monogram is just a file read; the epistemic figure is a
pure function of frontmatter and `git log --follow`. Two consecutive
builds of the same content tree must produce byte-identical SVGs.

This is enforced by:

  - No timestamps in generated SVGs.
  - No floating-point coordinates beyond two decimal places.
  - Stable ordering of attributes (alphabetical) and elements
    (declaration order).
  - No build-time UUIDs or random IDs (use deterministic IDs derived
    from slug, e.g. `id="mark-title-{slug}"`).

This matters for the GPG signing pipeline (`make sign`): a
non-deterministic SVG would invalidate page signatures across
otherwise-identical builds.

### 8.2 Performance

Reading 200 small SVG files at build is negligible. Rendering 200
epistemic figures is a few hundred lines of string concatenation each
and well within the existing build budget. No new build step is
needed; the work happens inside `Compilers.hs` alongside existing
filter passes.

The Hakyll dependency tracking already keys on frontmatter changes
via the existing essay context. Adding `monogramSvg` and
`epistemicSvg` to the same context propagates dependency tracking
for free: editing a frontmatter field invalidates the page; replacing
a `mark.svg` invalidates only that page's dependencies (Hakyll's
file-watch already tracks `content/**`).

### 8.3 Failure modes

| Condition | Build behavior |
|---|---|
| `mark.svg` absent | Monogram column collapses; no warning. |
| `mark.svg` malformed XML | Warn; render the slot empty; do not fail the build. |
| `mark.svg` exceeds 8 KiB | Warn; render anyway. |
| `mark.svg` violates §2.2 contract | Warn (with specific violation); render anyway. |
| `status:` absent | Epistemic column collapses; no warning. |
| `status:` set, `confidence` missing | Render figure; confidence axis has no vertex point. |
| `peer-status:` invalid value | Warn; treat as `unreviewed`. |
| `result-shape:` invalid value | Warn; render figure without center glyph. |
| `confidence: proved` and `confidence-history:` both set | Warn; ignore `confidence-history`. |

Warnings go to stderr during `make build`. They are captured and
surfaced on `/build/` (§9).

### 8.4 Backwards compatibility

Every existing essay must render identically after this change is
deployed, until and unless the author edits the file to add a
`mark.svg` or new frontmatter fields. The new template grid must
collapse to the existing single-column layout when both
`$monogramSvg$` and `$epistemicSvg$` are empty; CSS feature-tests
for grid fallback are not needed because the existing template uses
flexbox/block already.

A pre-merge regression test runs `make build` on a snapshot of
`content/` from before the change and diffs `_site/` against a
known-good snapshot. The only allowed diffs are template-driven
whitespace.

---

## 9. Audit and telemetry

### 9.1 `make audit-marks`

A new build target lists pieces missing one or both marks. Output
columns: path, has-monogram?, has-epistemic-figure?, suggested
action.

    $ make audit-marks
    content/essays/ozymandias.md            ✓ ✓
    content/essays/branch-based-...md       ✗ ✗   add mark.svg, set status:
    content/essays/beyond-comorbidity-...   ✗ ✓   add mark.svg
    ...

Implementation: `tools/audit-marks.py` walks `content/**/*.md`,
parses YAML frontmatter, checks for the corresponding `mark.svg`,
checks whether `status:` is set, and emits the table.

The script also emits two summary metrics: corpus monogram coverage
percentage and corpus epistemic-figure coverage percentage.

### 9.2 `/build/` integration

The existing build telemetry page already includes "epistemic
coverage" per the WRITING.md auto-generated-pages list. Two new
sub-sections are added to that page:

  - **Monogram coverage**: count and percentage of essays/blog/poetry/
    fiction/music with `mark.svg` present, broken down by portal.
  - **Epistemic-figure coverage**: count and percentage of pieces
    with `status:` set and a renderable figure, broken down by portal.

The same Stats.hs module that produces existing coverage figures
extends to compute these. No new external dependencies.

### 9.3 Linting hook

A pre-commit hook (`tools/hooks/pre-commit-marks.sh`) runs
`make audit-marks` and warns on any new `.md` file under
`content/essays/` or `content/research/` (effectively, anything
tagged `research/*` or in those directories) added without a
`mark.svg` or with `status:` unset. Warning only; does not block
the commit. Authors who genuinely want to publish without marks
can ignore the warning.

---

## 10. Migration

### Phase 1 — Wire the system, no content (1 build)

  - Land `Filters/Mark.hs`, the template changes, and `static/css/marks.css`.
  - Land `tools/audit-marks.py`.
  - Land the two new schema fields (`peer-status`, `result-shape`)
    and the `confidence: proved` exception in `Contexts.hs` and
    `Stability.hs`.
  - Update `WRITING.md` with the new fields and the `mark.svg`
    convention.
  - Update the colophon with the §6 gloss.
  - Build. Every existing page renders identically (§8.4).

### Phase 2 — Reference monograms (1 week of evenings)

  - Author monograms for the 8–10 most-trafficked pieces (likely:
    *Colophon*, *Memento Mori*, *Ozymandias*, *Beyond Comorbidity Indices*,
    *Branch-Based Local Capture*, the *Music* index, the *Library* portal
    landing, and a poetry collection landing).
  - Author the reference monogram template at
    `static/templates/mark-template.svg`.
  - Validate them against §2.2 with `make audit-marks`.

### Phase 3 — Backfill epistemic fields (incremental)

  - For each piece in `research/` and `nonfiction/`, decide whether to
    add `status:`, `peer-status:`, `result-shape:`. The audit script
    surfaces the candidates.
  - Specifically: *Branch-Based Local Capture* gets `status: Durable`,
    `confidence: proved`, `evidence: 5`, `peer-status: unreviewed`,
    `result-shape: mixed`. *Beyond Comorbidity Indices* gets
    `peer-status: under-review` and `result-shape: comparative`
    added.

### Phase 4 — Iterate

  - Once 30+ marks exist, review the corpus as a system. Tighten
    §2.2 constraints if cross-mark consistency is weaker than expected.
    Loosen if the constraints are pinching authorship.
  - Decide whether portal-level base monograms (the
    Approach 5 idea) are worth adding as a third tier.

---

## 11. Rejected alternatives

These were considered and not adopted; recording them so future
revisions don't relitigate.

  - **Two figure types (essay vs. research badge).** The existing
    fields handle both genres when read with appropriate gloss
    (§6). Two figures would create a visual fork that costs more
    than it pays. *Beyond Comorbidity Indices* is the proof point:
    formal research already renders cleanly with the existing
    vocabulary.
  - **Mode-switched figure with axes that change meaning per genre.**
    Visual grammar should be unambiguous. A single radial figure
    where the axes mean different things depending on a frontmatter
    flag would require footnotes to read. Genre-gloss in the colophon
    handles the same need without ambiguity.
  - **Auto-derived monograms from semantic-search embeddings.** Tried
    in spec drafting. The result is generic and lacks the editorial
    statement that a hand-authored monogram makes. Authors may use
    AI-assist tools to generate monograms (against §2.2 contract),
    but the system does not derive them automatically.
  - **Ghosted axes for missing fields.** Tested visually. Reads as a
    bug, not a deliberate position. Better to suppress the figure
    entirely (§3.1) and surface the absence in `/build/` (§9).
  - **A separate `claim-mode: formal | empirical | essay` field.**
    Solved the wrong problem. The fields don't need a mode flag; they
    need a gloss. The two new fields (`peer-status`, `result-shape`)
    plus the `confidence: proved` exception cover the genre-specific
    needs surfaced in audit.
  - **Folding `peer-status` into `status`.** Tempting but wrong.
    `status` is the author's position ("I expect this to hold up").
    `peer-status` is the world's position ("the field has confirmed
    it"). A piece can be `Durable` and `unreviewed` simultaneously
    (the author believes it; the world hasn't checked yet). Keeping
    them factored preserves that distinction.

---

## 12. Open questions for review

  1. **Monogram filename convention.** Spec proposes `mark.svg` (in
     directory-form) and `{slug}.mark.svg` (flat-form). Alternative:
     always require directory-form for any piece that wants a
     monogram, simplifying the resolver. Cost: forces directory-form
     migration on currently-flat essays. Recommend keeping both
     forms; the resolver is small and the migration cost is real.

  2. **Should `peer-status: retracted` survive `make build`?**
     Currently spec'd as a normal field with a strikethrough.
     Alternative: `make build` refuses to publish pieces marked
     `retracted` and instead generates a tombstone page at the
     original URL. Probably overkill for the personal-site context;
     leaving as a normal field with visual indicator. Worth flagging.

  3. **Should the figure's confidence trend arrow distinguish
     "stable" (∆ ≤ 2) from "unchanged" (∆ = 0)?** Currently treats
     them the same as `→`. The existing trend arrow in the epistemic
     block does too. No need to diverge.

  4. **Per-portal monogram defaults.** Should an absent `mark.svg`
     fall back to a portal-level base monogram (e.g. all `research/`
     pieces show a default research mark)? Spec says no — absence
     is meaningful and surfaces in `/build/`. The visual specimen
     sheets in the earlier exploration suggested portal-level
     iconography is interesting; defer to a future spec.

  5. **Naming.** The pair of glyphs is currently called "monogram"
     and "epistemic figure." Considered alternatives: "device"
     (printer's-mark lineage) and "figure" (Tufte lineage), or
     "mark" and "badge" (more colloquial). Spec uses
     "monogram + epistemic figure" because it most accurately
     describes what each thing *is*. Open to naming bikeshed.

---

## 13. Files touched

A complete list of files this spec creates or modifies, for tracking
PR scope:

**New:**

  - `build/Filters/Mark.hs`
  - `tools/audit-marks.py`
  - `tools/hooks/pre-commit-marks.sh`
  - `static/css/marks.css`
  - `static/templates/mark-template.svg`
  - `static/templates/epistemic-figure-reference.svg`
  - `MARKS.md` (this file, after merge)

**Modified:**

  - `build/Compilers.hs` (expose new context fields where essay /
    blog / reading / page contexts are assembled)
  - `build/Contexts.hs` (parse `subtitle`, `peer-status`,
    `result-shape`, `confidence: proved`; produce `monogramSvg` and
    `epistemicSvg` context fields; render the inline trend arrow
    inside the compact-row `confidence` chip)
  - `build/Stability.hs` (consume `peer-status` for tick styling
    if rendering moves out of pure SVG generator)
  - `build/Stats.hs` (monogram + epistemic-figure coverage on
    `/build/`)
  - `templates/essay.html`
  - `templates/blog-post.html`
  - `templates/reading.html` (monogram column + `subtitle`; no figure)
  - `templates/partials/metadata.html` (split into the two new
    partials below; this file becomes a thin shim or is removed)
  - `templates/partials/metadata-header.html` (new — center-column
    metadata: byline, abstract, compact epistemic strip)
  - `templates/partials/metadata-tail.html` (new — row beneath the
    three-column header: tags, keywords, affiliation, page-nav, in
    that order)
  - `Makefile` (`audit-marks` target)
  - `WRITING.md` (new fields including `subtitle`; monogram convention)
  - `content/colophon.md` (genre gloss)

**Per-essay (Phase 2+):**

  - `content/essays/{slug}/mark.svg` × N (hand-authored monograms)
  - frontmatter edits to add `peer-status:`, `result-shape:`,
    `confidence: proved` where applicable.

---

## 14. Future work (out of scope for the initial rollout)

These extensions are explicitly deferred. They are recorded here so
that the structural decisions in §§2–9 do not foreclose them.

  - **Monogram in hyperlink popup previews.** The existing on-hover
    page-preview popup (which already renders title and abstract for
    internal links) should display the monogram alongside the title
    when one exists. The popup is the smallest place a reader meets a
    page; the monogram earns its keep there.
  - **Monogram in `/library/` and `/new/` feed listings.** Both the
    library portal and the recent-changes feed render lists of pages.
    Once monogram coverage is non-trivial (Phase 2 ships ≥10), each
    list item should render the monogram as a small inline glyph
    beside the title.
  - **Portal-level base monograms.** Deferred per §12.4, but the
    correct natural place to introduce them is once the popup and
    feed-listing wiring is in place — base monograms compensate for
    list rows where the per-page monogram is absent.

These items are scoped as a follow-up PR (informally "PR 4") after
the audit-tool PR ships and after at least 10 hand-authored monograms
exist to test the popup/listing rendering against real content.
