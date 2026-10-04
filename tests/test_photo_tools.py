"""tools/scaffold-photos.py and tools/extract-palette.py (audit T14)."""

import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


try:
    import yaml
    scaffold = load("scaffold_photos", "scaffold-photos.py")
except ImportError:
    scaffold = None

try:
    from PIL import Image
    palette = load("extract_palette", "extract-palette.py")
except ImportError:              # Pillow or colorthief missing: no .venv
    palette = None


@unittest.skipIf(scaffold is None, "PyYAML not installed")
class ScaffoldTests(unittest.TestCase):
    def test_rendered_values_parse_back_unchanged(self):
        for value in ('Nikon "Z" 6', "back\\slash", "a: b", "København", "#hash", "2024-07-11"):
            with self.subTest(value=value):
                self.assertEqual(yaml.safe_load(scaffold.render("title", value)), {"title": value})

    def test_numbers_booleans_and_dates_stay_unquoted(self):
        self.assertEqual(scaffold.render("iso", 400), "iso: 400")
        self.assertEqual(scaffold.render("draft", False), "draft: false")
        self.assertEqual(scaffold.render("captured", "2024-07-11"), "captured: 2024-07-11")

    def test_tags_are_filed_under_photography(self):
        self.assertEqual(scaffold.build_tags("travel, denmark/copenhagen, ,travel"),
                         ["photography", "photography/travel", "denmark/copenhagen"])
        self.assertEqual(scaffold.build_tags(""), ["photography"])

    def test_tags_line_parses_back_whatever_the_tags_hold(self):
        tags = scaffold.build_tags("travel: denmark, «Nyhavn», [x]")
        self.assertEqual(yaml.safe_load(scaffold.tags_line(tags)), {"tags": tags})

    def test_title_from_slug(self):
        self.assertEqual(scaffold.title_from_slug("from-the-belt-bridge"), "From The Belt Bridge")

    def test_exif_lines_prefer_the_composed_exposure(self):
        tmp = Path(tempfile.mkdtemp(prefix="scaffold-"))
        self.addCleanup(shutil.rmtree, tmp)
        side = tmp / "a.jpg.exif.yaml"
        side.write_text(yaml.safe_dump({"captured": "2024-07-11", "camera": "X100V", "lens": "",
                                        "shutter": "1/125", "aperture": "f/8", "iso": 400,
                                        "exposure": "1/125 f/8 ISO 400"}))
        self.assertEqual(scaffold.exif_lines(side),
                         ["captured: 2024-07-11", 'camera: "X100V"', 'exposure: "1/125 f/8 ISO 400"'])
        side.write_text(yaml.safe_dump({"shutter": "1/60", "iso": 800}))
        self.assertEqual(scaffold.exif_lines(side), ['shutter: "1/60"', "iso: 800"])
        self.assertEqual(scaffold.exif_lines(tmp / "missing.yaml"), [])


@unittest.skipIf(palette is None, "Pillow or colorthief not installed")
class PaletteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="palette-"))
        self.addCleanup(shutil.rmtree, self.tmp)

    def test_the_frame_s_colors_are_found(self):
        img = Image.new("RGB", (400, 300), (200, 30, 30))
        img.paste((20, 60, 200), (0, 0, 100, 300))          # a quarter blue, the rest red
        path = self.tmp / "frame.jpg"
        img.save(path, quality=95)
        swatches = palette._extract_palette(path)
        self.assertTrue(1 <= len(swatches) <= palette.N_SWATCHES)
        rgb = [tuple(int(s[i:i + 2], 16) for i in (1, 3, 5)) for s in swatches]
        self.assertTrue(any(r > 150 and max(g, b) < 80 for r, g, b in rgb), swatches)
        self.assertTrue(any(b > 150 and r < 80 for r, g, b in rgb), swatches)

    def test_hex_and_staleness(self):
        self.assertEqual(palette._hex((255, 0, 16)), "#ff0010")
        img = self.tmp / "a.jpg"
        Image.new("RGB", (8, 8)).save(img)
        side = palette._sidecar_path(img)
        self.assertEqual(side.name, "a.jpg.palette.yaml")
        self.assertTrue(palette._is_stale(img, side))
        palette._atomic_write_yaml(side, {"palette": ["#000000"]})
        self.assertFalse(palette._is_stale(img, side))


if __name__ == "__main__":
    unittest.main()
