#!/usr/bin/env python3
"""Render canonical CV data through named layouts and audience variants.

The YAML under ``data/`` owns facts. Files under ``variants/`` own selection,
ordering, and presentation. Local application metadata may live under the
Git-ignored ``variants/private/`` directory. Files do not gain a new
visibility/order field for each application.

Legacy commands remain valid::

    python build.py cv
    python build.py resume
    python build.py resume_ats

Generic commands::

    python build.py example-research-engineering
    python build.py --variant example-research-engineering
    python build.py --list
"""

import argparse
import copy
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, TemplateError


ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
TEMPLATE_DIR = ROOT / "templates"
VARIANT_DIR = ROOT / "variants"
LAYOUT_FILE = ROOT / "layouts.yml"
OUTPUT_DIR = ROOT / "output"
BUILD_DIR = ROOT / "build"

SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LIST_COLLECTIONS = (
    "education",
    "experience",
    "publications",
    "presentations",
    "grants",
    "affiliations",
    "projects",
    "languages",
)
SECTION_COLLECTIONS = set(LIST_COLLECTIONS) | {"skills"}
VARIANT_KEYS = {
    "version",
    "description",
    "abstract",
    "extends",
    "layout",
    "output",
    "document_title",
    "summary",
    "availability",
    "header",
    "sections",
    "presentation_sets",
    "overrides",
    "legacy_visibility",
}
SECTION_KEYS = {"id", "label", "entries", "page_break_before"}
REQUIRED_SECTION_KEYS = {"id", "label", "entries"}
HEADER_KEYS = {"links"}
LAYOUT_KEYS = {"template", "description"}
COMMON_PRESENTATION_FIELDS = {
    "label",
    "summary",
    "short_summary",
    "notes",
    "section",
    "order",
}
PRESENTATION_FIELDS = {
    "education": COMMON_PRESENTATION_FIELDS | {"description"},
    "experience": COMMON_PRESENTATION_FIELDS
    | {"bullets", "description", "preamble", "scope"},
    "publications": COMMON_PRESENTATION_FIELDS | {"description"},
    "presentations": COMMON_PRESENTATION_FIELDS | {"description"},
    "grants": COMMON_PRESENTATION_FIELDS | {"description", "note"},
    "affiliations": COMMON_PRESENTATION_FIELDS | {"description"},
    "projects": COMMON_PRESENTATION_FIELDS | {"description", "bullets"},
    "languages": COMMON_PRESENTATION_FIELDS,
    # A variant may select/reorder a canonical skill subset, but cannot add a
    # skill that is absent from canonical data.
    "skills": COMMON_PRESENTATION_FIELDS | {"items"},
}
LEGACY_ALIASES = {"resume_ats": "resume-ats"}


class VariantError(ValueError):
    """A configuration error with enough context to fix the YAML."""


@dataclass
class ResolvedVariant:
    name: str
    config: dict
    layout: dict
    template: str
    output: str
    data: dict


def _load_yaml(path):
    try:
        with path.open(encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle)
    except yaml.YAMLError as exc:
        raise VariantError(f"{path}: malformed YAML: {exc}") from exc
    except OSError as exc:
        raise VariantError(f"cannot read {path}: {exc}") from exc
    return loaded


def load_all_data(data_dir=DATA_DIR):
    """Load every canonical data file and merge its top-level keys."""
    data = {}
    for yml_file in sorted(Path(data_dir).glob("*.yml")):
        loaded = _load_yaml(yml_file)
        if loaded is None:
            continue
        if not isinstance(loaded, dict):
            raise VariantError(f"{yml_file}: expected a YAML mapping")
        stem = yml_file.stem
        if stem == "personal":
            if "personal" in data:
                raise VariantError(f"{yml_file}: duplicate top-level key 'personal'")
            data["personal"] = loaded
            continue
        overlap = sorted(set(data) & set(loaded))
        if overlap:
            raise VariantError(
                f"{yml_file}: duplicate top-level data key(s): {', '.join(overlap)}"
            )
        data.update(loaded)
    data["build_date"] = date.today().strftime("%B %Y")
    return data


