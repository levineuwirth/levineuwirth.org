"""Transclusion, in Chromium and Firefox.

static/js/transclude.js fills each div.transclude with a page fetched by
its data-src (its #markdownBody, or one section), the fetched page's own
transclusions included, and shares one request between the
transclusions of one URL. A fixture page transcludes two fixture pages,
A and B, and B transcludes A again; A's answers are scripted here.

Checked: a passage that loads is shown, and a URL transcluded twice is
asked once; one that fails says so and links to its source; and a failed
request is not kept: it was, for the life of the page, so a later
transclusion of the same URL (B's) failed too without asking again.

    RUN_BROWSER_TESTS=1 python -m unittest tests.test_browser_transclude -v
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests._browser import (BROWSERS, FakeNetwork, check_site, enforcing_csp, require_playwright,
                            requires_browser, site_server)
from tests._browser import fake_answer as answer

HOST = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Transclusion fixture</title>
<script src="/js/utils.js"></script>
<script src="/js/transclude.js" defer></script>
</head><body><main id="markdownBody">
<div class="transclude" id="t-a" data-src="/__fixture/a.html"></div>
<div class="transclude" id="t-b" data-src="/__fixture/b.html"></div>
</main></body></html>
"""
A = """<!doctype html><html lang="en"><head><title>A</title></head><body>
<main id="markdownBody"><p class="from-a">Passage A.</p></main></body></html>
"""
B = """<!doctype html><html lang="en"><head><title>B</title></head><body>
<main id="markdownBody"><p class="from-b">Passage B, which quotes A:</p>
<div class="transclude" data-src="/__fixture/a.html"></div></main></body></html>
"""


@requires_browser
class Transclusion(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        check_site()
        require_playwright()
        from playwright.sync_api import expect, sync_playwright
        cls.expect = staticmethod(expect)
        tmp = Path(cls.enterClassContext(tempfile.TemporaryDirectory(prefix="browser-transclude-")))
        (tmp / "fixtures").mkdir()
        (tmp / "fixtures" / "host.html").write_text(HOST, encoding="utf-8")
        cls.base = cls.enterClassContext(site_server(tmp, enforcing_csp(), tmp / "fixtures"))
        playwright = cls.enterClassContext(sync_playwright())
        cls.browsers = {}
        for name in BROWSERS:
            cls.browsers[name] = getattr(playwright, name).launch()
            cls.addClassCleanup(cls.browsers[name].close)

    def host(self, browser: str, a, b):
        """The host page with A and B answered by `a` and `b` (callables
        taking the route); the page's errors and any request leaving
        serve.py are checked at cleanup."""
        context = self.browsers[browser].new_context()
        self.addCleanup(context.close)
        net = FakeNetwork(context, self.base, {"a": r"/__fixture/a\.html$", "b": r"/__fixture/b\.html$"},
                          {"a": a, "b": b}, local=r"__fixture/[ab]\.html$")
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))

        def clean():
            self.assertEqual(errors, [], "page errors")
            self.assertEqual(net.unexpected, [], "requests leaving serve.py")
        self.addCleanup(clean)
        page.goto(self.base + "/__fixture/host.html", wait_until="load")
        return page, net

    def test_a_passage_loads_and_one_request_serves_a_url(self) -> None:
        for browser in BROWSERS:
            with self.subTest(browser=browser):
                page, net = self.host(browser, lambda r: r.fulfill(**answer(A, "text/html")),
                                      lambda r: r.fulfill(**answer(B, "text/html")))
                self.expect(page.locator("#t-a .from-a")).to_have_text("Passage A.")
                self.expect(page.locator("#t-b .from-b")).to_be_visible()
                self.expect(page.locator("#t-b .from-a")).to_have_text("Passage A.")
                self.expect(page.locator("#t-a")).to_have_class("transclude transclude--loaded")
                self.assertEqual(net.hits["a"], 1)

    def test_a_failed_request_is_not_kept(self) -> None:
        # A's first request is refused; B is answered only after that, so
        # B's own transclusion of A comes later and must ask again.
        for browser in BROWSERS:
            with self.subTest(browser=browser):
                state = {"a": 0, "b": None}

                def a(route):
                    state["a"] += 1
                    if state["a"] > 1:
                        route.fulfill(**answer(A, "text/html"))
                        return
                    route.abort()
                    if state["b"]:
                        state["b"].fulfill(**answer(B, "text/html"))

                def b(route):
                    if state["a"]:
                        route.fulfill(**answer(B, "text/html"))
                    else:
                        state["b"] = route

                page, net = self.host(browser, a, b)
                error = page.locator("#t-a .transclude-error-note")
                self.expect(error).to_contain_text("This passage could not be loaded.")
                self.expect(error.locator("a")).to_have_attribute("href", "/__fixture/a.html")
                self.expect(page.locator("#t-b .from-a")).to_have_text("Passage A.")
                self.assertEqual(net.hits["a"], 2)


if __name__ == "__main__":
    unittest.main()
