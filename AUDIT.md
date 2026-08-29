---
title: Repository audit
date: 2026-05-07
---

# Repository audit — levineuwirth.org

Comprehensive audit of the repo on `main` at commit `670d477` (working tree
modified: `data/now.yaml`, `static/cv.pdf`, `static/resume.pdf`; untracked
`Fermata_2.pdf`).

Severity legend: **HIGH** (likely to break a build, cause data loss, or
expose a security weakness) — **MED** (latent bug, brittleness, or
documentation drift) — **LOW** (minor robustness gap or fragile assumption) —
**NIT** (style, polish, or paranoia).

Numbers are file:line. "Unverified" means I noticed the issue but did not
reproduce its consequence; the line still appears load-bearing enough to
flag.

---

## 1. Build & dependency chain

### 1.1 `cabal build` from scratch is unsolvable with the current freeze — **HIGH**

Running `cabal build` resolves the dependency tree freshly because no fresh
`.ghc.environment` link exists for the current GHC. The freeze pins
`aeson ==2.2.1.0`, but `warp` (pulled in by `hakyll +previewserver`) needs
`hashable ==1.4.7.0/installed`, while `aeson 2.2.1.0` needs
`hashable >=1.4.2.0 && <1.4.5.0`. Result:

```
[__8] fail (backjumping, conflict set: aeson, levineuwirth, warp)
After searching the rest of the dependency tree exhaustively, these were
the goals I've had most trouble fulfilling: aeson, warp, hakyll, http2,
async, network-control, unliftio, levineuwirth, hakyll:previewserver
```

Day-to-day this is masked because `dist-newstyle/` has cached binaries
from an earlier successful resolve. A fresh clone, a `cabal clean`, or a
GHC upgrade will make `make build` fail. (`cabal.project.freeze:9` pins
aeson; `levineuwirth.cabal:60` allows `>= 2.1 && < 2.3`.)

Fix: regenerate the freeze (`tools/refreeze.sh`) against the current
hackage index. If `tools/refreeze.sh` is what produced the broken freeze,
a manual `cabal freeze --constraint='aeson >= 2.2.2'` is needed.

### 1.2 `levineuwirth.cabal` upper bounds are tight — **MED**

- `hakyll >= 4.16 && < 4.17` (`levineuwirth.cabal:52`) — pins to a single
  minor line. 4.17.x is already on Hackage; the freeze is one rebase away
  from forcing a bound bump.
- `pandoc >= 3.1 && < 3.7` (`levineuwirth.cabal:53`) — pandoc historically
  ships breaking changes on minor bumps, so the caution is fair, but 3.7
  exists.
- `aeson >= 2.1 && < 2.3` (`levineuwirth.cabal:60`) — see 1.1; this bound
  combined with the freeze conflict is what makes the build unsolvable.

### 1.3 Python version mismatch — **HIGH**

`.python-version` says `3.14`. `pyproject.toml:5` says
`requires-python = ">=3.12"`. `uv.lock:3` agrees with pyproject. Anyone
who clones with pyenv/asdf will install Python 3.14. Anyone whose system
ships 3.12/3.13 only will be told the project is fine, then hit
`.python-version` later. Either bump `requires-python` to `>=3.14` or
downgrade `.python-version` to a release that's actually a baseline.

### 1.4 No `tools/model-checksums.sha256` despite supply-chain hardening
in `download-model.sh` — **HIGH**

`tools/download-model.sh:75-78` reads the checksum file when present and
falls through with a printed note when it's missing. The file is absent
from the tree. So today: model weights are pulled from Hugging Face
unverified. If the upstream is compromised or MITM'd, the embedding +
client-side semantic search ship trojaned weights. The fix path is
already documented in the script comments — generate and commit the
checksum file.

### 1.5 Cabal modules vs filesystem — verified consistent

Every `.hs` under `build/` is listed in `levineuwirth.cabal`'s
`other-modules`. No orphan files. No phantom modules.

---

## 2. Makefile

### 2.1 `rsync` line does not quote variables — **MED (security-shaped)**

`Makefile:147`:

```make
rsync -avz --delete _site/ $(VPS_USER)@$(VPS_HOST):$(VPS_PATH)/
```

