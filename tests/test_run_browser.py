"""tests/run_browser.py, and the cleanup in tests/_browser.py it relies on,
with fake modules in a scratch root and a fake harness script.

Checked: module names are taken once each, however spelled; the memory
floor holds with nothing running (the runner waits, then stops and names
what it did not run); a stopped runner (SIGTERM or SIGINT) stops its
modules, killing one that ignores SIGTERM after the grace period, and a
child that ignores it under a module that does not (the group is killed,
not only its leader); a module stopped during setUpClass, where unittest
runs no class cleanup, still stops the harness scripts it started in
sessions of their own, a stubborn child of theirs included; and the whole
chain, runner to module to harness script to its stubborn child, stops
from the runner (the module's cleanup must end before the runner's grace
does, or the runner kills the module with the child still there).
"""

from __future__ import annotations

import importlib.util
import os
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tests" / "run_browser.py"

# A process in its parent's group that ignores SIGTERM, records its pid in
# argv[1] and waits.
STUBBORN_CHILD = (
    "import os, pathlib, signal, sys, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); "
    "pathlib.Path(sys.argv[1]).write_text(str(os.getpid())); time.sleep(120)")

# A browser-test module that records its pid, then waits (in setUpClass, as
# the real ones do their work) until it is stopped; it may ignore SIGTERM,
# or leave a child that does.
FAKE_MODULE = """
import os, pathlib, signal, subprocess, sys, time, unittest
class Fake(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.environ.get("FAKE_STUBBORN"):
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
        if os.environ.get("FAKE_CHILD_MARK"):
            subprocess.Popen([sys.executable, "-c", os.environ["STUBBORN_CHILD"], os.environ["FAKE_CHILD_MARK"]])
        pathlib.Path(os.environ["FAKE_MARK"]).write_text(str(os.getpid()))
        time.sleep(120)
    def test_nothing(self):
        pass
"""

# A harness script that records its pid and sleeps; it may leave a child
# that ignores SIGTERM, in its own group.
SLEEPER = """
import os, pathlib, subprocess, sys, time
if os.environ.get("SLEEPER_CHILD_MARK"):
    subprocess.Popen([sys.executable, "-c", os.environ["STUBBORN_CHILD"], os.environ["SLEEPER_CHILD_MARK"]])
pathlib.Path(os.environ["SLEEPER_MARK"]).write_text(str(os.getpid()))
time.sleep(120)
"""

# A module whose setUpClass starts SLEEPER through the real run_harness;
# DRIVER runs it as a script.
HARNESS_MODULE = """
import pathlib, sys, unittest
sys.path.insert(0, {root!r})
from tests._browser import run_harness
class Driver(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        run_harness(cls, "http://127.0.0.1:9", pathlib.Path({out!r}), [[{sleeper!r}, "x"]], seconds=120)
    def test_nothing(self):
        pass
"""
DRIVER = HARNESS_MODULE + """unittest.main(argv=["driver"])
"""


def alive(pid: int) -> bool:
    """Running, and not a zombie waiting to be reaped."""
    try:
        state = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0]
    except (OSError, IndexError):
        return False
    return state != "Z"


def wait_until(predicate, seconds: float) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.1)
    return predicate()


def kill(pid: int) -> None:
    """Cleanup: a process a failing test left behind."""
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def read_pid(mark: Path, seconds: float = 20) -> int:
    if not wait_until(lambda: mark.exists() and mark.read_text().strip(), seconds):
        raise AssertionError(f"{mark.name} never written")
    return int(mark.read_text())


