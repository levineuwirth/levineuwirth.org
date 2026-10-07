"""Every route under the enforcing CSP, in Chromium and Firefox.

tools/browser/csp_run.py visits the 43 routes in tools/browser/lib.py (every
page type and the 404 page), scrolls through each, exercises what the policy governs (math,
both search tabs, the photography map, link popups, the PDF.js viewer
with its thumbnails and print output, archive snapshots, the score reader, the lightbox), and records CSP
violations, page errors and responses. Here it runs against
tools/browser/serve.py, the production vhost's emulation, with the
enforcing `add_header Content-Security-Policy` line from
nginx/security-headers.conf (the commented candidate while the live policy
is Report-Only), and these tests assert on what it recorded. This is the
check behind promoting that policy.

It needs the network: popups, map tiles and semantic search's
transformers.js come from their real origins, as in production. Popups are
hovered so that their requests meet the policy; whether each provider
shows its popup is for a popup test, not this sweep.

    RUN_BROWSER_TESTS=1 python -m unittest tests.test_browser_csp -v
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests._browser import (BROWSERS, check_site, enforcing_csp, harness_routes,
                            require_playwright, requires_browser, run_harness, site_server)

ROUTES = harness_routes()

# Each browser's routes are split across this many csp_run.py processes,
# all running at once; one process alone takes about seven minutes. The
# whole sweep gets SWEEP_SECONDS.
SHARDS = 3
SWEEP_SECONDS = 1800

# The 404 route is the only one whose document is not a 200.
STATUS = {"404": 404}

# Violations the policy is meant to produce, by route.
EXPECTED_VIOLATIONS = {
    # transformers.js tests once whether eval works and carries on without
    # it; WebAssembly ('wasm-unsafe-eval') is all semantic search needs
    # (nginx/security-headers.conf).
    "search": lambda v: (v.get("effective") == "script-src" and v.get("blocked") == "eval"
                         and (v.get("source") or "").startswith(
                             "https://cdn.jsdelivr.net/npm/@xenova/transformers@")),
}


@requires_browser
class CspSweep(unittest.TestCase):
    results: dict[str, dict[str, dict]]

    @classmethod
    def setUpClass(cls) -> None:
        check_site()
        require_playwright()
        tmp = Path(cls.enterClassContext(tempfile.TemporaryDirectory(prefix="browser-csp-")))
        out = tmp / "runs"
        base = cls.enterClassContext(site_server(tmp, enforcing_csp()))
        names = list(ROUTES)
        port = base.rsplit(":", 1)[1]
        # Online: this sweep is the one meant to meet the live origins.
        run_harness(cls, base, out, [["csp_run.py", browser, port, f"{browser}-{i}.json",
                                      *names[i::SHARDS]]
                                     for browser in BROWSERS for i in range(SHARDS)],
                    offline=False, seconds=SWEEP_SECONDS)
        cls.results = {b: {} for b in BROWSERS}
        for browser in BROWSERS:
            for i in range(SHARDS):
                cls.results[browser].update(json.loads((out / f"{browser}-{i}.json").read_text()))

    def visited(self) -> list[tuple[str, str, dict]]:
        """(browser, route, record) for each route visited in each browser;
        test_every_route_loads reports the others."""
        return [(b, route, self.results[b][route])
                for b in BROWSERS for route in ROUTES if route in self.results[b]]

    def test_every_route_loads(self) -> None:
        for browser in BROWSERS:
            for route, path in ROUTES.items():
                with self.subTest(browser=browser, route=route):
                    rec = self.results[browser].get(route)
                    self.assertIsNotNone(rec, "not visited")
                    self.assertNotIn("goto_err", rec)
                    self.assertEqual(rec["status"], STATUS.get(route, 200), path)
                    self.assertNotIn("features_err", rec)

    def test_no_csp_violations(self) -> None:
        for browser, route, rec in self.visited():
            with self.subTest(browser=browser, route=route):
                expected = EXPECTED_VIOLATIONS.get(route, lambda v: False)
                self.assertEqual([v for v in rec["csp"] if not expected(v)], [])

    def test_no_page_errors(self) -> None:
        for browser, route, rec in self.visited():
            with self.subTest(browser=browser, route=route):
                self.assertEqual(rec["pageerrors"], [])
                self.assertEqual(rec["jserrs"], [])

    def test_no_elements_fail_to_load(self) -> None:
        """An img, script or stylesheet that fires `error`: blocked by the
        policy, missing, or cleared with src=''."""
        for browser, route, rec in self.visited():
            with self.subTest(browser=browser, route=route):
                self.assertEqual(rec["reserrs"], [])

    def test_no_failed_same_origin_responses(self) -> None:
        for browser, route, rec in self.visited():
            with self.subTest(browser=browser, route=route):
                bad = [r for r in rec["bad_status"] if r["url"].startswith("http://127.0.0.1:")
                       # serve.py has no upstream for the popup proxy, and the
                       # 404 route's own document is meant to be one.
                       and "/proxy/" not in r["url"]
                       and not (route == "404" and r["url"].endswith(ROUTES[route]))]
                self.assertEqual(bad, [])

    def test_images_math_and_transclusions_render(self) -> None:
        for browser, route, rec in self.visited():
            f = rec.get("features")
            if f is None:
                continue  # features_err, reported by test_every_route_loads
            with self.subTest(browser=browser, route=route):
                self.assertEqual(f["imgs_broken"], [])
                self.assertEqual(f["katex_err"], 0)
                self.assertGreaterEqual(f["katex"], f["math_raw"], "math left unrendered")
                self.assertEqual(f["transclude_unfilled"], 0)

    def test_features(self) -> None:
        """What the Promotion note in nginx/security-headers.conf says to
        re-test, in each browser."""
        for browser in BROWSERS:
            got = {route: rec.get("features", {}) for route, rec in self.results[browser].items()}

            def check(feature: str, route: str):
                return self.subTest(browser=browser, feature=feature, route=route)

            with check("keyword search", "search"):
                self.assertGreater(got["search"]["search"].get("keyword_results", 0), 0,
                                   got["search"]["search"])
            with check("semantic search", "search"):
                self.assertGreater(got["search"]["search"].get("semantic_results", 0), 0,
                                   got["search"]["search"])
            with check("map tiles and markers", "photo-map"):
                m = got["photo-map"]["map"]
                self.assertGreater(m["tilesLoaded"], 0, m)
                self.assertGreater(m["markers"], 0, m)
                self.assertIsNone(m["err"])
            with check("PDF.js viewer", "pdfjs"):
                pdf = got["pdfjs"]["pdf"]
                self.assertGreater(pdf["canvases"], 0, pdf)
                self.assertGreater(pdf["text"], 0, pdf)
                self.assertIsNone(pdf["err"])
            with check("PDF.js thumbnails (blob: images)", "pdfjs"):
                self.assertNotIn("thumbs_err", pdf)
                self.assertGreater(pdf["thumbs_loaded"], 0, pdf)
            with check("PDF.js print output (blob: images)", "pdfjs"):
                self.assertNotIn("print_err", pdf)
                self.assertEqual(pdf["print_loaded"], pdf["pages"], pdf)
            with check("archive snapshot", "archive-snapshot"):
                frames = [f["url"] for f in got["archive-snapshot"]["iframe"]]
                self.assertTrue(any(u.endswith("/archive/djb-aes-speed/snapshot.html")
                                    for u in frames), frames)
            with check("score pages", "score-reader"):
                self.assertGreater(got["score-reader"]["score"]["stage"]["svgs"], 0)
            with check("lightbox", "photo-single"):
                self.assertTrue(got["photo-single"].get("lightbox", {}).get("visible"),
                                got["photo-single"])
            with check("transclusion", "colophon"):
                loaded = [t["cls"] for t in got["colophon"]["transclude_after"]]
                self.assertTrue(loaded and all("transclude--loaded" in c for c in loaded), loaded)
            with check("math", "essay-grd"):
                self.assertGreater(got["essay-grd"]["katex"], 0)


if __name__ == "__main__":
    unittest.main()
