"""The site's Makefile links the engine checked out beside it.

The engine is its own repository, checked out beside the site as
../ozymandias; the Makefile makes `engine` a link to it on first use, and
says what to do when there is none (A10a). Each case is a scratch site with
a copy of the Makefile, and the real engine linked in as its sibling."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests._helpers import ENGINE, SITE_ROOT, script_env


class EngineLink(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="engine-link-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.site = self.root / "site"
        self.site.mkdir()
        shutil.copy2(SITE_ROOT / "Makefile", self.site / "Makefile")

    def make(self) -> subprocess.CompletedProcess:
        # deploy-guard only prints with -n (no sub-make): the Makefile is
        # parsed, and nothing runs.
        return subprocess.run(["make", "-n", "--no-print-directory", "-C", str(self.site), "deploy-guard"],
                              env=script_env(), capture_output=True, text=True, timeout=60)

    def beside(self) -> None:
        (self.root / "ozymandias").symlink_to(ENGINE)

    def test_the_engine_beside_the_site_is_linked(self):
        self.beside()
        done = self.make()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue((self.site / "engine").is_symlink())
        self.assertEqual(os.readlink(self.site / "engine"), "../ozymandias")
        # And left as it is the next time.
        self.assertEqual(self.make().returncode, 0)
        self.assertEqual(os.readlink(self.site / "engine"), "../ozymandias")

    def test_without_one_it_says_where_to_get_it(self):
        done = self.make()
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("clone Ozymandias beside this site, as ../ozymandias", done.stderr)
        self.assertFalse(os.path.lexists(self.site / "engine"))

    def test_a_link_left_dangling_is_made_again(self):
        self.beside()
        (self.site / "engine").symlink_to("../gone")
        self.assertEqual(self.make().returncode, 0)
        self.assertEqual(os.readlink(self.site / "engine"), "../ozymandias")

    def test_an_engine_directory_that_is_no_engine_is_refused(self):
        self.beside()
        (self.site / "engine").mkdir()
        done = self.make()
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("engine holds no engine.mk", done.stderr)
        self.assertFalse((self.site / "engine").is_symlink())

    def test_a_link_to_something_else_is_left_alone(self):
        self.beside()
        (self.root / "elsewhere").mkdir()
        (self.site / "engine").symlink_to("../elsewhere")
        done = self.make()
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("engine holds no engine.mk", done.stderr)
        self.assertEqual(os.readlink(self.site / "engine"), "../elsewhere")


if __name__ == "__main__":
    unittest.main()