def make_env(template_dir=TEMPLATE_DIR):
    """Return a Jinja environment with delimiters that are safe in LaTeX."""
    return Environment(
        loader=FileSystemLoader(str(template_dir)),
        block_start_string="((*",
        block_end_string="*))",
        variable_start_string="(((",
        variable_end_string=")))",
        comment_start_string="((#",
        comment_end_string="#))",
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=False,
    )


def render(template_name, data, template_dir=TEMPLATE_DIR):
    try:
        return make_env(template_dir).get_template(template_name).render(**data)
    except TemplateError as exc:
        raise VariantError(f"cannot render {template_name}: {exc}") from exc


def _slug(value, context):
    if not isinstance(value, str) or not SLUG.fullmatch(value):
        raise VariantError(
            f"{context}: expected a stable slug-like ID "
            "(lowercase letters/numbers separated by hyphens)"
        )
    return value


def index_canonical_data(data):
    """Validate canonical IDs and return ``collection -> id -> record``."""
    indexes = {}
    for collection in LIST_COLLECTIONS:
        records = data.get(collection, [])
        if not isinstance(records, list):
            raise VariantError(f"data.{collection}: expected a list")
        index = {}
        for position, record in enumerate(records):
            context = f"data.{collection}[{position}]"
            if not isinstance(record, dict):
                raise VariantError(f"{context}: expected a mapping")
            record_id = _slug(record.get("id"), f"{context}.id")
            if record_id in index:
                raise VariantError(f"data.{collection}: duplicate ID '{record_id}'")
            index[record_id] = record
        indexes[collection] = index

    skills = data.get("skills", {})
    if not isinstance(skills, dict):
        raise VariantError("data.skills: expected a mapping of stable IDs")
    skill_index = {}
    for record_id, record in skills.items():
        _slug(record_id, f"data.skills.{record_id}")
        if not isinstance(record, dict):
            raise VariantError(f"data.skills.{record_id}: expected a mapping")
        skill_index[record_id] = record
    indexes["skills"] = skill_index

    personal = data.get("personal")
    if not isinstance(personal, dict):
        raise VariantError("data.personal: expected a mapping")
    links = personal.get("links", [])
    if not isinstance(links, list):
        raise VariantError("data.personal.links: expected a list")
    link_index = {}
    for position, link in enumerate(links):
        context = f"data.personal.links[{position}]"
        if not isinstance(link, dict):
            raise VariantError(f"{context}: expected a mapping")
        link_id = _slug(link.get("id"), f"{context}.id")
        if link_id in link_index:
            raise VariantError(f"data.personal.links: duplicate ID '{link_id}'")
        link_index[link_id] = link
    indexes["header_links"] = link_index
    return indexes


def _deep_merge(parent, child):
    """Merge mappings recursively; scalar and list values replace parents."""
    result = copy.deepcopy(parent)
    for key, value in child.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


