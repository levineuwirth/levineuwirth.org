"""The real config CLI, its consumers, and Hakyll dependency invalidation."""

import json
import os
import re
from pathlib import Path
import subprocess
import tempfile
import unittest

from tests._helpers import ROOT, requires_cabal, script_env, site_binary, write_site_config


@requires_cabal
class ConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.binary = site_binary()

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="site-config-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.config = write_site_config(self.root)

    def write_config(self):
        (self.root / "site.yaml").write_text(json.dumps(self.config), encoding="utf-8")

    def run_site(self, *args):
        return subprocess.run([str(self.binary), *args], cwd=self.root, env=script_env(),
                              capture_output=True, text=True, timeout=120)

    def test_config_json_uses_this_sites_identity(self):
        done = self.run_site("config")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(json.loads(done.stdout), self.config)
        self.assertFalse((self.root / "_cache").exists())
        self.assertFalse((self.root / "data").exists())

    def test_make_values_preserve_literal_metacharacters(self):
        # A make include must not expand dollars, lose text after '#', or
        # consume its terminator when a value ends in a backslash.
        self.config["title"] = "Élodie # $5 $(error expanded) \\"
        self.write_config()
        done = self.run_site("config", "--make")
        self.assertEqual(done.returncode, 0, done.stderr)
        (self.root / "config.mk").write_text(done.stdout)
        (self.root / "Makefile").write_text(
            "include config.mk\n"
            "$(file >title.txt,$(SITE_TITLE))\n"
            "$(file >config.json,$(SITE_CONFIG_JSON))\n"
            "all:;@:\n")
        made = subprocess.run(["make", "--no-print-directory"], cwd=self.root,
                              capture_output=True, text=True)
        self.assertEqual(made.returncode, 0, made.stderr)
        self.assertEqual((self.root / "title.txt").read_text(), self.config["title"] + "\n")
        self.assertEqual(json.loads((self.root / "config.json").read_text()), self.config)

    def test_missing_and_malformed_config_fail(self):
        path = self.root / "site.yaml"
        for text in ("[", "{}", "title: [not, a, string]"):
            with self.subTest(text=text):
                path.write_text(text)
                done = self.run_site("config")
                self.assertNotEqual(done.returncode, 0)
                self.assertIn("site.yaml", done.stderr)
        path.unlink()
        self.assertNotEqual(self.run_site("config").returncode, 0)

    def test_invalid_settings_are_rejected(self):
        feed = {"path": "feed.xml", "title": "Example", "description": "Posts",
                "sections": ["essays"], "advertise": True, "limit": 30}
        bad = [
            {"titel": "misspelled"}, {"author": ""}, {"title": "one\ntwo"},
            {"url": "example.org"}, {"url": "https://example.org/"},
            {"host": "example.org/path"}, {"code-license": "../outside"},
            {"host": "other.example"}, {"host": "www.example.org"},
            {"feeds": [feed, feed]},
            *[{"feeds": [dict(feed, **change)]} for change in (
                {"path": "../feed.xml"}, {"path": "/feed.xml"}, {"limit": 0},
                {"sections": []}, {"sections": ["essays", "essays"]},
                {"sections": ["unknown"]}, {"sections": ["essays", "photography"]},
                {"adveritse": True}, {"advertise": "yes"},
            )],
        ]
        original = self.config.copy()
        for overrides in bad:
            with self.subTest(overrides=overrides):
                self.config = original | overrides
                self.write_config()
                done = self.run_site("config")
                self.assertNotEqual(done.returncode, 0, done.stdout)
                self.assertIn("site.yaml", done.stderr)

    def test_url_may_be_the_www_alias_of_host(self):
        self.config["url"] = "https://www.example.org"
        self.write_config()
        done = self.run_site("config")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(json.loads(done.stdout)["url"], "https://www.example.org")

    def test_feed_routes_and_default_author_follow_config(self):
        (self.root / "data").mkdir()
        page = self.root / "content/essays/example.md"
        page.parent.mkdir(parents=True)
        page.write_text("---\ntitle: Example\ndate: 2026-01-01\n---\nText.\n")
        self.config["feeds"] = [
            {"path": "updates.xml", "title": "Updates", "description": "Posts",
             "sections": ["essays"], "limit": 2},
            {"path": "photos.xml", "title": "Photos", "description": "Pictures",
             "sections": ["photography"], "limit": 5},
        ]
        self.write_config()
        done = self.run_site("list-routes")
        self.assertEqual(done.returncode, 0, done.stderr)
        routes = {line.split("\t")[0] for line in done.stdout.splitlines()}
        self.assertTrue({"updates.xml", "photos.xml", "authors/example-author/index.html"} <= routes)
        self.assertTrue({"feed.xml", "music/feed.xml", "photography/feed.xml"}.isdisjoint(routes))

    def test_link_filters_use_configured_hosts_and_repository(self):
        (self.root / "Makefile").write_text("all:;@:\n")
        (self.root / "probe.md").write_text(
            "[own](https://example.org/page)\n\n"
            "[www](https://www.example.org/page)\n\n"
            "[lookalike](https://example.org.attacker.invalid/page)\n\n"
            "[forge](https://git.example.org/author/other)\n\n"
            "[source](https://git.example.org/author/site/src/branch/main/Makefile)\n\n"
            "[configured](https://git.example.org/author/site/raw/branch/next/docs/Makefile)\n\n"
            "`Makefile`\n")
        self.config["source-branch"] = "next/docs"
        self.write_config()
        done = self.run_site("render-fixture", "probe.md")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout.count('class="link-external"'), 2)
        self.assertIn('data-link-icon="forgejo"', done.stdout)
        self.assertEqual(done.stdout.count('class="source-ref"'), 3)
        self.assertIn('href="https://git.example.org/author/site/src/branch/next/docs/Makefile"', done.stdout)
        self.assertNotIn("levineuwirth", done.stdout)


