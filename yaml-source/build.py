#!/usr/bin/env python3
"""
Build script for CV and résumé.

Loads YAML data files, renders Jinja2 LaTeX templates with a LaTeX-safe
delimiter configuration, and compiles both documents via xelatex.

Usage:
    python build.py cv           # build CV only
    python build.py resume       # build website résumé only
    python build.py resume_ats   # build ATS-optimized résumé only
    python build.py all          # build cv + resume (default; not ats)
    python build.py all_all      # build cv + resume + resume_ats
"""

import sys
import subprocess
import shutil
from pathlib import Path
from datetime import date

import yaml
from jinja2 import Environment, FileSystemLoader


ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
TEMPLATE_DIR = ROOT / "templates"
OUTPUT_DIR = ROOT / "output"
BUILD_DIR = ROOT / "build"


def load_all_data():
    """Load every .yml file in data/ and merge into a single dict."""
    data = {}
    for yml_file in sorted(DATA_DIR.glob("*.yml")):
        with open(yml_file) as f:
            loaded = yaml.safe_load(f)
            if not loaded:
                continue
            stem = yml_file.stem
            if stem == "personal":
                # personal.yml's contents become the `personal` key
                data["personal"] = loaded
            elif stem == "skills":
                # skills.yml has multiple top-level keys — merge all directly
                data.update(loaded)
            else:
                # everything else merges directly (education.yml has key
                # 'education', experience.yml has key 'experience', etc.)
                data.update(loaded)
    data["build_date"] = date.today().strftime("%B %Y")
    return data


def make_env():
    """Jinja2 environment configured for LaTeX-safe delimiters."""
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
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


def render(template_name, data):
    env = make_env()
    template = env.get_template(template_name)
    return template.render(**data)


def compile_tex(tex_path, output_name):
    """Run xelatex twice (for cross-references) and move the PDF to output/."""
    BUILD_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Copy shared templates into build dir so \input paths resolve cleanly
    build_template_dir = BUILD_DIR / "templates"
    if build_template_dir.exists():
        shutil.rmtree(build_template_dir)
    shutil.copytree(TEMPLATE_DIR, build_template_dir)

    # Write .tex into build dir
    tex_in_build = BUILD_DIR / f"{output_name}.tex"
    tex_in_build.write_text(tex_path.read_text())

    # Compile (twice, as is tradition)
    for _ in range(2):
        result = subprocess.run(
            ["xelatex", "-interaction=nonstopmode", "-halt-on-error",
             f"-output-directory={BUILD_DIR}", str(tex_in_build)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"ERROR compiling {output_name}.tex:")
            print(result.stdout[-2000:])
            sys.exit(1)

    # Move PDF to output/
    pdf_src = BUILD_DIR / f"{output_name}.pdf"
    pdf_dst = OUTPUT_DIR / f"{output_name}.pdf"
    shutil.copy(pdf_src, pdf_dst)
    print(f"  → {pdf_dst}")


def build_one(name):
    """Build a single document by name ('cv' or 'resume')."""
    print(f"Building {name}...")
    data = load_all_data()
    tex_source = render(f"{name}.tex.j2", data)

    # Write rendered .tex into build dir
    BUILD_DIR.mkdir(exist_ok=True)
    tex_path = BUILD_DIR / f"{name}.tex"
    tex_path.write_text(tex_source)

    compile_tex(tex_path, name)


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "all"
    if target in ("cv", "resume", "resume_ats"):
        build_one(target)
    elif target == "all":
        build_one("cv")
        build_one("resume")
    elif target == "all_all":
        build_one("cv")
        build_one("resume")
        build_one("resume_ats")
    else:
        print(f"Unknown target: {target}")
        print("Usage: python build.py [cv|resume|resume_ats|all|all_all]")
        sys.exit(1)


if __name__ == "__main__":
    main()
