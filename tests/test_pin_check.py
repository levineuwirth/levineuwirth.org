"""tools/pin-check.sh, the SHA-256 check the vendoring scripts share. An
unpinned file used to be vendored with a warning; it is refused now, unless
ALLOW_UNPINNED=1, which prints the line to pin."""

import hashlib
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests._helpers import engine_path, script_env


class VendoringAcrossTheMove(unittest.TestCase):
    def test_pins_are_found_where_a6_has_moved_them(self):
        # A6d moves the vendored assets and their checksums under engine/
        # before A6e moves the scripts: a downloader still in tools/ must
        # verify the files it has against the moved pins, not refuse and
        # delete them.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("download-model.sh", "site-paths.sh", "pin-check.sh"):
                (root / "tools").mkdir(exist_ok=True)
                shutil.copy2(engine_path(f"tools/{name}"), root / "tools" / name)
            model = root / "engine/static/models/all-MiniLM-L6-v2"
            pins = []
            for rel in ("config.json", "tokenizer.json", "tokenizer_config.json",
                        "special_tokens_map.json", "onnx/model_quantized.onnx"):
                (model / rel).parent.mkdir(parents=True, exist_ok=True)
                (model / rel).write_text(rel)
                pins.append(f"{hashlib.sha256(rel.encode()).hexdigest()}  {rel}\n")
            (root / "engine/tools").mkdir()
            (root / "engine/tools/model-checksums.sha256").write_text("".join(pins))
            done = subprocess.run(["bash", "tools/download-model.sh"], cwd=root, env=script_env(),
                                  capture_output=True, text=True, timeout=30)
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertEqual(done.stdout.count("sha256 verified"), 5)
            self.assertTrue((model / "onnx/model_quantized.onnx").is_file())


class PinVerify(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.file = self.dir / "viewer.zip"
        self.file.write_bytes(b"archive bytes")
        self.sha = hashlib.sha256(b"archive bytes").hexdigest()
        self.sums = self.dir / "checksums.sha256"

    def verify(self, key="viewer-1.0.zip", **env):
        return subprocess.run(
            ["bash", "-c", 'source "$1"; pin_verify "$2" "$3" "$4" test',
             "-", str(engine_path("tools/pin-check.sh")), str(self.sums), key, str(self.file)],
            env=script_env(**env), capture_output=True, text=True)

    def test_a_matching_pin_passes(self):
        self.sums.write_text(f"{'0' * 64}  viewer-0.9.zip\n{self.sha}  viewer-1.0.zip\n")
        self.assertEqual(self.verify().returncode, 0)

    def test_a_mismatch_fails_and_says_both_hashes(self):
        self.sums.write_text(f"{'0' * 64}  viewer-1.0.zip\n")
        done = self.verify()
        self.assertEqual(done.returncode, 1)
        self.assertIn("sha256 mismatch for viewer-1.0.zip", done.stderr)
        self.assertIn(self.sha, done.stderr)

    def test_unpinned_is_refused(self):
        # Neither a missing line nor a missing file may pass any more; an
        # older version's line does not cover a new version.
        self.sums.write_text(f"{self.sha}  viewer-0.9.zip\n")
        for case in ("no line", "no file"):
            with self.subTest(case=case):
                if case == "no file":
                    self.sums.unlink()
                done = self.verify()
                self.assertEqual(done.returncode, 1)
                self.assertIn("refusing to vendor", done.stderr)

    def test_allow_unpinned_vendors_and_prints_the_line_to_pin(self):
        done = self.verify(ALLOW_UNPINNED="1")
        self.assertEqual(done.returncode, 0)
        self.assertIn(f"{self.sha}  viewer-1.0.zip", done.stderr)


if __name__ == "__main__":
    unittest.main()