class RunBrowser(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory(prefix="run-browser-")
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        (self.tmp / "tests").mkdir()
        (self.tmp / "tests" / "test_browser_fake.py").write_text(FAKE_MODULE)
        self.mark = self.tmp / "fake.pid"

    def runner(self, *args: str, **env: str) -> subprocess.Popen:
        proc = subprocess.Popen([sys.executable, str(RUNNER), *args],
                                env={**os.environ, "BROWSER_TESTS_ROOT": str(self.tmp),
                                     "FAKE_MARK": str(self.mark), "BROWSER_MIN_FREE_GB": "0",
                                     "STUBBORN_CHILD": STUBBORN_CHILD, **env},
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self.addCleanup(lambda: proc.poll() is None and proc.kill())
        return proc

    def test_names_once_each(self) -> None:
        spec = importlib.util.spec_from_file_location("run_browser", RUNNER)
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        self.assertEqual(runner.modules(["nav", "test_browser_nav", "toc", "nav"]),
                         ["test_browser_nav", "test_browser_toc"])
        with self.assertRaises(SystemExit):
            runner.modules(["no_such_module"])

    def test_the_memory_floor_holds_with_nothing_running(self) -> None:
        proc = self.runner(BROWSER_MIN_FREE_GB="1e9", BROWSER_MEM_WAIT="1")
        out, _ = proc.communicate(timeout=30)
        self.assertEqual(proc.returncode, 1, out)
        self.assertIn("not run: test_browser_fake", out)
        self.assertFalse(self.mark.exists(), "a module started below the memory floor")

    def test_a_stopped_runner_stops_its_modules(self) -> None:
        child_mark = self.tmp / "child.pid"
        for sig in (signal.SIGTERM, signal.SIGINT):
            for case in ("cooperative", "ignores SIGTERM", "its child ignores SIGTERM"):
                with self.subTest(signal=sig.name, module=case):
                    self.mark.unlink(missing_ok=True)
                    child_mark.unlink(missing_ok=True)
                    env = {"BROWSER_STOP_GRACE": "2"}
                    if case == "ignores SIGTERM":
                        env["FAKE_STUBBORN"] = "1"
                    if case == "its child ignores SIGTERM":
                        env["FAKE_CHILD_MARK"] = str(child_mark)
                    proc = self.runner(**env)
                    pids = [read_pid(self.mark)]
                    if "FAKE_CHILD_MARK" in env:
                        pids.append(read_pid(child_mark))
                    for pid in pids:
                        self.addCleanup(kill, pid)
                    proc.send_signal(sig)
                    out, _ = proc.communicate(timeout=20)
                    self.assertEqual(proc.returncode, 128 + sig, out)
                    for pid in pids:
                        self.assertTrue(wait_until(lambda: not alive(pid), 10),
                                        f"{pid} outlived the runner")

    def test_harness_scripts_stop_with_their_module(self) -> None:
        # Stopped during setUpClass: unittest runs no class cleanup there.
        sleeper = self.tmp / "sleeper.py"
        sleeper.write_text(SLEEPER)
        driver = self.tmp / "driver.py"
        driver.write_text(DRIVER.format(root=str(ROOT), out=str(self.tmp / "out"), sleeper=str(sleeper)))
        for sig in (signal.SIGTERM, signal.SIGINT):
            for stubborn_child in (False, True):
                with self.subTest(signal=sig.name, child_ignores_sigterm=stubborn_child):
                    mark = self.tmp / f"sleeper-{sig.name}-{stubborn_child}.pid"
                    child = self.tmp / f"child-{sig.name}-{stubborn_child}.pid"
                    env = {**os.environ, "SLEEPER_MARK": str(mark), "BROWSER_HARNESS_GRACE": "2",
                           "STUBBORN_CHILD": STUBBORN_CHILD}
                    if stubborn_child:
                        env["SLEEPER_CHILD_MARK"] = str(child)
                    proc = subprocess.Popen([sys.executable, str(driver)], env=env,
                                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    self.addCleanup(lambda p=proc: p.poll() is None and p.kill())
                    pids = [read_pid(mark)] + ([read_pid(child)] if stubborn_child else [])
                    for pid in pids:
                        self.addCleanup(kill, pid)
                    proc.send_signal(sig)
                    proc.wait(timeout=30)
                    for pid in pids:
                        self.assertTrue(wait_until(lambda: not alive(pid), 15),
                                        f"{pid} outlived its module")

    def test_a_stopped_runner_stops_the_whole_chain(self) -> None:
        sleeper = self.tmp / "sleeper.py"
        sleeper.write_text(SLEEPER)
        (self.tmp / "tests" / "test_browser_chain.py").write_text(
            HARNESS_MODULE.format(root=str(ROOT), out=str(self.tmp / "out"), sleeper=str(sleeper)))
        for sig in (signal.SIGTERM, signal.SIGINT):
            with self.subTest(signal=sig.name):
                mark = self.tmp / f"sleeper-{sig.name}.pid"
                child = self.tmp / f"child-{sig.name}.pid"
                proc = self.runner("chain", BROWSER_STOP_GRACE="3", SLEEPER_MARK=str(mark),
                                   SLEEPER_CHILD_MARK=str(child))
                pids = [read_pid(mark), read_pid(child)]
                for pid in pids:
                    self.addCleanup(kill, pid)
                proc.send_signal(sig)
                out, _ = proc.communicate(timeout=20)
                self.assertEqual(proc.returncode, 128 + sig, out)
                for pid in pids:
                    self.assertTrue(wait_until(lambda: not alive(pid), 10), f"{pid} outlived the runner")


if __name__ == "__main__":
    unittest.main()
