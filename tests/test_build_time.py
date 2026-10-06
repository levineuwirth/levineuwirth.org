"""The footer build time comes from one file, and an unchanged page keeps
its signature (tools/stamp-build-time.py, tools/sign-site.sh).

Until 2026-10-06 the time was stamped into every page after every build,
so every build rewrote and recompressed ~500 unchanged pages and every
deploy re-signed and re-sent them. Now the build writes
_site/build/time.txt, the pages stay byte-identical, and sign-site.sh
signs a page again only when its content changed.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests._helpers import ROOT, script_env

STAMP = ROOT / "tools" / "stamp-build-time.py"
SIGN = ROOT / "tools" / "sign-site.sh"
FOOTER = '<footer><span class="footer-build-time" data-build-time></span></footer>'


class StampTests(unittest.TestCase):
    def test_writes_the_time_once_and_leaves_pages_alone(self):
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            page = site / "essays" / "a.html"
            page.parent.mkdir(parents=True)
            page.write_text(f"<html><body><p>Prose.</p>{FOOTER}</body></html>\n")
            before = page.read_bytes()
            done = subprocess.run(["python3", str(STAMP), str(site)], env=script_env(),
                                  capture_output=True, text=True, timeout=30)
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertEqual(page.read_bytes(), before)
            # The footers' format: "Monday, October 6th, 2026 13:03:33".
            self.assertRegex((site / "build" / "time.txt").read_text(),
                             r"^[A-Z][a-z]+day, [A-Z][a-z]+ \d{1,2}(st|nd|rd|th), "
                             r"\d{4} \d{2}:\d{2}:\d{2}\n$")

    def test_the_footer_ships_an_empty_span(self):
        footer = (ROOT / "templates" / "partials" / "footer.html").read_text()
        self.assertIn('<span class="footer-build-time" data-build-time></span>', footer)


@unittest.skipUnless(shutil.which("gpg") and shutil.which("gpgconf"), "needs gpg")
class SignTests(unittest.TestCase):
    """Signed with a throwaway Ed25519 key in a scratch keyring."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.home = self.root / "gnupg"
        self.home.mkdir(mode=0o700)
        self.addCleanup(subprocess.run, ["gpgconf", "--homedir", str(self.home), "--kill", "all"],
                        capture_output=True)
        subprocess.run(["gpg", "--homedir", str(self.home), "--batch", "--passphrase", "",
                        "--quick-gen-key", "sign-site test", "ed25519", "sign", "never"],
                       check=True, capture_output=True, timeout=60)
        listing = subprocess.run(["gpg", "--homedir", str(self.home), "--list-keys", "--with-colons"],
                                 check=True, capture_output=True, text=True).stdout
        self.key = next(line.split(":")[9] for line in listing.splitlines() if line.startswith("fpr:"))
        self.site = self.root / "site"
        self.manifest = self.root / "sign-manifest.txt"
        for rel in ("index.html", "essays/a.html", "essays/b.html"):
            self.write(rel, f"<p>{rel}</p>")

    def write(self, rel, body):
        path = self.site / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"<html><body>{body}{FOOTER}</body></html>\n")
        return path

    def sign(self, **extra):
        env = script_env(GNUPGHOME=str(self.home), SIGNING_KEY=self.key,
                         SIGN_MANIFEST=str(self.manifest), **extra)
        done = subprocess.run(["bash", str(SIGN), str(self.site)], env=env,
                              capture_output=True, text=True, timeout=120)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        return int(re.search(r"Signed (\d+) HTML", done.stdout).group(1))

    def verifies(self, rel):
        page = self.site / rel
        return subprocess.run(["gpg", "--homedir", str(self.home), "--verify",
                               f"{page}.sig", str(page)], capture_output=True).returncode == 0

    def test_only_changed_or_unsigned_pages_are_signed_again(self):
        self.assertEqual(self.sign(), 3)
        sig_a = (self.site / "essays/a.html.sig").read_bytes()
        self.assertEqual(self.sign(), 0)
        self.assertEqual((self.site / "essays/a.html.sig").read_bytes(), sig_a)

        self.write("essays/a.html", "<p>revised</p>")
        (self.site / "essays/b.html.sig").unlink()
        self.assertEqual(self.sign(), 2)
        for rel in ("index.html", "essays/a.html", "essays/b.html"):
            self.assertTrue(self.verifies(rel), rel)

    def test_a_new_mtime_alone_is_not_a_change(self):
        self.sign()
        (self.site / "essays/a.html").touch()
        self.assertEqual(self.sign(), 0)

    def test_sign_all_and_another_key_sign_everything(self):
        self.sign()
        self.assertEqual(self.sign(SIGN_ALL="1"), 3)
        lines = self.manifest.read_text().splitlines()
        self.manifest.write_text("\n".join(["key OTHER" + lines[0][len("key " + self.key):]]
                                           + lines[1:]) + "\n")
        self.assertEqual(self.sign(), 3)


if __name__ == "__main__":
    unittest.main()
