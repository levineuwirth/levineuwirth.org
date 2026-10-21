"""The engine's files inside a site's build (build/EngineFiles.hs).

A site is built from its own directory with the engine at engine/. Each
engine file stands in for the path it has without that prefix, and a site
file at that path overrides it: templates by alias, static files by route,
raw reads through one resolver. These probes run the real rules over a
scratch site.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from tests._helpers import ENGINE, SITE_ROOT, engine_path, requires_cabal, script_env, site_binary

PROBE = '''{-# LANGUAGE OverloadedStrings #-}
import Control.Monad (forM_, (>=>))
import EngineFiles
import Hakyll
import System.Environment (getArgs)

main :: IO ()
main = getArgs >>= \\args -> case args of
    "resolve" : paths -> mapM_ (resolveFile >=> putStrLn) paths
    "existing" : paths -> mapM_ (existingFile >=> print) paths
    "files" : dirs -> mapM_ (filesIn >=> mapM_ putStrLn) dirs
    _ -> hakyll $ do
        twins <- engineTwins
        staticRules twins
        templateRules twins
        forM_ ["plain.html", "shadowed.html"] $ \\name ->
            create [fromFilePath name] $ do
                route idRoute
                compile $ makeItem ("" :: String)
                    >>= loadAndApplyTemplate (fromFilePath ("templates/" ++ name)) defaultContext
'''


@requires_cabal
class EngineFilesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tmp = tempfile.TemporaryDirectory(prefix="engine-files-probe-")
        cls.addClassCleanup(tmp.cleanup)
        build = Path(tmp.name)
        (build / "Probe.hs").write_text(PROBE)
        cls.binary = build / "probe"
        done = subprocess.run(["cabal", "exec", "--", "ghc", "-v0", f"-i{engine_path('build')}",
                               "-outputdir", str(build), str(build / "Probe.hs"),
                               "-o", str(cls.binary)], cwd=ENGINE, env=script_env(),
                              capture_output=True, text=True, timeout=180)
        if done.returncode:
            raise AssertionError(done.stderr)

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="engine-files-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        # The probe renders a page through each.
        self.write("engine/templates/plain.html", "engine plain")
        self.write("engine/templates/shadowed.html", "engine shadowed")

    def write(self, rel, text, mtime=None):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        if mtime is not None:
            os.utime(path, (mtime, mtime))
        return path

    def run_probe(self, *args):
        done = subprocess.run([str(self.binary), *args], cwd=self.root, env=script_env(),
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        return done.stdout

    def built(self, rel):
        return (self.root / "_site" / rel).read_text()

    def test_engine_templates_answer_to_their_site_names_and_site_templates_win(self):
        self.write("engine/templates/plain.html",
                   '<!-- an editor\'s note -->engine plain, $partial("templates/partials/p.html")$')
        self.write("engine/templates/partials/p.html", "engine partial")
        self.write("templates/shadowed.html", 'site shadowed, $partial("templates/partials/p.html")$')
        self.run_probe("build")
        self.assertEqual(self.built("plain.html"), "engine plain, engine partial")
        self.assertEqual(self.built("shadowed.html"), "site shadowed, engine partial")
        # A site partial reaches the engine's templates that include it.
        self.write("templates/partials/p.html", "site partial")
        self.run_probe("build")
        self.assertEqual(self.built("plain.html"), "engine plain, site partial")
        self.assertEqual(self.built("shadowed.html"), "site shadowed, site partial")

    def test_template_edits_and_new_overrides_rebuild_without_a_clean(self):
        self.run_probe("build")
        stamp = (self.root / "engine/templates/plain.html").stat().st_mtime
        self.write("engine/templates/plain.html", "engine plain, edited", stamp + 2)
        self.run_probe("build")
        self.assertEqual(self.built("plain.html"), "engine plain, edited")
        # An override older than the engine's file still wins: it is a new
        # identifier, so it is out of date whatever its mtime.
        self.write("templates/plain.html", "site plain", stamp - 100)
        self.run_probe("build")
        self.assertEqual(self.built("plain.html"), "site plain")
        # Removing it brings back an alias whose stored body is the site's
        # and whose dependencies have not changed, so it needs the clean
        # build that tools/build-freshness.sh forces when the overrides
        # change (tests/test_build_freshness.py).
        (self.root / "templates/plain.html").unlink()
        self.run_probe("clean")
        self.run_probe("build")
        self.assertEqual(self.built("plain.html"), "engine plain, edited")

    def test_engine_static_files_are_served_as_the_site_s_and_site_files_win(self):
        self.write("engine/static/css/base.css", "a {\n  color: red;\n}\n")
        self.write("engine/static/js/engine.js", "engine();\n")
        self.write("engine/static/js/shared.js", "engine();\n")
        self.write("static/js/shared.js", "site();\n")
        self.write("engine/static/images/a.png.dims.yaml", "width: 1\n")
        self.write("static/css/site.css", "b { color: blue; }\n")
        self.run_probe("build")
        self.assertEqual(self.built("css/base.css"), "a{color:red}")
        self.assertEqual(self.built("css/site.css"), "b{color:blue}")
        self.assertEqual(self.built("js/engine.js"), "engine();\n")
        self.assertEqual(self.built("js/shared.js"), "site();\n")
        self.assertFalse((self.root / "_site/images/a.png.dims.yaml").exists())
        self.assertFalse((self.root / "_site/engine").exists())

    def test_raw_reads_take_the_site_file_then_the_engine_s(self):
        self.write("data/both.csl", "site")
        self.write("engine/data/both.csl", "engine")
        self.write("engine/data/engine.csl", "engine")
        self.assertEqual(self.run_probe("resolve", "data/both.csl", "data/engine.csl", "data/none.csl")
                         .splitlines(), ["data/both.csl", "engine/data/engine.csl", "data/none.csl"])
        self.assertEqual(self.run_probe("existing", "data/engine.csl", "data/none.csl").splitlines(),
                         ['Just "engine/data/engine.csl"', "Nothing"])

    def test_a_directory_lists_the_site_s_and_the_engine_s_entries_once(self):
        for rel in ("build/Site.hs", "engine/build/Site.hs", "engine/build/Main.hs",
                    "engine/static/css/base.css"):
            self.write(rel, "")
        self.assertEqual(self.run_probe("files", "build", "static/css", "static/js").splitlines(),
                         ["build/Site.hs", "engine/build/Main.hs", "engine/static/css/base.css"])


@requires_cabal
class ProviderWalkTests(unittest.TestCase):
    def test_the_engine_s_demonstration_site_and_build_directories_are_not_walked(self):
        refused = ["engine/fixture-site/content/a.md", "engine/dist-newstyle/cache/plan.json",
                   "engine/fixture-site/static/x.css"]
        walked = ["engine/templates/page.html", "engine/static/css/base.css",
                  "engine/tests/test_a.py", "content/essays/a.md"]
        done = subprocess.run([str(site_binary()), "private-paths"], cwd=ENGINE,
                              input="\n".join(refused + walked) + "\n",
                              capture_output=True, text=True, check=True)
        self.assertEqual(done.stdout.splitlines(), refused)


if __name__ == "__main__":
    unittest.main()
