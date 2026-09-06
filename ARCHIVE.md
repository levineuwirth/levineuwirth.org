# Archive

Design and implementation plan for the link-archiving system of levineuwirth.org.
This is the source of truth for how external references are preserved, hosted,
displayed, and indexed. It sits alongside `WRITING.md`, `PHOTOGRAPHY.md`,
`HOMEPAGE.md`, and `MARKS.md` as authoritative spec.

## Status

**Reviewed and ratified 2026-05-21, with revisions.** The original draft was
reviewed against the live site over three rounds; the decisions below
incorporate every round of deltas and are now locked.

**Phase 1 complete (2026-05-22).** PDF entries: `archive/manifest.yaml`,
`tools/archive.py` (`fetch` + `gc`), `build/Archive.hs`, the four templates,
and the Makefile / `head.html` / `.gitignore` wiring are built and verified —
`/archive/` and `/archive/nist-fips-203/` render.

**Phase 2 complete (2026-05-22).** HTML snapshots: the pinned `monolith`
binary is vendored at `tools/bin/monolith`, `archive.py fetch` snapshots HTML
pages (CSP injected, text extracted, quality classified), and `archive.html`
renders them in a sandboxed iframe — `/archive/djb-aes-speed/` renders. The
cross-browser CSP check and the per-snapshot review remain author-gated by
design.

**Archive pages styled (2026-05-22).** `static/css/archive.css` gives the
index and entry pages a framed treatment (banner callout, provenance panel,
artifact viewer); the PDF embed was changed to the raw `document.pdf` (browser-
native viewer), symmetric with HTML snapshots — see the Display — PDF decision.

**Phase 3 complete (2026-05-22).** Link annotation + Wayback: `Filters/Archive.hs`
appends an archive affordance to body links whose target is archived;
`archive.py wayback` (+ `make archive-wayback`) backfills Wayback captures;
`visibility: private` keeps an entry's artifact in-repo but undeployed.
Bibliography annotation is documented as a `Citations.hs` follow-up
*(implemented 2026-06-10 — see the Bibliography note under Link annotation)*.

**Phase 4 complete (2026-05-22).** Backlinks + similar-pages: `Backlinks.hs`
keeps archived external links and canonicalises them to their `/archive/<slug>/`
page, so an archived work lists every essay that cites it under "Referenced by"
(grouped by the fragment each citation targets); `archive.html` also carries a
"Related" block from the `embed.py` similarity corpus, which now indexes archive
pages and excludes the `/archive/` index.

**Phase 5 complete (2026-05-22).** Link-rot detection: `tools/archive.py check`
(+ `make archive-check`) HEAD/GET-probes every manifest URL and updates the
gitignored `data/archive-state.json` under asymmetric hysteresis (`rotted`
needs 3 fails over ≥14 days; a single success recovers immediately).
`Filters.Archive` flips a body link to the archive when its target is `rotted`;
each archive page surfaces its link status (provenance row, header note,
Pagefind `status` filter tag); `/archive/` flags rotted entries; `/build/`
gains a "Link archive" telemetry section. The search-UI `status` filter wiring
in `search-filters.js` was deliberately partial in this phase *(completed
2026-06-10 — see the Phase 5 Met note)*.

**All five phases done.** Refinements next; see the Phase 5 Met note for the
documented deferrals (search-UI status filter, bibliography annotation from
Phase 3, and pull-from-Wayback at fetch time — all three implemented
2026-06-10).

**Refinements (2026-05-22).** A code-review pass found and fixed several
correctness and posture issues across the system:

- **Missing committed artifact no longer re-fetches silently.** `cmd_fetch`
  used to skip its SHA guard when the artifact was absent and then download
  fresh bytes whose hash differed from the recorded `sha256` — replacing the
  recorded snapshot without surfacing it. The guard now also halts when
  `PROVENANCE.json` is present but the artifact is missing, requiring the
  author to restore the committed bytes before rebuilding.
- **`archive/removed.yaml` is now enforced in `fetch` and `check`.** It was
  only read by `gc`. A removed URL re-added to the manifest now halts
  `cmd_fetch` loudly; `cmd_check` skips removed URLs so the link-rot
  scanner does not keep probing a deliberate takedown.
- **SHA verification closed the `.venv`-bypass hole.** The original
  decision relied solely on `archive.py fetch` re-hashing, but that step is
  `.venv`-gated — a contributor or deploy host without `.venv`, or a direct
  `cabal run site -- build`, would publish a tampered artifact unchecked.
  `build/Archive.hs` now also re-hashes via `sha256sum` from
  `loadArchiveEntries` and halts the build on a mismatch, so the guarantee
  holds independent of the Python step.
- **Raw artifacts are no longer publicly indexable.** Pass 1 added a
  `robots.txt` `Disallow: /archive/`, which pass 2 then reverted (see
  below — it was counter-productive). Pass 1's other change — injecting
  `<meta name=robots content="noindex, noarchive">` into every new HTML
  snapshot alongside the archive CSP — remains in place; the
  deploy-side header for raw PDFs landed in pass 2 as `nginx/archive.conf`.
- **The documented `archive.py refresh {slug}` subcommand is implemented.**
  It clears the slug's directory, re-fetches via `cmd_fetch`, and records
  the prior `sha256` as `previous-sha256` in the new `PROVENANCE.json`. The
  URL-changed error message in `cmd_fetch` now points at it instead of
  asking the author to delete the directory by hand.
- **`url_aliases` widened** to the design's full equivalent-URL set:
  tracking-parameter stripping (`utm_*`, `fbclid`, `gclid`, `mc_*`, `ref`,
  `igshid`, `_hsenc`, `_hsmi`, `mkt_tok`) and arXiv abs / pdf / versioned /
  `.pdf` form expansion. Phase 1 had deliberately kept these as a Phase 4
  deferral, but Phase 4 missed the follow-through.
- **`X-Robots-Tag: noarchive` is now honoured on both HEAD and GET.** Some
  servers omit the header on HEAD but emit it on GET; HTML capture now
  aborts if either response carries the directive.

Three smaller items remain documented and deferred:

- **Archive tags joining the site-wide tag indexes.** `manifest.yaml`'s
  `tags:` is authored but `Tags.hs`/`Patterns.tagIndexable` does not yet
  ingest archive entries — it needs a Tags.hs-side integration with its
  own design pass (archive pages aren't `match`ed Hakyll items in the
  normal way).
- **`archive.py suggest`** (bibliography discovery — diff `.bib` URLs
  against the manifest) is documented but not implemented. *(Implemented
  2026-06-10 — see the status note below.)*
- **The controlled-host end-to-end link-rot test** (reserve
  `archive-test.levineuwirth.org`, run it through a 14-day-spanning fail
  streak, watch the flip happen) is inherently a multi-week real-world
  verification the author runs; the hysteresis logic is unit-tested
  deterministically and the rendering side is verified by a hand-crafted
  `rotted` state file.

**Refinements pass 2 (2026-05-23).** A second code-review pass surfaced
correctness gaps the first pass missed:

- **`refresh` is now atomic.** It used to delete the slug directory and
  then call `cmd_fetch`; a failed re-fetch left the entry with no
  snapshot at all, while `refresh` returned 0 (because `cmd_fetch`
  reports per-entry skips, not a process failure). The slug directory is
  now *renamed* to a `.refresh-backup` sibling; success removes the
  backup, any failure restores it. Verified by hiding the `monolith`
  binary and confirming the prior snapshot survives intact.
- **Invalid `visibility` values fail closed.** The `ManifestEntry` parser
  used to accept any string and only treat the exact `"private"` as
  private — a typo like `privte` would publish a work the author intended
  to keep offline. The parser now rejects any value other than `public`
  or `private`, and `readManifest` halts the build on any parse error of
  a present file (instead of warning + returning an empty list — that
  silent-skip was for `file absent`, not `file present but corrupt`).
- **Lookup-side URL normalisation.** Alias generation alone cannot cover
  unbounded forms (arXiv versions, arbitrary tracking-parameter
  combinations). `ArchiveIndex` now normalises both index keys and
  lookup inputs through the same `normalizeUrl` (drop fragment, strip
  tracking, fold http→https, arXiv-canonicalise, trim trailing slash).
  Verified: `https://cr.yp.to/aes-speed.html`,
  `https://cr.yp.to/aes-speed.html?utm_source=mail`, and
  `http://cr.yp.to/aes-speed.html/` all match the same archived entry.
- **Raw-artifact indexing posture corrected.** The Phase-5 `robots.txt`
  `Disallow: /archive/` was counter-productive: a URL blocked by
  robots.txt can still appear in results when externally linked, and the
  Disallow also prevents compliant crawlers from reading the wrapper
  pages' `<meta name=robots>`. The Disallow is reverted; a new
  `nginx/archive.conf` snippet emits `X-Robots-Tag: noindex, noarchive`
  for the whole `/archive/` tree, which crawlers honour for any resource
  (HTML and PDF alike). The deploy vhost should `include
  snippets/archive.conf`.
- **`cmd_wayback` skips `removed.yaml`.** The eviction procedure says
  record in `removed.yaml` *before* dropping the manifest line; `fetch`
  and `check` now honour that ordering, but `wayback` did not. A removed
  entry whose manifest line was still in place could be submitted to a
  third-party archive after a takedown was recorded.
- **The shipped HTML snapshot was refreshed in the working tree** so it
  carries the noarchive meta the Phase-5 inject promises. `archive.py
  refresh djb-aes-speed` re-fetched cr.yp.to, applied
  `inject_archive_metas`, and recorded the prior SHA as `previous-sha256`.
  `archive/djb-aes-speed/{snapshot.html, PROVENANCE.json}` now reflect the
  new bytes; matching SHA is verified by `Archive.hs`. *Caveat surfaced
  in pass 3 (below): the prior snapshot was not committed at the moment
  of this refresh, so its bytes are no longer recoverable via `git log
  -S`. A pass-3 fix to `refresh` now refuses to replace an uncommitted
  prior, but the historical artifact survives — `previous-sha256`
  records a hash whose bytes this working tree cannot reproduce.*
- **The URL-changed error in `cmd_fetch`** now points at
  `archive.py refresh {slug}` instead of asking the author to delete the
  directory by hand.

Tag integration remains the one deferred refinement (it needs a Tags.hs
design pass).

**Refinements pass 3 (2026-05-23).** A third audit surfaced gaps the pass-2
fixes didn't fully close:

- **`refresh` refuses to replace an uncommitted prior snapshot.** Pass 2
  preserved a prior snapshot through *failed* re-fetches, but a *successful*
  one happily discarded uncommitted bytes — `previous-sha256` then pointed
  at a hash no `git log -S` could recover. Pass 3 shells out to `git
  ls-files` + `git diff --quiet HEAD` and refuses the refresh unless both
  the prior PROVENANCE.json and its artifact are tracked and clean.
- **`refresh` is atomic across *every* exit path.** Pass 2 handled the
  ordinary `cmd_fetch returns 0 but the artifact wasn't produced` case but
  not fatal `sys.exit`s (e.g. a `removed.yaml` conflict halting `cmd_fetch`
  mid-refresh) nor mid-refresh exceptions, and it never rolled back the
  `data/archive-index.json` rewrite. The work is now wrapped in
  `try/finally` that restores both the slug directory and the index on any
  exit path — normal failure, `SystemExit`, `KeyboardInterrupt`, or
  exception.
- **Removal enforcement now uses the same equivalence as link matching.**
  Pass 2 introduced `normalizeUrl` for incoming citations but compared
  removals as literal URL strings, so a tracking-laden manifest URL could
  bypass a takedown. Python gains `normalize_url` mirroring the Haskell
  helper, and `fetch` / `check` / `wayback` compare normalised forms.
  `cmd_fetch` additionally rejects two manifest entries whose canonical
  forms collide — that would otherwise route both under one slug.
- **`fetch_html` honours `X-Robots-Tag: noarchive` on the captured GET too.**
  Pass 1 added HEAD + ranged-GET probes, but a server can emit the header
  only on the full document response. The Python tool now downloads that
  response itself, checks its header and body directives, then passes those
  exact bytes to `monolith --base-url ... -` so the saved snapshot is not
  obtained through a second unobservable document request.
