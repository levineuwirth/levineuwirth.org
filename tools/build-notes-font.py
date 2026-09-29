#!/usr/bin/env python3
"""Build static/fonts/tempo-notes.woff2 — note values for tempo marks.

Composition pages print metronome marks (``♩ = 80``) in running text.
Spectral has no note glyphs, and system fallbacks draw them at mismatched
sizes. This builds a tiny font from Leland Text, the text companion to
MuseScore's engraving font (SIL OFL 1.1), so a tempo on the page matches
the tempo in the score.

The font answers every way a note value reaches the page:

  * the SMuFL metronome range (U+ECA0–ECBF), which MuseScore writes into
    tempo text;
  * the hand-typed ♩ and ♪ (U+2669, U+266A);
  * the Unicode note values U+1D15D–1D161 — and, because Unicode
    normalisation always decomposes those, the notehead + stem (+ flag)
    sequences they become. Those are joined back into one note by a ccmp
    ligature, so the text keeps its real characters (a screen reader
    still says "half note") and only the drawing changes.

Usage:
    uv run --with fonttools --with brotli tools/build-notes-font.py LelandText.otf

LelandText.otf is in the MuseScore repository at fonts/leland/.
"""

import sys
from pathlib import Path

from fontTools.fontBuilder import FontBuilder
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

OUT = Path(__file__).resolve().parent.parent / "static" / "fonts" / "tempo-notes.woff2"

# Our glyph name -> the Leland Text (SMuFL) glyph it is drawn from.
DRAWN = {
    "whole":     "metNoteWhole",
    "half":      "metNoteHalfUp",
    "quarter":   "metNoteQuarterUp",
    "eighth":    "metNote8thUp",
    "sixteenth": "metNote16thUp",
    "dot":       "metAugmentationDot",
}

# Code point -> our glyph name.
CMAP = {
    0xECA2: "whole", 0xECA3: "half", 0xECA5: "quarter",
    0xECA7: "eighth", 0xECA9: "sixteenth", 0xECB7: "dot",
    0x2669: "quarter", 0x266A: "eighth",
    0x1D15D: "whole", 0x1D15E: "half", 0x1D15F: "quarter",
    0x1D160: "eighth", 0x1D161: "sixteenth", 0x1D16D: "dot",
    # The pieces the precomposed notes decompose into. Alone they draw as
    # the note they most often begin; the stem and flags are invisible
    # until the ligature below consumes them.
    0x1D157: "voidhead", 0x1D158: "blackhead",
    0x1D165: "stem", 0x1D16E: "flag1", 0x1D16F: "flag2",
}

FEATURES = """
languagesystem DFLT dflt;
feature ccmp {
    sub blackhead stem flag2 by sixteenth;
    sub blackhead stem flag1 by eighth;
    sub blackhead stem by quarter;
    sub voidhead stem by half;
} ccmp;
"""


def main(src: str) -> None:
    leland = TTFont(src)
    glyphs = leland.getGlyphSet()
    upm = leland["head"].unitsPerEm

    outlines, advances = {}, {}

    def draw(name, source, gap=0):
        pen = TTGlyphPen(None)
        shifted = TransformPen(Cu2QuPen(pen, max_err=1.0, reverse_direction=True),
                               (1, 0, 0, 1, gap, 0))
        glyphs[source].draw(shifted)
        outlines[name] = pen.glyph()
        advances[name] = glyphs[source].width + gap

    def empty(name, width=0):
        outlines[name] = TTGlyphPen(None).glyph()
        advances[name] = width

    empty(".notdef", upm // 2)
    for name, source in DRAWN.items():
        # In a score the engraver spaces the dot; in text it would touch
        # the notehead, so it carries its own gap.
        draw(name, source, gap=70 if name == "dot" else 0)
    draw("voidhead", DRAWN["half"])
    draw("blackhead", DRAWN["quarter"])
    for name in ("stem", "flag1", "flag2"):
        empty(name)

    order = list(outlines)
    fb = FontBuilder(upm, isTTF=True)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap(CMAP)
    fb.setupGlyf(outlines)
    fb.setupHorizontalMetrics({
        n: (advances[n], outlines[n].xMin if outlines[n].numberOfContours else 0)
        for n in order
    })
    hhea = leland["hhea"]
    fb.setupHorizontalHeader(ascent=hhea.ascent, descent=hhea.descent)
    # A modified OFL font may not carry a Reserved Font Name, so the
    # subset is named for what it does rather than for its source.
    fb.setupNameTable({
        "familyName": "Tempo Notes",
        "styleName": "Regular",
        "copyright": "Glyphs from Leland Text, copyright MuseScore BVBA.",
        "licenseDescription": "This Font Software is licensed under the "
                              "SIL Open Font License, Version 1.1.",
        "licenseInfoURL": "https://openfontlicense.org",
    })
    fb.setupOS2(sTypoAscender=hhea.ascent, sTypoDescender=hhea.descent,
                usWinAscent=hhea.ascent, usWinDescent=-hhea.descent)
    fb.setupPost()
    addOpenTypeFeaturesFromString(fb.font, FEATURES)

    fb.font.flavor = "woff2"
    fb.save(str(OUT))
    print(f"{OUT} — {OUT.stat().st_size} bytes, {len(order)} glyphs")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
