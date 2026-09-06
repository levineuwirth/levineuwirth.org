import copy
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


YAML_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(YAML_ROOT))

import build  # noqa: E402


def minimal_data():
    data = {collection: [] for collection in build.LIST_COLLECTIONS}
    data.update(
        {
            "experience": [
                {
                    "id": "alpha-role",
                    "organization": "Canonical Org",
                    "start": "2025",
                    "end": "Present",
                    "bullets": ["Canonical bullet."],
                    "presentation_sets": {
                        "assurance": {"bullets": ["Assurance presentation."]},
                        "performance": {"bullets": ["Performance presentation."]},
                    },
                },
                {
                    "id": "beta-role",
                    "organization": "Second Org",
                    "start": "2024",
                    "end": "2025",
                },
            ],
            "projects": [
                {
                    "id": "tooling",
                    "name": "Canonical Tool",
                    "start": "2025",
                    "end": "Present",
                    "description": "Canonical description.",
                }
            ],
            "skills": {
                "languages": {
                    "label": "Programming",
                    "items": ["Python", "Rust", "C"],
                }
            },
            "personal": {
                "name": "Test Person",
                "links": [
                    {
                        "id": "github",
                        "label": "GitHub",
                        "href": "https://example.test",
                    }
                ],
            },
        }
    )
    return data


class ResolverFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.variants = self.root / "variants"
        self.templates = self.root / "templates"
        self.variants.mkdir()
        self.templates.mkdir()
        (self.templates / "application.tex.j2").write_text("test", encoding="utf-8")
        self.layouts = self.root / "layouts.yml"
        self.write_yaml(
            self.layouts,
            {"layouts": {"application": {"template": "application.tex.j2"}}},
        )

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def write_yaml(path, value):
        path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")

    def write_variant(self, name, value):
        self.write_yaml(self.variants / f"{name}.yml", value)

    def write_private_variant(self, name, value):
        private = self.variants / "private"
        private.mkdir(exist_ok=True)
        self.write_yaml(private / f"{name}.yml", value)

    def resolver(self, data=None):
        return build.VariantResolver(
            data or minimal_data(),
            variant_dir=self.variants,
            layout_file=self.layouts,
            template_dir=self.templates,
        )