If `VPS_PATH` ever contains a space or a shell metacharacter, the
expansion splits and rsync is handed extra arguments. The Makefile does
guard `VPS_PATH` against `/`, `/srv`, etc., but does not guard against
whitespace or against `;` / `&&`. Most variables in this Makefile are
already quoted (`@test -s _site/index.html`), so this is the odd one out.
Quote with `"$(VPS_USER)@$(VPS_HOST):$(VPS_PATH)/"`.

### 2.2 `> IGNORE.txt` line — **NIT**

`Makefile:55`. The recipe truncates `IGNORE.txt` at the repo root. It is
gitignored. The purpose is undocumented in this Makefile (its intent
seems to be "tell whatever sync tool watches the workspace to ignore the
build output"). Either replace with `: > IGNORE.txt` (POSIX no-op) and a
one-line comment explaining its consumer, or drop it.

### 2.3 `notify-send … || true` swallows errors — **NIT**

`Makefile:141`. Fine for a desktop notification, but the `|| true`
silently masks `notify-send` failures. Acceptable.

### 2.4 Auto-snapshot recipe — **NIT (worth re-reading)**

`Makefile:12-26` runs `git add content/` and creates an automatic
`auto: <ts> [skip ci]` commit before every build. The .gitignore
excludes credential-shaped patterns under `content/`, so accidental
secrets won't be staged. But:

- The commit happens **regardless of the build outcome**. A build that
  starts and crashes mid-way still leaves a snapshot commit. The comment
  says this is intentional. It does mean the recent commit history is
  full of `auto:` commits even for failed builds.
- The recipe reads `.env` via `-include .env` and exports
  `VPS_USER VPS_HOST VPS_PATH GITHUB_REPO`. The comment claims this
  prevents future GITHUB_TOKEN from leaking. That's correct only if
  `GITHUB_TOKEN` is never added to the explicit export list. Worth a
  comment in `.env.example` reminding the future author.

### 2.5 Nested `$(MAKE)` and parallelism — **LOW**

`Makefile:29` (`@$(MAKE) -s pdf-thumbs`) and `:126` (`@$(MAKE) -C
yaml-source all`) — fine in serial mode, but `make -j build` will
parallelize sub-makes against the parent's job server only if they
inherit `MAKEFLAGS`. The `-s` flag is fine, but if parallelism is ever
desired, audit this.

---

## 3. Haskell build code (`build/`)

### 3.1 `unsafePerformIO` with module-global IORef — **MED**

`build/Filters/SourceRefs.hs:155`:

```haskell
{-# NOINLINE existsCacheRef #-}
existsCacheRef :: IORef (Map.Map Text Bool)
existsCacheRef = unsafePerformIO (newIORef Map.empty)
```

Standard "global mutable cache" pattern. `NOINLINE` is correct. `cabal
run site -- watch` and `cabal run site -- build` are single-threaded
today (Hakyll's compile loop is sequential), but the cabal file enables
`-threaded`, and the cache is reachable from any compiler thread. Cache
entries can also become stale between watches if a referenced source
file is deleted: the cache holds `Just True`, but `doesFileExist` would
now return `False`. Two practical consequences:

1. If a file is moved, `watch` may keep treating wikilinks/source-refs
   to the old path as live until the build server restarts.
2. If `existsCacheRef` is ever read concurrently by two threads, the
   `atomicModifyIORef'` is safe but the underlying check race could let
   two threads call `doesFileExist` on the same path. Harmless.

Acceptable as-is; document the staleness caveat.

### 3.2 Lazy `readFile` in IO — **MED**

- `build/Stats.hs:857-860`: `readFile "data/last-build-seconds.txt"` is
  lazy, wrapped in a `catch` that returns `"\x2014"` on any IOException.
  The em-dash fallback hides "file missing", "permission denied", and
  "encoding error" alike. Worse, lazy IO means the handle may be open at
  the time the catch fires. Use `Data.Text.IO.readFile` or
  `withFile`+`hGetContents'`.
- `build/BibExtras.hs:66`: `parseBibExtras path = … <$> readFile path`.
  Same concern. Failure surfaces only when the result is forced.

Fix: standardize on strict `Data.Text.IO.readFile` (already used in
`build/Stability.hs:56,144` and `build/Now.hs`).

### 3.3 Defensive but technically partial pattern matches — **LOW**

These are "this case can't happen because of the guard" patterns. They
all carry a comment, so they're not bugs, but `-Wall` may warn (and
they reduce confidence under refactor). Cite-and-fix is straightforward.

- `build/Stats.hs:169-172` — `median` falls through to `0` on
  unreachable empty after a `length`-based guard.
- `build/Stability.hs:109-113` — `stabilityFromDates` falls through.
- `build/Catalog.hs:233-235` — `renderGroup []` when `groupBy` cannot
  produce empty groups.
- `build/Tags.hs:181` — `init segs` after a length-> 1 guard.
- `build/Stability.hs:297, 311, 324` — `last (newest:more)`.

Replace each with structural pattern matches (`(x:xs)`, `NonEmpty`) or
use `Data.List.NonEmpty`. Or pragma-suppress the warning.

### 3.4 Magic offsets / hardcoded prefixes — **LOW**

- `build/Site.hs:388, 392`: `replaceExtension (drop 8 fp) "html"` —
  `drop 8` is "strip `content/`". `T.stripPrefix` reads better and
  fails closed.
- `build/Filters/Wikilinks.hs:43, 77-78`: assumes destination URLs end
  with `.html`. Documented in code; brittle if routing changes.

### 3.5 `fail` for parse errors aborts the entire build — **LOW**

- `build/Commonplace.hs:144` and `build/Now.hs:258`: a malformed
  `commonplace.yaml` or `now.yaml` aborts the build. The data is
  hand-edited and small, so this is fine; a friendly error message
  would be nicer.
- `build/Backlinks.hs:359`: `fail "backlinks: could not parse
  data/backlinks.json"` aborts every page that uses the backlinks
  context. The file is generated at build time, so corruption is
  unlikely, but consider degrading to "no backlinks" instead.

### 3.6 Silent-drop parsers — **LOW**

- `build/BibExtras.hs:95`: malformed `.bib` entries become `[]` with no
  warning. The author edits these by hand; a stderr note for dropped
  entries would catch typos.
- `build/Contexts.hs:198-205`: malformed history entries are silently
  dropped. Same trade-off.
- `build/Stats.hs:464`: `listDirectory dir `catch` …` returns `[]` on
  any IOException. Acceptable for stats.

### 3.7 `trim` does double-reverse — **NIT**

`build/Utils.hs:61`. `dropWhileEnd` (Data.List) avoids the second
`reverse`. Cosmetic.

---

## 4. Tools (`tools/`)

### 4.1 `tools/extract-exif.py:292` uses Pillow's deprecated `_getexif()` — **MED**

```python
exif = img._getexif() or {}
```

Pillow has marked `_getexif` private since 9.0. The public API is
`img.getexif()`. The bound in `pyproject.toml` allows up to Pillow 12,
so a future `uv sync` could break this silently. One-line fix.

### 4.2 `embed.py` and `import-poetry.py` are not executable — **LOW**

Both have `#!/usr/bin/env python3` shebangs but bits are `0644`, while
their siblings (`extract-*.py`) are `0755`. The Makefile invokes them
via `uv run python tools/embed.py`, so this is cosmetic — unless a
future contributor tries `./tools/embed.py`. `chmod +x` both.

### 4.3 `tools/import-photo.sh` does not check `magick` exit codes — **MED**

- Lines ~115-122: the resize/`-strip` `magick` call has no `|| exit`.
- Line ~144: `magick mogrify -strip "$TARGET"` likewise. If mogrify
  fails, EXIF survives, but the script proceeds to write frontmatter
  asserting the photo was stripped.

The shell prelude already runs `set -euo pipefail`, but `magick … |
…` can still partial-succeed with the pipefail correctly catching it.
A direct `magick … "$TARGET" || exit 1` is clearer.

### 4.4 `tools/import-photo.sh` does not validate `$SLUG` — **LOW**

The slug is taken from CLI input and used as `content/photography/$SLUG`.
A slug containing `../` traverses out of the photography tree. The
Hakyll build would refuse to ingest it later, but the import has
already written files. Add a `[[ "$SLUG" =~ ^[a-z0-9-]+$ ]] || exit 1`
near the argument parse.

### 4.5 `subset-fonts.sh` hardcodes Arch font paths — **LOW**

`SPECTRAL=/usr/share/fonts/ttf-spectral`,
`FIRA=/usr/share/fonts/TTF`, etc. macOS / Debian put fonts elsewhere.
Doesn't break the site (the script is rarely run), but the README does
not mention this constraint.

### 4.6 `download-pdfjs.sh` checksum scope is narrow — **LOW**

`tools/pdfjs-checksums.sha256` pins only the archive. After extraction,
the unpacked tree is trusted blindly. Compare to
`tools/leaflet-checksums.sha256`, which pins individual extracted files.
The archive pin is sufficient against tampered downloads but offers
nothing against a corrupted unzip on disk.

### 4.7 `add-popup-source.sh` masks curl failures — **LOW**

Lines ~67, ~98: `curl -sSI … 2>&1 || true` followed by piping into
`grep`. A network failure produces an empty `$HEADERS`, and the
downstream "CORS allowed?" detection silently reports OK. The script
is interactive, so a user notices, but a stricter `if curl … ; then`
guard would be better.

### 4.8 `embed.py` model staleness window — **LOW**

`tools/embed.py:39` hardcodes `MODEL_NAME = "all-MiniLM-L6-v2"` and
`DIM = 384`. The Hugging Face cache is unpinned, so a model bump would
silently change embedding semantics. The script regenerates everything,
so the immediate breakage would be benign, but commits referencing the
similar-links file would then drift. Pin to a model revision SHA.

### 4.9 `embed.py` `needs_update` race — **LOW**

`tools/embed.py:79-84` calls `.stat().st_mtime` while iterating
`SITE_DIR.rglob("*.html")`. A file deleted mid-walk raises
`FileNotFoundError`. In practice the build runs solo, so this never
triggers; mention it.

### 4.10 `extract-*.py` swallow exceptions without traceback — **LOW**

`extract-dimensions.py:101`, `extract-exif.py:424`,
`extract-palette.py:105`: each prints `f"…: {e}"` and continues. When a
file is corrupt, the operator sees the exception type but no stack
trace. Adding `traceback.format_exc()` to the stderr line costs
nothing.

### 4.11 Other shell scripts

- All shell scripts in `tools/` already use `set -euo pipefail`.
- `convert-images.sh`, `compress-assets.sh`, `download-leaflet.sh`,
  `sign-site.sh`, `preset-signing-passphrase.sh` are clean.
- `compress-assets.sh:21` — no validation that `MIN_SIZE` is numeric.
  A misconfigured env var fails with a cryptic arithmetic error. NIT.

### 4.12 Stray `TODO`s in tooling — **NIT**

- `tools/add-popup-source.sh:12,128,131,134,137,156,194` — by design;
  the script is a scaffolder.
- `tools/import-photo.sh:185` — emits `caption: TODO — short caption…`
  into the generated `index.md`. Authors who forget to edit will ship
  the literal `TODO`. A `make`-time check (`! grep -r "TODO " content/
  photography`) would catch it.

---

## 5. Content & frontmatter (`content/`)

### 5.1 Every `date:` in frontmatter is unquoted — **MED**

`WRITING.md:103` shows the canonical form as `date: "2026-03-01"`. Across
all of `content/` (sample: 40+ files), every `date:` line is
**unquoted**. Examples:

- `content/index.md`, `content/about.md`, `content/colophon.md`,
  `content/library.md`, `content/search.md`, `content/current.md`,
  `content/links.md`, `content/gpg.md`, `content/commonplace.md`
- All essays under `content/essays/` and drafts under `content/drafts/`
- All tag-meta files

YAML promotes ISO 8601 to a `Date`, not a `String`. Hakyll's `dateField`
historically reads the string back, but as the Pandoc YAML decoder
evolves, this can shift. Either the documentation is wrong (and dates
are deliberately stored as YAML dates) or the corpus is. Reconcile by
either:

1. Quoting all dates project-wide (sed across `content/`).
2. Updating `WRITING.md:103` to show the unquoted form.

### 5.2 `content/tag-meta/*.md` lack `title:` — **MED (likely intentional, undocumented)**

Nine files under `content/tag-meta/` have only `tooltip:` in their
frontmatter, no `title:`. `WRITING.md` documents `title:` as required
on every authored page. Either:

- The Hakyll rules for tag-meta consume a different schema (likely —
  the title comes from the tag itself), in which case `WRITING.md`
  should mention this exception, **or**
- Hakyll is silently inserting empty titles into rendered tag pages.

Files: `ai.md`, `fiction.md`, `miscellany.md`, `music.md`,
`nonfiction.md`, `photography.md`, `poetry.md`, `research.md`,
`tech.md`.

### 5.3 `Fermata_2.pdf` at the repo root — **MED**

48 KB PDF, untracked, not in `.gitignore`, not referenced by any
template/CSS/script/Markdown. `git log` shows no history. Likely
dropped by accident during writing. Either move it under
`static/papers/` (with thumbnail) or delete it. While present at the
root, the auto-snapshot `git add content/` will not pick it up — but
any future `git add .` typo will.

### 5.4 `data/now.yaml` shows `last-updated: 2026-05-06`, today is 2026-05-07 — **NIT**

Working-tree modification, not yet committed. If the page is meant to
read "yesterday", it's fine; if it's meant to read "today", refresh.

### 5.5 Wikilinks — verified

A spot-grep for `[[...]]` references against the page slugs found
nothing pointing outside the corpus. The audit only verified the
high-traffic pages (essays, drafts, photography); a complete
walk-through would need a Hakyll-aware checker.

### 5.6 Image references — verified

All relative image references in essays I sampled
(`memento-mori`, `specification-dilemma`, `beyond-comorbidity-indices`,
`where-does-simd-help-post-quantum-cryptography`) resolve to existing
files.

---

## 6. Static assets (`static/`)

### 6.1 `static/images/canto31.jpg` is 4.0 MB — **MED**

Single largest static asset. Loads on whichever page references it. A
2400px JPEG should be ≤ 800 KB at quality 85. WebP companion will help
modern browsers, but the legacy JPEG still ships. Either re-export at
quality 80 / 2400px, or move to `content/` so the photography pipeline
can manage it.

### 6.2 No `console.log` survivors — verified

A grep across `static/js/` finds none.

### 6.3 No orphaned vendored libraries — verified

`pdfjs/`, `leaflet/`, `models/` are all `.gitignore`'d and downloaded
fresh by the Makefile.

### 6.4 No `http://` references in CSS / templates — verified

Only the SVG/XML namespace declarations in vendored `pdfjs/` use
`http://`, which is the correct (non-fetched) form for XML.

---

## 7. Templates (`templates/`)

### 7.1 No `robots.txt` and no `sitemap.xml` are emitted — **MED (SEO)**

`_site/` after a build does not contain either file. `build/Site.hs`
has no rule for them. `templates/` has no template for them. For a
content-heavy personal site this is meaningful: search engines have no
crawl guidance and no canonical URL list. Add a `create "robots.txt"`
and a `create "sitemap.xml"` rule (Hakyll supports both via
`makeItem`/`renderRss`-style compilers).

### 7.2 No `<meta name="robots">` — **NIT**

`templates/partials/head.html` has `og:image`, canonical, og:title /
og:description. No `<meta name="robots" content="…">` and no fallback
indexing hint. Together with §7.1, this is "search visibility is
unconfigured".

### 7.3 Tag-balance — verified

A pairing check across `templates/*.html` for `$if$/$endif$` and
`$for$/$endfor$` blocks (accounting for partial inheritance) reported
no mismatches. The earlier flagged occurrences resolve when the
relevant partial is included.

---

## 8. Data files (`data/`)

### 8.1 `data/annotations.json` is `{}` — **NIT**

Empty object. Either populate or document that it's intentionally a
schema slot.

### 8.2 `data/now.yaml` — see §5.4.

### 8.3 Generated files (`semantic-index.bin`, `semantic-meta.json`,
`similar-links.json`, `build-start.txt`, `last-build-seconds.txt`) —
verified gitignored.

