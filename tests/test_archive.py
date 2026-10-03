"""tools/archive.py's pure functions: slugs, URL equivalence, link-rot
hysteresis, .bib citations, snapshot grading (audit T14). The network probe
has its own tests in test_archive_probe.py."""

import datetime
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SPEC = importlib.util.spec_from_file_location(
    "archive_tool", Path(__file__).resolve().parents[1] / "tools" / "archive.py")
archive = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(archive)

try:
    import bs4  # noqa: F401
    HAVE_BS4 = True
except ImportError:
    HAVE_BS4 = False

DAY = datetime.date(2026, 10, 1)


def days(n):
    return DAY + datetime.timedelta(days=n)


class SlugTests(unittest.TestCase):
    def test_domain_label_and_path_tail(self):
        self.assertEqual(archive.derive_slug("https://www.example.com/papers/Foo_Bar.pdf"),
                         "example-foo-bar-pdf")

    def test_trailing_slash_and_bare_host(self):
        self.assertEqual(archive.derive_slug("https://blog.example.org/post/"), "example-post")
        self.assertEqual(archive.derive_slug("https://example.org/"), "example-index")

    def test_truncated_without_a_trailing_hyphen(self):
        slug = archive.derive_slug("https://example.com/" + "word-" * 30)
        self.assertLessEqual(len(slug), 64)
        self.assertFalse(slug.endswith("-"))

    def test_nothing_sluggable_falls_back_to_a_hash(self):
        slug = archive.derive_slug("https://例え.テスト/記事")
        self.assertRegex(slug, r"^[0-9a-f]{12}$")

    def test_manifest_slug_wins(self):
        self.assertEqual(archive.entry_slug({"url": "https://example.com/x", "slug": "mine"}), "mine")
        self.assertEqual(archive.entry_slug({"url": "https://example.com/x"}), "example-x")

    def test_aliases_must_be_http_urls(self):
        self.assertEqual(archive.entry_aliases({"url": "u", "aliases": ["https://doi.org/1"]}),
                         ["https://doi.org/1"])
        self.assertEqual(archive.entry_aliases({"url": "u"}), [])
        for bad in ("https://doi.org/1", ["doi:10.1/x"], [3]):
            with self.assertRaises(SystemExit), mock.patch.object(archive, "err"):
                archive.entry_aliases({"url": "u", "aliases": bad})


class UrlEquivalenceTests(unittest.TestCase):
    def test_tracking_parameters_go_and_others_stay(self):
        self.assertEqual(archive.strip_tracking("https://e.com/a?utm_source=x&v=2&fbclid=y"),
                         "https://e.com/a?v=2")
        self.assertEqual(archive.strip_tracking("https://e.com/a"), "https://e.com/a")

    def test_normalize_url(self):
        self.assertEqual(archive.normalize_url("http://e.com/a/?utm_medium=m#sec"), "https://e.com/a")
        self.assertEqual(archive.normalize_url("https://arxiv.org/pdf/2401.01234v3.pdf"),
                         "https://arxiv.org/abs/2401.01234")
        self.assertEqual(archive.normalize_url("https://e.com/a?id=7"), "https://e.com/a?id=7")

    def test_arxiv_forms(self):
        forms = archive.arxiv_aliases("https://arxiv.org/abs/2401.01234v2")
        for f in ("https://arxiv.org/abs/2401.01234", "https://arxiv.org/abs/2401.01234v2",
                  "https://arxiv.org/pdf/2401.01234", "https://arxiv.org/pdf/2401.01234v2.pdf"):
            self.assertIn(f, forms)
        self.assertEqual(archive.arxiv_aliases("https://example.com/abs/1"), set())

    def test_url_aliases_fold_scheme_and_slash_but_omit_the_key(self):
        url = "https://e.com/a/?ref=x"
        aliases = archive.url_aliases(url)
        self.assertNotIn(url, aliases)
        for a in ("http://e.com/a/?ref=x", "https://e.com/a/", "https://e.com/a", "http://e.com/a"):
            self.assertIn(a, aliases)

    def test_moved_meaningfully(self):
        self.assertFalse(archive.moved_meaningfully("http://e.com/a/", "https://e.com/a#top"))
        self.assertTrue(archive.moved_meaningfully("https://e.com/a", "https://e.com/b"))

    def test_wayback_raw_url(self):
        self.assertEqual(archive.wayback_raw_url("https://web.archive.org/web/20200101000000/https://e.com/"),
                         "https://web.archive.org/web/20200101000000id_/https://e.com/")
        self.assertEqual(archive.wayback_raw_url("https://e.com/"), "https://e.com/")


