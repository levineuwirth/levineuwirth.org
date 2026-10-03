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

It then rewrites the fallback faces in static/css/base.css (audit V20,
A19): for each system font a reader may see before or instead of
Spectral and Fira Sans, an @font-face that names it with local() and
scales it (size-adjust) so a line of the site's prose sets to the same
width, with the web font's ascent and descent. Text then barely moves
when the web font arrives. The metrics come from metric-compatible open
fonts fetched from google/fonts — Gelasio for Georgia, Tinos for Times
New Roman, Arimo for Arial — and from Noto Serif and Roboto themselves;
the widths are averaged over the characters of content/'s prose.

Tempo Notes is built separately by tools/build-notes-font.py.
"""

from __future__ import annotations

import collections
import hashlib
import io
import re
import sys
import urllib.request
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "static" / "fonts"
BASE_CSS = ROOT / "static" / "css" / "base.css"
CONTENT = ROOT / "content"
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

# Fallback faces. Each set stands in for one web family on the systems
# that have its reference font, under every name that font goes by: the
# full name ("Tinos Bold Italic") and the PostScript name
# ("Tinos-BoldItalic"), which is what local() matches. A weight range
# takes the semibold's measure: headings and labels are 600, 700 is rarer.
# Monospace has none: JetBrains Mono and Courier both advance 0.6 em, and
# code is seldom above the fold.
STYLE_WORDS = {"Regular": "", "Italic": " Italic", "Bold": " Bold", "BoldItalic": " Bold Italic"}

def full(family: str, style: str, regular: str = "") -> str:
    return family + (STYLE_WORDS[style] or regular)

def ps(prefix: str, style: str, regular: str = "-Regular") -> str:
    return prefix + ("-" + style if style != "Regular" else regular)

def ms(prefix: str, style: str) -> str:          # Monotype's: TimesNewRomanPS-BoldMT
    return prefix + ("-" + style if style != "Regular" else "") + "MT"

def weight_of(style: str) -> int:
    return 700 if "Bold" in style else 400

SERIF = [("Regular", "400", "normal", "spectral-regular.woff2"),
         ("Italic", "400", "italic", "spectral-italic.woff2"),
         ("Bold", "600 700", "normal", "spectral-semibold.woff2"),
         ("BoldItalic", "600 700", "italic", "spectral-semibold-italic.woff2")]
SANS = [("Regular", "400", "normal", "fira-sans-regular.woff2"),
        ("Bold", "600 700", "normal", "fira-sans-semibold.woff2")]

# (family, faces, local names for a style, reference font for a style: URL and wght)
FALLBACK_SETS = [
    ("Spectral on Georgia", SERIF,
     lambda s: [full("Georgia", s), ps("Georgia", s, ""), full("Gelasio", s, " Regular"), ps("Gelasio", s)],
     lambda s: (google("gelasio", "Gelasio-Italic[wght].ttf" if "Italic" in s else "Gelasio[wght].ttf"), weight_of(s))),
    ("Spectral on Times", SERIF,
     lambda s: [full("Times New Roman", s), ms("TimesNewRomanPS", s), full("Liberation Serif", s),
                ps("LiberationSerif", s, ""), full("Tinos", s), ps("Tinos", s)],
     lambda s: (google("tinos", f"Tinos-{s}.ttf"), None)),
    ("Spectral on Noto", SERIF,
     lambda s: [full("Noto Serif", s), ps("NotoSerif", s)],
     lambda s: (google("notoserif", "NotoSerif-Italic[wdth,wght].ttf" if "Italic" in s else "NotoSerif[wdth,wght].ttf"), weight_of(s))),
    ("Fira Sans on Arial", SANS,
     lambda s: [full("Arial", s), ms("Arial", s), full("Liberation Sans", s), ps("LiberationSans", s, ""),
                full("Arimo", s), ps("Arimo", s)],
     lambda s: (google("arimo", "Arimo[wght].ttf"), weight_of(s))),
    ("Fira Sans on Roboto", SANS,
     lambda s: [full("Roboto", s), ps("Roboto", s)],
     lambda s: (google("roboto", "Roboto[wdth,wght].ttf"), weight_of(s))),
]
FALLBACK_BEGIN = "/* BEGIN fallback faces — written by tools/subset-fonts.py */\n"
FALLBACK_END = "/* END fallback faces */\n"

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
    # recalcTimestamp off: the same sources give the same bytes.
    font = TTFont(io.BytesIO(fetch(url)), recalcTimestamp=False)
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


def prose_frequencies() -> collections.Counter:
    """Characters of the site's prose: content/'s Markdown without front
    matter, code, maths, link targets or tags."""
    freq = collections.Counter()
    for md in CONTENT.rglob("*.md"):
        text = md.read_text(encoding="utf-8", errors="ignore")
        text = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)
        text = re.sub(r"```.*?```|\$\$.*?\$\$|\$[^$\n]+\$|`[^`\n]+`|\]\([^)]*\)|<[^>]+>", " ", text, flags=re.S)
        freq.update(re.sub(r"[#*_>\[\]|{}\\]", "", re.sub(r"\s+", " ", text)))
    return freq


def instance(font: TTFont, wght: int | None) -> TTFont:
    """A static instance: wght as asked, every other axis at its default."""
    if wght is None or "fvar" not in font:
        return font
    axes = {a.axisTag: (wght if a.axisTag == "wght" else a.defaultValue) for a in font["fvar"].axes}
    return instancer.instantiateVariableFont(font, axes)


def mean_advance(font: TTFont, freq: collections.Counter, chars: set[str]) -> float:
    cmap, hmtx, upm = font.getBestCmap(), font["hmtx"], font["head"].unitsPerEm
    total = sum(freq[c] for c in chars)
    return sum(freq[c] * hmtx[cmap[ord(c)]][0] for c in chars) / upm / total


def vertical_metrics(font: TTFont) -> tuple[int, int, int]:
    """Ascent, descent and line gap as browsers read them: OS/2's typo
    values when USE_TYPO_METRICS is set, else hhea's."""
    os2 = font["OS/2"]
    if os2.fsSelection & (1 << 7):
        return os2.sTypoAscender, -os2.sTypoDescender, os2.sTypoLineGap
    hhea = font["hhea"]
    return hhea.ascent, -hhea.descent, hhea.lineGap


