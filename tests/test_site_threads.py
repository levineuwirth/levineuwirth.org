"""How many items the generator compiles at once (build/Main.hs).

Hakyll runs one worker per capability, and the generator used to get one;
it now gets SITE_THREADS, a whole number from 1 to 256 (the RTS's limit),
or 4. Configurable per run: `SITE_THREADS=8 make build` or `make build
SITE_THREADS=8`, and a setting in the environment reaches the tests'
generator runs too.
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
        # before the missing templates stop the build. Only these tests drop
        # an inherited SITE_THREADS, to see the default.
        environment = script_env(**env)
        if "SITE_THREADS" not in env:
            environment.pop("SITE_THREADS", None)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            essay = root / "content" / "essays" / "a.md"
            essay.parent.mkdir(parents=True)
            essay.write_text("---\ntitle: A\ndate: 2026-01-01\n---\n\nBody.\n")
            return subprocess.run([str(site_binary()), "build"], cwd=root,
                                  env=environment, capture_output=True, text=True,
                                  timeout=120)

    def test_four_by_default(self):
        self.assertIn("async runtime with 4 threads", self.threads().stdout)

    def test_site_threads_sets_the_count_from_1_to_256(self):
        for value in ("1", "2", "256"):
            with self.subTest(value=value):
                done = self.threads(SITE_THREADS=value)
                self.assertIn(f"async runtime with {value} threads", done.stdout)
                self.assertNotIn("SITE_THREADS", done.stderr)

    def test_anything_else_warns_and_uses_four(self):
        # Out-of-range values are judged before they become an Int: read
        # straight into one, -18446744073709551614 wrapped round to 2 and
        # 4294967296 reached the RTS, which warned and used 1.
        for value in ("0", "257", "-3", "eight", "2.5", "-18446744073709551614",
                      "4294967296", "18446744073709551617"):
            with self.subTest(value=value):
                done = self.threads(SITE_THREADS=value)
                self.assertIn(f'SITE_THREADS="{value}" is not a whole number from 1 to 256; '
                              "using 4", done.stderr)
                self.assertIn("async runtime with 4 threads", done.stdout)

    def test_make_passes_it_to_the_generator(self):
        done = subprocess.run(["make", "-s", "--eval", "probe-threads: ; @echo $$SITE_THREADS",
                               "probe-threads", "SITE_THREADS=8"], cwd=ROOT, env=script_env(),
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(done.stdout.strip(), "8", done.stderr)


if __name__ == "__main__":
    unittest.main()
