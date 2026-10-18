"""tools/sitelib.py: the atomic writer every tool's output goes through.

It replaced eleven copies with five different sets of guarantees (fsync or
not, a PID-unique or a fixed temporary, cleanup on failure or not); the
merged one keeps the strongest of each, and these check them."""

import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests._helpers import engine_path

# The directory sitelib.py is in, not tools/ wherever one exists: A6 can
# leave engine/tools/ holding only what moved first.
sys.path.insert(0, str(engine_path("tools/sitelib.py").parent))
import sitelib  # noqa: E402


class AtomicPath(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def test_temporary_is_hidden_unique_and_gitignorable(self):
        target = self.dir / "sub" / "photo.jpg.exif.yaml"
        with sitelib.atomic_path(target) as tmp:
            # A dotfile (Hakyll skips it), in the target's directory (one
            # rename), unique to the process, ending in .tmp.
            self.assertEqual(tmp.parent, target.parent)
            self.assertTrue(tmp.name.startswith("."))
            self.assertIn(str(os.getpid()), tmp.name)
            self.assertTrue(tmp.name.endswith(".tmp"))
            tmp.write_text("new")
            self.assertFalse(target.exists())
        self.assertEqual(target.read_text(), "new")
        self.assertEqual(os.listdir(target.parent), [target.name])

    def test_failure_leaves_the_old_file_and_no_debris(self):
        target = self.dir / "index.json"
        target.write_text("old")
        with self.assertRaises(RuntimeError):
            with sitelib.atomic_path(target) as tmp:
                tmp.write_text("half")
                raise RuntimeError("interrupted")
        self.assertEqual(target.read_text(), "old")
        self.assertEqual(os.listdir(self.dir), ["index.json"])

    def test_durable_fsyncs_file_and_directory(self):
        target = self.dir / "a.json"
        with mock.patch.object(sitelib.os, "fsync", wraps=os.fsync) as fsync:
            sitelib.atomic_write_text(target, "x")
        self.assertEqual(fsync.call_count, 2)
        with mock.patch.object(sitelib.os, "fsync", wraps=os.fsync) as fsync:
            sitelib.atomic_write_text(target, "y", durable=False)
        self.assertEqual(fsync.call_count, 0)
        self.assertEqual(target.read_text(), "y")

    def test_mode(self):
        target = self.dir / "v.w480.jpg"
        with sitelib.atomic_path(target, durable=False, mode=0o644) as tmp:
            tmp.write_bytes(b"jpeg")
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o644)

    def test_skip_if_unchanged_keeps_the_mtime(self):
        target = self.dir / "similar-links.json"
        target.write_text("{}")
        os.utime(target, (1, 1))
        self.assertFalse(sitelib.atomic_write_text(target, "{}", skip_if_unchanged=True))
        self.assertEqual(target.stat().st_mtime, 1)
        self.assertTrue(sitelib.atomic_write_text(target, "{}"))
        self.assertNotEqual(target.stat().st_mtime, 1)

    def test_engine_path_finds_a_file_wherever_a6_has_put_it(self):
        repo, site = self.dir / "repo", self.dir / "site"
        for rel in ("repo/engine/tools/pins.sha256", "repo/tools/sitelib.py", "site/build/Site.hs"):
            (self.dir / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.dir / rel).write_text("")
        with mock.patch.object(sitelib, "ENGINE", repo), mock.patch.object(sitelib, "SITE_ROOT", site):
            # Moved, beside the code, beside the site, in that order.
            self.assertEqual(sitelib.engine_path("tools/pins.sha256"), repo / "engine/tools/pins.sha256")
            self.assertEqual(sitelib.engine_path("tools/sitelib.py"), repo / "tools/sitelib.py")
            self.assertEqual(sitelib.engine_path("build/Site.hs"), site / "build/Site.hs")
            # A directory is wherever anything of it has moved, so a file in
            # it is found by its own path, not by the directory's.
            self.assertEqual(sitelib.engine_path("tools"), repo / "engine/tools")

    def test_slugify(self):
        self.assertEqual(sitelib.slugify("Rilke's  Duino_Elegies — I"), "rilkes-duino-elegies-i")


if __name__ == "__main__":
    unittest.main()
