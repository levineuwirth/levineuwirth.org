# Levi Neuwirth — CV and Résumé

Single-source pipeline producing two PDFs from a shared YAML content store:

- `output/cv.pdf` — multi-page academic CV.
- `output/resume.pdf` — one-page industry résumé.

## How it works

Content lives in `data/*.yml`, one file per logical section. Each entry has
`cv_visible` and `resume_visible` flags that control whether it appears in
the CV, the résumé, or both. The two Jinja2 templates in `templates/` render
into LaTeX, which `xelatex` compiles.

## Building

```bash
make all       # build both PDFs
make cv        # build CV only
make resume    # build résumé only
make clean     # remove build/ and output/
make install   # pip install pyyaml + jinja2 (user install)
```

Requires: Python 3.9+, `xelatex` (TeX Live, MacTeX, or equivalent), Source
Serif Pro and Source Sans Pro fonts. On most Linux distributions these fonts
are in the `texlive-fonts-extra` or equivalent package; on macOS they're
available through Homebrew (`brew install --cask font-source-serif-pro
font-source-sans-pro`) or directly from Adobe.

## Maintenance patterns

**Add a new publication:** edit `data/publications.yml`, append an entry,
set `cv_visible` and `resume_visible` as appropriate. Rebuild.

**Update a role:** edit `data/experience.yml`. The `cv_order` and
`resume_order` fields let you reorder per document.

**Change the ordering on the résumé without changing the CV:** adjust
`resume_order` in `experience.yml`. The CV uses `cv_order` independently.

**Move a project from "in progress" to "published":** move its entry from
`projects.yml` into `publications.yml`.

**Hide something temporarily:** flip its visibility flag to `false`. The
entry stays in source, preserving history.

## Page-count notes

- **Résumé is a clean 1 page.** It holds five Experience entries (MARS V,
  Shu Lab, NeuroAI, xAI, contracting), 3 projects, education, and header.
  The fit depends on two deliberate choices: xAI is held to a single line
  (scope line dropped, metrics bullets removed — see below), and the
  résumé-only spacing in `resume.tex.j2` (`\titlespacing`, `itemize`
  spacing, `\parskip`) is tuned so the last education note lands on page 1.
  Adding a multi-line Experience or Projects entry will spill onto a second
  page; when that happens, either trim content or nudge `\parskip` down
  (0.1em is the current value; page 1 still reads with air at that level).
- **xAI is intentionally de-emphasized.** It sits fourth in Experience and
  is one line that keeps only the `grok-code-fast-1` credential. The old
  scope line and the two metrics bullets (tool-execution / API-usage
  percentages, hallucination-rate reduction) were removed on purpose to
  keep both documents' centre of gravity on research; do not re-add them
  without a reason.
- **CV at 4 pages is normal** for this level of output. Page 4 is sparse
  (Languages, Skills, Research Interests); tightening `\titlespacing` and
  `\parskip` in `preamble.tex` can collapse to 3 pages but tends to
  reappear at 4 as soon as new content is added.

## Design notes

- Body: Source Serif Pro. Headers: Source Sans Pro. Fully black and white.
- Templates use LaTeX-safe Jinja delimiters: `%% ... %%` for blocks,
  `(( ... ))` for variables, `%# ... #%` for comments. This avoids
  collisions with LaTeX's own `%` and `{}`.
- `\entryheader` in `templates/shared/commands.tex` is the unified
  organization/role/date/location block used by both templates.
- The MARS V and Shu Lab entries have `cv_section: research` set in
  `experience.yml`, which routes them into the CV's "Research Experience"
  section while they still sit under plain "Experience" on the résumé.
  Other routing flags can be added similarly.
- **Ordering is per-axis.** The résumé sorts Experience by `resume_order`
  (research-first: MARS V, Shu Lab, NeuroAI, then xAI and contracting).
  The CV templates render in **file order** within each section — the
  `cv_order` field is documentation of intent, not a sort key, so keep the
  YAML file order and `cv_order` consistent when reordering.

## File layout

```
cv/
├── data/              # YAML content (source of truth)
│   ├── affiliations.yml
│   ├── education.yml
│   ├── experience.yml
│   ├── grants.yml
│   ├── personal.yml
│   ├── presentations.yml
│   ├── projects.yml
│   ├── publications.yml
│   └── skills.yml
├── templates/
│   ├── cv.tex.j2
│   ├── resume.tex.j2
│   └── shared/
│       ├── commands.tex
│       └── preamble.tex
├── build.py           # renders + compiles
├── Makefile
├── build/             # intermediate (.aux, .log, rendered .tex)
└── output/
    ├── cv.pdf
    └── resume.pdf
```
