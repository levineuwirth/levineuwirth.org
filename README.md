# levineuwirth.org

Personal site of Levi Neuwirth — essays, blog posts, poetry, fiction, and music.
Built with [Hakyll](https://jaspervdj.be/hakyll/) and [Pandoc](https://pandoc.org/),
with a custom build system in `build/` and a Haskell + JS + Python toolchain.

## Quickstart

```sh
make build              # one-shot production build into _site/
make dev                # dev build (drafts visible) + local server on :8000
make watch              # Hakyll live-reload dev server (drafts visible)
make clean              # cabal run site -- clean
make deploy             # build (incremental) → sign → push → rsync to VPS
make deploy-clean       # force a full rebuild, then deploy
```

`make build` is incremental by default; `tools/build-freshness.sh` forces a
full rebuild automatically when one is required for correctness (the Hakyll
rules under `build/` or the cabal metadata changed, content was deleted or
renamed, or the last full rebuild is over 7 days old — compile-time values
like stability labels drift otherwise). `make deploy-clean` forces one manually.
For day-to-day work, prefer `make dev` (which serves the site on
`http://localhost:8000`) or `make watch` (Hakyll's live-reload preview server,
which rebuilds on save and serves the site locally).

**Run `make build` any time you add or replace binary assets** (JPEG/PNG
figures, PDFs, music assets). `make dev` and `make watch` skip the
`convert-images.sh` / `pdf-thumbs` preprocessing steps, so a fresh JPEG
will have no `.webp` companion and a fresh PDF will have no thumbnail
until a full `make build` regenerates them. Once the companions exist
they survive subsequent `make dev` runs.

## What ends up in `_site/`

Essay directories are copied **recursively**: everything under
`content/essays/<slug>/` that is not itself a page source is published as-is
(`build/Site.hs`, the `content/essays/**` match). That rule is deliberately
broad so figures, data files, and scripts sit next to the prose that uses
them — but it means a stray artifact dropped into an essay directory
(`__pycache__/`, a `.log`, a scratch CSV, a private note) becomes a public
URL, whether or not Git ignores it. Git-ignoring a file does not keep it out
of the build.

What catches that is `tools/check-site.py`, the post-build artifact gate:
`make build` runs it automatically and `make validate` runs the same gate by
hand. It fails the build on unexpected artifacts in the output tree, so a
stray file is a build error rather than a silent publication. Add a
deliberate exception there rather than relying on `.gitignore`.

## Optional features

- **Similar-links and embeddings.** `tools/embed.py` precomputes
  page-level embeddings for the "Related" block. To enable:

  ```sh
  uv sync                 # creates .venv with sentence-transformers, faiss-cpu
  ```

  The build silently skips embedding when `.venv` is absent.

- **Client-side semantic search.** Downloads a quantized ONNX model
  used by `static/js/semantic-search.js` (run once; files are gitignored):

  ```sh
  make download-model
  ```

- **Image conversion.** `make build` calls `tools/convert-images.sh` to
  produce `.webp` companions next to every JPEG/PNG. Requires `cwebp`
  (`libwebp-utils` on Arch — *not* `libwebp`, which ships only the
  library and no `cwebp` binary; `webp` on Debian/Ubuntu). Without it the
  build still succeeds and simply serves the heavier originals.

- **PDF thumbnails.** `make pdf-thumbs` generates first-page thumbnails
  for PDFs in `static/papers/` using `pdftoppm` (`poppler` on Arch,
  `poppler-utils` on Debian/Ubuntu). Skipped silently when missing.

## Configuration

`.env` (gitignored, copy from `.env.example`) holds the GitHub PAT and
the VPS rsync target consumed by `make deploy`. Never commit it.

## Repository layout

- `build/` — Haskell build system (Hakyll rules, Pandoc filters, contexts).
  See `build/Filters/` for the Pandoc AST transforms (sidenotes,
  wikilinks, transclusion, score embedding, viz, …).
- `content/` — authored Markdown (essays, blog, poetry, fiction, music).
- `templates/` — Hakyll/Pandoc HTML templates.
- `static/` — CSS, JS, fonts, images, vendored PDF.js.
- `tools/` — Python tooling (embeddings, importers) and shell scripts.
- `data/` — generated and source data (commonplace.yaml, annotations.json,
  bibliographies, similar-links.json).
- `nginx/` — vhost snippets shipped to the VPS (`security-headers.conf`,
  `security-framing.conf`, `csp-report.conf`, `static-assets.conf`,
  `popup-proxy.conf`, `archive.conf`). The live vhost on the VPS is the
  source of truth; see `nginx/vhost.conf.example` for the canonical
  structure and the include order these snippets expect. Nothing here is
  deployed by `make deploy` — see "Deployment safety" below.

## Deployment safety

`make deploy` builds, signs, pushes, and rsyncs `_site/` to the VPS. Three
guards sit in front of that, and all three are worth knowing before the
first deploy of the day:

- **`make validate`** runs the test suite and then `tools/check-site.py`
  against `_site/` — the same artifact gate `make build` runs — so the
  output tree can be checked without deploying anything. Run it after any
  change to the build rules.
- **Clean-tree check.** `make deploy` refuses to publish when tracked build
  inputs differ from `HEAD`, because the revision it pushes would not
  describe the site it uploads. Commit the changes, or set
  `ALLOW_DIRTY_DEPLOY=1` to publish anyway — that records the exact dirty
  list in `data/last-deploy-dirty.txt`, which stays local and is never
  shipped.
- **`SKIP_SNAPSHOT=1`** skips `make build`'s automatic `git add content/` +
  auto-commit. Use it when building someone else's checkout, or to verify a
  build without touching history. The build is otherwise identical; only the
  stability labels of just-edited pieces can differ.

### nginx snippets are not deployed

`make deploy` only rsyncs `_site/`. Nothing under `nginx/` reaches the server
by itself — the files there are the reviewable copy of the configuration, and
they take effect only when you copy them by hand:

```sh
scp nginx/*.conf VPS:/etc/nginx/snippets/     # then, on the VPS:
sudo nginx -t                                 # must pass before reloading
sudo systemctl reload nginx
```

Always `nginx -t` before the reload: a snippet that fails to parse takes the
whole server down on a restart, and several snippets depend on directives
that live in `http { }` (`proxy_cache_path`, `limit_req_zone`, the
`csp_report` log format) and will fail the test if those are missing.
`nginx/vhost.conf.example` lists all of them.

## Architecture pointers

- `build/Site.hs` is the Hakyll rules entry point.
- `build/Patterns.hs` defines canonical content patterns shared by
  Backlinks, Authors, Tags, and Site.
- `build/Compilers.hs` wires the Pandoc filter chain into Hakyll.
- `build/Filters/Images.hs` does WebP `<picture>` wrapping; requires
  the `.webp` companions produced by `tools/convert-images.sh`.

## Graph-theory research

The graph-theory manuscript sources and experiments are maintained in
`~/Repos/research/meyniel`; its `HANDOFF.md` is the entry point for further
mathematical work. The website retains public articles and released graph-paper
assets. See [paper/README.md](paper/README.md) for the explicit export workflow.
Normal website builds do not require the research checkout or a TeX toolchain.

## License

See `LICENSE`.
