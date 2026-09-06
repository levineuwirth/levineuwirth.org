# CV and résumé publishing system

This directory renders several documents from one canonical YAML store. It has
two deliberately separate layers:

- `data/*.yml` records facts: organizations, roles, dates, degrees,
  publications, projects, links, and the fullest generally useful account of
  each item.
- `variants/*.yml` contains tracked, reusable content profiles and compatibility
  variants.
- `variants/private/*.yml` contains local application metadata: which records
  appear, their order and section, compact labels, and audience-specific
  presentation text. This directory is Git-ignored.

A new application should normally require one 30–80-line private variant file,
not a new field in every record and not a company-specific branch in Python or
LaTeX.

## Canonical data is factual

Canonical YAML is the source of truth. Correct a date, URL, institution,
authorship line, or project identity there. Do not copy a complete canonical
record into a variant.

Every addressable list record has a stable `id`, for example:

```yaml
experience:
  - id: mars-v
    organization: Cambridge AI Safety Hub
    role: MARS V Fellow
    start: July 2026
    end: Present
    # ...
```

IDs use lowercase letters/numbers separated by hyphens. They are unique within
their collection and remain stable when a display name or list position
changes. A variant refers to `experience:mars-v`, never an array index. Skill
group mapping keys (`programming`, `ml-ai`, and so on) serve as their IDs.

Adding an unknown or duplicate ID makes resolution fail before LaTeX runs.
Extra `id` fields are additive for the Haskell site consumer: Aeson ignores
them, and `web_visible` remains the site's intentionally separate visibility
axis.

## Layouts and audience variants

`layouts.yml` maps a durable layout name to a Jinja/LaTeX template:

| Layout | Template | Purpose |
| --- | --- | --- |
| `academic-cv` | `cv.tex.j2` | multi-page academic-record CV |
| `one-page-resume` | `resume.tex.j2` | website-facing one-page résumé |
| `ats-resume` | `resume_ats.tex.j2` | plain, keyword-rich ATS résumé |
| `application-cv` | `application_cv.tex.j2` | roughly two-page technical/research CV |

A variant chooses one of those layouts and independently defines a content
profile. Company-specific research/technical CVs should normally extend
`application-cv`; conventional one-page recruiting résumés can extend the
section-driven `ats-application` base. Both reuse shared templates rather than
introducing company-specific LaTeX.

`ai-infra-assurance.yml` is a tracked role-family profile for AI infrastructure,
verification, accelerator systems, trusted execution, and technical-assurance
roles. Private employer-specific variants may extend or selectively replace it.

`frontier-evals-control.yml` is the corresponding tracked profile for
frontier-model evaluation, control, monitoring, red-team, embedded-assessment,
and safety-investigation roles. It emphasizes empirical investigation and
adversarial assurance while retaining selected systems evidence.

`inference-systems-performance.yml` extends `ai-infra-assurance` for ML
inference systems, accelerator performance, workload modeling, and correctness
roles. It keeps the parent's layout and reusable presentation choices while
reweighting the narrative toward quantitative performance investigation.

`gpu-inference-systems.yml` extends `inference-systems-performance` and switches
to the compact one-page résumé layout for software-engineering roles spanning
GPU-aware inference, runtime and serving infrastructure, performance modeling,
profiling, and multi-device execution. It keeps kernel/compiler technologies out
unless canonical evidence supports them.

`trusted-compute-verification.yml` also extends `ai-infra-assurance`, but for
trusted execution, verifiable computation, high-assurance systems, and
hardware/software-boundary verification roles. It prioritizes small trusted
bases, independently checkable evidence, cryptographic authority/provenance,
and low-level system comprehension without claiming direct TEE or attestation
implementation experience.

`software-engineering-systems.yml` extends the abstract `ats-application` base
and is the conventional one-page software-engineering profile. It uses ordinary
Experience, Selected Engineering Projects, Education, and Technical Skills
sections; research talks and publications stay out of this narrative.

