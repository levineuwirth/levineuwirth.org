"""How many items the generator compiles at once (build/Main.hs).

Hakyll runs one worker per capability, and the generator used to get one;
it now gets SITE_THREADS, a positive integer, or 4. Configurable per run:
`SITE_THREADS=8 make build` or `make build SITE_THREADS=8`.
"""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from tests._helpers import ROOT, requires_cabal, script_env, site_binary


@requires_cabal
class SiteThreadsTests(unittest.TestCase):
    def threads(self, **env) -> subprocess.CompletedProcess[str]:
        # A scratch tree is enough: the count is logged as compiling starts,
        # before the missing templates stop the build.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            essay = root / "content" / "essays" / "a.md"
            essay.parent.mkdir(parents=True)
            essay.write_text("---\ntitle: A\ndate: 2026-01-01\n---\n\nBody.\n")
            return subprocess.run([str(site_binary()), "build"], cwd=root,
                                  env=script_env(**env), capture_output=True, text=True,
                                  timeout=120)

    def test_four_by_default(self):
        self.assertIn("async runtime with 4 threads", self.threads().stdout)

    def test_site_threads_sets_the_count(self):
        self.assertIn("async runtime with 2 threads", self.threads(SITE_THREADS="2").stdout)

    def test_anything_else_warns_and_uses_four(self):
        for value in ("0", "eight", "-3"):
            with self.subTest(value=value):
                done = self.threads(SITE_THREADS=value)
                self.assertIn(f'SITE_THREADS="{value}" is not a positive integer; using 4',
                              done.stderr)
                self.assertIn("async runtime with 4 threads", done.stdout)

    def test_make_passes_it_to_the_generator(self):
        done = subprocess.run(["make", "-s", "--eval", "probe-threads: ; @echo $$SITE_THREADS",
                               "probe-threads", "SITE_THREADS=8"], cwd=ROOT, env=script_env(),
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(done.stdout.strip(), "8", done.stderr)


if __name__ == "__main__":
    unittest.main()