- **`nginx/archive.conf` is wired into the deploy template** and
  re-`include`s `security-headers.conf` inside its `location` block.
  `nginx/vhost.conf.example` now includes `archive.conf`; the snippet
  itself re-emits the baseline headers because nginx's `add_header` chain
  is inherited from a parent only when the current context declares *no*
  `add_header` directives — without the re-include, /archive/ would lose
  HSTS, CSP, etc.

  **Framing exception (added later).** The framing directives now live in
  their own snippet, `nginx/security-framing.conf`, which the vhost
  includes at server level and which `archive.conf` deliberately does
  *not* re-include. The site-wide `X-Frame-Options: DENY` applied to the
  snapshots too, so `templates/archive.html`'s same-origin
  `<iframe class="archive-frame" … sandbox>` was refused by the browser
  and the wrapper page showed an empty frame. `archive.conf` now emits
  `X-Frame-Options: SAMEORIGIN` plus an enforcing
  `Content-Security-Policy: frame-ancestors 'self'` as the whole framing
  policy for the subtree — one coherent pair, not a second header layered
  over a conflicting one. Third-party embedding stays blocked, and the
  containment of the untrusted snapshot is unchanged because that comes
  from the iframe's own `sandbox` attribute, which the embedding page
  sets and these response headers do not touch.
- **Contract doc cleanups.** The Phase-5 paragraph claiming `robots.txt`
  disallows `/archive/` is reworded to acknowledge the pass-2 reversal;
  the Phase-1 checkbox claiming `Archive.hs` does not re-hash is updated
  to point at `verifyArtifactSha`; the pass-2 note about the refreshed
  djb snapshot now carries the caveat that its prior bytes were
  uncommitted and are therefore unrecoverable.

The historical `previous-sha256` value in `archive/djb-aes-speed/
PROVENANCE.json` is left in place: it is a truthful record that *a* prior
snapshot existed and what its hash was. It just is not recoverable from
git in this working tree — the pass-3 `refresh` precondition exists so
that property is never broken again.

**Refinements pass 4 (2026-05-23).** A fourth audit completed the
failure-closed paths:

- **Direct Hakyll builds now enforce removals and missing-artifact failures.**
  `Archive.hs` reads `removed.yaml`, rejects normalized manifest conflicts
  and duplicate archive targets, and aborts if provenance exists without its
  artifact. `ArchiveIndex.hs` filters the generated index through the live
  manifest minus normalized removals, so a stale ignored index cannot retain
  archive affordances after a takedown when `archive.py` was skipped.
- **`refresh` verifies the prior bytes before replacing them.** A prior
  snapshot must now be present, tracked, clean, and match its recorded
  SHA-256 before its hash can be written into `previous-sha256`.
- **Failed refresh restores an originally-absent index state.** If
  `data/archive-index.json` did not exist before a failed refresh, any index
  created by the attempted fetch is deleted during rollback.

The genuinely-open questions that remain are collected at the end — the list is
short.

**`archive.py suggest` implemented (2026-06-10).** The bibliography-discovery
subcommand from the design is built: `make archive-suggest` scans `data/*.bib`
for `url` / `doi` fields (per entry the `url` field wins; a DOI-only entry
resolves to `https://doi.org/{doi}`), diffs them against `manifest.yaml` and
`removed.yaml` under the same `normalize_url` equivalence the link-annotation
filter uses, and prints manifest-ready `- url:` lines, each preceded by
`# cited by {bibfile}:{key}` comments (a work cited from several papers prints
once, with every citer). Read-only and offline: it never edits the manifest
and performs no network I/O. Known equivalence gap, surfaced by the first real
run: a work archived under its landing URL but cited via its DOI (e.g.
FIPS 203 — archived as the `nvlpubs.nist.gov` PDF, cited as
`doi.org/10.6028/NIST.FIPS.203`) is re-suggested, because nothing offline can
equate the two forms. That is the same gap that denies those bibliography
links an archive affordance, so the suggestion is honest — the fix, if wanted,
is alias-level (manifest or `url_aliases`), not suppression in `suggest`.

**Manifest `aliases:` field implemented (2026-06-10).** The alias-level fix
above: an optional authored `aliases:` list per manifest entry for equivalent
URLs that normalisation cannot derive (the DOI ↔ landing-URL case). Aliases
are matching metadata, not identity — editing them rewrites the index on the
next fetch, no `refresh` involved. Enforcement mirrors canonical URLs on both
sides of the build: the `archive.py fetch` pre-scan and `Archive.hs`'s
`validateManifestEntries` each reject an alias that collides with another
entry (directly or via aliases) or that matches a `removed.yaml` takedown,
and `ArchiveIndex.flatIndex` additionally drops alias keys matching recorded
takedowns so a stale index cannot keep annotating a removed work. `suggest`
counts aliases as covered. Applied: `nist-fips-203` now carries
`https://doi.org/10.6028/NIST.FIPS.203`, so the simd paper's DOI citation
resolves to the archived PDF and `suggest` no longer re-suggests it.

**Link-rot scan scheduled (2026-06-10).** The scan now runs unattended: a
systemd user timer (`systemd/archive-check.{service,timer}`, symlink-installed
on the build machine) fires `make archive-check` daily. Going unattended
exposed a hysteresis hazard hand-run scans masked — a machine left offline
would record a `fail` against every entry, and three such scans spanning two
weeks would flip the whole archive to `rotted` — so `cmd_check` gained a
canary guard: `https://levineuwirth.org/` unreachable → scan inconclusive,
state untouched, exit 0. Details in the Phase 5 section.

