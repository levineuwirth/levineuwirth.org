"""Collapsible sections, printing them, and sidenotes, in Chromium and
Firefox.

collapse.js turns each h2/h3 of an essay into a section a reader can
close, remembered per page; sidenotes.js sets each sidenote beside its
reference, keeps the notes from overlapping, links the two on hover and
click, and on narrow screens opens a note as a sheet. A fixture page,
styled as an essay, has sections and a sidenote below them; the
font-loading test uses a built essay with many notes.

Checked: closing a section takes its content out of view, the tab order
and the accessibility tree, and reopening restores it; the state survives
a reload; a link into a closed section opens it, at load, on hashchange,
and when it names the fragment already in the address bar (no hashchange:
it did nothing); a closed section prints in full (audit J07: it was left off
the paper); sidenotes follow the text when a section above them closes,
and when web fonts arrive after the first layout (J03: notes stayed where
the fallback font had put them); hover, click, Space and Escape on a
reference; the narrow-screen sheet, which gives focus back to its
reference when it closes.

    RUN_BROWSER_TESTS=1 python -m unittest tests.test_browser_sections -v
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests._browser import (BROWSERS, check_site, enforcing_csp, page_styles, require_playwright,
                            requires_browser, site_server)

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Sections fixture</title>
{styles}
<script src="/js/utils.js"></script>
<script src="/js/collapse.js" defer></script>
<script src="/js/sidenotes.js" defer></script>
</head><body><div class="page-shell"><main id="markdownBody">
<h1 class="page-title">Sections Fixture</h1>
<p>An introduction that stays open, with <a id="to-deep" href="#deep">a link to the subsection</a>.</p>
<h2 id="first">First section</h2>
<p id="p1">The first section's text, with <a id="link1" href="#second">a link</a> in it.</p>
{filler}
<h3 id="sub">A subsection</h3>
<p id="deep">Text deep inside the first section.</p>
<h2 id="second">Second section</h2>
<p id="p2">The second section's text, with a note<sup class="sidenote-ref" id="snref-1"><a href="#sn-1">1</a></sup><span class="sidenote" id="sn-1">The note itself, beside its reference.</span> and more after it.</p>
<p>A closing paragraph.</p>
</main></div></body></html>
"""
FILLER = "\n".join(f"<p>Filler paragraph {i}, long enough to take a line or two of the measure "
                   f"so that closing this section moves what follows it.</p>" for i in range(12))

KEY = "section-collapsed:/__fixture/sections.html:"

# Each note where sidenotes.js should have put it, given the layout now:
# level with its reference, or GAP below the note before it.
LAYOUT = """() => {
    const notes = [...document.querySelectorAll('#markdownBody .sidenote')];
    let prevBottom = 0, worst = 0;
    const out = [];
    for (const sn of notes) {
        const ref = document.getElementById('snref-' + sn.id.slice(3));
        const want = Math.max(ref.offsetTop, prevBottom + 12);
        const got = parseFloat(sn.style.top);
        worst = Math.max(worst, Math.abs(got - want));
        out.push([sn.id, got, want]);
        prevBottom = got + sn.offsetHeight;
    }
    return {worst, notes: out};
}"""


