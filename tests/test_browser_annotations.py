"""Highlights and the selection toolbar, in Chromium and Firefox.

annotations.js keeps a reader's highlights in localStorage, keyed by
page, and finds their text again on every load; selection-popup.js
offers a toolbar for a selection, one of whose actions (Annotate) makes
a highlight. A fixture page, styled as an essay, carries a paragraph
with a source line break inside its text, as Pandoc leaves them, an
inline element, code and math.

Checked: a highlight across a line break is shown and found again after
a reload (audit J02: it used to be stored but never shown), as is one
across an inline element; a passage that cannot be highlighted says so
and stores nothing; colours; the tooltip, its escaped note, Delete, and
its keyboard path; the toolbar's buttons for prose, a single word, code
and math, and what each action opens or copies (window.open and the
clipboard are stubbed, so nothing leaves the machine).

    RUN_BROWSER_TESTS=1 python -m unittest tests.test_browser_annotations -v
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from urllib.parse import quote

from tests._browser import (BROWSERS, check_site, enforcing_csp, page_styles, require_playwright,
                            requires_browser, site_server)

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Reading fixture — Levi Neuwirth</title>
{styles}
<script src="/js/utils.js"></script>
<script src="/js/annotations.js" defer></script>
<script src="/js/selection-popup.js" defer></script>
</head><body><div class="page-shell"><main id="markdownBody">
<h1 class="page-title">Reading Fixture</h1>
<p id="wrapped">As a result, three
accounts are given of the same event, each of them partial.</p>
<p id="inline">A phrase with <em>emphasis inside</em> it, and then more.</p>
<p id="plain">Serendipity favours the prepared mind.</p>
<pre><code class="language-python">def increment(x):
    return x + 1</code></pre>
<p id="math">Consider <span class="math inline">x^2 + y^2</span> here.</p>
</main></div></body></html>
"""

KEY = "site-annotations"

# window.open and the clipboard, recorded instead of used.
STUBS = """
window.__opened = [];
window.open = (url, target, features) => { window.__opened.push(url); return null; };
window.__copied = [];
Object.defineProperty(navigator, 'clipboard', {configurable: true, value: {
    writeText: text => { window.__copied.push(text); return Promise.resolve(); }}});
"""

# Select `start`…`end` (first occurrences, in textContent, newlines and all)
# under `selector`, then release the mouse as a reader would.
SELECT = """([selector, start, end]) => {
    const el = document.querySelector(selector);
    const nodes = [];
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    let n, pos = 0;
    while ((n = walker.nextNode())) { nodes.push([n, pos]); pos += n.nodeValue.length; }
    const text = el.textContent;
    const a = text.indexOf(start);
    const b = text.indexOf(end, a) + end.length;
    const at = (i, isEnd) => {
        for (const [node, from] of nodes) {
            const to = from + node.nodeValue.length;
            if (isEnd ? i <= to : i < to) return [node, i - from];
        }
    };
    const r = document.createRange();
    r.setStart(...at(a, false));
    r.setEnd(...at(b, true));
    const s = getSelection();
    s.removeAllRanges();
    s.addRange(r);
    document.dispatchEvent(new MouseEvent('mouseup', {bubbles: true}));
    return s.toString();
}"""