**Fetch-time Wayback fallback implemented (2026-06-10).** The design's
"original already dead at first fetch → pull the most recent existing Wayback
capture" promise is now real. `fetch_pdf`/`fetch_html` classify their
failures (`ok` / `dead` / `skip`), and only a *dead* original — not a
`noarchive` refusal, cap skip, or tooling failure — falls through to
`fetch_from_wayback`, which pulls the raw `id_` capture bytes through the
normal pipeline, honours a preserved `X-Archive-Orig-X-Robots-Tag:
noarchive`, re-detects the artifact type against the capture (the dead
original's Content-Type probe degrades to the html default), and records
`fetched-from` + `wayback` in `PROVENANCE.json`. `refresh` deliberately
excludes the fallback: a dead original fails the refresh and restores the
prior first-hand snapshot. Mechanics in Wayback Machine — non-blocking.

**Bibliography annotation implemented (2026-06-10).** The Phase 3 follow-up
is done: bibliography entries now carry the same archive affordance (and
rotted-link flip) as body links. The gating CSL-URL check passed —
citeproc renders entry URLs as `Link` inlines — so `Filters.Archive` exports
`annotateBlock` and `Citations.hs` applies it after `enhanceEntry` in both
`renderBibDiv` (essay bibliographies) and `renderBibliographyHtml`
(`/bibliography/` pages). Verified on the rendered SIMD essay, including the
DOI-cited FIPS 203 entry resolving through its manifest alias. Details under
Link annotation — Bibliography.

**Search-UI archive filter implemented (2026-06-10).** The last deferred
refinement with a code-shaped fix: the search page's filter panel gains an
"archive" mode (exclude / only) and a "link status" multi-select (live /
moved / rotted / error), backed by a new `data/archive-meta.json` emitted by
`Archive.hs` — the archive analogue of `epistemic-meta.json`. The collision
with the epistemic `status` filter is resolved by scoping (own state fields,
button classes, and labels), not renaming. Verified in headless Chrome.
Details in the Phase 5 Met note.

---

## Motivation

The site cites external work — papers, articles, blog posts, documentation.
Three things go wrong with a plain hyperlink over time:

1. **Link rot.** The target moves, paywalls, or vanishes. A 2019 essay's
   citations decay silently; nobody notices until a reader clicks.
2. **Content drift.** The target stays up but changes. The sentence you quoted
   is no longer the sentence at that URL.
3. **Opacity to the site's own machinery.** An external link is invisible to
   `Backlinks.hs` (`isPageLink` drops every `http(s)://` URL) and to
   `embed.py` (it indexes only `_site/**/*.html`). The site knows nothing about
   the things it most often points at. A paper cited by six essays has no page,
   no backlinks list, no place in any "Related" set.

The archive fixes all three by keeping a **local, hosted, immutable snapshot**
of each referenced work, giving it a stable URL on this domain, and making that
URL a first-class citizen of the existing backlinks and similar-pages systems.

This is deliberately *not* a general web crawler. It archives a curated set:
the things this site references. The author adds a URL to a manifest; the build
does the rest.

### Relationship to existing pieces

| Existing piece | What it does | Why the archive is different |
|----------------|--------------|------------------------------|
| `static/papers/` | Hosts Levi's **own** typeset PDFs (`preprint:`, `{{pdf:}}`) | The archive holds **third-party** works. Distinct directory, distinct purpose. Never conflate the two. |
| nginx `popup-proxy.conf` | Caches **metadata** (title/abstract) from arXiv / archive.org / PubMed for hover previews | Caches structured metadata, not documents. A preview accelerator, not preservation. |
| `Backlinks.hs` | Inverts **internal** links into a "who links here" map | Indexes site content only; external URLs are dropped. The archive makes referenced works internal enough to index. |
| `embed.py` / `SimilarLinks.hs` | Semantic "Related" block from `_site/**/*.html` embeddings | Only sees site pages. Archived works become site pages, so they enter the embedding corpus for free. |

---

## Goals

- **Preservation.** Every referenced work the author chooses to archive has a
  byte-for-byte local snapshot that survives the original going dark.
- **Stable hosting.** Each snapshot is reachable at a permanent
  `/archive/{slug}/` URL on levineuwirth.org, rendered in site chrome.
- **Hyperlink-able.** Archive URLs are ordinary internal links: usable in
  prose, wikilinks, citations, and `further-reading`.
- **Indexed.** Archived works appear in the **backlinks** ("Referenced by") and
  **similar-pages** ("Related") systems exactly as native content does — and,
  where the source structure allows, granularly by section.
- **Curated, low-friction.** Adding an archive is one line in one manifest.
  Everything else — fetch, text extraction, page generation, indexing — is
  automatic and build-time.
- **Static-friendly.** Every archive page renders at build time; JS is layered
  on, never required. Matches the rest of the site's contract.
- **Honest.** Archive pages never impersonate the original. They are framed as
  archived copies, link prominently to the source, are kept out of search
  engines, and carry a real, advertised removal channel on every page.
- **Safe by default.** No build step ever deletes or overwrites a committed
  artifact; destruction and replacement are always explicit, opt-in acts.

---

## Decisions (locked)

| Topic | Decision | Rationale |
|-------|----------|-----------|
| Trigger | Curated manifest, not auto-crawl | Archives what the site *references*, not the web. Legally and operationally sane. |
| Authored input | One hand-edited file: `archive/manifest.yaml` | One line per archived link. Mirrors `data/commonplace.yaml`'s authoring model. |
| Bibliography seeding | **Rejected** as auto-seeding. `make archive-suggest` prints a "cited but not archived" diff; the author copies lines by hand. | Keeps the manifest the *identity* of the archive, not a cache of the `.bib` files. |
| Per-entry provenance | `archive/{slug}/PROVENANCE.json`, committed — immutable for the current snapshot | An immutability claim that isn't in version control isn't immutable. |
| Mutable state | `data/archive-state.json`, gitignored — link-rot status only | Strict split: immutable facts committed, volatile status disposable. |
| Hakyll input | `data/archive-index.json` — `url` + aliases → slug, written by the tool | Minimal stable shape for the Haskell side; treated like `data/annotations.json`. |
| Missing-index behaviour | `Backlinks.hs` and `Filters/Archive.hs` silently no-op when `archive-index.json` is absent | Preserves the established `.venv`-gated silent-skip convention. The archive degrades to invisible, never to an error. |
| `fetch` idempotence | `fetch` is keyed on `(slug, url)` together; a slug whose recorded URL has changed is refused, not overwritten. `fetch` always rewrites `archive-index.json` to mirror the manifest. | A committed artifact is replaced only by an explicit `refresh`, never as a `fetch` side effect. |
| Artifact storage | `archive/{slug}/` at repo root, **committed to git** | A preservation guarantee that depends on an un-versioned store is weaker. Repo stays reproducible. |
| Per-artifact size cap | 25 MB; `archive.py fetch` warns and skips above it; `git add -f` to override deliberately | A 200 MB scan must never land in an auto-commit silently. |
| Storage migration | If `archive/` exceeds ~5 GB or doubles year-over-year, evaluate a separate archive repo / object store. **Never git LFS.** | LFS breaks `git clone → make build` reproducibility — a regression for a preservation system. |
| HTML snapshots | `monolith -j` → one self-contained HTML file; the pinned `monolith` binary is committed at `tools/bin/monolith` | Single static binary, no headless browser. Strips JS. Committing it (vs downloading) removes a network dependency and keeps the build reproducible from a bare clone. |
| PDF snapshots | Direct download via `requests` | Papers are usually clean PDF URLs (arXiv etc.). |
| Display — PDF | The raw `document.pdf` in an `<iframe>` — the browser's native PDF viewer renders it | A hyperlinked archive should display the document exactly as it is. Symmetric with the HTML snapshot (both embed the raw artifact); no PDF.js wrapper. `static/pdfjs/` stays vendored for the site's own `{{pdf:}}` embeds. |
| Display — HTML | Snapshot in a sandboxed `<iframe>` (`referrerpolicy="no-referrer"`, no `allow-scripts`) + CSP `<meta>` baked into the snapshot + extracted text in the wrapper | Sandbox isolates markup; CSP is defense-in-depth; no-referrer stops leaking the reading path; extracted text feeds indexing. |
| Snapshot quality | Recorded per entry (`ok` / `degraded` / `js-required`); degraded snapshots flagged on `/archive/` and `/build/` | `monolith` fails quietly on lazy-loaded images and SPAs; silent degradation is the enemy. |
| Index thumbnails | **Dropped for v1.** `/archive/` is a text list. | At v1 scale a text list is faster to scan and to build than a thumbnail grid; revisit past ~50 entries (it is deferred capability, not a rejected one). |
| Second archive | Submit every URL to the Wayback Machine — **non-blocking**; record the URL when it returns, backfill via `make archive-wayback` | Belt-and-suspenders, never on the critical path of a build. |
| URL scheme | `/archive/{slug}/` | Permanent, human-readable, internal. |
| URL matching | `archive-index.json` carries each entry's equivalent-URL aliases; **only tracking parameters** are stripped, other query parameters preserved; backlinks match any alias | Without it, "Referenced by" silently under-counts; blanket query stripping would over-match. |
| Homepage portal | No | Infrastructure, not a content section. Reachable from `/archive/`, `/colophon`, footer. |
| Search engines | `noindex` on every archive page | Preserving, not republishing or competing with originals. |
| `robots.txt` | Not gated: a curated single-shot fetch of an already-cited URL is not crawling. But honour `X-Robots-Tag: noarchive` and `<meta name="robots" content="noarchive">`; skip anything behind authentication. | Matches Save-Page-Now / reference-manager norms. The load-bearing ethic is the removal channel, not `robots.txt`. |
| Removal channel | A request to `ln@levineuwirth.org` is honoured; advertised on `/archive/`, on **every archive page**, and in the fetcher's User-Agent string | This is the real ethical commitment `robots.txt` only proxies for. |
| Pagefind | Archived full text is indexed, tagged by `type: archive` and by link-rot `status` | Searching everything you've cited is a feature; the tags let results be filtered or excluded. |
| Visibility levels | `public` (default) / `private` | `private` keeps the artifact in-repo but undeployed, for content not safe to redistribute. |
| Paywalled originals | A manual `paywalled: true` manifest flag — **not** an automated scanner state. Soft paywalls return `200` and cannot be reliably detected. | Drives a banner note only, never a link flip. |
| Eviction | Opt-in `make archive-gc`, **never part of `make build`**. Procedure: record in `removed.yaml` *first*, then drop the manifest line, then GC. GC deletes only slugs listed in `removed.yaml`. | A rename, branch-switch, or typo'd manifest edit must not silently eat committed artifacts. |
| Snapshot mutability | Immutable for the current snapshot; `archive.py refresh` deliberately replaces it | A stable citation target must not move under readers — except by an explicit act. |
| Rot hysteresis | Asymmetric: `rotted` requires 3 consecutive failed scans over ≥ 14 days; one failure is `error`. Recovery is immediate — a single success → `live`. | A transient failure must not flip a live citation; a recovered original should be reached eagerly, so un-rotting needs no delay. |
| SHA verification | Both `archive.py fetch` *and* `build/Archive.hs` re-hash every committed artifact against `PROVENANCE.json` and halt non-zero on a mismatch. `archive.py` runs first in `make build`; `Archive.hs` shells out to `sha256sum` from `loadArchiveEntries`, so the integrity guarantee holds even when `archive.py` did not run (no `.venv`, a direct `cabal run site -- build`, or a deploy host that bypasses `make build`). | The original "Python tool is the sufficient enforcement point" assumption was unsafe: the Python step is `.venv`-gated, and a contributor or deploy without it could publish a tampered artifact unchecked. Two enforcement points cost a `sha256sum` call per entry and close the hole. |

---

## Content model & directory structure

```
archive/
├── manifest.yaml                       # AUTHORED — the curated list of links
├── removed.yaml                        # AUTHORED — record of evicted entries
├── arxiv-2403-12345/
│   ├── document.pdf                    # the snapshot (committed)
│   ├── PROVENANCE.json                 # immutable archival facts (committed)
│   ├── document.txt                    # extracted text (gitignored, regenerated)
│   └── document.txt.sha256             # artifact SHA the .txt was built from (gitignored)
├── gwern-net-scaling-hypothesis/
│   ├── snapshot.html                   # self-contained monolith snapshot (committed)
│   ├── PROVENANCE.json                 # immutable archival facts (committed)
│   ├── snapshot.txt                    # extracted readable text (gitignored)
│   └── snapshot.txt.sha256             # artifact SHA the .txt was built from (gitignored)
└── ...
```

- `archive/` is a top-level directory, sibling to `content/`, `static/`, and
  `data/` — **not** under `content/`. Files in `content/` are author-written
  Markdown processed by Pandoc; `archive/` holds raw third-party artifacts plus
  the manifest and provenance.
- One directory per entry, keyed by **slug**.
- Committed: the artifact (`document.pdf` / `snapshot.html`) — the preservation
  payload — and `PROVENANCE.json` — the immutable record of the archival event.
- Gitignored: the regenerable extracted text (`*.txt`) and its staleness stamp
  (`*.txt.sha256`) — deterministic from the committed artifact, so committing
  them is pure churn. This mirrors the photography sidecar and `*.webp`
  companion rules already in `.gitignore`.
- `make build`'s auto-commit stages `content/` **only**. Changes under
  `archive/` (new artifacts, `PROVENANCE.json`, manifest edits) are committed
  **deliberately by the author**. This is a feature, not a gap: it is the
  eyeball-before-commit checkpoint where a degraded snapshot gets caught.

### Authored input — `archive/manifest.yaml`

The **only** file the author edits for normal operation. Adding an archive =
adding one list item. Minimum is a bare `url:`; everything else is optional or
auto-derived.

```yaml
# archive/manifest.yaml — curated list of works to preserve.
# Edited by hand. Tools never write to this file.
# Per-artifact cap: 25 MB. Above that, archive.py warns and skips the fetch;
# commit an oversize artifact deliberately with `git add -f`.
# To evict an entry, see archive/removed.yaml — record there FIRST, then
# delete the line here, then run `make archive-gc`.

- url: "https://arxiv.org/abs/2403.12345"
  # slug:  auto-derived → arxiv-2403-12345  (override only to disambiguate)
  # title: auto-derived from the artifact / popup-proxy metadata
  # type:  auto-detected (pdf | html)
  aliases:                         # optional — equivalent URLs that URL
    - "https://doi.org/10.48550/arXiv.2403.12345"  # normalisation cannot derive
  tags: [research/ml]              # optional — same slash-hierarchy as content
  note: >                          # optional — why this is referenced
    Cited in the scaling-laws essay; section 4 is the load-bearing part.

- url: "https://www.gwern.net/Scaling-hypothesis"
  type: html                       # optional override when detection is wrong
  visibility: public               # public (default) | private

- url: "https://example.com/paywalled-report"
  paywalled: true                  # author-set; the original sits behind a paywall
  visibility: private              # archived for the author; artifact not deployed
```

| Field | Required | Notes |
|-------|----------|-------|
| `url` | yes | The original URL. The identity of the entry. |
| `slug` | no | Override the auto-derived slug. Must be unique. |
| `title` | no | Override the auto-derived title. |
| `type` | no | `pdf` \| `html`. Auto-detected from `Content-Type` / extension. |
| `aliases` | no | Equivalent URLs of the same work that normalisation cannot derive — above all a DOI form vs. the landing URL it resolves to. Matching metadata, not identity: edit freely, no `refresh` needed. Each must be unique across the manifest and absent from `removed.yaml`; both `archive.py` and the direct-build validator enforce this. |
| `tags` | no | Slash-hierarchy tags (`Tags.hs`). Place the work on tag indexes. |
| `note` | no | Author's reason for archiving; shown on the archive page. |
| `visibility` | no | `public` (default) or `private`. |
| `paywalled` | no | Author-set flag: the original is gated. Declared, not inferred — no reliable automated detection exists. Drives a banner note only. |
| `source-date` | no | Publication date of the original, if known. |

### Per-entry provenance — `archive/{slug}/PROVENANCE.json`

Committed alongside the artifact. Written by `tools/archive.py fetch` and then
stable for the lifetime of that snapshot — `wayback` is the one field backfilled
later (by `make archive-wayback`).

**"Immutable" means immutable for the *current* snapshot, not forever.**
`archive.py refresh` deliberately re-snapshots an entry and **replaces** both
the artifact and its `PROVENANCE.json` (new `sha256`, new `archived` date),
moving the old `sha256` into `previous-sha256`. A refresh is a conscious act;
absent one, the file does not change.

`PROVENANCE.json` holds the facts that make the archival claim verifiable:
`tools/archive.py fetch` re-hashes every present artifact against the recorded
`sha256` on every run — *before* the Hakyll build — and **exits non-zero on a
mismatch, halting `make build`**. The verification lives in the Python tool,
not `Archive.hs`: the Haskell toolchain carries no SHA-256 library, and
`archive.py` runs first in the pipeline regardless. `Archive.hs` trusts a
present (provenance, artifact) pair and skips any entry lacking either.

```json
{
  "url": "https://arxiv.org/abs/2403.12345",
  "slug": "arxiv-2403-12345",
  "title": "Scaling Laws for Neural Language Models",
  "type": "pdf",
  "artifact": "document.pdf",
  "sha256": "9f86d0818884...",
  "previous-sha256": null,
  "bytes": 2317004,
  "archived": "2026-05-21",
  "source-date": "2024-03-15",
  "snapshot-quality": "ok",
  "wayback": "https://web.archive.org/web/20260521.../https://arxiv.org/abs/2403.12345"
}
```

`previous-sha256` is `null` on first fetch and set by `refresh` to the
immediately-prior snapshot's hash, so the last prior snapshot is reachable
(via `git log -S`) without deeper archaeology. `PROVENANCE.json` lives **with
the artifact**, not in a rolling global file, so the immutable claim is
genuinely immutable in git history.

One optional field: `fetched-from`, present only when the original was
already dead at first fetch and the snapshot's bytes came from a Wayback
capture instead (see Wayback Machine — non-blocking). It holds the exact raw
(`id_`) capture URL that was fetched; its absence means a first-hand fetch
from the original.

### Mutable state — `data/archive-state.json`

Written **only** by `tools/archive.py check`. Holds the volatile link-rot
status, keyed by URL. Gitignored (`data/` generated files already are); a fresh
clone simply rebuilds it on the next scan. Until a scan has run, every entry
renders as the safe default (`live`, no link flip).

```json
{
  "https://arxiv.org/abs/2403.12345": {
    "status": "live",
    "checked": "2026-05-21",
    "consecutive-failures": 0,
    "status-since": "2026-05-21"
  }
}
```

`status` ∈ `live` / `moved` / `rotted` / `error` — set by the scanner.
(`paywalled` is *not* here: it is a manual manifest flag, not a scanner state.)
`consecutive-failures` + `status-since` implement the rot hysteresis (Phase 5).

### Hakyll input — `data/archive-index.json`

A small map written by `tools/archive.py fetch`, consumed inside the Hakyll
build by `Backlinks.hs` and the link-annotation filter. **`fetch` always
rewrites this file to mirror the current manifest exactly** — whether or not any
network I/O occurred — so an entry un-listed from the manifest (even without a
GC) immediately stops being treated as archived, and `Backlinks.hs` never keeps
writing backlinks toward a slug whose page no longer exists. The index is cheap
to recompute (manifest + provenance, no network) and must never lag the
manifest. Kept separate from `archive-state.json` so the Haskell side loads a
minimal, stable shape; treated exactly like the existing `data/annotations.json`
build input.

```json
{
  "https://arxiv.org/abs/2403.12345": {
    "slug": "arxiv-2403-12345",
    "type": "pdf",
    "title": "Scaling Laws for Neural Language Models",
    "aliases": [
      "http://arxiv.org/abs/2403.12345",
      "https://arxiv.org/abs/2403.12345v1",
      "https://arxiv.org/abs/2403.12345v2",
      "https://arxiv.org/pdf/2403.12345",
      "https://arxiv.org/pdf/2403.12345.pdf"
    ]
  }
}
```

`aliases` is the equivalent-URL set (see URL matching, under Backlinks). The
Haskell side flattens it into an `alias → entry` lookup on load.

**When `archive-index.json` is absent** — `.venv` not set up, or `archive.py`
has never run — it is treated as empty: `Backlinks.hs` and `Filters/Archive.hs`
silently no-op, and the build succeeds unchanged. This is the same
`.venv`-gated silent-skip convention used by `embed.py` and the photography
extractors. (This exact phrasing recurs below; it is the canonical statement of
the property.)

### Eviction & removal

Removing an archived work is a first-class, supported operation — a takedown
request, an author request, a legal concern, or a quality cull will arrive, and
probably before the system is mature. The cardinal rule: **no build step ever
deletes a committed artifact.** Deletion is opt-in and explicit.

Procedure (documented in the `manifest.yaml` header comment), in order:

1. **Record the removal in `archive/removed.yaml` first** — before touching the
   manifest:

   ```yaml
   - url: "https://example.com/withdrawn-article"
     slug: example-com-withdrawn-article
     removed: 2026-06-01
     reason: takedown        # takedown | author-request | legal | quality
     note: "DMCA from X; see archived email."
   ```

   | Field | Required | Notes |
   |-------|----------|-------|
   | `url` | yes | The original URL (matches the manifest URL at time of removal) |
   | `slug` | yes | The slug whose `archive/{slug}/` directory `make archive-gc` is authorized to delete |
   | `removed` | yes | ISO date of removal |
   | `reason` | yes | Closed enum: `takedown` \| `author-request` \| `legal` \| `quality` |
   | `note` | no | Free-text context |

2. Delete the entry's line from `manifest.yaml`.
3. Run `make archive-gc` (opt-in; **never** invoked by `make build`). It deletes
   only `archive/{slug}/` directories whose slug is recorded in `removed.yaml`.
   A directory orphaned by a rename, a branch switch, or a typo'd manifest edit
   — i.e. *not* in `removed.yaml` — is **never deleted**; it is reported to
   stderr with its slug and a one-line hint, and `gc` exits non-zero while any
   orphan is present (`--ignore-orphans` suppresses the non-zero exit once the
   author has consciously reviewed them). The author commits the deletion.

An orphaned `archive/{slug}/` directory (manifest line gone, not yet GC'd) is
inert in the meantime: `Archive.hs` generates pages and routes artifacts only
for current `manifest.yaml` entries, so an orphan produces no page and is not
deployed.

`removed.yaml` is **not** a hostile-tracking list. It exists so that (a)
`make archive-gc` knows exactly what is safe to delete, (b) re-adding a removed
URL to the manifest is surfaced loudly at build time, (c) the link-rot scanner
skips removed entries instead of probing them forever, and (d) `make
archive-suggest` never re-suggests a deliberately-removed work. A removed URL
still cited from a site page falls back to the original-only link: no archive
affordance, no backlink canonicalization.

---

## Routing & generated pages

| URL | Source | Notes |
|-----|--------|-------|
| `/archive/` | Generated from `manifest.yaml` | Index of all archived works; text list, filter by type, tag, status |
| `/archive/{slug}/` | Generated per manifest entry | The archive page — wrapper chrome + embedded snapshot |
| `/archive/{slug}/document.pdf` | `archive/{slug}/document.pdf` | Raw artifact, copied through unchanged |
| `/archive/{slug}/snapshot.html` | `archive/{slug}/snapshot.html` | Raw HTML snapshot, copied through unchanged |
| `/archive/{tag}/` | Existing `Tags.hs` | Archive entries with tags join the normal tag indexes |

`PROVENANCE.json` is build input, not a routed page — it is consumed by
`Archive.hs`, not served (the archive page surfaces the relevant fields).

Slugs are auto-derived as `{domain-stem}-{path-slug}`, truncated, with a short
hash appended on collision (`arxiv-2403-12345`, `gwern-net-scaling-hypothesis`).
`slug:` in the manifest overrides.

`/archive/` is **not** a homepage portal — it is infrastructure. It is reachable
from `/colophon` (where the site explains its own machinery), from the footer's
infrastructure links, and optionally as a shelf on `/library.html`. The
`/archive/` page also carries the removal-request notice.

---

## The archive page

`/archive/{slug}/` is a **wrapper**: site chrome around a preserved artifact.
Top to bottom:

1. **Archive banner.** An unmissable strip: "Archived copy — snapshot taken
   2026-05-21. View the original ↗". The original URL is the most prominent
   link on the page. The page never pretends to be the source.
2. **Metadata block.** Title, original URL, archive date, source publication
   date, content hash (short form), file size, snapshot quality, the author's
   `note`, the Wayback Machine link, and current link-rot `status`.
3. **The artifact.**
   - **PDF** — the raw `document.pdf` embedded in an `<iframe>`, rendered by
     the browser's native PDF viewer. Deliberately *not* the site's PDF.js
     viewer: a hyperlinked archive should display the document as it is.
   - **HTML** — the `monolith` snapshot loaded in a sandboxed `<iframe>`:
     `sandbox` without `allow-scripts` (JS already stripped at fetch time) and
     `referrerpolicy="no-referrer"` (so a click inside the snapshot does not
     leak `levineuwirth.org/archive/...` — and which essay the reader came
     from — to the original site). The snapshot file itself carries a
     restrictive `Content-Security-Policy` `<meta>` tag, injected at fetch time,
     as defense-in-depth (see Fetch pipeline).
4. **Full text.** The extracted readable text (`document.txt` / `snapshot.txt`)
   rendered into the DOM — collapsed in a `<details>` for PDFs, inline for HTML.
   This block is the load-bearing one for indexing: `embed.py` and Pagefind see
   text, not an opaque iframe. It also gives readers a fast, styled, dark-mode
   reading path that does not depend on the original's markup.
5. **Referenced by.** The backlinks list — every site page that cites this work.
   (See Backlinks integration.)
6. **Related.** The similar-pages list — semantically near content, site pages
   and other archives alike. (See Similar-pages integration.)

A removal-request line — the `partials/archive-removal-notice.html` partial,
carrying `ln@levineuwirth.org` — is included on **every** archive page and on
`/archive/`. It is its own partial, included directly by `archive.html` and
`archive-index.html`; the site-wide `page-footer.html` is *not* touched.

The page carries `<meta name="robots" content="noindex">`. The `head.html`
partial currently has no robots hook; adding a `noindex` context flag is part
of Phase 1.

---

## Fetch & snapshot pipeline

`tools/archive.py` — a Python tool, gated on `.venv`, silent-skip when absent,
matching the established `embed.py` / `extract-exif.py` pattern. Subcommands:

- `archive.py fetch` — for every manifest URL without an artifact: download it,
  detect the type, store it, extract text, write `PROVENANCE.json`. Always
  rewrites `archive-index.json` to mirror the manifest (see below). Records
  `wayback: null` (filled in later). Incremental — only URLs without an
  artifact incur network I/O.
- `archive.py wayback` — submit URLs whose `PROVENANCE.json` has `wayback: null`
  to the Wayback Machine; backfill the returned URL. (`make archive-wayback`)
- `archive.py check` — the link-rot scan. (`make archive-check`, Phase 5)
- `archive.py suggest` — scan `data/*.bib` for `url` and `doi` fields; a
  DOI-only entry is resolved to its `https://doi.org/{doi}` form. Prints a diff
  of works cited but not yet in `manifest.yaml`, **excluding any URL already in
  `archive/removed.yaml`** — a deliberately-removed work is never re-suggested.
  (`make archive-suggest`)
- `archive.py gc` — delete `archive/{slug}/` directories whose slug is recorded
  in `removed.yaml`. Orphan directories (not in `manifest.yaml`, not in
  `removed.yaml`) are never deleted: each is reported to stderr with its slug
  and a one-line hint, and `gc` exits non-zero while any orphan is present
  (`--ignore-orphans` to override). (`make archive-gc`)
- `archive.py refresh {slug}` — deliberately re-snapshot one entry, replacing
  both the artifact and its `PROVENANCE.json`; the prior `sha256` is written to
  `previous-sha256` and printed.

### `fetch` is keyed on `(slug, url)` together

If a slug's directory already exists and its `PROVENANCE.json` records a
*different* URL than the manifest now gives — the author edited a URL but kept
the slug — `fetch` **refuses to overwrite** the committed artifact. It prints
`URL changed for {slug}: run 'archive.py refresh {slug}' to re-snapshot` and
leaves the entry untouched. Overwriting a committed artifact is always an
explicit act (`refresh`), never a side effect of `fetch` — the same principle
as GC requiring `removed.yaml`.

Regardless of whether any artifact was fetched, `fetch` finishes by rewriting
`data/archive-index.json` from the current manifest + provenance, so the index
can never lag a manifest edit.

### PDF

Direct download via `requests`, with a per-request timeout and the size cap
(25 MB; warn + skip above). User-Agent:
`levineuwirth.org/archive (ln@levineuwirth.org; removal requests honored)`.
Stored as `document.pdf`; text extracted with `pdftotext`.

### HTML

`monolith -j {url}` produces a single self-contained HTML file: CSS, images,
and fonts inlined as data URIs, JavaScript stripped (`-j`).

`monolith` is a single static Rust binary — no headless browser. Unlike Leaflet
and PDF.js (servable assets fetched at build time and gitignored), `monolith` is
a build-time **executable**: the pinned linux-x86_64 binary is **committed** at
`tools/bin/monolith`, with its version and sha256 recorded in
`tools/monolith-version.txt`. Committing it removes a network dependency from
`make build` and keeps the archive pipeline reproducible from a bare clone.
(If the build host ever changes architecture, re-vendor the matching binary.)

After capture, `archive.py` injects a CSP `<meta>` into the snapshot's `<head>`:

```html
<meta http-equiv="Content-Security-Policy"
      content="default-src 'none'; img-src data:;
               style-src 'unsafe-inline'; style-src-elem 'unsafe-inline';
               style-src-attr 'unsafe-inline'; font-src data:;
               script-src 'none'; object-src 'none'; frame-src 'none'">
```

`monolith` inlines images and fonts as data URIs, and inlines styles both as
`<style>` elements *and* as inline `style=""` attributes — so `style-src-elem`
and `style-src-attr` are spelled out alongside `style-src` to cover both in
browsers that honour the granular directives. `script-src 'none'` /
`object-src 'none'` / `frame-src 'none'` are explicit because `monolith` inlines
SVGs as `data:` images, and an SVG can carry a `<script>` block — the iframe
sandbox already blocks execution, but a belt-and-suspenders claim should not
rely on the sandbox alone. This CSP permits everything a correct snapshot needs
and blocks every network fetch and script a broken or malicious snapshot might
attempt. Correct rendering under this CSP is verified cross-browser as a
Phase 2 exit criterion. (An nginx `location ^~ /archive/` block may add the
header at the HTTP level too; the baked-in `<meta>` is what makes `make dev`'s
plain server safe.)

**`monolith` failure modes** — capture is not always faithful, and fails
*quietly*. Known cases: lazy-loaded images using `data-src` (common on Substack,
Medium, modern blogs) are not resolved — the snapshot looks complete but is
missing images; soft-paywalled pages (Medium, NYT) often serve full article
HTML to the fetch and gate it with a client-side overlay, so `-j` yields a
snapshot that *looks* like unauthorized access (it is not — the server sent it
— but the optics are poor); `<picture>`/`srcset` sources are inconsistently
inlined. `archive.py` therefore classifies each capture and records
`snapshot-quality` ∈ `ok` / `degraded` / `js-required` in `PROVENANCE.json`;
degraded captures are flagged on `/archive/` and `/build/`. The author reviews
the rendered snapshot before committing `archive/` (Phase 2 exit criterion). A
headless-browser fallback for `js-required` pages is deferred — see Open
questions.

### Wayback Machine — non-blocking

Wayback submission is **never on the critical path of a build.** `archive.py
fetch` records `wayback: null` and moves on. `make archive-wayback` runs
separately, POSTs the outstanding URLs to `https://web.archive.org/save/`
(retrying transient 5xx, tolerating rate limits and hangs), and backfills the
returned timestamped URL into each `PROVENANCE.json`. This second, independent
copy means a rotted entry whose local artifact is somehow lost still has a
fallback. If the original is *already* dead at first fetch, `archive.py fetch`
pulls the most recent existing Wayback capture instead (implemented
2026-06-10):

- **Dead means dead** — the fallback fires only when the document itself
  could not be retrieved (DNS failure, refused connection, timeout, HTTP
  error). A `noarchive` refusal, the size cap, or a local/tooling failure
  never falls through to a third-party copy.
- **Raw bytes via `id_`** — the capture is fetched in its
  `…/web/{timestamp}id_/{url}` form, which replays the original response
  bytes without the Wayback toolbar or link rewriting; the normal pipeline
  (size cap, CSP + noindex injection, quality classification) applies.
- **Preserved directives are honoured** — Wayback replays the original's
  response headers as `X-Archive-Orig-*`; a capture whose
  `X-Archive-Orig-X-Robots-Tag` carries `noarchive` is refused, since the
  dead original can no longer be asked directly.
- **Honest provenance** — `PROVENANCE.json` gains an optional
  `fetched-from` field holding the exact raw capture URL, so the record
  never implies a first-hand fetch that did not happen; `wayback` is set
  to the capture immediately (so `archive-wayback` correctly skips the
  entry — a dead URL cannot be re-submitted).
- **Lookup only** — the fallback queries the availability API; it never
  creates third-party state. Note the API has blind spots (it reports no
  capture for some URLs that arguably have one, e.g. certain large PDFs);
  a "no capture" skip is retried on the next build like any other skip.
- **Never during `refresh`** — a deliberate re-snapshot of a dead original
  fails and restores the prior first-hand snapshot rather than silently
  downgrading it to third-party bytes.

### Politeness & safety

The manifest is author-controlled, so SSRF is not a real threat, but the tool
still: sets per-request timeouts, enforces the 25 MB cap, rate-limits to one
request per host at a time, and identifies itself honestly. Beyond that:

- **Honour `X-Robots-Tag: noarchive`** — and the equivalent
  `<meta name="robots" content="noarchive">` in an HTML response body (cheap to
  check: it is in the head of the document just fetched). If either is present,
  the fetch is abandoned and the manifest entry flagged. This is the directive
  that actually governs *archiving* (as opposed to crawling); respecting it
  costs nothing and makes the posture defensible.
- **Skip authenticated content.** `archive.py` never sends cookies or
  credentials. If a URL needs authentication, it is not archived; at most it is
  a manual `visibility: private` artifact.
- **`robots.txt` is not gated.** A curated, single-shot, attributed, `noindex`'d
  fetch of a URL the site already cites is not crawling — it is the same
  operation a reader's browser performs on click. This matches Save-Page-Now
  and reference-manager norms. The load-bearing ethical commitment is the
  removal channel, advertised on `/archive/`, on every archive page, and inside
  the User-Agent string.

---

## Text extraction & indexing

The "Full text" block is what makes an archived work *indexable* rather than an
opaque blob. Extraction:

- **PDF** → `pdftotext` (from `poppler`, already a build dependency for the
  `pdf-thumbs` Makefile target). Stored as `document.txt`.
- **HTML** → readable text pulled from the `monolith` snapshot with
  `BeautifulSoup` (already a dependency of `embed.py`). Headings are preserved.
  Stored as `snapshot.txt`.

Both `.txt` files are gitignored. `archive.py fetch` regenerates a `.txt`
whenever the artifact's current SHA-256 differs from the value stamped in the
adjacent `*.txt.sha256` sidecar (also gitignored), then re-stamps it. This
catches every way the committed artifact and the local — gitignored, not
`git pull`-ed — text could drift apart: a `refresh`, a `pdftotext` upgrade, a
truncated file. The indexed text is thus always in sync with the embedded
artifact.

Once the archive page renders this text into `_site/archive/{slug}/index.html`:

- **`embed.py`** walks `_site/**/*.html` *after* the Hakyll build. Archive pages
  are ordinary HTML files in that tree, so they are embedded with **no change to
  `embed.py`** — they automatically join both the page-level similarity corpus
  (`similar-links.json`) and the paragraph-level semantic index
  (`semantic-index.bin` / `semantic-meta.json`).
- **Pagefind** likewise indexes them automatically. Two filter tags on the
  archive template — `type: archive` and the link-rot `status` — let
  `search-filters.js` separate archive hits from native content and let a reader
  see (or exclude) `rotted`-citation archive pages.

The one requirement this imposes: the archived text **must** be in the rendered
DOM, not only inside the PDF.js / sandbox iframe. `embed.py`'s `BeautifulSoup`
pass and Pagefind both see DOM text only. Hence the "Full text" block in §4 of
the archive page is non-optional.

---

## Backlinks integration — "Referenced by"

The goal: an archived paper's page shows every site page that cites it.

Today `Backlinks.hs` runs in two passes (see its module header). Pass 1
(`version "links"`) extracts links per content file; `isPageLink` **drops every
external URL**. Pass 2 inverts `target → [sources]`. The archive needs two
surgical changes, both driven by `data/archive-index.json`:

1. **Pass 1 — keep archived externals.** `isPageLink` is widened: an external
   URL is *kept* if it matches an entry in `archive-index.json`. Non-archived
   externals are still dropped, exactly as now.
2. **Pass 2 — canonicalize to the archive URL.** When inverting, an archived
   external URL is rewritten to its `/archive/{slug}/` key.

`backlinksField` then works unchanged: the archive page looks up its own route
and finds its citing pages. The archive template labels the section
**"Referenced by"** rather than "Backlinks" — semantically truer for a
third-party work — but the underlying field is the same.

This is purely additive: the *visible* link in the essay still points at the
original URL (reader expectation is preserved); only the backlink *relationship*
is recorded against the archive page. Archive pages do not need to be added to
`Patterns.allContent` — they only *receive* backlinks, and that needs a route,
not a `version "links"` pass.

**When `archive-index.json` is absent** — `.venv` not set up, or `archive.py`
has never run — it is treated as empty: `Backlinks.hs` and `Filters/Archive.hs`
silently no-op, and the build succeeds unchanged. For `Backlinks.hs` that means
every external URL is dropped exactly as today, with no canonicalization and no
error. This is a hard requirement, not a nicety: it preserves the established
`.venv`-gated silent-skip convention so a contributor without the Python
environment still gets a clean build.

### URL matching — the alias problem

A cited URL in the wild has many equivalent forms: `http://` vs `https://`,
trailing slash or not, `?utm_source=…` query junk, arXiv `abs` ↔ `pdf` ↔
versioned (`/abs/2403.12345`, `/abs/2403.12345v2`, `/pdf/2403.12345.pdf`). If
the index is keyed only by the manifest's canonical URL, a citation to any
variant misses, and **"Referenced by" silently under-counts** — a failure that
breaks nothing visibly and is miserable to debug.

So `archive.py` computes the equivalent-URL set per entry and stores it as
`aliases` in `archive-index.json`. The normalization is deliberately narrow:

- **Tracking parameters are stripped** — `utm_*`, `fbclid`, `gclid`, `mc_*`,
  `ref`, `igshid`, `_hsenc`, `_hsmi`, `mkt_tok`.
- **All other query parameters are preserved.** A `?v=…`, a `?id=…`, a Wayback
  timestamp is load-bearing; blanket query stripping would alias
  `…/article?id=42` to every other article on the host.
- `http`/`https` are folded, trailing slashes normalized, and known arXiv
  families (`abs` / `pdf` / versioned) expanded.

`Backlinks.hs` matches an incoming link against any alias before keying it to
the archive URL.

Forms that no offline normalisation can derive — above all a **DOI vs. the
landing URL it resolves to** — are *authored*: the manifest's `aliases:` field
lists equivalent URLs per entry. Authored aliases join the entry's alias set
in `archive-index.json` (each with its own generated expansions, so a DOI
alias's `http://` form matches like the canonical's would), they count as
"covered" in `archive.py suggest`, and they are validated like canonical URLs:
unique across the manifest and absent from `removed.yaml`, enforced by both
the `archive.py fetch` pre-scan and `Archive.hs`'s direct-build validator.

### Granular backlinks (Phase 4 refinement)

If a citation targets a fragment — `…/abs/2403.12345#section-4`, or a PDF page
`…/document.pdf#page=7` — the fragment is preserved through pass 2 instead of
being stripped by `normaliseUrl`. The archive page can then group "Referenced
by" entries by which section/page they cite: *"Section 4 — referenced by [Essay
A], [Essay B]."* This is the "indexed granularly, by section" behaviour, on the
backlinks side.

---

## Similar-pages integration — "Related"

This side is almost free. `embed.py` produces `data/similar-links.json` (page
similarity) from every file in `_site/`. Once archive pages render with their
full text (above), they are in the corpus:

- An **essay's** "Related" block can surface an archived paper.
- An **archive page's** "Related" block surfaces neighbouring archives and the
  site content nearest to it.

`SimilarLinks.hs` needs no change — `/archive/{slug}/` is just another URL key,
and `similarLinksField` resolves it like any page. Two small `embed.py` config
nudges: add `/archive/` to `EXCLUDE_URLS` (the index is a list page and would
otherwise dominate neighbours), and let individual archive pages through.

**Cost — a Phase 4 risk with a concrete trigger.** `embed.py` has a coarse
whole-run staleness skip but no per-document incrementality: when it *does* run,
it re-embeds the entire corpus. A serious archive (hundreds of entries, several
MB of extracted text each for long papers) materially extends every run that
executes. Phase 4 measures this and applies a fixed trigger: **once the archive
passes 50 entries, or `embed.py`'s runtime exceeds 60 seconds, add a
per-document embedding cache** keyed by content hash to `embed.py`. Below both
thresholds, the full-corpus re-embed is left alone — premature optimization
otherwise.

### Granular similar-pages (deferred)

`embed.py` *already* builds a **paragraph-level** index
(`semantic-index.bin` + `semantic-meta.json`, keyed `{url, title, heading,
excerpt}`). An archived HTML snapshot's preserved headings mean its sections get
distinct paragraph vectors automatically — the data for section-granular
"Related" exists the moment archive text is in the DOM. What does *not* yet
exist is a UI that consumes it per-section, for *any* content type. A
per-section "Related" block is deferred site-wide; the archive system *feeds*
the granular index regardless. For PDFs, section structure is unreliable
(`pdftotext` flattens it); per-*page* chunking is the realistic granularity —
see Open questions.

---

## Link annotation in content

When the author writes a link to a URL that is archived, the build appends a
small archive affordance — a superscript "[A]" / "archived" marker next to the
link — pointing at `/archive/{slug}/`. No per-link markup; entirely automatic.

Implementation: a Pandoc filter, `Filters/Archive.hs`, registered in
`Filters.hs`. For every `Link` whose URL matches `archive-index.json` (alias
set included), it appends the affordance inline.

**Filter ordering — pinned, then verified.** Per `/colophon`, the site's AST
chain is `markdown → pandoc → citations → wikilinks → preprocessing → sidenotes
→ smallcaps/dropcaps → links → images → math`. `Filters/Archive.hs` is pinned
**immediately after `smallcaps/dropcaps` and immediately before `links`** — not
merely "somewhere before `links`". The reason is the narrower window matters:
`smallcaps/dropcaps` rewrites the *text content* of nodes, so if `Archive.hs`
decorated first, the `[A]` affordance could be swept into a smallcaps run or
mistaken for an opening character by dropcap logic. Running it after
`smallcaps/dropcaps` appends the affordance to already-styled text that nothing
downstream re-touches; running it before `links` lets the link-decoration pass
(and any future popup hooks) act on the already-annotated tree. This chain is
transcribed from a published page; **Phase 3 confirms it against `Filters.hs`'s
actual registration order** before the position is pinned in code — a doc and
the implementation can drift.

**Confirmed (2026-05-22).** `Filters.hs`'s `applyAll` applies, innermost
first: `Images → SourceRefs → Code → Math → Dropcaps → Smallcaps → Links →
Typography → Sidenotes → Aftermatter`. The `/colophon` narrative is a loose
paraphrase — `Images` and `Math` run early, `Sidenotes` runs late — but
`Smallcaps` and `Links` *are* adjacent, so `Filters.Archive` is pinned between
them, exactly as specified above. (`/colophon` is prose, not authoritative for
filter order, and was left unchanged.)

**When `archive-index.json` is absent** — `.venv` not set up, or `archive.py`
has never run — it is treated as empty: `Backlinks.hs` and `Filters/Archive.hs`
silently no-op, and the build succeeds unchanged. For `Filters/Archive.hs` that
means every `Link` passes through un-annotated, no error raised.

**Bibliography — confirmed (2026-05-22): a separate context field.**
`Citations.hs` runs `applyCitations` *before* the `applyAll` filter chain; it
partitions the citeproc `refs` Div out of the document AST
(`extractBibliography`) and renders it to an HTML string via `writeHtml5String`
for the template's `$bibliography$` field. The body filter chain — and so
`Filters.Archive` — never sees the bibliography. Prose links get affordances;
bibliography reference links do not.

This does **not** put the broken popup layer on the critical path, as the
draft feared. `Citations.hs` already performs AST surgery on each bibliography
entry (`enhanceEntry` — it wraps `file:` PDF links and appends keyword strips),
so the realistic annotation hook is `enhanceEntry`, reusing `Filters.Archive`'s
index lookup — no popup dependency. That was **deferred to a Phase 3
follow-up** pending a check that `chicago-notes.csl` renders a cited work's
`url`/`doi` as a `Link` node (a CSL style that omits URLs would leave nothing
to match). A future popup rewrite may *also* consult `archive-index.json`, but
the archive system depends on neither the current nor a future popup
implementation.

**Implemented (2026-06-10).** The CSL-URL check passed empirically: citeproc
with `chicago-notes.csl` renders entry URLs as real `Link` inlines.
`Filters.Archive` now exports `annotateBlock` — the same annotation pass
(affordance when live, primary-link flip when `rotted`), minus the header
protection bibliography entries don't need — and `Citations.hs` composes it
after `enhanceEntry` at both rendering sites: essay bibliographies
(`renderBibDiv`) and the synthetic `/bibliography/` pages
(`renderBibliographyHtml`). It runs *after* `enhanceEntry` so the PDF-link
title wrap sees the entry's original inline shape. Verified on the rendered
SIMD essay: the FIPS 203 entry (cited via its DOI — resolved through the
manifest `aliases:` field) and the `cr.yp.to/aes-speed.html` entry both carry
the affordance, correctly relativized.

---

## Link-rot detection & maintenance (Phase 5)

`tools/archive.py check` issues a `HEAD` (falling back to a ranged `GET`) to
every original URL in the manifest and updates `data/archive-state.json`.

**Offline guard (canary).** Before probing any target, `check` probes
`https://levineuwirth.org/` itself. If the canary is unreachable, the machine
is offline (or DNS is down) and no probe result would be evidence about the
*targets* — the scan is declared inconclusive, the state file is left
untouched, and the run exits 0. Without this, an unattended scheduled scan on
a machine left offline would record a `fail` against every entry, and three
such scans spanning two weeks would flip the entire archive to `rotted` at
once. An empty manifest skips the canary too: no network I/O at all.

**Hysteresis is asymmetric.** Rotting is slow; recovery is fast.

- *Rotting.* A failed probe increments `consecutive-failures` and sets
  `status: error`. Only after **3 consecutive failed scans spanning ≥ 14 days**
  does the status become `rotted`. A single transient failure — a Cloudflare
  challenge, a temporary 5xx, a DNS hiccup — therefore never flips a live
  citation.
- *Recovery.* A **single** successful probe resets `consecutive-failures` to 0
  and returns the status straight to `live`, from `error` or `rotted` alike.
  There is no cost to un-rotting eagerly — if the original is reachable again,
  the reader should go there — so recovery needs no hysteresis.

| `status` | Meaning | Rendering effect |
|----------|---------|------------------|
| `live` | Original reachable, unchanged | Normal: link to original, archive as backup |
| `moved` | 3xx to a new location | Banner notes the move; new URL recorded |
| `rotted` | Failed the hysteresis threshold (3 fails / ≥14 days) | Build flips the *primary* link to the archive copy; original shown struck-through as "(dead link)" |
| `error` | Transient / inconclusive — below the hysteresis threshold | No rendering change; retried next scan |

`paywalled` is deliberately **absent** from this table: a soft paywall returns
`200`, so an automated `HEAD`/`GET` cannot reliably detect it. Paywall status is
the manual `paywalled: true` manifest flag instead, and it drives only a banner
note — never a link flip.

The flip on `rotted` is the actual link-rot *cure*: a reader of a 2019 essay
clicks through to a working local snapshot instead of a 404, with no manual
intervention — and only after the rot is confirmed, not guessed.

`check` is a slow network job, not something every `make build` should pay for.
It runs on its own cadence, decoupled from the main build: the build consumes
whatever `archive-state.json` exists.

**Scheduling (installed 2026-06-10).** A systemd *user* timer runs the scan
daily on the build machine — the state file is local and gitignored, so the
scan must run where builds happen, not on the VPS. The units live in the repo
at `systemd/archive-check.{service,timer}` and are installed as symlinks, so
the repo stays the source of truth (edits apply after
`systemctl --user daemon-reload`):

```
systemctl --user link   ~/Repos/levineuwirth.org/systemd/archive-check.service
systemctl --user enable --now ~/Repos/levineuwirth.org/systemd/archive-check.timer
```

Cadence: daily at 12:00 (±30 min jitter) gives the hysteresis its minimum
detection latency — 14 days — at one polite `HEAD` per cited host per day.
`Persistent=true` fires a missed scan at the next login; the canary guard
makes an offline fire harmless. The timer only runs while a session is up
(`Linger=no`); `loginctl enable-linger` would lift that, but with
`Persistent=true` and a 14-day rot floor it is not needed. Rendering remains
pull-based by design: a status flip reaches the live site at the next
`make deploy` (always a clean build), and `/build/` shows the current tallies.

---

## Build-pipeline integration

New steps slot into the `Makefile` `build` target, gated on `.venv` (silent
skip), consistent with `embed.py` and the photography extractors:

```
make build:
  git auto-commit content/                       (existing — archive/ NOT swept in)
  tools/convert-images.sh                         (existing)
  pdf-thumbs                                      (existing)
  download-pdfjs.sh / download-leaflet.sh         (existing)
  → tools/archive.py fetch                        (NEW — fetch missing artifacts,
                                                          extract text, write
                                                          PROVENANCE.json +
                                                          archive-index.json)
  extract-exif / palette / dimensions             (existing)
  cabal run site -- build                         (existing — now also routes archive/)
  pagefind --site _site                           (existing — now also indexes archive pages)
  tools/embed.py                                  (existing — now also embeds archive pages)
  stamp-build-time.py / compress-assets.sh        (existing)
```

`tools/archive.py fetch` runs **before** `cabal run site -- build` so the
artifacts, `PROVENANCE.json` files, and `archive-index.json` all exist when
Hakyll routes the `archive/` tree and when `Backlinks.hs` loads the index.
`fetch` is incremental — a normal build with no new manifest entries does no
network I/O — but it still rewrites `archive-index.json` every run. Wayback
submission is **not** in this path. The `monolith` binary is committed
(`tools/bin/monolith`), so there is no download step.

**`make build` never deletes anything under `archive/`.** Artifact removal is
exclusively the job of the opt-in `make archive-gc` (see Eviction).

Standalone targets, none a dependency of `build`:

- `make archive-check` — link-rot scan.
- `make archive-wayback` — backfill outstanding Wayback captures.
- `make archive-suggest` — print the "cited but not archived" diff against
  `data/*.bib` (DOI-only entries resolved; `removed.yaml` entries excluded).
- `make archive-gc` — delete `archive/{slug}/` directories whose slug is
  recorded in `removed.yaml`; report (never delete) orphans that are not.

---

## Build module structure

New Haskell module:

- **`build/Archive.hs`** — patterns, routing rules, and contexts for the
  archive. Generates `/archive/` and every `/archive/{slug}/` page from
  `archive/manifest.yaml` + `PROVENANCE.json` + `data/archive-state.json`;
  routes the raw artifacts through unchanged. Pages and routed artifacts come
  only from current `manifest.yaml` entries, so an orphaned `archive/{slug}/`
  directory is inert (no page, not deployed). Integrity (SHA-256) verification
  is `tools/archive.py`'s job — it runs first and halts the build on a
  mismatch; `Archive.hs` trusts a present (provenance, artifact) pair and skips
  any entry lacking either. Separated from `Site.hs` for the same reason
  `Catalog.hs`, `Authors.hs`, and `Photography.hs` are — scoped concerns,
  isolated reasoning.

New Pandoc filter:

- **`build/Filters/Archive.hs`** — the link-annotation filter; registered in
  `Filters.hs` immediately after `smallcaps/dropcaps`, before the `links` pass.
  No-op when `archive-index.json` is absent.

Edits to existing modules:

- **`build/Patterns.hs`** — add `archivePattern` (artifact files) and
  `archiveManifest`. Add archive entries to `tagIndexable` so tagged archives
  reach the tag indexes. (Deliberately *not* added to `allContent`: archive
  pages receive backlinks but are not crawled for outbound links in v1.)
- **`build/Backlinks.hs`** — load `data/archive-index.json` (silent no-op if
  absent); widen `isPageLink` to keep archived externals; match incoming links
  against the alias set; canonicalize them to `/archive/{slug}/` in pass 2.
- **`build/Site.hs`** — wire the archive rules from `Archive.hs`; add the
  `/archive/` link to the footer / `colophon` routing.
- **`build/Stats.hs`** — contribute archive metrics to the `/build/` telemetry
  page: count; total bytes; median artifact age; counts by `snapshot-quality`,
  `status`, and `visibility`; `paywalled` count; and any orphan slugs
  (directories not in `manifest.yaml` and not in `removed.yaml` — they should
  not exist, so surface them where drift is visible).
- **`templates/partials/head.html`** — add a `noindex` context hook and a
  `$if(archive)$` link to `static/css/archive.css` (the archive pages'
  stylesheet — banner, provenance panel, artifact viewer, index list;
  scoped under `#markdownBody` to clear the prose rules in `typography.css`).

---

## Templates

New files under `templates/`:

| File | Role |
|------|------|
| `archive-index.html` | `/archive/` — the full text list, type/tag/status filters; includes `archive-removal-notice` |
| `archive.html` | `/archive/{slug}/` — banner, metadata, embedded artifact, full text, Referenced-by, Related; includes `archive-removal-notice` |

New partials:

| File | Role |
|------|------|
| `partials/archive-banner.html` | The "archived copy / view original" strip — reused by `archive.html` and any inline archive embed |
| `partials/archive-card.html` | Archive-entry card (text-only; no thumbnail in v1) for the index and for `/library.html` |
| `partials/archive-removal-notice.html` | The removal-request line (`ln@levineuwirth.org`); included directly by `archive.html` and `archive-index.html` |

Existing partials reused unchanged: `nav.html`, `head.html` (with the new
`noindex` flag), `footer.html`, `page-footer.html`. The removal notice is a
*new* partial precisely so `page-footer.html` stays untouched.

---

## Storage, repo size & `.gitignore`

Committed: the artifacts (`document.pdf`, `snapshot.html`), `PROVENANCE.json`,
`manifest.yaml`, `removed.yaml`, and the pinned `monolith` binary
(`tools/bin/monolith`). Gitignored: everything regenerable.

Append to `.gitignore`:

```
# Archive: generated text + its staleness stamp (recreated from the committed
# artifact on every build — deterministic, so committing them is churn).
archive/**/*.txt
archive/**/*.txt.sha256

# Archive: generated state (written by tools/archive.py).
# NOTE: archive/**/PROVENANCE.json is deliberately NOT ignored — it is the
# committed, immutable record of each archival event.
data/archive-state.json
data/archive-index.json
```

**Repo-size policy.** Archived artifacts are immutable once taken, so they add
no *history* bloat — but the working tree grows. v1 commits them: a preservation
guarantee that depends on an un-versioned side store is a weaker guarantee, and
`git clone` → `make build` must reproduce the whole site.

- **Per-artifact cap: 25 MB.** `archive.py fetch` warns and skips above it; a
  deliberately-oversize artifact is committed with `git add -f`. This stops a
  200 MB scan from being swept silently into a commit.
- **Migration tripwire.** If `archive/` exceeds **~5 GB**, or **doubles
  year-over-year**, evaluate moving the artifact store out of the main repo —
  to a separate `archive` repository or a content-addressed store the VPS
  rsyncs independently. `tools/archive.py` reads the store root from a single
  config value, so the move is a config change, not a redesign.
- **Never git LFS.** LFS smudges the property that makes this system worth
  having: with LFS, `git clone` no longer yields the artifacts unless the LFS
  server is up and authenticated. For a system whose value proposition is "this
  survives," that is a regression. If migration is needed, the destination is a
  separate repo or object store — not LFS in this one.

---

## Legal, ethical & SEO posture

Archiving third-party content touches copyright. The design's guardrails:

- **`noindex` on every archive page.** The archive preserves; it does not
  republish to search engines or compete with originals for ranking.
- **The original is the hero.** Every archive page links prominently to the
  source and is explicitly framed as a dated archived copy.
- **A real removal channel, everywhere.** A request to `ln@levineuwirth.org`
  gets the entry removed (see Eviction). The channel is advertised on
  `/archive/`, on **every individual archive page**, and inside the fetcher's
  User-Agent string. This is the load-bearing ethical commitment; `robots.txt`
  is only a proxy for it.
- **`noarchive` honoured.** Both `X-Robots-Tag: noarchive` (HTTP header) and
  `<meta name="robots" content="noarchive">` (HTML body) abort a fetch.
- **Authenticated content skipped.** The fetcher sends no credentials. Anything
  behind a login is not archived.
- **`visibility: private`** keeps a snapshot in-repo for the author's own
  reference without deploying the artifact to `_site/` — the appropriate
  setting for licensed material the author may read but should not redistribute.
  The archive *page* still exists (metadata + "held offline"), so link-rot
  tracking and the Wayback link survive.
- **Curated, not crawled.** The archive only ever contains works this site
  deliberately references — a fundamentally different posture from a scraper.
- **Attribution preserved.** Author, source title, source date, and original
  URL are surfaced on every archive page.

This is a personal-scale citation archive, consistent with long-standing
practice on research-oriented personal sites. It is not a content platform.

---

## Phased implementation

Each phase has explicit exit criteria. Do not start a phase until the previous
one passes.

### Phase 1 — Skeleton, PDF only

Bootstrap entry: **NIST FIPS 203 (ML-KEM)**, PDF at
`https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.203.pdf` — a stable, auth-free
PDF already cited in `data/simd-paper.bib`, so the test entry keeps its value
after Phase 1 ships.

- [x] Define `archive/manifest.yaml` and `archive/removed.yaml` schemas; create
      `manifest.yaml` with the bootstrap entry
- [x] `tools/archive.py fetch` — PDF download, size cap, `pdftotext`,
      `.txt.sha256` staleness stamp, write per-entry `PROVENANCE.json`; always
      rewrite `archive-index.json`; refuse a `(slug, url)` mismatch, and
      re-hash every committed artifact (non-zero exit on a SHA mismatch)
- [x] `build/Archive.hs` — routing for `/archive/`, `/archive/{slug}/`, and the
      raw `document.pdf`; orphaned directories produce no page (a pass-1
      refinement subsequently added a Haskell-side SHA-256 re-hash via
      `sha256sum`, so the integrity guarantee holds even when `archive.py`
      did not run first — direct `cabal` invocations, deploy hosts without
      `.venv`, etc.)
- [x] `templates/archive.html`, `templates/archive-index.html`,
      `partials/archive-banner.html`, `partials/archive-removal-notice.html`
- [x] PDF artifact embedded on the page (Phase 2 changed this to a raw,
      browser-native `<iframe>` embed — see the Display — PDF decision)
- [x] Extracted text rendered into the page DOM (collapsed `<details>`)
- [x] `noindex` hook in `head.html`; set on archive pages
- [x] **Eviction works** end-to-end — `make archive-gc`, `removed.yaml` gating,
      orphan reporting (see Eviction & removal)
- [x] Wire `tools/archive.py fetch` into the Makefile, `.venv`-gated
- [x] `.gitignore` additions (`PROVENANCE.json` explicitly *not* ignored)

**Exit criteria:** the FIPS 203 PDF renders at `/archive/{slug}/` with banner,
metadata, working PDF.js embed, visible extracted text, and a removal-request
notice; `/archive/` lists it; both carry `noindex`. The eviction procedure
(record in `removed.yaml` → drop the manifest line → `make archive-gc`) removes
the artifact; a manifest line deleted *without* a `removed.yaml` entry leaves
the artifact intact and emits a warning. **Running `make build` ten times in
succession with no manifest edits produces no changes under `archive/`** — no
deletions, no `PROVENANCE.json` rewrites, no artifact replacements.

**Met (2026-05-22).** FIPS 203 fetched (1.25 MB, 3601 lines of extracted
text); `/archive/nist-fips-203/` renders with banner, metadata, PDF.js iframe,
in-DOM full text, and removal notice; `/archive/` lists it; both carry
`noindex`. `gc` was verified on both paths — an orphan directory is reported
and left intact (exit 1); a `removed.yaml`-listed directory is deleted while
the manifest entry is untouched. `archive/` is byte-identical across repeated
fetch + build cycles. The PDF.js iframe is correctly wired; rendering the
viewer needs `static/pdfjs/`, which `make build` vendors via `download-pdfjs.sh`.

### Phase 2 — HTML snapshots

Bootstrap entry: **`https://cr.yp.to/aes-speed.html`** (`slug: djb-aes-speed`)
— Bernstein's cache-timing-attacks page, cited in `data/simd-paper.bib`. A
stable, JavaScript-free static page, so its snapshot is reproducible and
classifies cleanly as `ok`; like FIPS 203 it keeps its value after the phase
ships.

- [x] Commit the pinned `monolith` binary at `tools/bin/monolith`; record
      version + sha256 in `tools/monolith-version.txt`
- [x] `tools/archive.py fetch` — HTML branch: `monolith --no-js`, CSP `<meta>`
      injection (`style-src` + `-elem` + `-attr`, `script-src`/`object-src`/
      `frame-src 'none'`), text extraction via `BeautifulSoup`, type detection
- [x] `snapshot-quality` classification (`ok` / `degraded` / `js-required`)
      written to `PROVENANCE.json`; degraded captures flagged on `/archive/`
- [x] Sandboxed `<iframe>` rendering (`referrerpolicy="no-referrer"`, no
      `allow-scripts`) in `archive.html`

**Exit criteria:** an HTML URL snapshots to a self-contained file with a CSP
`<meta>`, renders in a sandboxed no-referrer iframe with the original's styling
isolated, and shows extracted readable text in site chrome; the sandboxed
snapshot renders correctly under the CSP in **both Firefox and a Chromium-based
browser**; capture quality is classified and a `degraded` snapshot is visibly
flagged; the author has reviewed the rendered snapshot before committing it.

**Met (2026-05-22).** `monolith` 2.10.1 (`monolith-gnu-linux-x86_64`) is
vendored at `tools/bin/monolith` with its version + sha256 in
`tools/monolith-version.txt`; `archive.py fetch` locates it via `$MONOLITH_BIN`
→ `tools/bin/monolith` → `$PATH`, and warns-and-skips (build continues) when it
is absent. `cr.yp.to/aes-speed.html` snapshots to a 26 KB self-contained
`snapshot.html` with the archive CSP `<meta>` as the first `<head>` child;
`/archive/djb-aes-speed/` renders it in a `sandbox`ed, `no-referrer` iframe with
291 lines of extracted prose shown inline as `<p>` paragraphs; `snapshot-quality`
classifies `ok`, and a (synthetically forced) `degraded` entry shows the warning
note on the page and a flag on `/archive/`. `fetch` is idempotent — `archive/`
is byte-identical across re-runs. The committed artifact is `snapshot.html`;
`snapshot.txt` + `.sha256` are gitignored (the existing `archive/**/*.txt`
globs already cover them).

**Author-gated, by design (exit-criteria wording).** Two criteria are not
machine-checkable here and remain the author's: (1) the cross-browser CSP
render in Firefox *and* a Chromium browser; (2) the per-snapshot review before
committing `archive/`. The vendored `monolith` binary and the FIPS 203 / djb
artifacts are staged but **not committed** — committing `archive/` and
`tools/bin/monolith` is the deliberate author act the design specifies.

One real-world note from the bootstrap: `cr.yp.to` ships
`<meta name="robots" content="none">`. Per spec `none` ≡ `noindex, nofollow` —
it is *not* `noarchive`, so the snapshot proceeded correctly; only an explicit
`noarchive` (header or meta) aborts a fetch.

### Phase 3 — Link annotation & Wayback

- [x] **Confirm `Filters.hs`'s actual filter registration order** matches the
      AST chain documented on `/colophon` before pinning the filter's position
- [x] **Confirm** whether the bibliography is rendered into the document AST or
      a separate context field — this decides whether bibliography annotation
      is in scope here or gated on the popup rewrite (see Link annotation)
- [x] `build/Filters/Archive.hs` — annotate body links to archived URLs;
      register in `Filters.hs` after `smallcaps/dropcaps`, before `links`;
      no-op when `archive-index.json` is absent
- [x] `archive.py wayback` + `make archive-wayback` — non-blocking submission,
      backfill `wayback` into `PROVENANCE.json`
- [x] `visibility: private` handling (artifact not routed to `_site/`)

**Exit criteria:** a prose link to an archived URL gets an automatic archive
affordance; a build without `.venv` (no `archive-index.json`) still succeeds
with links un-annotated; every entry has a recorded Wayback URL after `make
archive-wayback`; a `private` entry's page renders without deploying its
artifact; the bibliography-annotation path is documented as either in-scope or
popup-gated.

**Met (2026-05-22).** `build/Filters/Archive.hs` walks body `Link` nodes and,
for any URL in `data/archive-index.json` (canonical + alias set, fragment- and
trailing-slash-tolerant), appends a superscript `archive-affordance` link to
`/archive/<slug>/` — emitted as `RawInline` HTML so the downstream `Links`
pass leaves it alone. It is registered in `Filters.applyAll` between
`Smallcaps` and `Links`; the index loads once via an `unsafePerformIO` CAF and
an absent/empty index makes the filter the identity (verified: a prose link to
the archived `cr.yp.to/aes-speed.html` gains the affordance, a non-archived
link does not). `archive.py wayback` (+ `make archive-wayback`) submits each
entry lacking a `wayback` capture to the Wayback Machine and backfills
`PROVENANCE.json`; it always exits 0 and is never on a build's critical path.
`visibility: private` is a `manifest.yaml` field: a private entry's artifact is
never routed to `_site/` (artifacts are routed by an explicit public-only list,
which also stops an orphan directory's artifact deploying), and its page
renders provenance + a "held offline" panel with no embed and no extracted text
(verified: a private `_site/archive/<slug>/` contains only `index.html`).

Two items are deliberately scoped out of this pass, both documented above:
**bibliography annotation** (the bibliography is a separate `$bibliography$`
field; the hook is `Citations.hs`'s `enhanceEntry`, pending a CSL-URL check —
not popup-gated) and **pull-from-Wayback when the original is dead at fetch
time** (it belongs with Phase 5 link-rot detection, where a dead URL is the
central case and a Wayback-sourced artifact's provenance can be handled
properly). *(Both implemented 2026-06-10 — see the Bibliography note under
Link annotation, and Wayback Machine — non-blocking.)* The live
`make archive-wayback` run is author-initiated — it submits
public captures to a third-party service.

### Phase 4 — Backlinks & similar-pages indexing

- [x] `Backlinks.hs` — load `archive-index.json` (silent no-op if absent);
      widen `isPageLink`; match the alias set; canonicalize archived externals
      to `/archive/{slug}/` in pass 2
- [x] "Referenced by" section on `archive.html`
- [x] `embed.py` — add `/archive/` to `EXCLUDE_URLS`; verify archive pages join
      `similar-links.json` and the paragraph index
- [x] **Measure `embed.py` runtime** against a populated archive; add a
      per-document embedding cache (keyed by content hash) once the archive
      passes 50 entries or `embed.py` exceeds 60 s
- [x] "Related" section on `archive.html`
- [x] Fragment-preserving backlinks → grouped "Referenced by" by section/page

**Exit criteria:** an archive page lists the essays that cite it under
"Referenced by", including citations that used an alias URL form; essays surface
relevant archived works under "Related"; a fragment-targeted citation appears
grouped under its section; `embed.py` runtime with the archive populated is
measured and either under the thresholds or the cache is in place.

**Met (2026-05-22).** A shared `build/ArchiveIndex.hs` loads
`data/archive-index.json` once (the `unsafePerformIO` CAF formerly private to
`Filters.Archive`); `Backlinks.hs` and `Filters.Archive` both consume it.
`Backlinks.isPageLink` keeps an archived external URL regardless of scheme or
extension; pass 2 (`targetKey`) canonicalises it to the archived work's
`/archive/<slug>/` page key — computed as the same string fed through
`normaliseUrl` that `backlinksField` uses for the page's own route, so the two
always agree. `archiveEntryCtx` gains `referencedByField` and
`similarLinksField`; `archive.html` renders `$if(referenced-by)$` /
`$if(similar-links)$` sections. `referencedByField` reuses the backlinks lookup
but groups sources by the fragment each citation targets — a `#page=12`
citation renders under a "Page 12" subheading, a bare citation in a flat list
above. `embed.py` excludes the `/archive/` index from the corpus (individual
entry pages stay in) and is measured at **~12 s** for the whole site (43 → 25
pages, 802 paragraphs) — far under the 60 s threshold and the 50-entry trigger,
so the per-document embedding cache is correctly *not* built (premature at this
scale; revisit at the threshold).

Verified end-to-end with a temporary citation in `content/about.md`: the
FIPS 203 page listed it under "Referenced by" with a flat entry *and* a grouped
"Page 12" entry; both archive pages surfaced the SIMD/PQC essay and each other
under "Related"; the `/archive/` index was absent from `similar-links.json`.

One pre-existing `embed.py` issue was surfaced and fixed: the `/source/`
repository code mirror was in the similarity corpus — a template file was
surfacing as a neighbour, titled with its unrendered `$title$` placeholder. An
`EXCLUDE_PREFIXES` rule now keeps `/source/` out, which also dropped 18 junk
pages from the site-wide corpus (43 → 25).

### Phase 5 — Link-rot detection & maintenance

**Prerequisite — resolved 2026-05-22.** `/build/` had been serving a stale
cached page: its build-varying telemetry is gathered in `unsafeCompiler`, which
Hakyll does not dependency-track, so the page recompiled only when tracked
*content* changed. Fixed — `build/Main.hs` writes a per-build
`data/build-stamp.txt` that `Stats.hs` loads as a dependency, forcing `/build/`
and `/stats/` to recompile every build. The archive-metrics exit criterion
below is now measurable.

- [x] `tools/archive.py check` + `make archive-check` — HEAD/GET scan
- [x] Asymmetric hysteresis: `rotted` requires 3 consecutive failed scans over
      ≥ 14 days; a single success → `live`; `consecutive-failures` +
      `status-since` tracked in `archive-state.json`
- [x] Dead-link rendering: flip primary link to the archive on `rotted`
- [x] Pagefind `status` filter tag wired into `search-filters.js`
- [x] Archive metrics on `/build/` telemetry (`Stats.hs`)
- [x] `/archive/` index shows per-entry health

Test endpoint: reserve a controlled host — e.g. `archive-test.levineuwirth.org`,
a sub-host the author owns — that can be toggled to return 404 on demand, so the
rot-detection test flips without depending on a third party's uptime.

**Exit criteria:** the controlled test URL is detected as `rotted` only after
the hysteresis threshold is met, and the citing essay's link then flips to the
archived copy; a single transient failure does *not* flip it; restoring the URL
returns it to `live` on the next successful scan; the `/build/` page reports
archive coverage and health; search results can be filtered by archive `status`.

**Met (2026-05-22).** `tools/archive.py check` HEAD/GET-probes every manifest
URL (HEAD first, ranged GET on 403/405/501) and updates the gitignored
`data/archive-state.json`, which mirrors the manifest exactly (state for
dropped URLs is discarded). The asymmetric hysteresis in `next_state` is
unit-verified against synthetic scenarios — fail/fail/fail across 20 days flips
to `rotted`; three fast fails within 2 days stay at `error`; a single `ok` from
any non-live status recovers immediately to `live`. `ArchiveIndex.hs` exposes
the parsed status to consumers as `archiveStatusForSlug`. `Filters.Archive`
flips a `rotted` body link's href to `/archive/<slug>/` (adding an
`archive-rotted` class and a solid "archived" affordance marker) — verified
end-to-end with a hand-crafted `rotted` state file: a content link to the
djb URL was rewritten to the archive page; reverting the state restored the
original link. `archive.html` carries `data-pagefind-filter="type:archive,
status:$status$"`, a "Link status" row in the provenance panel, and a
status-note callout in the header for non-live states. The `/archive/` index
flags rotted entries with a solid "link rotted" chip. `Stats.hs` `/build/`
gains a "Link archive" section (count, total size, median age, by-status /
by-quality / by-visibility breakdowns, paywalled count, orphan directories) —
verified showing the test state's `error 1  ·  rotted 1` mix.

**Rendering staleness — by design.** Rot status is consumed at build time via
@unsafePerformIO@ CAFs; archive entry pages and content pages don't have a
Hakyll dependency edge to `archive-state.json` (that would only fix half the
problem — the archive pages — while leaving content-link flips stale, since
`Filters.Archive` runs during content compilation and can't cheaply force
every content page to depend on the state). So after `make archive-check`,
an *incremental* build can leave both surfaces uniformly stale until a clean
build refreshes everything. `make deploy` always does `make clean`, which
makes the deployed site consistent. The `/build/` page is the one
always-fresh surface: it recompiles every build via the existing build-stamp
dependency, so its archive metrics always reflect the current scan.

**Test endpoint deferred.** Spinning up `archive-test.levineuwirth.org` and
running it through a 14-day-spanning fail streak is a multi-week real-world
verification the author runs (or a CI cron); the hysteresis logic itself is
unit-tested deterministically in `next_state`, and the rendering side is
verified by the hand-crafted `rotted` state file.

**Search-UI filter (`search-filters.js`) — implemented (2026-06-10).** The
data-side was in place since Phase 5 (every archive page carries
`data-pagefind-filter="type:archive, status:$status$"`); the deferred UI
work is now done, with the naming collision resolved by *scoping, not
renaming*: the epistemic `status` filter keeps its name and namespace, and
the archive dimension lives in its own state fields (`archiveMode`,
`archiveStatus`), button classes (`filter-archive-mode-btn`,
`filter-archive-status-btn`), and panel rows ("archive", "link status").
Mechanics follow the established epistemic pattern rather than the Pagefind
filter API: `Archive.hs` emits `data/archive-meta.json` (routed page path →
link-rot status, the analogue of `data/epistemic-meta.json`), which
`search-filters.js` fetches lazily and applies to rendered results — both
Pagefind and semantic. Semantics: `archiveMode` is a single-select toggle —
`exclude` hides `/archive/` results, `only` shows nothing else; `link
status` is a multi-select that further restricts *archive* results to the
chosen statuses and never affects native content; both compose freely with
the epistemic filters. Verified in headless Chrome against a harness with a
simulated `rotted` entry: exclude / only / rotted-only / rotted+draft all
behave per the table above.

---

## Open / deferred questions

Non-blocking, and now a short list — the draft's larger set was resolved into
Decisions during review.

- **JS-heavy / SPA pages.** `monolith` cannot execute JavaScript;
  `js-required` captures are degraded. A headless-browser fallback (SingleFile,
  Chromium capture) would handle them but adds a heavyweight dependency. Defer
  until a real entry needs it.
- **First-viewport thumbnails.** Dropped for v1 — `/archive/` is a text list. A
  visual grid does not earn its keep at small N; revisit past ~50 entries.
- **PDF section-granularity.** `pdftotext` flattens structure. Per-*page*
  chunking (`#page=N` anchors, per-page text) is the realistic granularity for
  PDF backlinks and semantic indexing. Defer.
- **Per-section "Related" UI.** The paragraph-level semantic index already
  receives archive text; a UI surfacing section-level "Related" does not exist
  for *any* content type yet. Out of scope here; a site-wide feature.
- **Snapshot versioning.** v1 snapshots are immutable per snapshot; `refresh`
  replaces in place but records `previous-sha256`. If a referenced work is
  meaningfully revised, should a new dated snapshot be kept *alongside* the old
  (`document-2027-01-01.pdf`) with a version switcher? `previous-sha256` is the
  seed — extend it to a list and the switcher reads it. Defer until needed.
- **Intra-archive link rewriting.** When archived page A links to a URL that is
  *also* archived, A's snapshot could be rewritten to point at the local copy
  of B — keeping the reader inside the preserved set. Gwern-style; defer.
- **Media beyond PDF/HTML.** EPUB, plain images, video. Out of scope for v1;
  `type` is an open enum so it can extend.

---

## References

- `WRITING.md` — authoring conventions; the link-annotation feature will be
  documented there once Phase 3 lands
- `PHOTOGRAPHY.md` — the closest precedent: authored-input/generated-sidecar
  split, phased build, `.venv`-gated tools, vendored binaries
- `build/Backlinks.hs` — two-pass backlinks; `isPageLink` is the integration
  point
- `build/SimilarLinks.hs` — "Related" block; consumes `embed.py` output
- `tools/embed.py` — embedding pipeline; archive pages join its corpus for free
- `build/Patterns.hs` — canonical content patterns
- `build/Tags.hs` — slash-hierarchy tags (reused for archive tags)
- `tools/download-leaflet.sh`, `tools/download-pdfjs.sh` — the sha256-pinning
  convention; `monolith` is committed directly rather than downloaded (a
  build-time executable, not a servable asset)
- `nginx/popup-proxy.conf` — the metadata proxy; related but distinct (caches
  previews, does not preserve documents)
```
</content>