class VariantResolutionTests(ResolverFixture):
    def test_private_variant_is_discovered_and_extends_tracked_base(self):
        self.write_variant(
            "base",
            {"version": 1, "abstract": True, "layout": "application"},
        )
        self.write_private_variant(
            "private-application",
            {
                "extends": "base",
                "abstract": False,
                "output": "Private-Application.pdf",
                "sections": [
                    {
                        "id": "work",
                        "label": "Work",
                        "entries": ["experience:alpha-role"],
                    }
                ],
            },
        )

        resolver = self.resolver()
        resolved = resolver.resolve("private-application")
        self.assertTrue(resolver.is_private("private-application"))
        self.assertFalse(resolver.is_private("base"))
        self.assertEqual(resolved.config["layout"], "application")
        self.assertEqual(resolved.output, "Private-Application.pdf")

    def test_inheritance_selection_ordering_and_presentation_overrides(self):
        self.write_variant(
            "base",
            {
                "version": 1,
                "abstract": True,
                "layout": "application",
                "summary": "Inherited summary.",
                "header": {"links": ["github"]},
            },
        )
        self.write_variant(
            "child",
            {
                "extends": "base",
                "abstract": False,
                "output": "child.pdf",
                "sections": [
                    {
                        "id": "first",
                        "label": "First",
                        "entries": ["experience:alpha-role", "projects:tooling"],
                    },
                    {
                        "id": "second",
                        "label": "Second",
                        "entries": ["experience:beta-role"],
                    },
                ],
                "overrides": {
                    "experience": {
                        "alpha-role": {
                            "bullets": ["Audience-specific bullet."],
                            "label": "Display label",
                        },
                        "beta-role": {"order": 1},
                    },
                    "projects": {
                        "tooling": {
                            "description": "Audience-specific description.",
                            "section": "second",
                            "order": 2,
                        }
                    },
                },
            },
        )

        resolved = self.resolver().resolve("child")
        self.assertEqual(resolved.config["summary"], "Inherited summary.")
        self.assertEqual(
            [link["id"] for link in resolved.data["variant"]["header_links"]],
            ["github"],
        )
        first, second = resolved.data["variant_sections"]
        self.assertEqual([entry["id"] for entry in first["entries"]], ["alpha-role"])
        self.assertEqual(
            first["entries"][0]["record"]["bullets"],
            ["Audience-specific bullet."],
        )
        self.assertEqual(
            first["entries"][0]["record"]["presentation_label"], "Display label"
        )
        self.assertEqual(
            [entry["id"] for entry in second["entries"]],
            ["beta-role", "tooling"],
        )
        self.assertEqual(
            second["entries"][1]["record"]["description"],
            "Audience-specific description.",
        )

    def test_unknown_referenced_record_id_fails(self):
        self.write_variant(
            "bad-id",
            {
                "version": 1,
                "layout": "application",
                "output": "bad.pdf",
                "sections": [
                    {
                        "id": "work",
                        "label": "Work",
                        "entries": ["experience:not-real"],
                    }
                ],
            },
        )
        with self.assertRaisesRegex(build.VariantError, "unknown record ID"):
            self.resolver().resolve("bad-id")

    def test_named_presentation_sets_compose_through_inheritance(self):
        sections = [
            {
                "id": "work",
                "label": "Work",
                "entries": ["experience:alpha-role"],
            }
        ]
        self.write_variant(
            "base",
            {
                "version": 1,
                "abstract": False,
                "layout": "application",
                "output": "base.pdf",
                "sections": sections,
                "presentation_sets": {
                    "experience": {"alpha-role": "assurance"}
                },
            },
        )
        self.write_variant(
            "child",
            {
                "extends": "base",
                "output": "child.pdf",
                "presentation_sets": {
                    "experience": {"alpha-role": "performance"}
                },
            },
        )

        resolver = self.resolver()
        parent_record = resolver.resolve("base").data["variant_sections"][0][
            "entries"
        ][0]["record"]
        child_record = resolver.resolve("child").data["variant_sections"][0][
            "entries"
        ][0]["record"]
        self.assertEqual(parent_record["bullets"], ["Assurance presentation."])
        self.assertEqual(child_record["bullets"], ["Performance presentation."])

    def test_unknown_named_presentation_set_fails(self):
        self.write_variant(
            "unknown-presentation",
            {
                "version": 1,
                "layout": "application",
                "output": "unknown.pdf",
                "sections": [
                    {
                        "id": "work",
                        "label": "Work",
                        "entries": ["experience:alpha-role"],
                    }
                ],
                "presentation_sets": {
                    "experience": {"alpha-role": "not-real"}
                },
            },
        )
        with self.assertRaisesRegex(build.VariantError, "unknown presentation set"):
            self.resolver().resolve("unknown-presentation")

    def test_named_presentation_set_rejects_factual_fields(self):
        data = minimal_data()
        data["experience"][0]["presentation_sets"]["illegal"] = {
            "organization": "Invented Org"
        }
        with self.assertRaisesRegex(
            build.VariantError, "illegal factual/unknown presentation field"
        ):
            self.resolver(data)

    def test_child_can_clear_inherited_presentation_set_for_removed_entry(self):
        self.write_variant(
            "base",
            {
                "version": 1,
                "abstract": False,
                "layout": "application",
                "output": "base.pdf",
                "sections": [
                    {
                        "id": "work",
                        "label": "Work",
                        "entries": ["experience:alpha-role"],
                    }
                ],
                "presentation_sets": {
                    "experience": {"alpha-role": "assurance"}
                },
            },
        )
        self.write_variant(
            "child",
            {
                "extends": "base",
                "output": "child.pdf",
                "sections": [
                    {
                        "id": "work",
                        "label": "Work",
                        "entries": ["experience:beta-role"],
                    }
                ],
                "presentation_sets": {"experience": {"alpha-role": None}},
            },
        )

        resolved = self.resolver().resolve("child")
        self.assertEqual(
            resolved.data["variant_sections"][0]["entries"][0]["id"],
            "beta-role",
        )

    def test_duplicate_canonical_ids_fail(self):
        self.write_variant(
            "valid",
            {
                "version": 1,
                "abstract": True,
                "layout": "application",
            },
        )
        data = minimal_data()
        data["experience"].append(copy.deepcopy(data["experience"][0]))
        with self.assertRaisesRegex(build.VariantError, "duplicate ID 'alpha-role'"):
            self.resolver(data)

    def test_illegal_factual_override_fails(self):
        self.write_variant(
            "illegal",
            {
                "version": 1,
                "layout": "application",
                "output": "illegal.pdf",
                "sections": [
                    {
                        "id": "work",
                        "label": "Work",
                        "entries": ["experience:alpha-role"],
                    }
                ],
                "overrides": {
                    "experience": {
                        "alpha-role": {"organization": "Invented Org"}
                    }
                },
            },
        )
        with self.assertRaisesRegex(build.VariantError, "illegal factual/unknown"):
            self.resolver().resolve("illegal")

    def test_override_for_unselected_record_fails(self):
        self.write_variant(
            "dead-override",
            {
                "version": 1,
                "layout": "application",
                "output": "dead-override.pdf",
                "sections": [
                    {
                        "id": "work",
                        "label": "Work",
                        "entries": ["experience:alpha-role"],
                    }
                ],
                "overrides": {
                    "experience": {
                        "beta-role": {"bullets": ["Never rendered."]}
                    }
                },
            },
        )
        with self.assertRaisesRegex(
            build.VariantError,
            "override targets unselected record 'experience:beta-role'",
        ):
            self.resolver().resolve("dead-override")

    def test_duplicate_concrete_output_filenames_fail_whole_validation(self):
        for name in ("first", "second"):
            self.write_variant(
                name,
                {
                    "version": 1,
                    "layout": "application",
                    "output": "collision.pdf",
                    "sections": [
                        {
                            "id": "work",
                            "label": "Work",
                            "entries": ["experience:alpha-role"],
                        }
                    ],
                },
            )
        with self.assertRaisesRegex(
            build.VariantError,
            "duplicate output PDF filename 'collision.pdf'",
        ):
            self.resolver().resolve_all()

    def test_skill_override_must_be_canonical_subset(self):
        self.write_variant(
            "skills",
            {
                "version": 1,
                "layout": "application",
                "output": "skills.pdf",
                "sections": [
                    {
                        "id": "skills",
                        "label": "Skills",
                        "entries": ["skills:languages"],
                    }
                ],
                "overrides": {
                    "skills": {"languages": {"items": ["Python", "COBOL"]}}
                },
            },
        )
        with self.assertRaisesRegex(build.VariantError, "subset of canonical"):
            self.resolver().resolve("skills")

    def test_inheritance_cycle_fails_with_path(self):
        self.write_variant("cycle-a", {"extends": "cycle-b"})
        self.write_variant("cycle-b", {"extends": "cycle-a"})
        with self.assertRaisesRegex(
            build.VariantError, "cycle-a -> cycle-b -> cycle-a"
        ):
            self.resolver().resolve("cycle-a")

    def test_unknown_variant_fails_with_available_names(self):
        self.write_variant(
            "known",
            {"version": 1, "abstract": True, "layout": "application"},
        )
        with self.assertRaisesRegex(build.VariantError, "unknown variant 'missing'"):
            self.resolver().resolve("missing")

    def test_missing_layout_template_fails(self):
        self.write_variant(
            "known",
            {"version": 1, "abstract": True, "layout": "application"},
        )
        self.write_yaml(
            self.layouts,
            {"layouts": {"application": {"template": "missing.tex.j2"}}},
        )
        with self.assertRaisesRegex(build.VariantError, "missing template"):
            self.resolver()


class RepositoryCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.resolver = build.VariantResolver(build.load_all_data())

    def test_backwards_compatible_targets(self):
        expected = {
            "cv": ("cv.tex.j2", "cv.pdf"),
            "resume": ("resume.tex.j2", "resume.pdf"),
            "resume_ats": ("resume_ats.tex.j2", "resume_ats.pdf"),
        }
        for target, (template, output) in expected.items():
            with self.subTest(target=target):
                resolved = self.resolver.resolve(target)
                self.assertEqual(resolved.template, template)
                self.assertEqual(resolved.output, output)

    def test_website_cv_is_academic_and_omits_dtu(self):
        resolved = self.resolver.resolve("cv")
        visible_education = {
            entry["id"]
            for entry in resolved.data["education"]
            if entry.get("cv_visible")
        }
        self.assertEqual(resolved.config["legacy_visibility"], "cv")
        self.assertIn("brown-scb-math-cs", visible_education)
        self.assertNotIn("dtu-msc-cse", visible_education)

    def test_gpu_inference_systems_is_a_brown_only_one_page_child(self):
        self.assertEqual(
            self.resolver.raw_variants["gpu-inference-systems"]["extends"],
            "inference-systems-performance",
        )
        resolved = self.resolver.resolve("gpu-inference-systems")
        self.assertEqual(resolved.template, "resume_ats.tex.j2")
        self.assertEqual(
            [section["id"] for section in resolved.data["variant_sections"]],
            [
                "experience",
                "selected-systems-projects",
                "education",
                "technical-skills",
            ],
        )
        education_ids = {
            entry["id"]
            for section in resolved.data["variant_sections"]
            for entry in section["entries"]
            if entry["collection"] == "education"
        }
        self.assertEqual(education_ids, {"brown-scb-math-cs"})
        mars = resolved.data["variant_sections"][0]["entries"][0]["record"]
        self.assertIn("NVIDIA B200", " ".join(mars["bullets"]))

    def test_agent_platform_systems_is_a_brown_only_swe_child(self):
        self.assertEqual(
            self.resolver.raw_variants["agent-platform-systems"]["extends"],
            "software-engineering-systems",
        )
        resolved = self.resolver.resolve("agent-platform-systems")
        self.assertEqual(resolved.template, "resume_ats.tex.j2")
        self.assertEqual(
            [link["id"] for link in resolved.data["variant"]["header_links"]],
            ["github"],
        )
        self.assertEqual(
            [section["id"] for section in resolved.data["variant_sections"]],
            ["experience", "selected-projects", "education", "technical-skills"],
        )
        self.assertEqual(
            self.resolver.raw_variants["technical-generalist-ai-safety"][
                "presentation_sets"
            ]["experience"],
            {
                "mars-v": "agent-platform-systems",
                "frontier-ai-contracting": "frontier-evals-control",
                "shu-lab-undergrad": "agent-platform-systems",
            },
        )

        selected = {
            (entry["collection"], entry["id"])
            for section in resolved.data["variant_sections"]
            for entry in section["entries"]
        }
        self.assertIn(("education", "brown-scb-math-cs"), selected)
        self.assertNotIn(("education", "dtu-msc-cse"), selected)
        self.assertNotIn(("experience", "xai-grok-code-fast"), selected)
        self.assertNotIn(("experience", "neuroai"), selected)
        self.assertEqual(
            [
                entry["id"]
                for entry in resolved.data["variant_sections"][1]["entries"]
            ],
            ["levcs", "levshell", "proof-broker"],
        )

        experience_text = " ".join(
            bullet
            for entry in resolved.data["variant_sections"][0]["entries"]
            for bullet in entry["record"].get("bullets", [])
        )
        project_text = " ".join(
            entry["record"].get("description", "")
            for entry in resolved.data["variant_sections"][1]["entries"]
        )
        self.assertIn("NVIDIA B200", experience_text)
        self.assertIn("debug agent scaffolds", experience_text)
        self.assertIn("crashes and restarts", experience_text)
        self.assertIn("append-only journal", project_text)
        self.assertIn("rollback capsules", project_text)
        self.assertIn("tool-execution boundary", project_text)

    def test_technical_generalist_is_a_reusable_brown_only_one_page_child(self):
        self.assertEqual(
            self.resolver.raw_variants["technical-generalist-ai-safety"]["extends"],
            "software-engineering-systems",
        )
        resolved = self.resolver.resolve("technical-generalist-ai-safety")
        self.assertEqual(resolved.template, "resume_ats.tex.j2")
        self.assertEqual(
            [link["id"] for link in resolved.data["variant"]["header_links"]],
            ["github", "linkedin"],
        )
        self.assertEqual(
            resolved.data["variant"]["header_links"][1]["href"],
            "https://www.linkedin.com/in/levi-neuwirth",
        )
        self.assertEqual(
            [section["id"] for section in resolved.data["variant_sections"]],
            ["experience", "selected-projects", "education", "technical-skills"],
        )

        selected = {
            (entry["collection"], entry["id"])
            for section in resolved.data["variant_sections"]
            for entry in section["entries"]
        }
        self.assertIn(("education", "brown-scb-math-cs"), selected)
        self.assertNotIn(("education", "dtu-msc-cse"), selected)
        self.assertNotIn(("experience", "xai-grok-code-fast"), selected)
        self.assertEqual(
            [
                entry["id"]
                for entry in resolved.data["variant_sections"][1]["entries"]
            ],
            ["pmacs", "levcs", "proof-broker"],
        )

        experience_text = " ".join(
            bullet
            for entry in resolved.data["variant_sections"][0]["entries"]
            for bullet in entry["record"].get("bullets", [])
        )
        project_text = " ".join(
            entry["record"].get("description", "")
            for entry in resolved.data["variant_sections"][1]["entries"]
        )
        self.assertIn("NVIDIA B200", experience_text)
        self.assertIn("apparent failures arise", experience_text)
        self.assertIn("v1.1.0", project_text)
        self.assertIn("194 tests", project_text)
        self.assertIn("small trusted kernel", project_text)
        self.assertIn("open-ended technical questions", resolved.config["summary"])

        skills = {
            entry["id"]: entry["record"]
            for entry in resolved.data["variant_sections"][3]["entries"]
        }
        self.assertEqual(
            skills["programming"]["items"], ["Python", "Rust", "C", "C++", "Go"]
        )
        self.assertEqual(skills["ml-ai"]["items"], ["PyTorch", "TensorFlow", "NumPy"])
        self.assertEqual(
            skills["verification"]["items"], ["Lean 4", "Rocq", "Vampire"]
        )


if __name__ == "__main__":
    unittest.main()