---

## 9. nginx (`nginx/`)

### 9.1 No security headers — **HIGH (security)**

`nginx/static-assets.conf` and `nginx/popup-proxy.conf` set neither of:

- `server_tokens off;`
- `Strict-Transport-Security` (HSTS, with `preload` if HSTS-preload-listed)
- `Content-Security-Policy` (or at minimum a CSP report-only)
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: SAMEORIGIN` (or `frame-ancestors` in CSP)
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy` (camera/microphone/geolocation deny)

These would normally live in the **vhost** rather than these include
snippets, which is presumably where they belong on the VPS. But the
repo has no vhost file checked in, which means the configuration in the
repo is incomplete. Either commit a `nginx/vhost.conf` with the
security headers or document explicitly that the vhost is owned outside
the repo.

### 9.2 `nginx/static-assets.conf:75-78` — CSS/JS `must-revalidate` with
`max-age=86400` — **MED**

CSS/JS filenames are not fingerprinted (no `app.abc123.css`). A 1-day
`must-revalidate` means a stylesheet bug ships for up to 24 hours per
client. Either drop `max-age` to 3600 or add a build-time content hash
to filenames (and switch to `immutable`).

### 9.3 `popup-proxy.conf:28` — public DNS resolver — **LOW**

`resolver 1.1.1.1 8.8.8.8 ipv6=off valid=300s;`. Fine on a VPS without
local DNS, but if the host runs systemd-resolved, prefer
`127.0.0.1:53`. Also leaks "this server proxies to {arxiv,
internet-archive, ncbi}" to whichever resolver answers — the public
resolvers see the upstream queries.