`agent-platform-systems.yml` extends `software-engineering-systems` for
agent-runtime, orchestration, evaluation-infrastructure, sandbox, tool-boundary,
and reliable-LLM-systems roles. It remains a conventional one-page software
engineering résumé, emphasizing implemented evaluation, execution, durable
state, crash recovery, rollback, and validation evidence rather than framework
keywords.

`technical-generalist-ai-safety.yml` extends `software-engineering-systems` as a
sibling of `agent-platform-systems`, for
technical special projects, research-program incubation, research/engineering
hybrids, and other high-ownership roles in AI safety and adjacent technical
organizations. It explicitly selects the relevant evaluation and systems
presentations without inheriting the agent-platform role family's future
positioning. It reframes the same research and engineering record around
cross-domain execution and empirical judgment, while retaining concrete
systems depth and deployed-software evidence.

The generic application template renders sections in variant order and knows
how to format entries from all maintained collections. A section may mix
collections; this supports compact sections such as “Selected Research / Talks.”

## Variant format

A private variant can contain all of the application-specific selection and
wording without exposing it in tracked files. A minimal new application in
`variants/private/example-research-engineering.yml` looks like this:

```yaml
version: 1
extends: application-cv
abstract: false
description: Example research-engineering application.
output: Levi-Neuwirth-CV-Example.pdf
document_title: Research Engineer
summary: >-
  Two or three factual sentences that replace the work a cover letter would
  otherwise do.
# Optional; leave null rather than guessing about availability or relocation.
availability: null

header:
  links: [github, linkedin]

sections:
  - id: experience
    label: Selected Experience
    entries:
      - experience:mars-v
      - experience:frontier-ai-contracting

  - id: systems
    label: Systems Projects
    entries:
      - projects:weenix
      - projects:networking-stack

overrides:
  experience:
    mars-v:
      bullets:
        - A shorter, audience-facing account using the same canonical facts.
  projects:
    networking-stack:
      label: TCP/IP and SSH Stack
      description: A compact presentation for this document.
```

Section order is the order written in `sections`. Entry order is the order of
each `entries` list. References can also use the longer equivalent form:

```yaml
- collection: experience
  id: mars-v
```

The compact `collection:id` form is preferred. Duplicate selections are
rejected. A section may set `page_break_before: true` when a maintained
two-page variant needs a stable editorial break; this is a generic layout hint,
not a company branch in the template.

### Inheritance

`extends` names another variant without the `.yml` suffix. The parent may be a
tracked file in `variants/` or another local file in `variants/private/`.
Mapping values merge recursively. Scalars and lists replace the inherited
value. This keeps inheritance predictable: a child that writes `sections` owns
the entire section list instead of receiving an implicit list concatenation.
Set an inherited named presentation-set selection to `null` when the child no
longer selects that record.

The reusable `application-cv` base supplies the research-application layout,
default header-link selection, and an unset availability field. The
`ats-application` child switches to the ATS layout and a compact header while
remaining content-free. Both are `abstract: true`, so they can be listed and
validated but not built. A concrete child must set `abstract: false` and
provide an output and sections. Unknown parents and inheritance cycles fail
with the resolution path.

### Safe presentation overrides

Overrides are a closed allowlist. Common presentation fields are:

- `label`, `summary`, `short_summary`, `notes`
- `section` and integer `order` (most variants should simply use the section
  and entry list order)
- `bullets`, `description`, `preamble`, and `scope` where meaningful for that
  collection
- `note` for grants
- `items` for skill groups

Skill `items` must be a subset of that group's canonical items. This permits
keyword curation without letting an application YAML invent a skill.

Canonical factual fields are not legal overrides. In particular, a variant
cannot replace:

- institution or organization identity;
- degree or role identity;
- authorship, publication/presentation title, or venue;
- start/end dates or years;
- canonical URLs and links;
- grant identity.

