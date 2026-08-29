---
title: Colophon
date: 2026-03-21
status: "Durable"
confidence: 93
tags: [meta]
abstract: On the design, tools, and philosophy of this site — and by extension, its author.
history:
  - date: "2026-06-10"
  - date: "2026-05-08"
  - date: "2026-04-27"
  - date: "2026-04-17"
  - date: "2026-04-12"
  - date: "2026-04-11"
  - date: "2026-04-10"
  - date: "2026-03-27"
  - date: "2026-03-26"
  - date: "2026-03-25"
  - date: "2026-03-24"
  - date: "2026-03-23"

---

::: dropcap
A personal website is not a publication. It is a position. A publication presents work
in a finalized, immutable state, and carries with it some sort of declaration - "this is my most polished and prized work!";
a position is something you inhabit, argue from, and continuously
revise in public. This page explains the design decisions forming my broader **position** and why they took the form they did.

What follows is a colophon in the grand old sense: a printer's note at the end of the book,
recording how it was made, who made it, etc. The difference: here, the
printer and the author are the same person, and the process of making is itself not only *a* form
of argument, but *the only* form of argument permitted.
:::

---

## Typography

::: dropcap
You are reading this sentence in SPECTRAL, which is not only a font with particular personal importance to me, but also an exceedingly pleasing font to read.  [OpenType]{.smallcaps} features — `smcp`, `onum`, `liga`, `calt` are used throughout the website, which necessitates our self-hosting setup.^[Google Fonts strips OpenType features during
subsetting for bandwidth. Self-hosting with `pyftsubset` preserves `smcp` (small
capitals), `onum` (old-style figures), `liga` (common ligatures), and the full optical
size range. The difference is visible: old-style figures sit on the baseline rather
than hanging above it, small capitals are drawn to match the x-height rather than being
shrunken full caps, and ligatures prevent collisions in letter pairs like *fi* and *fl*.]
:::

The UI and headers are Fira Sans. Variation is good, and moreover, humanist sans are rather ubiquitous (we have Frutiger to thank for this fact!) - perhaps I am making some type of statement by not choosing one of the more corporate variations of it, like the dreaded Calibri and Tahoma you might recognize from Microsoft products. Code uses Jetbrains Mono, which is simply the font that I use within my editor. Code should look like code, simple as that.

