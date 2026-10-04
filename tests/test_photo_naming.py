"""tools/photo_naming.py, the responsive-variant names the photo tools share,
against the widths the generator offers in srcset (build/Contexts.hs,
through `site shared-rules`). A rung one side lacks is a srcset candidate
that 404s, or a variant written for nothing; and before 2026-10-04 four
tools each carried their own copy of the pattern."""

import importlib.util
import json
import shutil
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


photo_naming = load("photo_naming", REPO_ROOT / "tools" / "photo_naming.py")
_golden = load("golden", Path(__file__).with_name("test_golden.py"))


class PhotoNamingTests(unittest.TestCase):
    def test_pattern_matches_exactly_the_ladder(self) -> None:
        for width in photo_naming.WIDTHS:
            for ext in (".jpg", ".JPEG", ".png"):
                name = Path(f"a/photo.w{width}{ext}")
                with self.subTest(name=name):
                    self.assertTrue(photo_naming.is_variant(name))
                    self.assertEqual(photo_naming.variant_width(name), width)
                    self.assertEqual(photo_naming.source_for_variant(name), Path(f"a/photo{ext}"))
                    self.assertEqual(photo_naming.variant_path(Path(f"a/photo{ext}"), width), name)
        for name in ("photo.jpg", "photo.w960.webp", "photo.w720.jpg", "photo.w960.jpg.bak"):
            with self.subTest(name=name):
                self.assertFalse(photo_naming.is_variant(Path(name)))

    @unittest.skipUnless(shutil.which("cabal"), "cabal not on PATH")
    def test_widths_are_the_generators(self) -> None:
        out = subprocess.run([str(_golden.site_binary()), "shared-rules"],
                             capture_output=True, text=True, check=True)
        self.assertEqual(list(photo_naming.WIDTHS),
                         json.loads(out.stdout)["photo-variant-widths"])


if __name__ == "__main__":
    unittest.main()
