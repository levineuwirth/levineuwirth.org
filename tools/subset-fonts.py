#!/usr/bin/env python3
"""subset-fonts.py — the site's web fonts, from their upstream releases.

    uv run --with fonttools --with brotli tools/subset-fonts.py

Fetches Spectral and JetBrains Mono from the Google Fonts repository
(github.com/google/fonts, main) and Fira Sans 4.301 from bBox Type's
(github.com/bBoxType/FiraSans), each with its OFL.txt, caches them under
~/.cache/levineuwirth-fonts, and writes WOFF2 subsets and OFL-*.txt to
static/fonts/. Replaces subset-fonts.sh, which read fonts from
an Arch package path that is no longer installed (audit V08).

What changed from the shell script, and why:
  - Characters the site prints that the subsets dropped (audit V08):
    Latin Extended-A in full (ł in "Prałat–Wormald", 11 pages), ← → ↑ ↓,
    ● ○ (the epistemic dots, 21 pages), ≤ ≥ ≈, □ in Spectral; box drawing
    in JetBrains Mono (the levcs diagram); Fira Sans gains c2sc, tnum and
    lnum, which the all-small-caps labels and tabular figures ask for.
  - Every name record is kept (`--name-IDs '*'`): pyftsubset's default
    keeps only 0–6, which dropped the licence text and URL (IDs 13 and 14)
    from every font (audit C05).
  - Fira Sans 4.301 reserves the name "Fira" in its name table (bBox's
    OFL.txt omits it; the notice written here follows the font), and a
    subset is a Modified Version, which may not use it (audit C05). The OFL limits that to "the
    primary font name as presented to the users", so the subset's name
    records say "LN Sans"; the copyright, trademark and licence notices
    keep Fira's, and the stylesheets still call it "Fira Sans". Google
    Fonts' copy reserves no name but is the older 4.203, whose letters are
    up to 1.4 % wider: 0.5 % on a line of interface text, enough to move
    the nav's wrap points.

Tempo Notes is built separately by tools/build-notes-font.py.
"""

from __future__ import annotations

import hashlib
import io
import sys
import urllib.request
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "static" / "fonts"
CACHE = Path.home() / ".cache" / "levineuwirth-fonts"
GOOGLE = "https://raw.githubusercontent.com/google/fonts/main/ofl"
BBOX = "https://raw.githubusercontent.com/bBoxType/FiraSans/master"
FIRA_TTF = BBOX + "/Fira_Sans_4_3/Fonts/Fira_Sans_TTF_4301/Normal/Roman"

# Latin-1, Latin Extended-A, the punctuation block, and the few symbols
# the prose uses.
BASE = ("U+0000-00FF,U+0100-017F,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,"
        "U+2074,U+20AC,U+2122,U+2190-2193,U+2212,U+2215,U+FEFF,U+FFFD")
SPECTRAL_EXTRA = "U+2248,U+2264-2265,U+25A1,U+25CB,U+25CF"
JBM_EXTRA = "U+2500-257F"

SPECTRAL_FEATURES = "liga,dlig,smcp,c2sc,onum,lnum,pnum,tnum,frac,ordn,sups,subs,ss01,ss02,ss03,ss04,ss05,kern"
FIRA_FEATURES = "smcp,c2sc,liga,kern,tnum,lnum"
JBM_FEATURES = "liga,kern,calt"

def google(family: str, name: str) -> str:
    return f"{GOOGLE}/{family}/{urllib.request.quote(name)}"

# (family, source URL, output, features, extra unicodes, wght instance)
FONTS = [
    ("spectral", google("spectral", "Spectral-Regular.ttf"),        "spectral-regular.woff2",         SPECTRAL_FEATURES, SPECTRAL_EXTRA, None),
    ("spectral", google("spectral", "Spectral-Italic.ttf"),         "spectral-italic.woff2",          SPECTRAL_FEATURES, SPECTRAL_EXTRA, None),
    ("spectral", google("spectral", "Spectral-SemiBold.ttf"),       "spectral-semibold.woff2",        SPECTRAL_FEATURES, SPECTRAL_EXTRA, None),
    ("spectral", google("spectral", "Spectral-SemiBoldItalic.ttf"), "spectral-semibold-italic.woff2", SPECTRAL_FEATURES, SPECTRAL_EXTRA, None),
    ("spectral", google("spectral", "Spectral-Bold.ttf"),           "spectral-bold.woff2",            SPECTRAL_FEATURES, SPECTRAL_EXTRA, None),
    ("spectral", google("spectral", "Spectral-BoldItalic.ttf"),     "spectral-bold-italic.woff2",     SPECTRAL_FEATURES, SPECTRAL_EXTRA, None),
    ("firasans", FIRA_TTF + "/FiraSans-Regular.ttf",                "fira-sans-regular.woff2",        FIRA_FEATURES,     "",             None),
    ("firasans", FIRA_TTF + "/FiraSans-SemiBold.ttf",               "fira-sans-semibold.woff2",       FIRA_FEATURES,     "",             None),
    ("jetbrainsmono", google("jetbrainsmono", "JetBrainsMono[wght].ttf"),        "jetbrains-mono-regular.woff2", JBM_FEATURES, JBM_EXTRA, 400),
    ("jetbrainsmono", google("jetbrainsmono", "JetBrainsMono-Italic[wght].ttf"), "jetbrains-mono-italic.woff2",  JBM_FEATURES, JBM_EXTRA, 400),
]
# family -> (notice written to static/fonts/, upstream licence text)
LICENCES = {"spectral": ("OFL-Spectral.txt", google("spectral", "OFL.txt")),
            "firasans": ("OFL-FiraSans.txt", BBOX + "/OFL.txt"),
            "jetbrainsmono": ("OFL-JetBrainsMono.txt", google("jetbrainsmono", "OFL.txt"))}