def fallback_rule(family, weight, style, names, webfont, ref, freq) -> tuple[str, float]:
    common = {c for c in freq if ord(c) in webfont.getBestCmap() and ord(c) in ref.getBestCmap()}
    adjust = mean_advance(webfont, freq, common) / mean_advance(ref, freq, common)
    upm = webfont["head"].unitsPerEm
    # The overrides are scaled by size-adjust in turn, so divide it out.
    asc, desc, gap = (f"{100 * v / upm / adjust:.1f}%" for v in vertical_metrics(webfont))
    src = ", ".join(f'local("{n}")' for n in dict.fromkeys(names))
    return (f'@font-face {{\n'
            f'    font-family: "{family}";\n'
            f'    src: {src};\n'
            f'    font-weight: {weight};\n'
            f'    font-style: {style};\n'
            f'    size-adjust: {100 * adjust:.1f}%;\n'
            f'    ascent-override: {asc};\n'
            f'    descent-override: {desc};\n'
            f'    line-gap-override: {gap};\n'
            f'}}\n'), adjust


def write_fallbacks() -> None:
    freq = prose_frequencies()
    rules = []
    for family, faces, names_for, reference in FALLBACK_SETS:
        for style_name, weight, style, web in faces:
            ref_url, wght = reference(style_name)
            ref = instance(TTFont(io.BytesIO(fetch(ref_url))), wght)
            rule, adjust = fallback_rule(family, weight, style, names_for(style_name),
                                         TTFont(str(OUT / web)), ref, freq)
            rules.append(rule)
            print(f"  {family} {weight} {style}: size-adjust {100 * adjust:.1f}%")
    css = BASE_CSS.read_text(encoding="utf-8")
    start, end = css.find(FALLBACK_BEGIN), css.find(FALLBACK_END)
    if start < 0 or end < start:
        sys.exit(f"{BASE_CSS.name}: no fallback-face markers")
    BASE_CSS.write_text(css[:start + len(FALLBACK_BEGIN)] + "".join(rules) + css[end:], encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    notices = {}
    for spec in FONTS:
        notice = build(*spec)
        if notices.setdefault(spec[0], notice) != notice:
            sys.exit(f"{spec[2]}: copyright differs from the family's other faces")
    for family, notice in notices.items():
        write_licence(family, notice)
    write_fallbacks()


if __name__ == "__main__":
    main()