class LinkRotHysteresisTests(unittest.TestCase):
    def fail_streak(self, n, every=7):
        state = {"status": "live", "status-since": DAY.isoformat()}
        for i in range(n):
            state = archive.next_state(state, "fail", None, days(i * every))
        return state

    def test_one_failure_is_only_an_error(self):
        s = self.fail_streak(1)
        self.assertEqual((s["status"], s["consecutive-failures"]), ("error", 1))

    def test_rotting_needs_enough_failures_and_enough_days(self):
        self.assertEqual(self.fail_streak(archive.ROT_FAILS)["status"], "rotted")
        quick = self.fail_streak(archive.ROT_FAILS, every=1)
        self.assertEqual(quick["status"], "error", "three failures in two days are not rot")
        self.assertEqual(self.fail_streak(archive.ROT_FAILS - 1, every=30)["status"], "error")

    def test_the_streak_starts_at_its_first_failure(self):
        s = self.fail_streak(2)
        self.assertEqual(s["status-since"], DAY.isoformat())

    def test_recovery_is_immediate(self):
        s = archive.next_state(self.fail_streak(5), "ok", None, days(60))
        self.assertEqual((s["status"], s["consecutive-failures"], s["status-since"]),
                         ("live", 0, days(60).isoformat()))

    def test_a_live_link_keeps_its_since_date(self):
        s = archive.next_state({"status": "live", "status-since": "2025-01-01"}, "ok", None, DAY)
        self.assertEqual(s["status-since"], "2025-01-01")

    def test_moved_records_where_to(self):
        s = archive.next_state({"status": "live"}, "moved", "https://e.com/b", DAY)
        self.assertEqual((s["status"], s["new-url"]), ("moved", "https://e.com/b"))


class BibCitationTests(unittest.TestCase):
    BIB = """
@comment{ url = {https://ignored.example/} }
@article{Smith2020,
  title = {A},
  doi = {10.1000/xyz},
  url = {https://journal.example/a},
}
@inproceedings{Doe2021,
  doi = "10.1000/abc",
}
@misc{Local,
  url = {file:///tmp/x},
}
@book{NoLink, title = {B}}
"""

    def test_url_wins_doi_resolves_and_the_rest_is_skipped(self):
        self.assertEqual(archive.bib_citations(self.BIB),
                         [("Smith2020", "https://journal.example/a"),
                          ("Doe2021", "https://doi.org/10.1000/abc")])


@unittest.skipUnless(HAVE_BS4, "beautifulsoup4 not installed")
class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="archive-"))
        self.addCleanup(lambda: [p.unlink() for p in self.tmp.iterdir()] and self.tmp.rmdir())

    def page(self, body, head=""):
        p = self.tmp / "snapshot.html"
        p.write_text(f"<html><head>{head}</head><body>{body}</body></html>", encoding="utf-8")
        return p

    def test_grades(self):
        prose = "<p>" + "Words of an archived article. " * 20 + "</p>"
        self.assertEqual(archive.classify_snapshot(self.page(prose)), "ok")
        self.assertEqual(archive.classify_snapshot(self.page(prose + '<img src="https://cdn.example/a.png">')),
                         "degraded")
        self.assertEqual(archive.classify_snapshot(self.page(prose + '<img data-src="/a.png">')), "degraded")
        self.assertEqual(archive.classify_snapshot(self.page("<div id=app></div><script>" + "x" * 500 + "</script>")),
                         "js-required")

    def test_noarchive_meta(self):
        self.assertTrue(archive.body_noarchive(self.page("", '<meta name="robots" content="noindex, NOARCHIVE">')))
        self.assertFalse(archive.body_noarchive(self.page("", '<meta name="robots" content="noindex">')))


if __name__ == "__main__":
    unittest.main()