class VariantResolver:
    """Load, inherit, validate, and materialize document variants."""

    def __init__(
        self,
        data,
        variant_dir=VARIANT_DIR,
        layout_file=LAYOUT_FILE,
        template_dir=TEMPLATE_DIR,
    ):
        self.data = data
        self.variant_dir = Path(variant_dir)
        self.layout_file = Path(layout_file)
        self.template_dir = Path(template_dir)
        self.indexes = index_canonical_data(data)
        self._validate_canonical_presentation_sets()
        self.layouts = self._load_layouts()
        self.variant_sources = {}
        self.private_variant_names = set()
        self.raw_variants = self._load_variants()
        self._inherited = {}

    def _load_layouts(self):
        loaded = _load_yaml(self.layout_file)
        if not isinstance(loaded, dict) or set(loaded) != {"layouts"}:
            raise VariantError(
                f"{self.layout_file}: expected one top-level 'layouts' mapping"
            )
        layouts = loaded["layouts"]
        if not isinstance(layouts, dict) or not layouts:
            raise VariantError(f"{self.layout_file}: 'layouts' must be non-empty")
        result = {}
        template_root = self.template_dir.resolve()
        for layout_id, config in layouts.items():
            _slug(layout_id, f"{self.layout_file}: layout ID")
            if not isinstance(config, dict):
                raise VariantError(
                    f"{self.layout_file}: layout '{layout_id}' must be a mapping"
                )
            unknown = sorted(set(config) - LAYOUT_KEYS)
            if unknown:
                raise VariantError(
                    f"{self.layout_file}: layout '{layout_id}' has unknown field(s): "
                    f"{', '.join(unknown)}"
                )
            template = config.get("template")
            if not isinstance(template, str) or not template:
                raise VariantError(
                    f"{self.layout_file}: layout '{layout_id}' needs a template"
                )
            candidate = (self.template_dir / template).resolve()
            try:
                candidate.relative_to(template_root)
            except ValueError as exc:
                raise VariantError(
                    f"layout '{layout_id}' template escapes templates/: {template}"
                ) from exc
            if not candidate.is_file():
                raise VariantError(
                    f"layout '{layout_id}' references missing template '{template}'"
                )
            result[layout_id] = copy.deepcopy(config)
        return result

    def _load_variants(self):
        if not self.variant_dir.is_dir():
            raise VariantError(f"variant directory does not exist: {self.variant_dir}")
        variants = {}
        public_paths = sorted(self.variant_dir.glob("*.yml"))
        private_dir = self.variant_dir / "private"
        private_paths = sorted(private_dir.glob("*.yml")) if private_dir.is_dir() else []
        paths = [(path, False) for path in public_paths]
        paths.extend((path, True) for path in private_paths)
        if not paths:
            raise VariantError(f"no variants found in {self.variant_dir}")
        for path, is_private in paths:
            name = _slug(path.stem, f"{path}: filename")
            loaded = _load_yaml(path)
            if not isinstance(loaded, dict):
                raise VariantError(f"{path}: expected a YAML mapping")
            unknown = sorted(set(loaded) - VARIANT_KEYS)
            if unknown:
                raise VariantError(f"{path}: unknown field(s): {', '.join(unknown)}")
            if name in variants:
                raise VariantError(
                    f"duplicate variant '{name}' in "
                    f"{self.variant_sources[name]} and {path}"
                )
            variants[name] = loaded
            self.variant_sources[name] = path
            if is_private:
                self.private_variant_names.add(name)
        return variants

    def names(self):
        return sorted(self.raw_variants)

    def is_private(self, name):
        """Return whether a variant definition came from variants/private/."""
        return LEGACY_ALIASES.get(name, name) in self.private_variant_names

    def _inherit(self, name, stack=None):
        if name in self._inherited:
            return copy.deepcopy(self._inherited[name])
        if name not in self.raw_variants:
            available = ", ".join(self.names())
            raise VariantError(f"unknown variant '{name}' (available: {available})")
        stack = [] if stack is None else stack
        if name in stack:
            cycle = " -> ".join(stack + [name])
            raise VariantError(f"variant inheritance cycle: {cycle}")
        raw = self.raw_variants[name]
        parent_name = raw.get("extends")
        if parent_name is not None and not isinstance(parent_name, str):
            raise VariantError(f"variant '{name}': extends must be a variant name")
        parent = self._inherit(parent_name, stack + [name]) if parent_name else {}
        child = {key: value for key, value in raw.items() if key != "extends"}
        merged = _deep_merge(parent, child)
        self._inherited[name] = merged
        return copy.deepcopy(merged)

    @staticmethod
    def _parse_ref(ref, context):
        if isinstance(ref, str):
            if ref.count(":") != 1:
                raise VariantError(
                    f"{context}: expected 'collection:id', got {ref!r}"
                )
            collection, record_id = ref.split(":", 1)
        elif isinstance(ref, dict):
            unknown = sorted(set(ref) - {"collection", "id"})
            if unknown or set(ref) != {"collection", "id"}:
                raise VariantError(
                    f"{context}: entry mapping must contain only collection and id"
                )
            collection, record_id = ref["collection"], ref["id"]
        else:
            raise VariantError(
                f"{context}: entry must be 'collection:id' or a mapping"
            )
        if collection not in SECTION_COLLECTIONS:
            allowed = ", ".join(sorted(SECTION_COLLECTIONS))
            raise VariantError(
                f"{context}: unknown collection '{collection}' (allowed: {allowed})"
            )
        _slug(record_id, f"{context}: record ID")
        return collection, record_id

    def _validate_presentation_value(
        self, collection, record_id, field, value, context
    ):
        if field == "order":
            if not isinstance(value, int) or isinstance(value, bool):
                raise VariantError(f"{context}: order must be an integer")
        elif field == "section":
            _slug(value, context)
        elif field in {"bullets", "items"}:
            if not isinstance(value, list) or not all(
                isinstance(item, str) for item in value
            ):
                raise VariantError(f"{context}: {field} must be a list of strings")
            if field == "items":
                canonical = self.indexes[collection][record_id].get("items", [])
                unknown = [item for item in value if item not in canonical]
                if unknown:
                    raise VariantError(
                        f"{context}: variant skill items must be a subset of canonical "
                        f"items; unknown: {', '.join(unknown)}"
                    )
        elif value is not None and not isinstance(value, str):
            raise VariantError(f"{context}: expected a string or null")

    def _validate_override_value(self, name, collection, record_id, field, value):
        context = f"variant '{name}' override {collection}:{record_id}.{field}"
        self._validate_presentation_value(
            collection, record_id, field, value, context
        )

    def _validate_canonical_presentation_sets(self):
        """Validate reusable presentation prose without permitting factual edits."""
        for collection in SECTION_COLLECTIONS:
            allowed_fields = PRESENTATION_FIELDS[collection] - {"section", "order"}
            for record_id, record in self.indexes[collection].items():
                sets = record.get("presentation_sets", {})
                context = f"data.{collection}:{record_id}.presentation_sets"
                if not isinstance(sets, dict):
                    raise VariantError(f"{context}: expected a mapping")
                for set_id, fields in sets.items():
                    _slug(set_id, f"{context}: presentation-set ID")
                    set_context = f"{context}.{set_id}"
                    if not isinstance(fields, dict):
                        raise VariantError(f"{set_context}: expected a mapping")
                    illegal = sorted(set(fields) - allowed_fields)
                    if illegal:
                        allowed = ", ".join(sorted(allowed_fields))
                        raise VariantError(
                            f"{set_context}: illegal factual/unknown presentation "
                            f"field(s): {', '.join(illegal)}. Allowed: {allowed}"
                        )
                    for field, value in fields.items():
                        self._validate_presentation_value(
                            collection,
                            record_id,
                            field,
                            value,
                            f"{set_context}.{field}",
                        )

    def _validate_config(self, name, config):
        if config.get("version") != 1:
            raise VariantError(f"variant '{name}': version must be 1")
        abstract = config.get("abstract", False)
        if not isinstance(abstract, bool):
            raise VariantError(f"variant '{name}': abstract must be true or false")

        layout_id = config.get("layout")
        if not isinstance(layout_id, str) or layout_id not in self.layouts:
            available = ", ".join(sorted(self.layouts))
            raise VariantError(
                f"variant '{name}': unknown or missing layout {layout_id!r} "
                f"(available: {available})"
            )

        output = config.get("output")
        if abstract:
            if output is not None:
                raise VariantError(
                    f"variant '{name}': abstract variants cannot declare output"
                )
        elif (
            not isinstance(output, str)
            or not output.endswith(".pdf")
            or Path(output).name != output
        ):
            raise VariantError(
                f"variant '{name}': output must be a .pdf filename without a path"
            )

        for field in ("description", "document_title", "summary", "availability"):
            value = config.get(field)
            if value is not None and not isinstance(value, str):
                raise VariantError(
                    f"variant '{name}': {field} must be a string or null"
                )

        legacy = config.get("legacy_visibility")
        if legacy is not None and legacy not in {"cv", "resume"}:
            raise VariantError(
                f"variant '{name}': legacy_visibility must be 'cv' or 'resume'"
            )

        header = config.get("header", {})
        if not isinstance(header, dict):
            raise VariantError(f"variant '{name}': header must be a mapping")
        unknown_header = sorted(set(header) - HEADER_KEYS)
        if unknown_header:
            raise VariantError(
                f"variant '{name}': header has unknown field(s): "
                f"{', '.join(unknown_header)}"
            )
        header_links = header.get("links", [])
        if not isinstance(header_links, list):
            raise VariantError(f"variant '{name}': header.links must be a list")
        for link_id in header_links:
            _slug(link_id, f"variant '{name}' header link")
            if link_id not in self.indexes["header_links"]:
                raise VariantError(
                    f"variant '{name}': unknown header link ID '{link_id}'"
                )

        sections = config.get("sections", [])
        if not isinstance(sections, list):
            raise VariantError(f"variant '{name}': sections must be a list")
        if not abstract and legacy is None and not sections:
            raise VariantError(
                f"variant '{name}': generic variants need at least one section"
            )
        section_ids = set()
        selected = set()
        parsed_sections = []
        for section_pos, section in enumerate(sections):
            context = f"variant '{name}' sections[{section_pos}]"
            if not isinstance(section, dict):
                raise VariantError(f"{context}: expected a mapping")
            unknown = sorted(set(section) - SECTION_KEYS)
            if unknown:
                raise VariantError(f"{context}: unknown field(s): {', '.join(unknown)}")
            if not REQUIRED_SECTION_KEYS.issubset(section):
                missing = sorted(REQUIRED_SECTION_KEYS - set(section))
                raise VariantError(f"{context}: missing field(s): {', '.join(missing)}")
            section_id = _slug(section["id"], f"{context}.id")
            if section_id in section_ids:
                raise VariantError(
                    f"variant '{name}': duplicate section ID '{section_id}'"
                )
            section_ids.add(section_id)
            if not isinstance(section["label"], str) or not section["label"]:
                raise VariantError(f"{context}.label: expected a non-empty string")
            if not isinstance(section["entries"], list):
                raise VariantError(f"{context}.entries: expected a list")
            page_break = section.get("page_break_before", False)
            if not isinstance(page_break, bool):
                raise VariantError(
                    f"{context}.page_break_before: expected true or false"
                )
            parsed_entries = []
            for entry_pos, ref in enumerate(section["entries"]):
                ref_context = f"{context}.entries[{entry_pos}]"
                collection, record_id = self._parse_ref(ref, ref_context)
                if record_id not in self.indexes[collection]:
                    raise VariantError(
                        f"{ref_context}: unknown record ID "
                        f"'{collection}:{record_id}'"
                    )
                pair = (collection, record_id)
                if pair in selected:
                    raise VariantError(
                        f"variant '{name}': duplicate selected entry "
                        f"'{collection}:{record_id}'"
                    )
                selected.add(pair)
                parsed_entries.append(pair)
            parsed_sections.append((section_id, section, parsed_entries))

        overrides = config.get("overrides", {})
        if not isinstance(overrides, dict):
            raise VariantError(f"variant '{name}': overrides must be a mapping")
        for collection, records in overrides.items():
            if collection not in SECTION_COLLECTIONS:
                raise VariantError(
                    f"variant '{name}': overrides name unknown collection "
                    f"'{collection}'"
                )
            if not isinstance(records, dict):
                raise VariantError(
                    f"variant '{name}': overrides.{collection} must be a mapping"
                )
            for record_id, fields in records.items():
                _slug(record_id, f"variant '{name}' override ID")
                if record_id not in self.indexes[collection]:
                    raise VariantError(
                        f"variant '{name}': override references unknown record ID "
                        f"'{collection}:{record_id}'"
                    )
                if (collection, record_id) not in selected:
                    raise VariantError(
                        f"variant '{name}': override targets unselected record "
                        f"'{collection}:{record_id}'"
                    )
                if not isinstance(fields, dict):
                    raise VariantError(
                        f"variant '{name}': override {collection}:{record_id} "
                        "must be a mapping"
                    )
                illegal = sorted(set(fields) - PRESENTATION_FIELDS[collection])
                if illegal:
                    allowed = ", ".join(sorted(PRESENTATION_FIELDS[collection]))
                    raise VariantError(
                        f"variant '{name}': illegal factual/unknown override field(s) "
                        f"for {collection}:{record_id}: {', '.join(illegal)}. "
                        f"Presentation fields allowed here: {allowed}"
                    )
                for field, value in fields.items():
                    self._validate_override_value(
                        name, collection, record_id, field, value
                    )
                target = fields.get("section")
                if target is not None and target not in section_ids:
                    raise VariantError(
                        f"variant '{name}': override {collection}:{record_id} "
                        f"moves to unknown section '{target}'"
                    )

        presentation_sets = config.get("presentation_sets", {})
        if not isinstance(presentation_sets, dict):
            raise VariantError(
                f"variant '{name}': presentation_sets must be a mapping"
            )
        for collection, records in presentation_sets.items():
            if collection not in SECTION_COLLECTIONS:
                raise VariantError(
                    f"variant '{name}': presentation_sets names unknown collection "
                    f"'{collection}'"
                )
            if not isinstance(records, dict):
                raise VariantError(
                    f"variant '{name}': presentation_sets.{collection} must be a "
                    "mapping"
                )
            for record_id, set_id in records.items():
                _slug(record_id, f"variant '{name}' presentation-set record ID")
                # A concrete child may replace its parent's section list and
                # explicitly clear presentation-set choices for records it no
                # longer selects.  Keep the null in the inherited config so
                # normal recursive-map semantics remain predictable; resolve()
                # already treats a null selection as "use canonical prose."
                if set_id is None:
                    continue
                if record_id not in self.indexes[collection]:
                    raise VariantError(
                        f"variant '{name}': presentation set references unknown "
                        f"record ID '{collection}:{record_id}'"
                    )
                if (collection, record_id) not in selected:
                    raise VariantError(
                        f"variant '{name}': presentation set targets unselected "
                        f"record '{collection}:{record_id}'"
                    )
                _slug(set_id, f"variant '{name}' presentation-set selection")
                available = self.indexes[collection][record_id].get(
                    "presentation_sets", {}
                )
                if set_id not in available:
                    choices = ", ".join(sorted(available)) or "none"
                    raise VariantError(
                        f"variant '{name}': unknown presentation set '{set_id}' "
                        f"for {collection}:{record_id} (available: {choices})"
                    )
        return parsed_sections

    def resolve(self, name):
        name = LEGACY_ALIASES.get(name, name)
        config = self._inherit(name)
        parsed_sections = self._validate_config(name, config)
        layout = copy.deepcopy(self.layouts[config["layout"]])
        materialized = copy.deepcopy(self.data)

        header_links = [
            copy.deepcopy(self.indexes["header_links"][link_id])
            for link_id in config.get("header", {}).get("links", [])
        ]

        section_map = {}
        rendered_sections = []
        for section_id, section, _ in parsed_sections:
            rendered = {
                "id": section_id,
                "label": section["label"],
                "page_break_before": section.get("page_break_before", False),
                "entries": [],
            }
            rendered_sections.append(rendered)
            section_map[section_id] = rendered

        serial = 0
        presentation_sets = config.get("presentation_sets", {})
        overrides = config.get("overrides", {})
        for source_section_id, _section, entries in parsed_sections:
            for collection, record_id in entries:
                record = copy.deepcopy(self.indexes[collection][record_id])
                set_id = presentation_sets.get(collection, {}).get(record_id)
                set_fields = {}
                if set_id is not None:
                    set_fields = record.get("presentation_sets", {})[set_id]
                override_fields = copy.deepcopy(
                    overrides.get(collection, {}).get(record_id, {})
                )
                fields = _deep_merge(set_fields, override_fields)
                target_section = fields.pop("section", source_section_id)
                order = fields.pop("order", serial)
                label = fields.pop("label", None)
                if label is not None:
                    record["presentation_label"] = label
                if "preamble" in fields:
                    record["presentation_preamble"] = fields.pop("preamble")
                record.update(fields)
                section_map[target_section]["entries"].append(
                    {
                        "collection": collection,
                        "id": record_id,
                        "order": order,
                        "serial": serial,
                        "record": record,
                    }
                )
                serial += 1
        for section in rendered_sections:
            section["entries"].sort(key=lambda item: (item["order"], item["serial"]))

        materialized["variant"] = {
            **copy.deepcopy(config),
            "name": name,
            "header_links": header_links,
        }
        materialized["variant_sections"] = rendered_sections
        return ResolvedVariant(
            name=name,
            config=config,
            layout=layout,
            template=layout["template"],
            output=config.get("output"),
            data=materialized,
        )

    def resolve_all(self):
        """Resolve the repository and reject concrete output collisions."""
        resolved = [self.resolve(name) for name in self.names()]
        output_owners = {}
        for variant in resolved:
            if variant.config.get("abstract"):
                continue
            previous = output_owners.get(variant.output)
            if previous is not None:
                raise VariantError(
                    f"variants '{previous}' and '{variant.name}' declare duplicate "
                    f"output PDF filename '{variant.output}'"
                )
            output_owners[variant.output] = variant.name
        return resolved


