#!/usr/bin/env python3
"""Grow static/initials/logos-hand/: the logo's hand, A to Z.

Each letter is Spectral's capital, its outline read from the site's own
static/fonts/spectral-regular.woff2, with sprigs grown from its left edges
and pale veins in its stems after the site's mark, by
tools/initials-logos-hand.js in a headless Chromium (the growth needs a
raster of the letter). The randomness is seeded by the letter, so a run
reproduces the set exactly; change the generator, and the set changes with
it. Pages draw from the set through their frontmatter, initials: (see
MARKS.md 2.6).

Reading WOFF2 needs brotli, which the site's environment does not carry:

    uv run --no-project --with brotli --with fonttools --with playwright \
        tools/initials-logos-hand.py
"""

from __future__ import annotations

import json
import string
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
FONT = SITE / "static/fonts/spectral-regular.woff2"
OUT = SITE / "static/initials/logos-hand"
GENERATOR = Path(__file__).with_suffix(".js")


def outlines() -> dict:
    """Spectral's capitals as SVG paths in font units, y down: the cap line
    at 0, the baseline at the cap height."""
    try:
        import brotli  # noqa: F401  (fontTools reads WOFF2 through it)
    except ImportError:
        raise SystemExit("initials-logos-hand: reading WOFF2 needs brotli: uv run --no-project "
                         "--with brotli --with fonttools --with playwright tools/initials-logos-hand.py")
    from fontTools.pens.boundsPen import BoundsPen
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.ttLib import TTFont

    font = TTFont(FONT)
    glyphs, cmap = font.getGlyphSet(), font.getBestCmap()
    capital = BoundsPen(glyphs)
    glyphs[cmap[ord("H")]].draw(capital)
    cap = capital.bounds[3]
    letters = {}
    for letter in string.ascii_uppercase:
        glyph = glyphs[cmap[ord(letter)]]
        bounds = BoundsPen(glyphs)
        glyph.draw(bounds)
        x0, y0, x1, y1 = bounds.bounds
        pen = SVGPathPen(glyphs, ntos=lambda v: ("%.1f" % v).rstrip("0").rstrip("."))
        glyph.draw(TransformPen(pen, (1, 0, 0, -1, -x0, cap)))
        letters[letter] = {"d": pen.getCommands(), "w": x1 - x0, "top": cap - y1, "bottom": cap - y0}
    return {"cap": cap, "letters": letters}


def main() -> int:
    from playwright.sync_api import sync_playwright

    data = outlines()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content("<!doctype html><title>initials</title>")
        grown = page.evaluate("(" + GENERATOR.read_text().strip() + ")(" + json.dumps(data) + ")")
        browser.close()
    OUT.mkdir(parents=True, exist_ok=True)
    for letter, result in sorted(grown.items()):
        (OUT / f"{letter}.svg").write_text(result["svg"], encoding="utf-8")
    print(f"initials-logos-hand: {len(grown)} letters in {OUT.relative_to(SITE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
