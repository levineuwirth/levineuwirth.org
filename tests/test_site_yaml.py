"""What this site has chosen in site.yaml, of what the engine leaves open."""

import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def read(rel: str) -> dict:
    return yaml.safe_load((ROOT / rel).read_text(encoding="utf-8"))


class Choices(unittest.TestCase):
    def test_it_lists_every_popup_provider_the_engine_has(self):
        # The engine's default is none. A provider the engine gains is off
        # here until nginx/ allows it and this list has it.
        self.assertEqual(sorted(read("site.yaml")["popup-providers"]),
                         sorted(read("engine/switches.yaml")["popups"]["providers"]))


if __name__ == "__main__":
    unittest.main()