@requires_browser
class Annotations(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        check_site()
        require_playwright()
        from playwright.sync_api import expect, sync_playwright
        cls.expect = staticmethod(expect)
        tmp = Path(cls.enterClassContext(tempfile.TemporaryDirectory(prefix="browser-annotations-")))
        (tmp / "fixtures").mkdir()
        (tmp / "fixtures" / "reading.html").write_text(PAGE.format(styles=page_styles()),
                                                       encoding="utf-8")
        cls.base = cls.enterClassContext(site_server(tmp, enforcing_csp(), tmp / "fixtures"))
        playwright = cls.enterClassContext(sync_playwright())
        cls.browsers = {}
        for name in BROWSERS:
            cls.browsers[name] = getattr(playwright, name).launch()
            cls.addClassCleanup(cls.browsers[name].close)

    def fixture(self, browser: str):
        context = self.browsers[browser].new_context(viewport={"width": 1280, "height": 900})
        self.addCleanup(context.close)
        context.add_init_script(STUBS)
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        self.addCleanup(lambda: self.assertEqual(errors, [], "page errors"))
        page.goto(self.base + "/__fixture/reading.html", wait_until="load")
        return page

    def select(self, page, selector: str, start: str, end: str) -> str:
        text = page.evaluate(SELECT, [selector, start, end])
        self.expect(page.locator(".selection-popup.is-visible")).to_be_visible()
        return text

    def toolbar(self, page) -> list[str]:
        return page.locator(".selection-popup.is-visible .selection-popup-btn").all_inner_texts()

    def highlight(self, page, selector: str, start: str, end: str, note: str = "",
                  color: str | None = None) -> str:
        text = self.select(page, selector, start, end)
        page.click(".selection-popup [data-action=annotate]")
        self.expect(page.locator(".ann-picker.is-visible")).to_be_visible()
        if color:
            page.click(f".ann-picker-swatch[data-color={color}]")
        page.fill(".ann-picker-note", note)
        page.press(".ann-picker-note", "Enter")
        return text

    def stored(self, page) -> list[dict]:
        return json.loads(page.evaluate(f"localStorage.getItem('{KEY}') || '[]'"))

    @staticmethod
    def collapsed(text: str) -> str:
        return " ".join(text.split())

    # -- highlights --------------------------------------------------------

    def test_a_highlight_across_a_line_break(self) -> None:
        # J02: Pandoc leaves the source's line break in the text; the
        # selection reads it as a space.
        for browser in BROWSERS:
            with self.subTest(browser=browser):
                page = self.fixture(browser)
                text = self.highlight(page, "#wrapped", "three", "accounts", note="two lines")
                self.assertEqual(self.collapsed(text), "three accounts")
                mark = page.locator("#wrapped mark.user-annotation")
                self.expect(mark).to_have_count(1)
                self.assertEqual(mark.evaluate("m => m.textContent"), "three\naccounts")
                self.expect(page.locator(".ann-picker.is-visible")).to_have_count(0)
                [ann] = self.stored(page)
                self.assertEqual((ann["url"], ann["note"], ann["color"]),
                                 ("/__fixture/reading.html", "two lines", "amber"))
                page.reload(wait_until="load")
                self.expect(page.locator("#wrapped mark.user-annotation")).to_have_text("three\naccounts")
                self.assertEqual(len(self.stored(page)), 1)

    def test_a_highlight_across_an_inline_element(self) -> None:
        for browser in BROWSERS:
            with self.subTest(browser=browser):
                page = self.fixture(browser)
                self.highlight(page, "#inline", "phrase", "emphasis", color="sage")
                mark = page.locator("#inline mark.user-annotation")
                self.expect(mark).to_have_count(1)
                self.expect(mark).to_have_class("user-annotation user-annotation--sage")
                self.assertEqual(self.collapsed(mark.inner_text()), "phrase with emphasis")
                page.reload(wait_until="load")
                self.expect(page.locator("#inline mark.user-annotation--sage")).to_have_count(1)
                self.assertEqual(self.collapsed(page.inner_text("#inline")),
                                 "A phrase with emphasis inside it, and then more.")

    def test_what_cannot_be_highlighted_says_so(self) -> None:
        # Text already inside a highlight cannot be anchored again.
        for browser in BROWSERS:
            with self.subTest(browser=browser):
                page = self.fixture(browser)
                self.highlight(page, "#plain", "Serendipity", "prepared")
                self.select(page, "#plain mark", "favours", "the")
                page.click(".selection-popup [data-action=annotate]")
                page.click(".ann-picker-submit")
                error = page.locator(".ann-picker.is-visible .ann-picker-error")
                self.expect(error).to_have_text("This passage could not be highlighted.")
                self.expect(error).to_have_attribute("role", "alert")
                self.assertEqual(len(self.stored(page)), 1)
                self.expect(page.locator("mark.user-annotation")).to_have_count(1)

    def test_tooltip_and_delete(self) -> None:
        note = '<img src=x onerror="window.__pwned=1">a note'
        for browser in BROWSERS:
            with self.subTest(browser=browser, how="pointer"):
                page = self.fixture(browser)
                self.highlight(page, "#plain", "Serendipity", "favours", note=note)
                page.mouse.click(5, 5)
                page.hover("#plain mark")
                tooltip = page.locator(".ann-tooltip.is-visible")
                self.expect(tooltip.locator(".ann-tooltip-note")).to_have_text(note)
                self.expect(tooltip.locator("img")).to_have_count(0)
                tooltip.locator(".ann-tooltip-delete").click()
                self.expect(page.locator("mark.user-annotation")).to_have_count(0)
                self.assertEqual(self.stored(page), [])
                # The paragraph is whole again: one text node, as before.
                self.assertEqual(page.evaluate("document.querySelector('#plain').childNodes.length"), 1)
                self.assertIsNone(page.evaluate("window.__pwned"))
            with self.subTest(browser=browser, how="keyboard"):
                self.highlight(page, "#wrapped", "three", "accounts", note="keys")
                page.mouse.click(5, 5)
                mark = page.locator("#wrapped mark")
                mark.focus()
                self.expect(page.locator(".ann-tooltip.is-visible .ann-tooltip-note")).to_have_text("keys")
                # Enter within a frame or two of the focus (no reader is that
                # quick) lands while the tooltip is still fading in, and focus
                # cannot enter it yet: wait for its transition to end.
                page.locator(".ann-tooltip").evaluate(
                    "t => Promise.all(t.getAnimations().map(a => a.finished))")
                page.keyboard.press("Enter")
                self.expect(page.locator(".ann-tooltip-delete")).to_be_focused()
                page.keyboard.press("Escape")
                self.expect(page.locator(".ann-tooltip.is-visible")).to_have_count(0)
                self.expect(mark).to_be_focused()

    # -- the toolbar -------------------------------------------------------

    def test_toolbar_by_context(self) -> None:
        cases = {
            "prose": ("#plain", "favours", "prepared",
                      ["Annotate", "BibTeX", "Copy", "DuckDuckGo", "Here", "Wikipedia"]),
            "one word": ("#plain", "Serendipity", "Serendipity",
                         ["Annotate", "BibTeX", "Copy", "Define", "DuckDuckGo", "Here", "Wikipedia"]),
            "code": ("pre code", "return", "1", ["Copy", "Docs"]),
            "math": ("#math .math", "x^2", "y^2", ["Copy", "nLab", "OEIS", "Wolfram"]),
        }
        for browser in BROWSERS:
            page = self.fixture(browser)
            for case, (selector, start, end, buttons) in cases.items():
                with self.subTest(browser=browser, context=case):
                    page.mouse.click(5, 5)
                    self.select(page, selector, start, end)
                    self.assertEqual(self.toolbar(page), buttons)
            with self.subTest(browser=browser, part="Escape hides"):
                page.keyboard.press("Escape")
                self.expect(page.locator(".selection-popup.is-visible")).to_have_count(0)

    def test_toolbar_actions(self) -> None:
        phrase = "favours the prepared"
        q = quote(phrase, safe="~()*!.'")    # encodeURIComponent
        opens = {
            "search": f"https://duckduckgo.com/?q={q}",
            "here": f"/search.html?q={q}",
            "wikipedia": f"https://en.wikipedia.org/wiki/Special:Search?search={q}",
        }
        for browser in BROWSERS:
            page = self.fixture(browser)
            for action, url in opens.items():
                with self.subTest(browser=browser, action=action):
                    page.mouse.click(5, 5)
                    self.select(page, "#plain", "favours", "prepared")
                    page.click(f".selection-popup [data-action={action}]")
                    self.assertEqual(page.evaluate("window.__opened.pop()"), url)
                    self.expect(page.locator(".selection-popup.is-visible")).to_have_count(0)
            with self.subTest(browser=browser, action="define"):
                page.mouse.click(5, 5)
                self.select(page, "#plain", "Serendipity", "Serendipity")
                page.click(".selection-popup [data-action=define]")
                self.assertEqual(page.evaluate("window.__opened.pop()"),
                                 "https://en.wiktionary.org/wiki/Serendipity")
            with self.subTest(browser=browser, action="docs"):
                page.mouse.click(5, 5)
                self.select(page, "pre code", "increment", "increment")
                page.click(".selection-popup [data-action=docs]")
                self.assertEqual(page.evaluate("window.__opened.pop()"),
                                 "https://docs.python.org/3/search.html?q=increment")
            with self.subTest(browser=browser, action="copy"):
                page.mouse.click(5, 5)
                self.select(page, "#plain", "favours", "prepared")
                page.click(".selection-popup [data-action=copy]")
                self.assertEqual(page.evaluate("window.__copied.pop()"), phrase)
            with self.subTest(browser=browser, action="BibTeX"):
                page.mouse.click(5, 5)
                self.select(page, "#plain", "favours", "prepared")
                page.click(".selection-popup [data-action=cite]")
                bib = page.evaluate("window.__copied.pop()").splitlines()
                self.assertRegex(bib[0], r"^@online\{neuwirth\d{4}reading,$")
                self.assertIn("  title   = {Reading Fixture},", bib)
                self.assertIn("  author  = {Neuwirth, Levi},", bib)
                self.assertIn("  url     = {" + self.base + "/__fixture/reading.html},", bib)
                self.assertIn("  note    = {\\enquote{" + phrase + "}},", bib)


if __name__ == "__main__":
    unittest.main()
