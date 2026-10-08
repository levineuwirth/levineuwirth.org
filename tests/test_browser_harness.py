"""The browser harness's own probes, on cases whose answer is known.

tests/test_browser_a11y.py fails a Tab stop that tools/browser/kbd_run.py
finds clipped: inside a box that clips its overflow and leaves none of it
showing. Which boxes clip an element depends on its positioning, and a
probe that guesses wrong either fails stops a reader can see (it called
every stop on the score reader clipped) or passes ones nobody can (a
fixed control inside a transformed, collapsed box). Each case here says
what the probe must answer, and the browser's own hit test at the
element's centre must agree, so the expectation cannot be wrong either.
In Chromium and Firefox.

    RUN_BROWSER_TESTS=1 python -m unittest tests.test_browser_harness -v
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests._browser import (BROWSERS, check_site, harness_constant, require_playwright,
                            requires_browser, site_server)

# name: (markup, clipped). Each holds one focusable, #t-<name>; the fixed
# ones sit apart, so no case covers another's centre.
CASES = {
    "collapsed box": ('<div class="shut"><a id="t-collapsed-box" href="#x">a</a></div>', True),
    "open box": ('<div class="open"><a id="t-open-box" href="#x">a</a></div>', False),
    "fixed, viewport block": (
        '<div class="shut"><button id="t-fixed-viewport-block" class="fix" style="left: 20px">b</button></div>',
        False),
    "fixed, the box transformed": (
        '<div class="shut" style="transform: translateZ(0)">'
        '<button id="t-fixed-the-box-transformed" class="fix" style="left: 140px">b</button></div>', True),
    "fixed, transformed inside the box": (
        '<div class="shut"><div style="transform: translateX(0)">'
        '<button id="t-fixed-transformed-inside-the-box" class="fix" style="left: 260px">b</button></div></div>',
        True),
    "fixed, the box filtered": (
        '<div class="shut" style="filter: blur(0)">'
        '<button id="t-fixed-the-box-filtered" class="fix" style="left: 380px">b</button></div>', True),
    "fixed, the box contained": (
        '<div class="shut" style="contain: paint">'
        '<button id="t-fixed-the-box-contained" class="fix" style="left: 500px">b</button></div>', True),
    "absolute, the box positioned": (
        '<div class="shut" style="position: relative">'
        '<a id="t-absolute-the-box-positioned" class="abs" href="#x">a</a></div>', True),
    "absolute, its block above the box": (
        '<div style="position: relative; height: 40px"><div class="shut">'
        '<a id="t-absolute-its-block-above-the-box" class="abs" href="#x">a</a></div></div>', False),
}

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Probe fixture</title>
<style>
  body {{ margin: 0; padding: 400px 20px 20px; }}
  .shut {{ height: 0; overflow: hidden; margin: 20px 0; }}
  .open {{ overflow: hidden; margin: 20px 0; }}
  .fix {{ position: fixed; top: 300px; width: 100px; height: 30px; }}
  .abs {{ position: absolute; top: 0; left: 0; }}
</style></head><body>
{cases}
</body></html>
"""

# What the browser shows at the element's centre: the element, or another.
HIT = """el => { const r = el.getBoundingClientRect();
    const at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    return !!at && (at === el || el.contains(at)); }"""


def target(name: str) -> str:
    return "#t-" + name.replace(",", "").replace(" ", "-")


@requires_browser
class FocusProbe(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        check_site()
        require_playwright()
        from playwright.sync_api import sync_playwright
        cls.info = harness_constant("kbd_run.py", "FOCUS_INFO")
        tmp = Path(cls.enterClassContext(tempfile.TemporaryDirectory(prefix="browser-harness-")))
        (tmp / "fixtures").mkdir()
        (tmp / "fixtures" / "probe.html").write_text(
            PAGE.format(cases="\n".join(markup for markup, _ in CASES.values())), encoding="utf-8")
        cls.base = cls.enterClassContext(site_server(tmp, fixtures=tmp / "fixtures"))
        playwright = cls.enterClassContext(sync_playwright())
        cls.browsers = {}
        for name in BROWSERS:
            cls.browsers[name] = getattr(playwright, name).launch()
            cls.addClassCleanup(cls.browsers[name].close)

    def test_clipped(self) -> None:
        for browser in BROWSERS:
            page = self.browsers[browser].new_page(viewport={"width": 1000, "height": 800})
            self.addCleanup(page.close)
            page.goto(self.base + "/__fixture/probe.html", wait_until="load")
            for name, (_, clipped) in CASES.items():
                with self.subTest(browser=browser, case=name):
                    el = page.locator(target(name))
                    el.focus()
                    self.assertEqual(el.evaluate(HIT), not clipped, "the fixture's own premise")
                    got = page.evaluate(self.info)
                    self.assertEqual(bool(got["clipped"]), clipped, got)


if __name__ == "__main__":
    unittest.main()
