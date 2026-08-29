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
make deploy             # clean → build → sign → push → rsync to VPS
```

`make build` always runs `make clean` implicitly when invoked from `make deploy`.
For day-to-day work, prefer `make dev` (which serves the site on
`http://localhost:8000`) or `make watch` (Hakyll's live-reload preview server,
which rebuilds on save and serves the site locally).

**Run `make build` any time you add or replace binary assets** (JPEG/PNG
figures, PDFs, music assets). `make dev` and `make watch` skip the
`convert-images.sh` / `pdf-thumbs` preprocessing steps, so a fresh JPEG
will have no `.webp` companion and a fresh PDF will have no thumbnail
until a full `make build` regenerates them. Once the companions exist
they survive subsequent `make dev` runs.

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
  (`libwebp` on Arch, `webp` on Debian/Ubuntu).

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
  `static-assets.conf`, `popup-proxy.conf`). The live vhost on the VPS
  is the source of truth; see `nginx/vhost.conf.example` for the
  canonical structure and the include order these snippets expect.

## Architecture pointers

- `build/Site.hs` is the Hakyll rules entry point.
- `build/Patterns.hs` defines canonical content patterns shared by
  Backlinks, Authors, Tags, and Site.
- `build/Compilers.hs` wires the Pandoc filter chain into Hakyll.
- `build/Filters/Images.hs` does WebP `<picture>` wrapping; requires
  the `.webp` companions produced by `tools/convert-images.sh`.

## License

See `LICENSE`.
