# levineuwirth.org

[![tests](https://github.com/levineuwirth/levineuwirth.org/actions/workflows/tests.yml/badge.svg)](https://github.com/levineuwirth/levineuwirth.org/actions/workflows/tests.yml)

The personal site of Levi Neuwirth: essays, poetry, fiction, music,
photography and a CV. It is built with Ozymandias, a static site engine on
[Hakyll](https://jaspervdj.be/hakyll/) and [Pandoc](https://pandoc.org/),
whose repository, [Ozymandias](https://git.levineuwirth.org/neuwirth/ozymandias),
is checked out beside this one. Everything here is the site's own: its
writing, its configuration and overrides of the engine, and the
operations of the server it runs on.

## Building

Clone Ozymandias beside this repository, as `../ozymandias`; the Makefile
links it here as `engine`, which Git ignores. A site builds from the
engine's latest commit: there are no pins.

```sh
make venv          # once: the Python tools' environment, in .venv
make dev           # drafts visible, served on http://localhost:8000
make build         # the production build, into _site/
make test          # the site's and the engine's tests
make test-clean    # the same, on HEAD, in fresh clones of both
make deploy        # build, validate, sign, push both, and publish to the server
```

`make build` is incremental, and rebuilds from scratch on its own when it
must. It also commits `content/` (`SKIP_SNAPSHOT=1` skips that). Run it
after adding images or PDFs: `make dev` skips their WebP companions and
thumbnails.

The build needs GHC and `cabal`, `pagefind`, and `python3` with PyYAML;
`cwebp`, `pdftoppm` and `uv` are optional, and `make pdfs` (the CV) needs
XeLaTeX. A deploy needs `gpg` with the signing subkey, `ssh` and `rsync`,
and the server's address in `.env` (copy `.env.example`; never commit it).

## Layout

- `site.yaml`: the site's identity, sections, feeds, navigation and the
  engine's switches, all of them on here.
- `content/`: the writing. `WRITING.md` covers front matter and every
  authoring feature. Everything in an essay's directory is published, so
  keep scratch files out of it, or give a private note a `.local.md` name.
- `templates/`, `static/`: the site's templates (the CV pages, and its
  footer, ornament and not-found page) and assets (fonts, images, papers,
  icons), which override the engine's where `overrides.yaml` says so.
- `data/`, `yaml-source/`, `archive/`, `code-refs/`: annotations,
  bibliographies and similar links; the CV's sources; preserved copies of
  cited works (`ARCHIVE.md`); snapshots of linked code.
- `tests/`: the site's own tests, its identity records and the browser
  baselines.
- `tools/`: the site's own tools: the server's backup, update and status
  scripts, `cv-pdfs.py`, and the font configuration the engine's subsetter
  reads.
- `nginx/`, `systemd/`, `forgejo/`, `couchdb/`, `anki-sync/`, `anubis/`:
  the server's configuration and services, each with its README or
  runbook.
- `paper/`: a pointer to the graph-theory research, kept in its own
  repository (`meyniel`).

## Deploying

`make deploy` runs only on `main`, with a clean tree and a clean engine on
its `main`, and stops if either changes while it builds. It pushes the
engine's `main`, then the site's, to Forgejo and GitHub, then sends the
new scripts and stylesheets before any page that names them, keeping
earlier versions for 90 days for tabs left open. An rsync dry run refuses a
destination without an `index.html`, or a transfer deleting too much.
`make deploy SKIP_TESTS=1` is for a change the tests can say nothing
about, such as a typo.

Nothing under `nginx/` is deployed. Copy each file to its place on the
server as `nginx/README.md` says, and run `nginx -t` before reloading.

## License

The website code and its software documentation are licensed under
[GPL-2.0-or-later](LICENSE), with an additional permission for the websites it
generates. Versions through commit `0ff8792` were MIT-licensed.
Levi Neuwirth's original prose and textual content data are licensed under
[CC BY-NC-SA 4.0](LICENSE-CONTENT), unless a page says otherwise. These grants
do not relicense third-party material or public-domain works, and do not
automatically cover photographs, artwork, scores, recordings or papers.
See [the scope and third-party notices](THIRD-PARTY.md), also published at
[/licenses.html](https://levineuwirth.org/licenses.html).
