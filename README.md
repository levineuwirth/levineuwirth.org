# levineuwirth.org

Personal site of Levi Neuwirth — essays, poetry, fiction, music, photography,
and a CV.
Built with [Hakyll](https://jaspervdj.be/hakyll/) and [Pandoc](https://pandoc.org/),
with a custom build system in `build/` and a Haskell + JS + Python toolchain.

## Quickstart

```sh
make build              # one-shot production build into _site/
make dev                # dev build (drafts visible) + local server on :8000
make watch              # Hakyll live-reload dev server (drafts visible)
make clean              # cabal run site -- clean
make deploy             # preflight → build (incremental) → validate → sign
                        #   → recheck → push → rsync to VPS
make deploy-clean       # force a full rebuild, then deploy
```

`make build` is incremental by default; `tools/build-freshness.sh` forces a
full rebuild automatically when one is required for correctness (the Hakyll
rules under `build/` or the cabal metadata changed, content was deleted or
renamed, route-defining frontmatter such as `tags:` changed, or the last full
rebuild is over 7 days old — compile-time values like stability labels drift
otherwise). `make deploy-clean` forces one manually.
For day-to-day work, prefer `make dev` (which serves the site on
`http://localhost:8000`) or `make watch` (Hakyll's live-reload preview server,
which rebuilds on save and serves the site locally).

`build`, `deploy`, `watch` and `dev` each hold an exclusive lock on
`data/.site-build.lock` (`tools/with-lock.sh`, via `flock`), as do the
targets that write `_site/`, `_cache/` or `static/` (`clean`, `sign`,
`compress-assets`, `convert-images`, `thumbnails`, `pdf-thumbs`) and
`validate`. A second one fails at once instead of interleaving writes;
`LOCK_TIMEOUT=<seconds>` makes it wait. `watch` and `dev` hold the lock for
as long as their server runs. The lock is re-entrant, so the targets a locked
build or deploy runs in turn pass straight through.

**Run `make build` any time you add or replace binary assets** (JPEG/PNG
figures, PDFs, music assets). `make dev` and `make watch` skip the
`convert-images.sh` / `pdf-thumbs` preprocessing steps, so a fresh JPEG
will have no `.webp` companion and a fresh PDF will have no thumbnail
until a full `make build` regenerates them. Once the companions exist
they survive subsequent `make dev` runs.

## Requirements

- GHC and `cabal` (`cabal run site` builds the generator on first use).
- `pagefind` on `PATH`. Not optional: `make build` indexes `_site/` with it
  and fails without it.
- `python3`, `git`, `curl`, `unzip` and `sha256sum`. The build vendors
  PDF.js, Leaflet and the search model through `tools/download-*.sh`, which
  verify pinned SHA-256 sums (`unzip` is for PDF.js).
- `flock` (util-linux); without it `tools/with-lock.sh` warns and runs
  unlocked.
- For `make deploy`: `gpg` with the signing subkey, `ssh` and `rsync`.
- Optional: `uv`, `cwebp` and `pdftoppm` — see below.

## What ends up in `_site/`

Essay directories are copied **recursively**: everything under
`content/essays/<slug>/` that is not itself a page source is published as-is
(`build/Site.hs`, the `content/essays/**` match). That rule is deliberately
broad so figures, data files, and scripts sit next to the prose that uses
them — but it means a stray artifact dropped into an essay directory
(a scratch CSV) becomes a public URL, whether or not Git ignores
it. Git-ignoring a file does not keep it out of the build. A stray `.md`
there (say `notes.md` beside `index.md`) is compiled as an essay.

Two checks stand in the way, and both go by file name only.
`neverPublish` in `build/Site.hs` keeps private-looking names out of the
build: `*.local.md`, `*.draft.md`, key and credential files, `.env`, editor
backups, swap and `.pyc` files, `*.tmp`, `*.part`, `*.partial`, `*.log`, `__pycache__/`.
`tools/check-site.py`, the post-build artifact gate, fails the build when a
name on its own list (`PRIVATE_FILE_GLOBS`) reaches `_site/` anyway,
compressed and signed copies included. `make build` runs it automatically
and `make validate` runs the same gate by hand. Neither can tell what an
ordinary file is for: a CSV or a `notes.md` passes both, so keep
those out of essay directories, or give a private note a `.local.md` name.
To exclude a new kind of file, add it to both lists; `.gitignore` will not
do it.

## Optional features

- **Similar-links and embeddings.** `tools/embed.py` precomputes
  page-level embeddings for the "Related" block. To enable:

  ```sh
  uv sync                 # creates .venv with sentence-transformers, faiss-cpu
  ```

  Without `.venv` the build skips embedding (and the photo sidecar and
  archive steps) with a notice and continues.

- **Client-side semantic search.** Downloads a quantized ONNX model
  used by `static/js/semantic-search.js` (run once; files are gitignored):

  ```sh
  make download-model
  ```

- **Image conversion.** `make build` calls `tools/convert-images.sh` to
  produce `.webp` companions next to every JPEG/PNG. Requires `cwebp`
  (`libwebp-utils` on Arch — *not* `libwebp`, which ships only the
  library and no `cwebp` binary; `webp` on Debian/Ubuntu). Without it the
  build still succeeds, prints a prominent warning, and serves the heavier
  originals; `make validate REQUIRE_WEBP=1` makes that an error.

- **PDF thumbnails.** `make pdf-thumbs` (also run by `make build`)
  generates first-page thumbnails for every PDF under `static/` except the
  vendored `static/pdfjs/`, using `pdftoppm` (`poppler` on Arch,
  `poppler-utils` on Debian/Ubuntu). Without it the target prints a notice
  and skips.

## Configuration

`.env` (gitignored, copy from `.env.example`) holds the VPS rsync target
(`VPS_USER`, `VPS_HOST`, `VPS_PATH`) consumed by `make deploy`. Never commit
it. `git push` uses your own git credentials (credential helper), not
anything in `.env`.

`GITHUB_TOKEN` is read only by `tools/code-refs.py`, from the environment, to
raise the GitHub API rate limit for code snapshots. Export it in your shell:
the Makefile does not pass it on from `.env`.

## Repository layout

- `build/` — Haskell build system (Hakyll rules, Pandoc filters, contexts).
  See `build/Filters/` for the Pandoc AST transforms (sidenotes,
  wikilinks, transclusion, score embedding, viz, …).
- `content/` — authored Markdown (essays, poetry, fiction, music,
  photography, standalone pages).
- `templates/` — Hakyll/Pandoc HTML templates.
- `static/` — CSS, JS, fonts, images, vendored PDF.js.
- `tools/` — Python tooling (embeddings, importers) and shell scripts.
- `data/` — generated and source data (commonplace.yaml, annotations.json,
  bibliographies, similar-links.json).
- `yaml-source/` — the CV and résumé sources: `build/Vita.hs` renders
  `/about.html` from `yaml-source/data/`, and `make pdfs` typesets
  `static/cv.pdf` and `static/resume.pdf` (needs XeLaTeX).
- `archive/` — preserved copies of cited external works, listed in
  `archive/manifest.yaml`; see `ARCHIVE.md`.
- `code-refs/` — snapshots of linked GitHub code for the hover popups,
  written by `tools/code-refs.py` during the build. Tracked: commit it when
  a build changes it, or `make deploy` refuses.
- `tests/` — the Python `unittest` suite run by `make test` and
  `make validate`.
- `systemd/` — units and timers for the VPS (backups, updates) and the
  laptop's `archive-check`; installed by hand, see `systemd/README.md`.
- `forgejo/`, `couchdb/` — Docker Compose sources for the VPS's Forgejo
  and Obsidian LiveSync CouchDB, with upgrade and restore runbooks.
- `anki-sync/` — environment templates and roadmap for the VPS's Anki
  sync server.
- `paper/` — pointer to the separate graph-theory research repository.
- `nginx/` — every nginx file on the VPS: `nginx.conf`, the server blocks
  (`levineuwirth.conf`, `forgejo.conf`, the two sync servers, a default
  server), the site's snippets and their `conf.d` companions.
  `nginx/README.md` maps each to its path and has the install steps.
  Nothing here is deployed by `make deploy` — see "Deployment safety"
  below.

## Deployment safety

`make deploy` builds, validates, signs, pushes, and rsyncs `_site/` to the
VPS. `git push -u origin main` goes to both Forgejo and GitHub (`origin`
has two push URLs), and the rsync is preceded by a dry run that refuses a
destination without an `index.html` or a transfer that would delete more
than `DEPLOY_MAX_DELETE` files (see `tools/deploy-guard.sh`). These guards
are worth knowing before the first deploy of the day:

- **`make validate`** runs the test suite and then `tools/check-site.py`
  against `_site/` — the same artifact gate `make build` runs — so the
  output tree can be checked without deploying anything. Run it after any
  change to the build rules.
- **Branch check.** `make deploy` refuses to run on any branch but `main`,
  since it pushes `main` while the site would be built from that branch.
- **Clean-tree check.** `make deploy` refuses to publish when build inputs
  differ from `HEAD` (tracked changes, or untracked files outside `data/`),
  because the revision it pushes would not describe the site it uploads.
  It runs the code-ref and archive fetchers first, so a snapshot the build
  would add counts too. Commit the changes, or set
  `ALLOW_DIRTY_DEPLOY=1` to publish anyway — that records the exact dirty
  list in `data/last-deploy-dirty.txt`, which stays local and is never
  shipped.
- **Recheck.** After the build, validate and sign, and before the push,
  `deploy-recheck` repeats that check (now including `content/` and
  `tests/`), and the deploy confirms `HEAD` is still the commit that was
  built. An edit made while the build ran stops the deploy with nothing
  pushed or published.
- **Score pages.** The score pages are gitignored, so `deploy-preflight`
  runs `tools/music-import.py check` and refuses when pages are missing or
  incomplete, rather than letting a fresh checkout delete the published
  scores.
- **`SKIP_SNAPSHOT=1`** skips `make build`'s automatic `git add content/` +
  auto-commit. Use it when building someone else's checkout, or to verify a
  build without touching history. The build is otherwise identical; only the
  stability labels of just-edited pieces can differ.

### nginx snippets are not deployed

`make deploy` only rsyncs `_site/`. Nothing under `nginx/` reaches the server
by itself. The files there are the configuration the VPS runs, and each takes
effect only when copied to its own path (snippets, `conf.d`, server blocks
and `nginx.conf` all differ); `nginx/README.md` has the table and the steps.

Always `nginx -t` before the reload: a snippet that fails to parse takes the
whole server down on a restart, and several snippets depend on directives
that live in `http { }` (`proxy_cache_path`, `limit_req_zone`, the
`csp_report` log format), in the `conf.d` files beside them.

## Architecture pointers

- `build/Site.hs` is the Hakyll rules entry point.
- `build/Patterns.hs` defines canonical content patterns shared by
  Backlinks, Authors, Tags, and Site.
- `build/Compilers.hs` wires the Pandoc filter chain into Hakyll.
- `build/Filters/Images.hs` does WebP `<picture>` wrapping; requires
  the `.webp` companions produced by `tools/convert-images.sh`.

## Graph-theory research

The graph-theory manuscript sources and experiments are maintained in a
separate research repository, `meyniel`; its `HANDOFF.md` is the entry point
for further mathematical work. The website retains public articles and released graph-paper
assets. See [paper/README.md](paper/README.md) for the explicit export workflow.
Normal website builds do not require the research checkout or a TeX toolchain.

## License

The website code and its software documentation are [MIT-licensed](LICENSE).
Levi Neuwirth's original prose and textual content data are licensed under
[CC BY-NC-SA 4.0](LICENSE-CONTENT), unless a page says otherwise. These grants
do not relicense third-party material or public-domain works, and do not
automatically cover photographs, artwork, scores, recordings or papers.
See [the scope and third-party notices](THIRD-PARTY.md), also published at
[/licenses.html](https://levineuwirth.org/licenses.html).