@requires_browser
class Sections(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        check_site()
        require_playwright()
        from playwright.sync_api import expect, sync_playwright
        cls.expect = staticmethod(expect)
        tmp = Path(cls.enterClassContext(tempfile.TemporaryDirectory(prefix="browser-sections-")))
        (tmp / "fixtures").mkdir()
        (tmp / "fixtures" / "sections.html").write_text(
            PAGE.format(styles=page_styles(), filler=FILLER), encoding="utf-8")
        cls.base = cls.enterClassContext(site_server(tmp, enforcing_csp(), tmp / "fixtures"))
        playwright = cls.enterClassContext(sync_playwright())
        cls.browsers = {}
        for name in BROWSERS:
            cls.browsers[name] = getattr(playwright, name).launch()
            cls.addClassCleanup(cls.browsers[name].close)

    def open(self, browser: str, path: str = "/__fixture/sections.html", width: int = 1600,
             collapsed: tuple[str, ...] = (), wait: str = "load", context_setup=None):
        context = self.browsers[browser].new_context(viewport={"width": width, "height": 900})
        self.addCleanup(context.close)
        if collapsed:
            context.add_init_script("".join(
                f"try {{ localStorage.setItem('{KEY}{h}', '1'); }} catch (e) {{}}" for h in collapsed))
        if context_setup:
            context_setup(context)
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        self.addCleanup(lambda: self.assertEqual(errors, [], "page errors"))
        page.goto(self.base + path, wait_until=wait)
        return page

    def body(self, page, heading: str):
        return page.locator(f"#section-body-{heading}")

    def toggle(self, page, heading: str):
        return page.locator(f"#{heading} .section-toggle")

    def close_section(self, page, heading: str) -> None:
        self.toggle(page, heading).click()
        self.expect(self.body(page, heading)).to_have_attribute("hidden", "")

    def settled(self, page) -> None:
        """Two frames: sidenotes.js repositions at most once per frame."""
        page.evaluate("new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")

    # -- sections ----------------------------------------------------------

    def test_closing_a_section(self) -> None:
        for browser in BROWSERS:
            with self.subTest(browser=browser):
                page = self.open(browser)
                toggle = self.toggle(page, "first")
                self.expect(toggle).to_have_attribute("aria-label", "Toggle section: First section")
                self.expect(toggle).to_have_attribute("aria-expanded", "true")
                self.close_section(page, "first")
                self.expect(toggle).to_have_attribute("aria-expanded", "false")
                self.expect(self.body(page, "first")).to_have_attribute("inert", "")
                self.expect(page.locator("#p1")).to_be_hidden()
                # Out of the tab order: from this toggle, Tab skips the link
                # and the subsection's toggle inside the closed section.
                toggle.focus()
                page.keyboard.press("Tab")
                self.expect(self.toggle(page, "second")).to_be_focused()
                self.assertEqual(page.evaluate(f"localStorage.getItem('{KEY}first')"), "1")
                toggle.click()
                self.expect(self.body(page, "first")).not_to_have_attribute("hidden", "")
                self.expect(page.locator("#p1")).to_be_visible()
                toggle.focus()
                page.keyboard.press("Tab")
                self.expect(page.locator("#link1")).to_be_focused()
                self.assertEqual(page.evaluate(f"localStorage.getItem('{KEY}first')"), "0")

    def test_closed_state_survives_a_reload(self) -> None:
        for browser in BROWSERS:
            with self.subTest(browser=browser):
                page = self.open(browser, collapsed=("first",))
                self.expect(self.body(page, "first")).to_have_attribute("hidden", "")
                self.expect(self.toggle(page, "first")).to_have_attribute("aria-expanded", "false")
                self.expect(page.locator("#p2")).to_be_visible()

    def test_a_link_into_a_closed_section_opens_it(self) -> None:
        for browser in BROWSERS:
            with self.subTest(browser=browser, at="load"):
                page = self.open(browser, path="/__fixture/sections.html#deep", collapsed=("first",))
                self.expect(page.locator("#deep")).to_be_visible()
                self.expect(self.toggle(page, "first")).to_have_attribute("aria-expanded", "true")
                self.expect(page.locator("#deep")).to_be_in_viewport()
            with self.subTest(browser=browser, at="hashchange"):
                page.evaluate("location.hash = ''")
                self.close_section(page, "first")
                page.evaluate("location.hash = '#link1'")
                self.expect(page.locator("#link1")).to_be_visible()
                self.expect(self.toggle(page, "first")).to_have_attribute("aria-expanded", "true")
            with self.subTest(browser=browser, at="the fragment already in the address bar"):
                # A link to the current fragment fires no hashchange: one to
                # a passage closed since did nothing, its target hidden.
                page = self.open(browser, path="/__fixture/sections.html#deep")
                self.close_section(page, "first")
                page.evaluate("window.scrollTo(0, 0)")
                page.click("#to-deep")
                self.assertTrue(page.url.endswith("#deep"))
                self.expect(page.locator("#deep")).to_be_visible()
                self.expect(self.toggle(page, "first")).to_have_attribute("aria-expanded", "true")
                self.expect(page.locator("#deep")).to_be_in_viewport()

    def test_a_closed_section_prints(self) -> None:
        # J07: printed, a closed section was display:none.
        for browser in BROWSERS:
            with self.subTest(browser=browser):
                page = self.open(browser, collapsed=("first",))
                self.expect(page.locator("#p1")).to_be_hidden()
                page.emulate_media(media="print")
                self.expect(page.locator("#p1")).to_be_visible()
                self.expect(page.locator("#deep")).to_be_visible()
                self.assertGreater(self.body(page, "first").evaluate("b => b.offsetHeight"),
                                   page.locator("#p1").evaluate("p => p.offsetHeight"))
                self.expect(self.toggle(page, "second")).to_be_hidden()
                page.emulate_media(media="screen")
                # Printing changed nothing the reader chose.
                self.expect(page.locator("#p1")).to_be_hidden()
                self.assertEqual(page.evaluate(f"localStorage.getItem('{KEY}first')"), "1")

    # -- sidenotes ---------------------------------------------------------

    def test_sidenotes_follow_a_section_closing(self) -> None:
        for browser in BROWSERS:
            with self.subTest(browser=browser):
                page = self.open(browser)
                note = page.locator("#sn-1")
                self.expect(note).to_be_visible()
                self.settled(page)
                before = page.evaluate(LAYOUT)
                self.assertLessEqual(before["worst"], 1, before)
                self.close_section(page, "first")
                self.settled(page)
                after = page.evaluate(LAYOUT)
                self.assertLessEqual(after["worst"], 1, after)
                self.assertGreater(before["notes"][0][1] - after["notes"][0][1], 100,
                                   "closing the section moved the note up")

    def test_sidenotes_follow_late_fonts(self) -> None:
        # J03: the notes were set once, at DOMContentLoaded, often before the
        # web fonts; when they arrived the text moved and the notes did not.
        for browser in BROWSERS:
            with self.subTest(browser=browser):
                held = []
                page = self.open(browser, path="/essays/notes-from-underground.html", wait="domcontentloaded",
                                 context_setup=lambda c: c.route("**/*.woff2", lambda route: held.append(route)))
                self.expect(page.locator("#markdownBody .sidenote").first).to_be_visible()
                self.settled(page)
                refs = page.evaluate("[...document.querySelectorAll('.sidenote-ref')].map(r => r.offsetTop)")
                self.assertGreater(len(held), 0, "no web font was requested")
                self.assertGreaterEqual(len(refs), 3)
                for route in held:
                    route.continue_()
                page.evaluate("document.fonts.ready.then(() => 1)")
                page.wait_for_load_state("load")
                self.settled(page)
                moved = page.evaluate("[...document.querySelectorAll('.sidenote-ref')].map(r => r.offsetTop)")
                self.assertGreater(max(abs(a - b) for a, b in zip(refs, moved)), 10,
                                   "the fonts moved no reference: nothing was tested")
                layout = page.evaluate(LAYOUT)
                self.assertLessEqual(layout["worst"], 1, layout)

    def test_sidenote_linking(self) -> None:
        for browser in BROWSERS:
            with self.subTest(browser=browser):
                page = self.open(browser)
                ref, note = page.locator("#snref-1"), page.locator("#sn-1")
                page.hover("#snref-1")
                self.expect(ref).to_have_class("sidenote-ref is-active")
                self.expect(note).to_have_class("sidenote is-active")
                page.mouse.move(5, 5)
                self.expect(note).to_have_class("sidenote")
                # A click pins it; a click elsewhere lets go.
                page.click("#snref-1 a")
                page.mouse.move(5, 5)
                self.expect(note).to_have_class("sidenote is-active")
                page.mouse.click(5, 5)
                self.expect(note).to_have_class("sidenote")
                # The keyboard: Space pins, Escape lets go.
                page.focus("#snref-1 a")
                page.keyboard.press("Space")
                self.expect(note).to_have_class("sidenote is-active")
                page.keyboard.press("Escape")
                self.expect(note).to_have_class("sidenote")

    def test_narrow_screens_open_a_sheet(self) -> None:
        sheet = ".sidenote-popup-overlay.is-open"
        for browser in BROWSERS:
            page = self.open(browser, width=700)
            self.expect(page.locator("#sn-1")).to_be_hidden()
            link = page.locator("#snref-1 a")
            for close in ("Escape", "button", "outside"):
                with self.subTest(browser=browser, close=close):
                    link.focus()
                    page.keyboard.press("Enter")
                    self.expect(page.locator(sheet)).to_be_visible()
                    self.expect(page.locator(f"{sheet} .sidenote-popup-body")).to_have_text(
                        "The note itself, beside its reference.")
                    self.expect(page.locator(".sidenote-popup")).to_be_focused()
                    if close == "Escape":
                        page.keyboard.press("Escape")
                    elif close == "button":
                        page.click(".sidenote-popup-close")
                    else:
                        page.mouse.click(5, 5)
                    self.expect(page.locator(sheet)).to_have_count(0)
                    self.expect(link).to_be_focused()


if __name__ == "__main__":
    unittest.main()
