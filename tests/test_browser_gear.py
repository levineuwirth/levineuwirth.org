"""The site's fixed gear fades without blocking touch or keyboard input.

    PYTHONPATH=engine RUN_BROWSER_TESTS=1 .venv/bin/python -m unittest tests.test_browser_gear -v
"""

import tempfile
import unittest
from pathlib import Path

from tests._browser import (BROWSERS, check_site, enforcing_csp, off_season,
                            require_playwright, requires_browser, site_server)
from tests.target import route


@requires_browser
class FixedGear(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        check_site()
        require_playwright()
        from playwright.sync_api import expect, sync_playwright
        cls.expect = staticmethod(expect)
        tmp = Path(cls.enterClassContext(tempfile.TemporaryDirectory(prefix="browser-gear-")))
        cls.base = cls.enterClassContext(site_server(tmp, enforcing_csp()))
        playwright = cls.enterClassContext(sync_playwright())
        cls.browsers = {}
        for name in BROWSERS:
            cls.browsers[name] = getattr(playwright, name).launch()
            cls.addClassCleanup(cls.browsers[name].close)

    def open_page(self, browser, width=1440, touch=False, focus=False):
        context = self.browsers[browser].new_context(
            viewport={"width": width, "height": 900}, has_touch=touch)
        self.addCleanup(context.close)
        context.clock.set_fixed_time(off_season())
        if focus:
            context.add_init_script("localStorage.setItem('focus-mode', '1')")
        page = context.new_page()
        page.goto(self.base + route("essay"), wait_until="load")
        page.evaluate("document.fonts.ready")
        # The reading tracker allows 300 ms for the initial scroll position.
        page.wait_for_timeout(450)
        return page

    def scroll(self, page, y):
        page.evaluate("y => window.scrollTo({top: y, behavior: 'instant'})", y)
        self.expect(page.locator(".settings-wrap")).to_have_attribute("data-away", "")

    def test_pointer_dismissal_does_not_keep_the_gear_visible(self):
        for browser in BROWSERS:
            for touch, width in ((False, 1440), (True, 390), (True, 1024)):
                for focus in (False, True):
                    with self.subTest(browser=browser, touch=touch, width=width, focus=focus):
                        page = self.open_page(browser, width, touch, focus)
                        gear = page.locator(".settings-toggle")
                        activate = gear.tap if touch else gear.click
                        activate()
                        self.expect(gear).to_have_attribute("aria-expanded", "true")
                        activate()
                        self.expect(gear).to_have_attribute("aria-expanded", "false")
                        self.expect(gear).to_be_focused()
                        if not touch:
                            page.mouse.move(20, 200)
                        self.scroll(page, 2000)
                        self.expect(gear).to_have_css("opacity", "0")

    def test_hidden_gear_passes_touches_through_and_can_be_reopened(self):
        for browser in BROWSERS:
            for width in (390, 1024):
                for focus in (False, True):
                    with self.subTest(browser=browser, width=width, focus=focus):
                        page = self.open_page(browser, width, touch=True, focus=focus)
                        gear = page.locator(".settings-toggle")
                        self.scroll(page, 2000)
                        self.expect(gear).to_have_css("opacity", "0")
                        # Put a real tap target directly under the wrapper. A
                        # transparent wrapper must not intercept its clicks.
                        point = page.evaluate("""() => {
                            const r = document.querySelector('.settings-wrap').getBoundingClientRect();
                            const target = document.createElement('button');
                            target.id = 'under-gear';
                            target.textContent = 'Underlying action';
                            // Above the phone's Contents bar (90), below the gear.
                            Object.assign(target.style, {position: 'fixed', zIndex: '99',
                                left: r.x + 'px', top: r.y + 'px', width: r.width + 'px',
                                height: r.height + 'px', padding: '0', margin: '0', border: '0'});
                            target.addEventListener('click', () => target.dataset.clicked = 'yes');
                            document.body.appendChild(target);
                            return {x: r.x + r.width / 2, y: r.y + r.height / 2};
                        }""")
                        page.touchscreen.tap(point["x"], point["y"])
                        self.expect(page.locator("#under-gear")).to_have_attribute("data-clicked", "yes")
                        self.expect(gear).to_have_attribute("aria-expanded", "false")
                        page.evaluate("window.scrollTo({top: 1800, behavior: 'instant'})")
                        self.expect(gear).to_have_css("opacity", "1")
                        gear.tap()
                        self.expect(page.locator(".settings-panel")).to_be_visible()

    def test_keyboard_focus_reveals_the_hidden_gear(self):
        for browser in BROWSERS:
            for touch, width in ((False, 1440), (True, 390)):
                with self.subTest(browser=browser, touch=touch, width=width):
                    page = self.open_page(browser, width, touch)
                    gear = page.locator(".settings-toggle")
                    self.scroll(page, 2000)
                    self.expect(gear).to_have_css("opacity", "0")
                    # The preceding navigation control, without scrolling
                    # back to the masthead and revealing the gear that way.
                    page.locator(".nav-portal-toggle").evaluate("el => el.focus({preventScroll: true})")
                    page.keyboard.press("Tab")
                    self.expect(gear).to_be_focused()
                    self.expect(page.locator(".settings-wrap")).to_have_attribute("data-away", "")
                    self.expect(gear).to_have_css("opacity", "1")
                    page.keyboard.press("Enter")
                    self.expect(page.locator(".settings-panel")).to_be_visible()
                    page.keyboard.press("Escape")
                    self.expect(gear).to_be_focused()
                    self.scroll(page, 2400)
                    self.expect(gear).to_have_css("opacity", "1")


if __name__ == "__main__":
    unittest.main()