def compile_tex(tex_source, output_filename):
    """Run xelatex twice and copy the resulting PDF into ``output/``."""
    if shutil.which("xelatex") is None:
        raise VariantError("xelatex is not installed or not on PATH")
    output_stem = Path(output_filename).stem
    BUILD_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)

    build_template_dir = BUILD_DIR / "templates"
    if build_template_dir.exists():
        shutil.rmtree(build_template_dir)
    shutil.copytree(TEMPLATE_DIR, build_template_dir)

    tex_in_build = BUILD_DIR / f"{output_stem}.tex"
    tex_in_build.write_text(tex_source, encoding="utf-8")
    for _ in range(2):
        result = subprocess.run(
            [
                "xelatex",
                "-interaction=nonstopmode",
                "-halt-on-error",
                f"-output-directory={BUILD_DIR}",
                str(tex_in_build),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            tail = (result.stdout + "\n" + result.stderr)[-4000:]
            raise VariantError(
                f"xelatex failed while compiling {output_filename}:\n{tail}"
            )

    pdf_src = BUILD_DIR / output_filename
    pdf_dst = OUTPUT_DIR / output_filename
    shutil.copy(pdf_src, pdf_dst)
    print(f"  -> {pdf_dst}")


def build_variant(name, resolver):
    resolved = resolver.resolve(name)
    if resolved.config.get("abstract"):
        raise VariantError(f"variant '{resolved.name}' is an abstract base")
    print(
        f"Building {resolved.name} "
        f"[{resolved.config['layout']} -> {resolved.output}]..."
    )
    tex_source = render(resolved.template, resolved.data, resolver.template_dir)
    compile_tex(tex_source, resolved.output)


def _build_names(names, resolver):
    for name in names:
        build_variant(name, resolver)


def _list_variants(resolver):
    print("Variant                    Scope    Layout                    Output")
    print(
        "-------------------------  -------  ------------------------  "
        "-----------------------------"
    )
    for resolved in resolver.resolve_all():
        name = resolved.name
        scope = "private" if resolver.is_private(name) else "tracked"
        output = resolved.output or "(abstract base)"
        print(
            f"{name:<25}  {scope:<7}  "
            f"{resolved.config['layout']:<24}  {output}"
        )
    print("\nLegacy alias: resume_ats -> resume-ats")


def _parser():
    parser = argparse.ArgumentParser(
        description="Build CV/résumé audience variants from canonical YAML"
    )
    parser.add_argument(
        "target", nargs="?", help="variant name, all, or all_all (default: all)"
    )
    parser.add_argument("--variant", metavar="NAME", help="build one named variant")
    parser.add_argument("--list", action="store_true", help="list variants and outputs")
    parser.add_argument(
        "--all-variants",
        action="store_true",
        help="build every non-abstract maintained variant",
    )
    parser.add_argument(
        "--validate-config",
        action="store_true",
        help="resolve every variant without compiling PDFs",
    )
    return parser


def main(argv=None):
    parser = _parser()
    args = parser.parse_args(argv)
    mode_count = sum(
        bool(value)
        for value in (
            args.variant,
            args.list,
            args.all_variants,
            args.validate_config,
        )
    )
    if mode_count > 1 or (args.target and mode_count):
        parser.error("choose one target/mode")

    try:
        data = load_all_data()
        resolver = VariantResolver(data)
        if args.list:
            _list_variants(resolver)
            return 0
        if args.validate_config:
            resolved = resolver.resolve_all()
            print(f"Validated {len(resolved)} variants.")
            return 0
        if args.all_variants:
            names = [
                variant.name
                for variant in resolver.resolve_all()
                if not variant.config.get("abstract")
            ]
            _build_names(names, resolver)
            return 0

        target = args.variant or args.target or "all"
        if target == "all":
            _build_names(["cv", "resume"], resolver)
        elif target == "all_all":
            _build_names(["cv", "resume", "resume-ats"], resolver)
        else:
            build_variant(target, resolver)
        return 0
    except VariantError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
