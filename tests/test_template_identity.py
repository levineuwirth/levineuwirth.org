"""Real templates and the web manifest render alternate identity and track edits."""
import html
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from tests._helpers import ROOT, requires_cabal, script_env, write_site_config


@requires_cabal
class TemplateIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tmp = tempfile.TemporaryDirectory(prefix="template-identity-probe-")
        cls.addClassCleanup(tmp.cleanup)
        build = Path(tmp.name)
        (build / "Probe.hs").write_text('''{-# LANGUAGE OverloadedStrings #-}
import Config
import Hakyll
import Utils (stripHtmlComments)
import Control.Monad (forM_)
main = hakyll $ do
    configRules
    manifestRules
    match "templates/**" $ compile $ do
        item <- getResourceBody
        tpl <- compileTemplateItem (fmap stripHtmlComments item)
        pure (itemSetBody tpl item)
    let ctx = identityContext <> constField "home" "true" <> constField "title" "Piece"
              <> constField "url" "/probe" <> constField "canonical-url" "/probe"
              <> bodyField "body"
    forM_ ["partials/head.html", "partials/footer.html", "partials/archive-removal-notice.html",
           "404.html", "score-reader-default.html"] $ \\name ->
        create [fromFilePath name] $ do
            route idRoute
            compile $ makeItem ("" :: String) >>= loadAndApplyTemplate (fromFilePath ("templates/" ++ name)) ctx
''')
        cls.binary = build / "probe"
        done = subprocess.run(["cabal", "exec", "--", "ghc", "-v0", "-ibuild",
                               "-outputdir", str(build), str(build / "Probe.hs"),
                               "-o", str(cls.binary)], cwd=ROOT, env=script_env(),
                              capture_output=True, text=True, timeout=180)
        if done.returncode:
            raise AssertionError(done.stderr)

    def test_identity_escaping_advertisements_manifest_and_incremental_changes(self):
        with tempfile.TemporaryDirectory(prefix="template-identity-") as tmp:
            root = Path(tmp)
            shutil.copytree(ROOT / "templates", root / "templates")
            title = 'A & B <Studio> "quoted"'
            manifest = {"name": title, "short-name": 'A "B"', "description": "Art & photos",
                        "theme-color": "#123456", "background-color": "#abcdef"}
            feed = {"path": "news.xml", "title": title, "description": "News", "sections": ["essays"]}
            config = dict(title=title, email="a&b@example.org", **{
                "contact-email": "contact&us@example.org", "signing-fingerprint": "ABC DEF",
                "manifest": manifest, "feeds": [feed, dict(feed, path="hidden.xml", advertise=False)]})
            write_site_config(root, **config)
            for changed in (False, True):
                if changed:
                    before = (root / "site.yaml").stat().st_mtime
                    config["title"] = "Changed identity"
                    config["manifest"] = manifest | {"name": "Changed manifest"}
                    config["feeds"] = [dict(feed, **{"advertise-title": "Changed advertisement"})]
                    write_site_config(root, **config)
                    os.utime(root / "site.yaml", (before + 2, before + 2))
                done = subprocess.run([str(self.binary), "build"], cwd=root, env=script_env(),
                                      capture_output=True, text=True, timeout=60)
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
                def read(name):
                    return (root / "_site" / name).read_text()
                head = read("partials/head.html")
                self.assertIn(f'<title>{html.escape(config["title"])}</title>', head)
                self.assertIn('href="/news.xml"', head)
                self.assertNotIn('hidden.xml', head)
                self.assertEqual(head.count('rel="alternate"'), 1)
                if changed:
                    self.assertIn('title="Changed advertisement"', head)
                else:
                    self.assertIn(f'title="{html.escape(title)}"', head)
                self.assertIn("mailto:a&amp;b@example.org", read("404.html"))
                self.assertIn("contact&amp;us@example.org", read("partials/archive-removal-notice.html"))
                self.assertIn("Ed25519 signing subkey ABC DEF", read("partials/footer.html"))
                self.assertIn(f'Piece — Score — {html.escape(config["title"])}', read("score-reader-default.html"))
                parsed = json.loads(read("site.webmanifest"))
                for key, value in config["manifest"].items():
                    self.assertEqual(parsed[key.replace("-", "_")], value)