For example, `organization: Different Company` under an experience override is
rejected with the record ID and the legal fields. If a fact is wrong, edit
canonical data. If the fact is right but too verbose for one audience, use a
legal presentation field.

`section` may move a selected entry to another declared section. `order` sorts
within the destination section. An unknown destination is rejected. Explicit
section/entry lists are usually clearer for a one-off application.

### Reusable named presentation sets

When several maintained role-family variants need distinct presentations of
the same well-supported record, the record may define named
`presentation_sets`. These sets accept the same safe prose fields as overrides,
except positional `section` and `order`; factual identity, dates, URLs, and
other immutable fields remain illegal. For example:

```yaml
# data/experience.yml
- id: mars-v
  organization: Cambridge AI Safety Hub
  # canonical facts...
  presentation_sets:
    inference-systems-performance:
      bullets:
        - A reusable performance-oriented account of the canonical work.

# variants/inference-systems-performance.yml
presentation_sets:
  experience:
    mars-v: inference-systems-performance
```

The selected set is applied before ordinary `overrides`, so a variant can still
make a small legal adjustment without copying the whole set. Presentation-set
selection composes through inheritance: a child can replace one parent's set
name while inheriting all other selections. Unknown sets, dead selections,
malformed fields, and factual fields fail during resolution.

### Header links, summary, and availability

`header.links` selects stable IDs from `personal.yml`; variants cannot replace
their canonical labels or URLs. `document_title`, `summary`, and `availability`
belong to the application profile rather than the biography. They therefore
live in variants.

An unset `availability: null` prints nothing. Fill it only when the exact
full-time/relocation statement is known.

## Building and listing

From `yaml-source/`:

```bash
python build.py --list
python build.py ai-infra-assurance
python build.py frontier-evals-control
python build.py inference-systems-performance
python build.py gpu-inference-systems
python build.py trusted-compute-verification
python build.py software-engineering-systems
python build.py agent-platform-systems
python build.py technical-generalist-ai-safety
python build.py --variant ai-infra-assurance
make variant NAME=ai-infra-assurance
```

Outputs are written to `output/` using the filename declared by the variant.
A private application might produce `output/Levi-Neuwirth-CV-Example.pdf`; it
does not replace the website's `cv.pdf` or `resume.pdf`. `--list` labels each
discovered definition as `tracked` or `private`.

Requirements are Python 3.9+, PyYAML, Jinja2, and (for PDF compilation)
`xelatex`. Source Serif Pro and Source Sans Pro are preferred; the shared
preamble falls back to TeX Gyre fonts.

## Tracked, private, and published material

Git tracking and website publication are separate decisions:

| Thing | Git tracked? | Public website? |
| --- | ---: | ---: |
| Canonical `data/*.yml` | **Yes** | indirectly |
| Templates and build system | **Yes** | No |
| Generic definitions in `variants/*.yml` | **Yes** | No |
| Generated files in `output/` | **No** | **No** |
| Canonical `static/cv.pdf` | **Yes** | **Yes** |
| Canonical `static/resume.pdf` | **Yes** | **Yes** |
| Application metadata in `variants/private/` | **No (private)** | No |
| Company-specific one-off tweaks | **No (private/transient)** | No |

The build directory and every PDF under `yaml-source/output/` are ignored,
including temporary builds named `cv.pdf` and `resume.pdf`. The separately
tracked website artifacts are `../static/cv.pdf` and `../static/resume.pdf`;
building a variant does not publish or copy anything into `static/`.

Create a private application by making `variants/private/` and writing a YAML
file there. The resolver discovers it automatically, permits it to extend a
tracked generic base, validates it alongside tracked variants, and writes its
PDF only to ignored `output/`. Do not put company names, company-specific
summaries, company-specific availability details, or one-off tailoring in a
tracked generic variant.