class FeedRenderingTests(unittest.TestCase):
    def test_every_feed_goes_through_render_site_feed(self):
        # An empty feed is valid only through Config.renderSiteFeed; a rule
        # calling Hakyll's renderers directly would write <updated>Unknown.
        for path in sorted((ROOT / "build").rglob("*.hs")):
            if path.name == "Config.hs":
                continue
            with self.subTest(path=path.relative_to(ROOT)):
                text = path.read_text(encoding="utf-8")
                self.assertNotRegex(text, r"\brender(Atom|Rss)\b")

    @requires_cabal
    def test_an_empty_feed_has_a_valid_updated_and_a_populated_one_keeps_its_date(self):
        with tempfile.TemporaryDirectory(prefix="config-feed-") as tmp:
            root = Path(tmp)
            feed = {"description": "Posts", "sections": ["essays"], "limit": None}
            write_site_config(root, feeds=[dict(feed, path="empty.xml", title="Empty"),
                                           dict(feed, path="full.xml", title="Full")])
            (root / "posts").mkdir()
            (root / "posts/a.md").write_text("---\ntitle: A\ndate: 2026-01-02\n---\nText.\n")
            driver = root / "Probe.hs"
            driver.write_text('''{-# LANGUAGE OverloadedStrings #-}
import Config
import Hakyll
main :: IO ()
main = hakyll $ do
    configRules
    match "posts/*" $ do
        route $ setExtension "html"
        compile getResourceBody
    let ctx = bodyField "description" <> dateField "updated" "%Y-%m-%dT%H:%M:%SZ" <> defaultContext
    create ["empty.xml"] $ do
        route idRoute
        compile $ do
            (cfg, spec) <- loadFeed "empty.xml"
            renderSiteFeed cfg spec ctx []
    create ["full.xml"] $ do
        route idRoute
        compile $ do
            (cfg, spec) <- loadFeed "full.xml"
            renderSiteFeed cfg spec ctx =<< loadAll "posts/*"
''')
            binary = root / "probe"
            compiled = subprocess.run(
                ["cabal", "exec", "--", "ghc", "-v0", "-ibuild", "-outputdir", str(root),
                 str(driver), "-o", str(binary)], cwd=ROOT, env=script_env(),
                capture_output=True, text=True, timeout=120)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            done = subprocess.run([str(binary), "build"], cwd=root, env=script_env(),
                                  capture_output=True, text=True, timeout=60)
            self.assertEqual(done.returncode, 0, done.stderr)
            updated = re.compile(r"<updated>([^<]*)</updated>")
            empty = (root / "_site/empty.xml").read_text()
            self.assertRegex(updated.search(empty).group(1), r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
            self.assertNotIn("Unknown", empty)
            full = (root / "_site/full.xml").read_text()
            self.assertEqual(updated.search(full).group(1), "2026-01-02T00:00:00Z")


@requires_cabal
class ConfigDependencyTests(unittest.TestCase):
    def test_config_edit_recompiles_a_cached_context_consumer(self):
        # Compile a small Hakyll consumer of the actual Config module. It
        # bypasses build-freshness.sh, proving loadConfig itself tracks YAML.
        with tempfile.TemporaryDirectory(prefix="config-dependency-") as tmp:
            root = Path(tmp)
            write_site_config(root)
            (root / "page.txt").write_text("$site-title$")
            driver = root / "Probe.hs"
            driver.write_text('''{-# LANGUAGE OverloadedStrings #-}
import Config
import Hakyll
main :: IO ()
main = hakyll $ do
    configRules
    match "page.txt" $ do
        route $ setExtension "html"
        compile $ getResourceBody >>= applyAsTemplate (configField "site-title" siteTitle)
''')
            binary = root / "probe"
            compiled = subprocess.run(
                ["cabal", "exec", "--", "ghc", "-v0", "-ibuild", "-outputdir", str(root),
                 str(driver), "-o", str(binary)], cwd=ROOT, env=script_env(),
                capture_output=True, text=True, timeout=120)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for title in ("Example Site", "Changed Site"):
                if title == "Changed Site":
                    previous = (root / "site.yaml").stat().st_mtime
                    write_site_config(root, title=title)
                    os.utime(root / "site.yaml", (previous + 2, previous + 2))
                done = subprocess.run([str(binary), "build"], cwd=root, env=script_env(),
                                      capture_output=True, text=True, timeout=60)
                self.assertEqual(done.returncode, 0, done.stderr)
                self.assertEqual((root / "_site/page.html").read_text(), title)


if __name__ == "__main__":
    unittest.main()