# The subset's primary name, in place of the reserved "Fira Sans": the
# family, full and PostScript names and their typographic forms.
RENAME = {"firasans": ("Fira Sans", "LN Sans")}
PRIMARY_NAME_IDS = {1, 3, 4, 6, 16, 17, 18, 21, 22}

# What each family must cover after subsetting (audit V08).
MUST_COVER = {
    "spectral": "łŁ←→●○≤≥≈□",
    "firasans": "łŁ←→",
    "jetbrainsmono": "─│┌┐└┘├┤┬┴┼",
}


def fetch(url: str) -> bytes:
    cached = CACHE / hashlib.sha256(url.encode()).hexdigest()[:16] / url.rsplit("/", 1)[1]
    if not cached.is_file():
        cached.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=60) as r:
            cached.write_bytes(r.read())
    data = cached.read_bytes()
    print(f"  {url.rsplit('/', 1)[1]}  sha256 {hashlib.sha256(data).hexdigest()[:16]}…  ({len(data) // 1024} KB)")
    return data


def rename(font: TTFont, old: str, new: str) -> None:
    for rec in font["name"].names:
        if rec.nameID in PRIMARY_NAME_IDS:
            text = rec.toUnicode()
            rec.string = text.replace(old, new).replace(old.replace(" ", ""), new.replace(" ", ""))
    left = [r.nameID for r in font["name"].names if r.nameID in PRIMARY_NAME_IDS and "Fira" in r.toUnicode()]
    if left:
        sys.exit(f"name records {left} still carry the reserved name")


def build(family, url, out, features, extra, wght) -> str:
    """Write one subset; return the font's own copyright notice."""
    font = TTFont(io.BytesIO(fetch(url)))
    notice = font["name"].getDebugName(0)
    if wght is not None:
        font = instancer.instantiateVariableFont(font, {"wght": wght})
    options = subset.Options()
    options.layout_features = features.split(",")
    options.name_IDs = ["*"]
    options.hinting = False
    options.desubroutinize = True
    unicodes = subset.parse_unicodes(BASE + ("," + extra if extra else ""))
    sub = subset.Subsetter(options)
    sub.populate(unicodes=unicodes)
    sub.subset(font)
    if family in RENAME:
        rename(font, *RENAME[family])
    dest = OUT / out
    before = dest.stat().st_size if dest.is_file() else 0
    font.flavor = "woff2"          # Options.flavor is the CLI's; the API saves the font's own
    font.save(str(dest))
    cmap = TTFont(str(dest)).getBestCmap()
    missing = [c for c in MUST_COVER[family] if ord(c) not in cmap]
    if missing:
        sys.exit(f"{out}: upstream lacks {''.join(missing)}")
    print(f"  → {out}: {before // 1024} → {dest.stat().st_size // 1024} KB")
    return notice


def write_licence(family: str, notice: str) -> None:
    """The upstream OFL.txt, headed by the copyright notice the font itself
    carries. They differ for Fira Sans: bBox's OFL.txt drops the Reserved
    Font Name that 4.301's name table still declares, and the font is what
    is shipped."""
    name, url = LICENCES[family]
    text = fetch(url).decode("utf-8").replace("\r\n", "\n")
    head, sep, body = text.partition("\n\n")
    if head.strip() != notice:
        print(f"  {name}: notice taken from the font, not the upstream text")
        text = notice + sep + body
    (OUT / name).write_text(text, encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    notices = {}
    for spec in FONTS:
        notice = build(*spec)
        if notices.setdefault(spec[0], notice) != notice:
            sys.exit(f"{spec[2]}: copyright differs from the family's other faces")
    for family, notice in notices.items():
        write_licence(family, notice)


if __name__ == "__main__":
    main()
