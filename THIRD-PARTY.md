---
title: Licenses and third-party notices
description: The scope of the site's code and prose licenses, public-domain credits, and third-party notices.
---

## Code and original prose

Levi Neuwirth's website code and its software documentation are licensed
under the [MIT license](/licenses/MIT.txt). This includes the generator,
scripts, stylesheets, templates, tests, and build and server configuration.

Levi Neuwirth's original prose and textual content data are licensed under
[CC BY-NC-SA 4.0](/licenses/CC-BY-NC-SA-4.0.txt), unless a more specific
notice says otherwise. Attribute Levi Neuwirth and link to the original
page when sharing. The linked legal text sets out the terms, including
attribution, non-commercial use and sharing adaptations under the same
license. This covers essays, blog posts, page text, music program notes,
and authored text in content and CV data; facts and bibliographic records
are covered only to the extent that the author holds applicable rights.

These grants exclude third-party material and public-domain works. They do
not automatically cover photographs, illustrations, scores, recordings or
paper PDFs: consult the notice on the individual work. A page's prose
license does not relicense its embedded works, quotations or linked files.
Earlier grants and more specific notices on individual works remain in effect.

## Public-domain works

- William Shakespeare, *Sonnet 60* (1609), at
  [/poetry/sonnet-60.html](/poetry/sonnet-60.html), and its excerpt on
  *Memento Mori*: public domain.
- Percy Bysshe Shelley, *Ozymandias* (1818), at
  [/poetry/ozymandias.html](/poetry/ozymandias.html): public domain.
- Gustave Doré, *Paradiso*, Canto 31, the engraving reproduced as
  [/images/canto31.jpg](/images/canto31.jpg) on *Memento Mori*: public domain.

The [Public Domain Mark](https://creativecommons.org/publicdomain/mark/1.0/)
identifies the status of these works; it is not a new license grant.

## Archived material

The archive preserves works by their original authors. The site's MIT and
CC BY-NC-SA licenses do not apply to the preserved works or their extracted
text. Each wrapper links to the original and records the capture's provenance.

- Daniel J. Bernstein, [*Cycle counts for AES*](https://cr.yp.to/aes-speed.html),
  preserved in `archive/djb-aes-speed/`. No additional reuse license is
  granted by this site. Consult the original author's terms.
- NIST, [*FIPS 203: Module-Lattice-Based Key-Encapsulation Mechanism Standard*](https://doi.org/10.6028/NIST.FIPS.203),
  preserved in `archive/nist-fips-203/`. The document retains its own notices.

Other attributed excerpts retain their source's rights and terms.

## Code-reference snapshots

Snapshots under `code-refs/` keep the license of the upstream repository
at the recorded commit. They are excluded from this site's blanket grants.

- James Petrie's [VerInf](https://github.com/JamesPetrie/VerInf), copyright
  2026 James Petrie: the [full upstream MIT notice](/licenses/VerInf-MIT.txt)
  is retained for snapshots under `code-refs/github/JamesPetrie/VerInf/`.
  It matches the notice at eight of the nine stored commits. The earlier
  `2bdf823b08ea012cf5d26eeaac1c65698bb51e20` snapshot predates that file;
  consult the upstream author for its reuse terms. This site grants no
  additional rights in it.
- Levi Neuwirth's [proof-broker](https://github.com/levineuwirth/proof-broker)
  snapshots retain the upstream repository's terms. This website's prose
  license does not change those terms.

## Fonts

The following font software is distributed under the SIL Open Font License
1.1. The complete copyright notices and OFL terms accompany the served fonts:

- Spectral, the Spectral Project Authors: [OFL-Spectral.txt](/fonts/OFL-Spectral.txt).
- Fira Sans, the Mozilla Foundation, Telefonica S.A., bBox Type GmbH and
  Carrois Corporate GbR: [OFL-FiraSans.txt](/fonts/OFL-FiraSans.txt).
  The notice retains the reserved name “Fira”, so the modified subsets are
  named “LN Sans” in their own name tables; the stylesheets still call the
  family “Fira Sans”.
- JetBrains Mono, the JetBrains Mono Project Authors:
  [OFL-JetBrainsMono.txt](/fonts/OFL-JetBrainsMono.txt).
- Tempo Notes is a modified font containing glyphs from MuseScore's Leland
  Text, renamed for this site: [OFL-Leland.txt](/fonts/OFL-Leland.txt).
  The upstream notice retains the reserved name “Leland”.

Spectral, Fira Sans and JetBrains Mono are subset for web delivery by
`tools/subset-fonts.py`, which keeps each font's copyright, license and URL
records. These font files remain under the OFL, independently of the
documents using them.

## Browser libraries and model

- [Leaflet 1.9.4](https://github.com/Leaflet/Leaflet/tree/v1.9.4): BSD 2-Clause,
  copyright 2010–2023 Volodymyr Agafonkin and 2010–2011 CloudMade.
  [Full notice](/licenses/Leaflet-BSD-2-Clause.txt).
- [Leaflet.markercluster 1.5.3](https://github.com/Leaflet/Leaflet.markercluster/tree/v1.5.3):
  MIT, copyright 2012 David Leaver. [Full notice](/licenses/Leaflet.markercluster-MIT.txt).
- [KaTeX 0.16.11](https://github.com/KaTeX/KaTeX/tree/v0.16.11): MIT, copyright
  2013–2020 Khan Academy and other contributors. [Full notice](/licenses/KaTeX-MIT.txt).
  Self-hosted under `/katex/`; its fonts are under the same license.
- Mozilla PDF.js retains its distributed [Apache 2.0 license and notices](/pdfjs/LICENSE)
  and the notices in its release bundle.
- The semantic-search model, [Xenova/all-MiniLM-L6-v2](https://huggingface.co/Xenova/all-MiniLM-L6-v2),
  retains its upstream [Apache 2.0 terms](/licenses/Apache-2.0.txt).
  Other libraries loaded from a CDN
  retain their package licenses; this site's licenses do not replace them.

## Build tools

The vendored `tools/bin/monolith` is the GNU/Linux x86-64 executable from
[monolith 2.10.1](https://github.com/Y2Z/monolith/releases/tag/v2.10.1),
SHA-256 `663ca914b078e91d5a854b4a07e913c613bbbcfe8fb11a24da1a6ab23c9205df`.
Monolith's own code is dedicated under [CC0 1.0](/licenses/monolith-CC0.txt).
Its dependencies retain their individual licenses; CC0 does not replace
those notices. The [dependency notice bundle](/licenses/monolith-dependencies.txt)
covers the pinned Linux CLI dependency tree, including vendored OpenSSL,
and provides each package's version, source URL and checksum.

Installed build dependencies are governed by their own package licenses.
