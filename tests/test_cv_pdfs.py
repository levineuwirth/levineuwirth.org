"""tools/cv-pdfs.py: does /cv.pdf still match the CV data? (audit C02)"""

import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("cv_pdfs", ROOT / "tools" / "cv-pdfs.py")
cv_pdfs = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cv_pdfs)


class CvPdfTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="cv-pdfs-"))
        self.addCleanup(shutil.rmtree, self.tmp)
        self.src = self.tmp / "yaml-source"
        for rel in ("build.py", "layouts.yml", "data/publications.yml", "data/education.yml",
                    "templates/cv.tex.j2", "templates/shared/preamble.tex",
                    "variants/cv.yml", "variants/resume.yml", "variants/some-application.yml"):
            p = self.src / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(rel)
        self.record = self.src / "pdfs.sha256"
        cv_pdfs.write(self.src, self.record)

    def stale(self):
        return cv_pdfs.stale(self.src, self.record)

    def test_a_fresh_record_is_current(self):
        self.assertEqual(self.stale(), [])

    def test_changed_data_makes_both_pdfs_stale(self):
        (self.src / "data/publications.yml").write_text("a new publication")
        self.assertEqual(len(self.stale()), 2)

    def test_a_new_data_file_counts(self):
        (self.src / "data/grants.yml").write_text("a grant")
        self.assertEqual(len(self.stale()), 2)

    def test_a_variant_change_concerns_only_its_pdf(self):
        (self.src / "variants/cv.yml").write_text("changed")
        self.assertEqual([m.split(":")[0] for m in self.stale()], ["static/cv.pdf"])
        (self.src / "variants/cv.yml").write_text("variants/cv.yml")
        (self.src / "variants/some-application.yml").write_text("changed")
        self.assertEqual(self.stale(), [], "another audience's variant is not a website PDF's input")

    def test_no_record_says_so(self):
        self.record.unlink()
        self.assertTrue(all("no record" in m for m in self.stale()))


if __name__ == "__main__":
    unittest.main()
