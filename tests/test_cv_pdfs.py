"""tools/cv-pdfs.py: does /cv.pdf still match the CV data? (audit C02)"""

import shutil
import tempfile
import unittest
from pathlib import Path
from tests._helpers import load_tool

ROOT = Path(__file__).resolve().parents[1]
cv_pdfs = load_tool("cv-pdfs.py")


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

    def inherited_variants(self):
        (self.src / "variants/cv.yml").write_text("extends: application-cv\n")
        (self.src / "variants/resume.yml").write_text("extends: ats-application\n")
        (self.src / "variants/ats-application.yml").write_text("extends: application-cv\n")
        (self.src / "variants/application-cv.yml").write_text("abstract: true\n")
        cv_pdfs.write(self.src, self.record)

    def test_shared_ancestor_change_makes_both_pdfs_stale(self):
        self.inherited_variants()
        self.assertEqual(self.stale(), [])
        (self.src / "variants/application-cv.yml").write_text("abstract: true\nsummary: updated\n")
        self.assertEqual(len(self.stale()), 2)

    def test_resume_parent_change_affects_only_resume(self):
        self.inherited_variants()
        (self.src / "variants/ats-application.yml").write_text("extends: application-cv\nsummary: updated\n")
        self.assertEqual([m.split(":")[0] for m in self.stale()], ["static/resume.pdf"])

    def test_cyclic_inheritance_fails_instead_of_hanging(self):
        self.inherited_variants()
        (self.src / "variants/application-cv.yml").write_text("extends: cv\n")
        with self.assertRaisesRegex(ValueError, "cyclic PDF variant inheritance"):
            self.stale()


if __name__ == "__main__":
    unittest.main()
