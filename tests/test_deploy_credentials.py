"""tools/with-deploy-credentials.sh: the deploy's two Forgejo pushes ask for
the token once, and nothing outlives the deploy holding it.

Each case runs git's own credential protocol (fill, then approve, as a push
does on success) under the wrapper, with an isolated global configuration
whose helper records every call it gets."""

import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tools" / "with-deploy-credentials.sh"
URL = "https://forge.test"

# What a push does: ask for credentials, use them, and on success tell the
# helpers to keep them.
PUSH = ('printf "url=https://user@forge.test/{repo}.git\\n\\n" | git credential fill > "$OUT/{repo}.fill" && '
        'cat "$OUT/{repo}.fill" | git credential approve')


@unittest.skipUnless(shutil.which("git"), "git is needed")
class DeployCredentials(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="deploy-cred-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.out = self.root / "out"
        self.out.mkdir()
        self.runtime = self.root / "runtime"
        self.runtime.mkdir(mode=0o700)
        askpass = self.root / "askpass"
        askpass.write_text('#!/bin/sh\necho asked >> "$OUT/asked"\necho TOKEN\n')
        askpass.chmod(0o755)
        recorder = self.root / "recorder"
        recorder.write_text('#!/bin/sh\necho "$1" >> "$OUT/recorded"\ncat > /dev/null\n')
        recorder.chmod(0o755)
        self.global_config = self.root / "gitconfig"
        self.global_config.write_text(f"[credential]\n\thelper = !{recorder}\n")
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        self.env.update(HOME=str(self.root), XDG_RUNTIME_DIR=str(self.runtime), OUT=str(self.out),
                        GIT_CONFIG_GLOBAL=str(self.global_config), GIT_CONFIG_NOSYSTEM="1",
                        GIT_ASKPASS=str(askpass), GIT_TERMINAL_PROMPT="0")

    def run_tool(self, script: str, **env: str) -> subprocess.CompletedProcess:
        return subprocess.run([str(TOOL), URL, "sh", "-c", script], env={**self.env, **env},
                              capture_output=True, text=True, timeout=60)

    def lines(self, name: str) -> list[str]:
        path = self.out / name
        return path.read_text().split() if path.exists() else []

    def test_the_token_is_asked_for_once_across_both_pushes(self):
        done = self.run_tool(PUSH.format(repo="engine") + " && " + PUSH.format(repo="site"))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.lines("asked"), ["asked"])
        self.assertIn("password=TOKEN", (self.out / "site.fill").read_text())

    def test_no_other_helper_is_asked_or_handed_the_token(self):
        done = self.run_tool(PUSH.format(repo="engine") + " && " + PUSH.format(repo="site"))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.lines("recorded"), [])
        # Only for the forge: another host still reaches the configured helper.
        done = self.run_tool('printf "protocol=https\\nhost=other.test\\nusername=u\\npassword=p\\n\\n"'
                             ' | git credential approve')
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.lines("recorded"), ["store"])

    def test_the_cache_is_gone_when_the_command_ends(self):
        self.run_tool(PUSH.format(repo="engine"))
        self.assertEqual(list(self.runtime.iterdir()), [])
        # A later run starts empty and asks again.
        self.run_tool(PUSH.format(repo="site"))
        self.assertEqual(self.lines("asked"), ["asked", "asked"])

    def test_each_run_has_a_private_directory_of_its_own(self):
        script = 'echo "$DEPLOY_CRED_SOCKET" >> "$OUT/sockets"'
        for _ in range(2):
            self.assertEqual(self.run_tool(script + ' && stat -c %a "$(dirname "$(tail -1 "$OUT/sockets")")"'
                                           ' >> "$OUT/modes"').returncode, 0)
        sockets = self.lines("sockets")
        self.assertEqual(len(set(sockets)), 2, sockets)
        for socket in sockets:
            self.assertTrue(socket.startswith(str(self.runtime) + "/"), socket)
        self.assertEqual(self.lines("modes"), ["700", "700"])

    def test_a_runtime_directory_with_a_space_in_its_name(self):
        # Git runs the helper through the shell; a spelled-out socket path
        # was split there, and the second push asked again (review, 2026-11-25).
        spaced = self.root / "run time"
        spaced.mkdir(mode=0o700)
        done = self.run_tool(PUSH.format(repo="engine") + " && " + PUSH.format(repo="site"),
                             XDG_RUNTIME_DIR=str(spaced))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.lines("asked"), ["asked"])
        self.assertEqual(list(spaced.iterdir()), [])

    def test_configuration_the_caller_passes_is_kept(self):
        done = self.run_tool('git config --get deploy.kept > "$OUT/kept"',
                             GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="deploy.kept", GIT_CONFIG_VALUE_0="yes")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.lines("kept"), ["yes"])

    def test_the_command_s_status_is_the_tool_s(self):
        self.assertEqual(self.run_tool("exit 7").returncode, 7)
        self.assertEqual(list(self.runtime.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