### 9.4 popup-proxy caching — verified

30-day cache on arXiv/PubMed metadata, 7-day on Internet Archive,
`proxy_cache_lock on`, `proxy_cache_use_stale`. PubMed has
`limit_req zone=pubmed burst=3 nodelay;`, which matches NCBI etiquette.

---

## 10. README and ancillary docs

### 10.1 `README.md` references files that do not exist — **MED**

- `README.md:70-71`: "`paper/` — LaTeX source for in-progress academic
  papers." There is no `paper/` directory.
- `README.md:71, 82`: "`spec.md` — full architectural notes". There is
  no `spec.md`.

`yaml-source/` is mentioned **and** explained as local-only on
`README.md:118`. `paper/` and `spec.md` are not. Either create the
files (even as stubs) or remove the references.

### 10.2 README "Repository layout" section is otherwise current —
verified

`build/`, `content/`, `templates/`, `static/`, `tools/`, `data/`, all
present and described accurately.

### 10.3 `checklist.md`, `HOMEPAGE.md`, `PHOTOGRAPHY.md`, `WRITING.md` —
not shipped to `_site/` — verified

`checklist.md` is gitignored. `HOMEPAGE.md`, `PHOTOGRAPHY.md`,
`WRITING.md` are tracked but not copied into `_site/` (no Hakyll rule
matches them). Acceptable.

