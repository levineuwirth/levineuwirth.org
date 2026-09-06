#!/usr/bin/env python3
"""Tests for tools/check-site.py — the post-build artifact gate.

Every case builds a tiny synthetic ``_site`` in a temporary directory, so
nothing here reads or writes the real build output.  The baseline fixture is
deliberately *clean*: each test then introduces exactly one defect and
asserts that the gate notices it and nothing else changes verdict.

Run with: ``make test`` (or ``python3 -m unittest tests.test_check_site``).
"""

from __future__ import annotations

import importlib.util
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

# check-site.py is a hyphenated script, not an importable module name, so it
# is loaded by path rather than by `import`.

_SPEC = importlib.util.spec_from_file_location(
    "check_site",
    Path(__file__).resolve().parent.parent / "tools" / "check-site.py",
)
assert _SPEC and _SPEC.loader
check_site = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(check_site)


FEED = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Test</title>
  <id>https://example.org/feed.xml</id>
  <updated>2026-09-05T00:00:00Z</updated>
  <entry>
    <title>One</title>
    <id>https://example.org/one/</id>
    <updated>2026-09-05T00:00:00Z</updated>
  </entry>
</feed>
"""

SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.org/</loc></url>
</urlset>
"""

PAGE = """<!doctype html>
<html><body>
<main id="content">
<p>Ordinary prose with a <a href="/essays/one/">link</a>.</p>
<img src="/images/a.jpg" alt="a">
</main>
</body></html>
"""


