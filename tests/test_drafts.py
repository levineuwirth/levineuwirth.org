"""`draft: true` withholds a page in production builds (build/Drafts.hs,
audit C06). ``site list-unpublished`` prints exactly what the provider will
ignore; it runs here over a temporary content tree."""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location("golden", Path(__file__).with_name("test_golden.py"))
_golden = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_golden)
site_binary = _golden.site_binary

DRAFT = "---\ntitle: T\ndraft: true\n---\nBody.\n"
LIVE = "---\ntitle: T\n---\nBody.\n"


@unittest.skipUnless(shutil.which("cabal"), "cabal not on PATH")
class UnpublishedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.binary = site_binary()

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="drafts-"))
        self.addCleanup(shutil.rmtree, self.root)

    def write(self, rel: str, text: str = "x") -> None:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def unpublished(self) -> list[str]:
        done = subprocess.run([str(self.binary), "list-unpublished"], cwd=self.root,
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout.splitlines()

    def test_a_flagged_page_of_any_kind_is_withheld(self):
        for rel in ("content/essays/flat.md", "content/poetry/poem.md", "content/fiction/story.md",
                    "content/blog/post.md", "content/about-me.md", "content/notes/page.md"):
            self.write(rel, DRAFT)
        self.write("content/essays/live.md", LIVE)
        self.assertEqual(self.unpublished(), sorted([
            "file content/about-me.md", "file content/blog/post.md", "file content/essays/flat.md",
            "file content/fiction/story.md", "file content/notes/page.md", "file content/poetry/poem.md"]))

    def test_a_directory_entry_withholds_its_directory(self):
        self.write("content/essays/dir-essay/index.md", DRAFT)
        self.write("content/music/symphony/index.md", DRAFT)
        self.write("content/photography/series/index.md", DRAFT)
        self.assertEqual(self.unpublished(), [
            "dir content/essays/dir-essay", "dir content/music/symphony", "dir content/photography/series",
            "file content/essays/dir-essay/index.md", "file content/music/symphony/index.md",
            "file content/photography/series/index.md"])

    def test_a_collection_landing_withholds_only_itself(self):
        self.write("content/poetry/selected/index.md", DRAFT)
        self.write("content/poetry/selected/poem.md", LIVE)
        self.assertEqual(self.unpublished(), ["file content/poetry/selected/index.md"])

    def test_a_flat_photograph_withholds_its_images(self):
        self.write("content/photography/harbor.md",
                   "---\ntitle: Harbor\nphoto: IMG_0042.jpg\ndraft: true\n---\n")
        self.assertEqual(self.unpublished(), [
            "file content/photography/harbor.md",
            "stem content/photography/IMG_0042.", "stem content/photography/harbor."])

    def test_truthy_spellings_and_non_flags(self):
        self.write("content/a.md", "---\ndraft: yes\n---\n")
        self.write("content/b.md", "---\ndraft: \"true\"\n---\n")
        self.write("content/c.md", "---\ndraft: false\n---\n")
        self.write("content/d.md", "---\ntitle: D\n---\ndraft: true\n")          # body, not front matter
        self.write("content/e.md", "---\nstatus: Draft\n---\n")                  # the epistemic status
        self.write("content/f.md", "---\ndraft: true\n")                         # unterminated: not front matter
        self.write("content/drafts/essays/g.md", DRAFT)                        # drafts/ is never published anyway
        self.assertEqual(self.unpublished(), ["file content/a.md", "file content/b.md"])


if __name__ == "__main__":
    unittest.main()