`.gitignore` prevents accidental ordinary staging, but it is not encryption or
an access-control boundary: `git add -f` can still force-add a private file.
Before committing, verify a private variant with:

```bash
git check-ignore -v variants/private/example-research-engineering.yml
git status --short --ignored variants/private output
```

## Legacy compatibility

The historical data fields remain during the staged migration:

- `cv_visible`, `resume_visible`, `web_visible`
- `cv_order`, `resume_order`, `cv_section`
- `notes_cv`, `notes_resume`

The website academic CV and legacy résumé compatibility variants use the
document-specific CV/résumé axes. New application variants use generic ID
selection and overrides.

The old commands and Make targets resolve through named variants:

| Existing command | Variant | Layout | Output |
| --- | --- | --- | --- |
| `python build.py cv` / `make cv` | `cv` | `academic-cv` | `cv.pdf` |
| `python build.py resume` / `make resume` | `resume` | `one-page-resume` | `resume.pdf` |
| `python build.py resume_ats` / `make resume_ats` | alias of `resume-ats` | `ats-resume` | `resume_ats.pdf` |
| `python build.py all` / `make all` | `cv`, `resume` | mixed | both website PDFs |
| `python build.py all_all` / `make all_all` | plus `resume-ats` | mixed | all three named PDFs |

The website academic CV and legacy résumé templates still read the old
visibility/order fields, keeping their rendered content and page budgets
materially unchanged. This adapter can be retired later without affecting
generic application variants.

## Validation and tests

Configuration-only validation needs no TeX installation:

```bash
python build.py --validate-config
python -m unittest discover -s tests -v
```

The tests cover inheritance (including private children of tracked bases),
selection, ordering, section moves, presentation overrides, dead overrides,
bad IDs, duplicate canonical IDs, duplicate concrete output filenames, illegal
factual overrides, skill subsets, cycles, missing templates, and legacy target
resolution.

Full validation also compiles every discovered non-abstract tracked or private
variant when `xelatex` is present:

```bash
make validate
```

Resolver failures are deliberately early and specific: unknown variant,
inheritance cycle, malformed YAML/schema, duplicate or unknown record ID,
dead or illegal override, duplicate concrete output filename, unknown layout,
unsafe output path, and missing template all stop before rendering.

## Repository shape

```text
yaml-source/
├── data/                    # canonical facts and stable IDs
├── variants/                # tracked reusable/compatibility profiles
│   ├── application-cv.yml   # abstract reusable base
│   ├── ats-application.yml  # abstract section-driven ATS base
│   ├── ai-infra-assurance.yml # reusable role-family profile
│   ├── frontier-evals-control.yml # evaluation/control role-family profile
│   ├── inference-systems-performance.yml # inference/performance child profile
│   ├── gpu-inference-systems.yml # one-page GPU/inference-systems child profile
│   ├── trusted-compute-verification.yml # trusted-compute child profile
│   ├── software-engineering-systems.yml # conventional one-page SWE profile
│   ├── agent-platform-systems.yml # one-page agent-platform systems child
│   ├── technical-generalist-ai-safety.yml # one-page technical-generalist child
│   ├── cv.yml               # canonical website academic CV
│   ├── resume.yml
│   ├── resume-ats.yml
│   └── private/             # ignored local application metadata
│       └── example-research-engineering.yml
├── layouts.yml              # layout name -> shared template
├── templates/
│   ├── application_cv.tex.j2
│   ├── cv.tex.j2
│   ├── resume.tex.j2
│   ├── resume_ats.tex.j2
│   └── shared/
├── tests/test_variants.py
├── build.py
├── Makefile
├── build/                   # rendered TeX and xelatex intermediates (ignored)
└── output/                  # PDFs (ignored)
```

Templates use LaTeX-safe Jinja delimiters: `((* ... *))` for blocks,
`((( ... )))` for values, and `((# ... #))` for comments. Shared typography,
font fallbacks, section rules, and entry headers live under `templates/shared/`.