class SiteFixture:
    """A minimal, passing ``_site`` that each test perturbs."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.write("index.html", PAGE)
        self.write("404.html", "<!doctype html><title>Not found</title>")
        self.write("feed.xml", FEED)
        self.write("music/feed.xml", FEED)
        self.write("sitemap.xml", SITEMAP)
        self.write("images/a.jpg", "jpeg-bytes")
        self.write("images/a.webp", "webp-bytes")

    def write(self, rel: str, text: str) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path


class CheckSiteTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="check-site-test-")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "_site"
        self.root.mkdir()
        self.site = SiteFixture(self.root)

    def run_gate(self, *extra: str) -> tuple[int, str]:
        """Run the gate over the fixture, returning (exit code, output)."""
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = check_site.main([str(self.root), *extra])
        return code, out.getvalue() + err.getvalue()

    # -- baseline ----------------------------------------------------------

    def test_clean_site_passes(self):
        code, output = self.run_gate()
        self.assertEqual(code, 0, output)
        self.assertIn("check-site: OK", output)

    def test_missing_directory_is_usage_error(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = check_site.main([str(self.root / "nope")])
        self.assertEqual(code, 2)

    # -- S01: publication boundary ----------------------------------------

    def test_private_note_fails(self):
        self.site.write("essays/private.local.html", PAGE)
        code, output = self.run_gate()
        self.assertEqual(code, 1)
        self.assertIn("essays/private.local.html", output)

    def test_credential_shaped_file_fails(self):
        self.site.write("deploy.key", "not-a-real-key")
        code, output = self.run_gate()
        self.assertEqual(code, 1)
        self.assertIn("deploy.key", output)

    def test_planning_checklist_fails_even_under_source_mirror(self):
        self.site.write("source/checklist.md", "# local planning notes")
        code, output = self.run_gate()
        self.assertEqual(code, 1)
        self.assertIn("source/checklist.md", output)

    def test_compressed_sidecar_of_private_file_fails(self):
        # compress-assets.sh would make one of these for any published file.
        self.site.write("notes.local.md.gz", "compressed")
        code, output = self.run_gate()
        self.assertEqual(code, 1)
        self.assertIn("notes.local.md.gz", output)

    def test_pycache_directory_fails(self):
        self.site.write("source/tools/__pycache__/embed.cpython-313.pyc", "x")
        code, output = self.run_gate()
        self.assertEqual(code, 1)
        self.assertIn("__pycache__", output)

    def test_editor_and_temporary_debris_fails(self):
        self.site.write("essays/one.html~", PAGE)
        self.site.write("images/b.webp.part", "partial")
        code, output = self.run_gate()
        self.assertEqual(code, 1)
        self.assertIn("one.html~", output)
        self.assertIn("b.webp.part", output)

    # -- B08: drafts -------------------------------------------------------

    def test_drafts_directory_fails(self):
        self.site.write("drafts/essays/wip.html", PAGE)
        code, output = self.run_gate()
        self.assertEqual(code, 1)
        self.assertIn("drafts/", output)

    def test_draft_href_in_corpus_fails(self):
        self.site.write(
            "essays/index.html",
            '<html><body><a href="/drafts/essays/wip/">WIP</a></body></html>',
        )
        code, output = self.run_gate()
        self.assertEqual(code, 1)
        self.assertIn("links into /drafts/", output)

    def test_draft_string_in_source_mirror_is_ignored(self):
        # The published Makefile copy legitimately mentions _site/drafts.
        self.site.write(
            "source/templates/default.html",
            '<html><body><a href="/drafts/x/">$body$</a></body></html>',
        )
        code, output = self.run_gate()
        self.assertEqual(code, 0, output)

    # -- B03: render failures ---------------------------------------------

    def test_visualization_error_block_fails(self):
        self.site.write(
            "essays/figure.html",
            '<html><body><div class="viz-error"><strong>Visualization '
            "error:</strong> ModuleNotFoundError</div></body></html>",
        )
        code, output = self.run_gate()
        self.assertEqual(code, 1)
        self.assertIn("figure/visualization script failed", output)

    def test_score_error_block_fails(self):
        self.site.write(
            "music/piece.html",
            '<html><body><figure class="score-fragment '
            'score-fragment--error"><div class="score-fragment-error">'
            "Missing score: scores/x.svg</div></figure></body></html>",
        )
        code, output = self.run_gate()
        self.assertEqual(code, 1)
        self.assertIn("score fragment missing", output)

    def test_unresolved_figure_reference_fails(self):
        self.site.write(
            "essays/refs.html",
            '<html><body><p>See <a href="#fig-typo">Figure ?</a>.</p>'
            "</body></html>",
        )
        code, output = self.run_gate()
        self.assertEqual(code, 1)
        self.assertIn("unresolved figure cross-reference", output)

    def test_resolved_figure_reference_passes(self):
        self.site.write(
            "essays/refs.html",
            '<html><body><p>See <a href="#fig-1">Figure 1</a>.</p>'
            "</body></html>",
        )
        code, output = self.run_gate()
        self.assertEqual(code, 0, output)

    # -- missing media -----------------------------------------------------

    def test_missing_img_src_fails(self):
        self.site.write(
            "essays/missing.html",
            '<html><body><img src="/images/gone.jpg" alt=""></body></html>',
        )
        code, output = self.run_gate()
        self.assertEqual(code, 1)
        self.assertIn("/images/gone.jpg", output)

    def test_missing_srcset_candidate_fails(self):
        self.site.write(
            "essays/missing.html",
            "<html><body><picture>"
            '<source srcset="/images/a.webp 1x, /images/a-2x.webp 2x" '
            'type="image/webp">'
            '<img src="/images/a.jpg" alt=""></picture></body></html>',
        )
        code, output = self.run_gate()
        self.assertEqual(code, 1)
        self.assertIn("/images/a-2x.webp", output)

    def test_relative_and_remote_image_urls_resolve(self):
        self.site.write("essays/rel/img.png", "png")
        self.site.write(
            "essays/rel/index.html",
            "<html><body>"
            '<img src="img.png" alt="">'
            '<img src="https://example.org/remote.png" alt="">'
            '<img src="data:image/gif;base64,R0lGOD" alt="">'
            "</body></html>",
        )
        code, output = self.run_gate()
        self.assertEqual(code, 0, output)

    def test_percent_encoded_image_path_resolves(self):
        self.site.write("images/a b.jpg", "jpeg")
        self.site.write(
            "essays/enc.html",
            '<html><body><img src="/images/a%20b.jpg" alt=""></body></html>',
        )
        code, output = self.run_gate()
        self.assertEqual(code, 0, output)

    # -- feeds and sitemap -------------------------------------------------

    def test_non_rfc3339_feed_updated_fails(self):
        self.site.write("music/feed.xml", FEED.replace(
            "<updated>2026-09-05T00:00:00Z</updated>",
            "<updated>Unknown</updated>",
            1,
        ))
        code, output = self.run_gate()
        self.assertEqual(code, 1)
        self.assertIn("not RFC 3339", output)

    def test_malformed_feed_fails(self):
        self.site.write("feed.xml", "<feed><unclosed>")
        code, output = self.run_gate()
        self.assertEqual(code, 1)
        self.assertIn("not well-formed", output)

    def test_missing_feed_fails(self):
        os.unlink(self.root / "music" / "feed.xml")
        code, output = self.run_gate()
        self.assertEqual(code, 1)
        self.assertIn("feed:music/feed.xml", output)

    def test_malformed_sitemap_fails(self):
        self.site.write("sitemap.xml", "<urlset><url>")
        code, output = self.run_gate()
        self.assertEqual(code, 1)
        self.assertIn("sitemap.xml is not well-formed", output)

    def test_offset_timezone_updated_is_accepted(self):
        self.site.write("feed.xml", FEED.replace(
            "2026-09-05T00:00:00Z", "2026-09-05T00:00:00+02:00"
        ))
        code, output = self.run_gate()
        self.assertEqual(code, 0, output)

    # -- 404 ---------------------------------------------------------------

    def test_missing_404_fails_by_default(self):
        os.unlink(self.root / "404.html")
        code, output = self.run_gate()
        self.assertEqual(code, 1)
        self.assertIn("404.html is missing", output)

    def test_missing_404_is_a_warning_with_flag(self):
        os.unlink(self.root / "404.html")
        code, output = self.run_gate("--allow-missing-404")
        self.assertEqual(code, 0, output)
        self.assertIn("WARNINGS", output)
        self.assertIn("404.html is missing", output)

    # -- duplicate ids (warning only) --------------------------------------

    def test_duplicate_ids_warn_but_do_not_fail(self):
        self.site.write(
            "build/index.html",
            '<html><body><div id="content"><main id="content">x</main>'
            "</div></body></html>",
        )
        code, output = self.run_gate()
        self.assertEqual(code, 0, output)
        self.assertIn("duplicate-ids", output)
        self.assertIn("content", output)

    # -- webp --------------------------------------------------------------

    def test_zero_webp_warns_by_default(self):
        os.unlink(self.root / "images" / "a.webp")
        code, output = self.run_gate()
        self.assertEqual(code, 0, output)
        self.assertIn("zero .webp companions", output)

    def test_zero_webp_fails_with_require_webp(self):
        os.unlink(self.root / "images" / "a.webp")
        code, output = self.run_gate("--require-webp")
        self.assertEqual(code, 1)
        self.assertIn("zero .webp companions", output)

    def test_no_jpegs_means_no_webp_complaint(self):
        os.unlink(self.root / "images" / "a.webp")
        os.unlink(self.root / "images" / "a.jpg")
        self.site.write("index.html", "<html><body><p>text</p></body></html>")
        code, output = self.run_gate()
        self.assertEqual(code, 0, output)
        self.assertNotIn("zero .webp companions", output)

    # -- vendored subtrees are not first-party ------------------------------

    def test_vendored_pdfjs_is_not_scanned(self):
        self.site.write(
            "pdfjs/web/viewer.html",
            '<html><body><img src="images/toolbarButton.png" alt="">'
            '<div id="viewer"></div><div id="viewer"></div></body></html>',
        )
        code, output = self.run_gate()
        self.assertEqual(code, 0, output)

    def test_archive_snapshot_is_not_scanned(self):
        self.site.write(
            "archive/x/snapshot.html",
            '<html><body><img src="/gone-upstream.png" alt=""></body></html>',
        )
        code, output = self.run_gate()
        self.assertEqual(code, 0, output)


if __name__ == "__main__":
    unittest.main()
