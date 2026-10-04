"""The lists the tools share with the generator, as `site shared-rules`
prints them.

A list that a tool must agree with the build on (the epistemic
vocabularies, the content directories a page collection may not take) is
defined once, in build/, and read here: hand copies of these drifted.
Fails if the generator does not build.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
from functools import lru_cache
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "unpublished", Path(__file__).with_name("unpublished.py"))
unpublished = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(unpublished)


@lru_cache(maxsize=1)
def shared_rules() -> dict:
    return json.loads(subprocess.check_output(
        [unpublished.site_binary(), "shared-rules"], text=True))