---

## 11. `.env`, `.env.example`, `.gitignore`

### 11.1 `.env` is mode `0600` and gitignored — verified.

### 11.2 `.env.example` documents every variable the Makefile reads —
verified.

### 11.3 `.gitignore` defense-in-depth credential exclusion — verified
(`.gitignore:10-27`).

### 11.4 Redundant entries — **NIT**

`.gitignore:81-86` lists `README.profile.md`, `README.arcana.md`,
`README.simd.md`, `README.icd.md`, `README.neuropose.md`. None exist.
These are presumably scratch-pad names; harmless but cluttering.

---

## 12. Repo hygiene

### 12.1 Working-tree dirty on `main` — **NIT**

`data/now.yaml`, `static/cv.pdf`, `static/resume.pdf` are modified;
`Fermata_2.pdf` is untracked. The CV/resume PDFs are produced by
`make pdfs`, so the diff is presumably expected. Commit or revert
before the next deploy.

### 12.2 Cache size — **NIT**

`_cache/` 8.5 MB, `dist-newstyle/` 22 MB. Reasonable.

### 12.3 Auto-commit pollution — **NIT**

`git log --oneline -20` shows ~12 of the last 20 commits are `auto:
<timestamp> [skip ci]`. This is by design (see §2.4); just note that
`git log` for narrative review needs `--invert-grep --grep='^auto:'`.

---

## 13. Recommended fix order

In rough order of cost-to-impact:

1. **§1.1** — Regenerate `cabal.project.freeze` so a fresh clone can
   build. (Single command if `tools/refreeze.sh` works; otherwise a
   manual `cabal freeze` after bumping aeson.)
2. **§9.1** — Commit a vhost (or document explicitly that the vhost
   lives on the VPS) and add the standard security header set.
3. **§1.4** — Generate and commit `tools/model-checksums.sha256`.
4. **§1.3** — Reconcile `.python-version` (3.14) and `requires-python`
   (>= 3.12).
5. **§5.1** — Decide canonical date form, then sweep `content/` or
   `WRITING.md:103`.
6. **§10.1** — Drop `paper/` + `spec.md` references from `README.md`
   (or write them).
7. **§7.1** — Emit `robots.txt` + `sitemap.xml` from Hakyll.
8. **§5.3** — Move or delete `Fermata_2.pdf`.
9. **§4.1, §4.3, §4.4, §3.2** — Small Python and Haskell hardening.
10. **§3.3** — Replace defensive partial matches with structural ones.

Everything else in this document is style/polish or low-risk
brittleness.