The monochrome palette is an application of restraint grounded in my studies of Tools for Thought.
Color is often used to do work that typography
should do, such as demonstrating hierarchy, creating emphasis, etc. When those
functions are handled by weight, size, and spacing instead^[Color and saturation/hue are actually well known to be less effective than other means of distinguishment. I refer you to Tufte's *The Visual Display of Quantitative Information* for more.], color becomes available for the things it cannot be substituted for — and on a site with no data visualizations
requiring color encoding, those things turn out to be very few.^[The one exception is
the heatmap on the statistics page, which uses a four-step greyscale scale. Even there,
the encoding is luminance rather than hue.]
---

## The Build

This is a [Static Website](https://en.wikipedia.org/wiki/Static_web_page). For the purposes of this website, though the content is highly dynamic and iterated upon, the medium of expression is rather stable. There are numerous advantages to using a static webpage, many of which are focused at the Hetzner box from which this webpage is served. I use [Hakyll](https://jaspervdj.be/hakyll/) for reasons of performance, extensibility, and, of course given the underlying language Haskell, elegance! I had been wanting to do a project in Haskell ever since I took my undergraduate programming languages course,^[The programming languages course at Brown, somewhat infamous, is taught entirely with Racket, which is essentially a dialect of Lisp. The course itself is extremely focused within the functional paradigm as far as implementations go. I am aware that Racket itself, curiously, has some means by which static webpages can be built - the course infrastructure was produced this way, and this website has in a few places taken minor inspiration from it!] and Hakyll was more extensible and thus suitable than the alternative I was looking at most strongly, Hugo (in Go, a language with which I am intimately familiar). The philosophy of a static website is that the website is a program and the content is the source code^[Source code here **chiefly distinct** from mere markup language, like HTML.]. The step of compilation present in Haskell, which is outlined below, means that what you have here received in your browser is not merely a runtime rendering decision, but rather a deterministic artifact. By this step of compilation, the [Markdown](https://en.wikipedia.org/wiki/Markdown) in which I write these webpages is transformed to exactly what you currently see.

The [AST](https://en.wikipedia.org/wiki/Abstract_syntax_tree) we use is heavily customized and modified. The chain is roughly markdown -> pandoc -> citations -> wikilinks -> preprocessing -> sidenotes -> smallcaps and dropcaps -> links -> images -> math. Mathematics with LaTeX requires a second pass and is rendered at build-time with KaTeX - no math rendering occurs in your browser. Samples from music are displayed as SVGs, generally typeset with Lilypond through some helper scripts I wrote to automate the process.

Not all content on this site is markdown. A handful of pages — the [[Library]], the [[Commonplace]], and [[Current]] — are driven instead by YAML files under `data/`, rendered through dedicated Haskell modules that parse the schema, apply a sort or filter discipline particular to the surface, and emit the rendered HTML directly into a template. The split is deliberate: prose belongs in markdown, where the discipline is rhetorical; curated lists belong in YAML, where the discipline is editorial. The Current page, for instance, ladders entries by status (*in-review* → *revising* → *drafting* → *building*) before falling back to recency, and stamps each entry with its own "last updated" date — features that would be tedious to maintain in markdown but trivial to express in a small declarative schema.

The semantic search model is a particularly intriguing aspect of the website. The model used is self-hosted, with weights served from the same origin. There are NO external API calls when you use this, in contrast to just about every other similar feature on other websites. This is essential for the privacy model that this site strives to achieve - see **Design Decisions** for more.

A full accounting of what this build process has actually produced is available at the [[Build]] page. It is generated automatically at each compile: corpus word counts, length distributions, tag frequencies, link analysis, epistemic coverage, repository metrics, and build timing — all computed from the same source tree that produces the content. Think of it as the build system reporting on itself.

{{build}}

---

## The Computing Environment

::: dropcap
I am, like many passionate nerds within the realm of computing, obsessive over my technological choices. They are the subject of constant critique, review, revision, etc. I believe in the value of putting deep thought into the systems that one interacts with, rather than accepting the first showing of convenience and going with the flow. A system interacted with is an experience moreso than a mere tool.
:::

### Desktop

My primary desktop is a rig I built myself, running **Gentoo Linux** with **Hyprland** and a custom shell, *Levshell*, implemented with [Quickshell](https://github.com/quickshell-mirror/quickshell). The reasons for Gentoo are worth stating explicitly, since the choice is frequently met with bewilderment:

- Compiling software from source delivers measurable performance increases — not marginal ones.
- It provides fine-grained control over software configuration via [USE]{.smallcaps} flags, linking options, and the like. This matters for a machine tuned to a high degree of specificity.
- It is, in my experience, the best-maintained Linux distribution I have ever used.
- The community is phenomenal.

I have strong hardware preferences to match; [AMD]{.smallcaps} hardware is used in favor of Intel and NVIDIA. I have used at least 2 distinct chips from each manufacturer and consistently find that, as far as x86-64 is concerned, AMD is the clear winner. As for my preference for AMD gpus, not only do I quite disagree with the business direction of NVIDIA, but the VRAM offerings are simply superior from AMD.

### Laptop

For mobile computing, I use a [P]{.smallcaps}-series ThinkPad running **Arch Linux** — the same Hyprland environment, the same *Levshell*, the same muscle memory down to the config file. Gentoo is impractical on battery-constrained hardware, as compilation times are simply too long and require active power connection. Arch is a sound alternative, configurable enough to pass. Portage is better than pacman in my opinion, but pacman is still far better than horrid package managers like apt.

### Editor

Everything on this site — every word of prose, every line of Haskell, every [CSS]{.smallcaps} rule — was written in **Emacs**. I have used most of the major editors, and consistently experiment with others, but have yet to find any which come close to the power of Emacs. I intend to complete a project called "Pmacs," which will introduce much moderner parallelization, among other features, to Emacs. This is a project I intend to tackle in the Summer of 2026 at high intensity.

### Privacy-First Computing

My email and [VPN]{.smallcaps} are self-hosted; I use Thunderbird as a client for the former. For browsing I use [LibreWolf](https://librewolf.net/), not Firefox: the Chromium monopoly and Mozilla's evident incompetence at browser development are, to me, equally concerning developments, and LibreWolf is the most coherent response to both. My phone runs [GrapheneOS](https://grapheneos.org/) — the only reasonably secure and private option for a mobile device, and one whose restrictions are, frankly, a feature rather than a limitation.

The principle underlying all of these choices is the same one underlying the site's **No Tracking** policy: privacy is an architectural decision, not a settings toggle. Bolting on privacy after the fact, whether in a browser or on a website, is not privacy — it is the appearance of privacy.

---

## [AI]{.smallcaps} and This Site

::: dropcap
I will never use AI to write, whether for my personal communications with anyone or for pieces on this website. I take this extremely seriously - writing is religious in severity to me. The writing on this website is wholly human and wholly my own, to the extent that any writing can be.
:::

Much of the code that comprises the build system of this website was created in collaboration with AI. Rather than "vibe coding" proper, this was the result of an intensive engineering process where AI and I were equals in collaboration. Notably, all of the major architectural choices, design decisions, idiosyncracies, and elements of the tech stack were chosen entirely by me, and AI systems were only used to automate production of some (but not all) of the code that was required.

The commit history, of course, is available for you to view and licensed accordingly - see **No Tracking** for more.

---

## Design Decisions

### Sidenotes

The sidenotes are provided by a JavaScript file that was forked from the website of Gwern Branwen and authored by
Said Achmiz; I have simplified the script to fit the needs of this website and made some minor modifications.


### No Tracking

The site has no analytics, no visit counters, no fingerprinting, and no third-party
scripts.^[This is enforced at the nginx level via [CSP]{.smallcaps} headers, not just
by omission. The Content Security Policy prevents any script not explicitly whitelisted
from executing. The whitelist is short.] The Hetzner VPS that provides this content runs
only open source software, and my machines use *almost exclusively*^[It is nearly impossible to run an entirely free system, but in approximation, it is actually wonderfully easy.] the same. The code is licensed under MIT and hosted
on a [self-hosted Forgejo instance](https://git.levineuwirth.org/neuwirth/levineuwirth.org) at this domain, with a [GitHub mirror](https://github.com/levineuwirth/levineuwirth.org); you are welcome
to inspect it, fork it, or, more broadly, do whatever you please with it.

### Living Documents

The dominant convention of academic and professional publication is that a document, once released, is finished. It carries an implicit claim: *this is what I think, full stop.*^[This is particularly problematic in academia, where there is a long tradition of researchers whose work was eventually disproven taking an extreme defensive stance, usually rooted in [confirmation bias](https://en.wikipedia.org/wiki/Confirmation_bias).] I find this convention dishonest in proportion to how seldom it is actually true. Thinking is continuous; positions shift; evidence accumulates; people change their minds and rarely say so in public. This site operates under a different premise, one that I strive to operate all of my life under.

Every essay and post on this site carries an **epistemic footer** — a structured block that reports my current relationship to the work. The footer only appears when a `status` field is set in the document's frontmatter; standalone pages and very short items omit it.

The vocabulary below is genre-general but reads differently across genres. For a personal essay, *confidence* reflects credence in a thesis — "I might change my mind." For an empirical research paper, it reflects expected generalization — "this would replicate." For formal mathematics, it reflects credence in proof correctness, with a special value `proved` available for theorems with complete proofs (where any numeric value would be false precision). *Evidence* reads analogously: the strength of arguments and supporting writing in essays, the empirical base in research, the structure of the proof in mathematics. The fields are the same; the interpretive frame shifts with the work.

The full set of fields:

- **Status** — a controlled vocabulary describing where the work stands: *Draft*, *Working model*, *Durable*, *Refined*, *Superseded*, or *Deprecated*. A document marked *Working model* is not just unfinished — it is a position I currently hold but would not stake much on. A document marked *Durable* is something I expect to hold up. *Superseded* means I wrote a better version; *Deprecated* means I no longer endorse it.

- **Confidence** — an integer from 0–100, representing my credence in the central thesis. Not false precision: a rough honest assessment is more useful than no assessment at all. When a `confidence-history` list is present, a trend arrow (↑ ↓ →) is derived automatically from the last two entries — so you can see not just *what* I think but whether I am growing more or less confident over time.

- **Importance** — how much I think this matters, on a 1–5 dot scale (●●●○○). Useful for orienting a reader who has limited time.

- **Evidence** — how well-evidenced the claims are, on the same 1–5 scale. An essay with high importance and low evidence is a speculative position and should be read accordingly.

- **Trust score** — a single 0–100 integer derived automatically from confidence (weighted 60%) and evidence (weighted 40%, with the 1–5 scale rescaled so that evidence=1 contributes zero and evidence=5 contributes the full 40 points). It is deliberately *narrow*: it answers "how much should you trust the central claim?" and nothing else. It says nothing about how broadly the work matters, how novel it is, or how useful it is in practice — those are separate axes (see below) that are deliberately *not* folded into a composite, so a high trust score on a personal essay cannot be misread as "world-shaking." Following Gwern's lead, the orientations are presented in parallel rather than blended into a single index. The score is not entered manually and lives only in the epistemic footer.

- **Scope**, **Novelty**, **Practicality** — orientation fields shown as their own rows in the epistemic footer alongside confidence, importance, and evidence. *Scope* ranges from *personal* to *civilizational*; *novelty* from *conventional* to *innovative*; *practicality* from *abstract* to *exceptional*. These are not ratings — they are orientations, and they intentionally do not feed the trust score.

- **Peer status** — the *external* review state, distinct from `status` (which is my internal position). Values: *unreviewed* (default), *under review*, *peer reviewed*, *published*, *retracted*. A piece can be *Durable* (I expect it to hold up) and *unreviewed* (the world hasn't checked yet) at the same time; the two axes are deliberately factored. A *retracted* piece renders with the field name struck through and the outer ring of the epistemic figure crossed out.

- **Result shape** — the shape of the central claim: *positive* (argues something works), *negative* (argues something does not), *mixed* (both, as in a double-pincer barrier paper), *comparative* (compares approaches), or *descriptive* (describes without arguing for or against). Encoded as a small glyph beside the trust score on the epistemic figure. Adds nothing to the compact row.

- **Stability** — auto-computed at every build from `git log --follow`. The heuristic: very new or barely-touched documents are *volatile*; actively-revised documents are *revising*; older documents with more commits settle into *fairly stable*, *stable*, or *established*. This requires no manual maintenance — the build reads the repository history and makes the inference.

The version history block, directly above the epistemic footer, uses a three-tier fallback: authored `history:` notes when they exist (written by me when the git log alone would not convey what changed), then the raw git log, then the `date:` frontmatter field as a creation record. `make build` auto-commits any changed content files before the Hakyll compilation runs, so the git log is always current.

The [[Current]] page extends this premise from essays to ongoing work. Every research project listed there carries its own `updated:` timestamp and a status drawn from a controlled vocabulary — *in-review*, *revising*, *drafting*, *building*, *early-stage*, *paused* — and the page itself wears a masthead "last updated" date as its thesis. The page has no epistemic footer because it isn't an argument; it is, rather, the closest thing this site has to a publication, and yet by design it is the part of the site most committed to being out of date the moment you finish reading it.

The point of all this is simple: when you read something on this site, you should know what kind of claim I am making. The date a document was last modified is not decorative. A 40% confidence rating is not self-deprecation. The system is an attempt to make explicit something that most writing leaves implicit — where the author actually stands.

---

## Influences

The amount of influences on this website is immense, and cannot be detailed in the fullest extent. Every other webpage that I have visited, whether beautiful or pitiful, has evoked some type of reaction or response in me, and that response has played some role, even if minute, in the design of this website. I can point to Tufte's influence on many of my design choices, and for the introduction to Tufte, I am thankful to CSCI1377 at Brown. I am thankful to the many other courses I took in my undergrad that influenced how I interact or ideologically view visualizations, networks, systems, etc.

The tradition of the personal website is one that is built on a sense of community and interaction. I am thankful to everyone else who has a personal website and shares their content with the world. I am also particularly greatful to the open source and broader open culture movements, who have given me and the world so much. This website would not exist without you - and I wouldn't be the person I am without your influence - what a role model!

---

## The Future

This site is unfinished. Several portals have no content yet. The annotated bibliography
is sparse. I am in the progress of migrating content, so stay tuned!

The colophon itself is a living document. When the site changes substantially, this page will change with it. The git repository on Forgejo (hosted on the git subdomain here) should always be considered to take precedence.
