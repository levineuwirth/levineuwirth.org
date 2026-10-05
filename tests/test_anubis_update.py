"""Stateful failure rehearsals; no real Docker, services, or network."""
import fcntl
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from tests._helpers import load_tool

update = load_tool("anubis-update.py")
OLD = update.REGISTRY + ':v1.27.0@sha256:' + 'a' * 64
NEW = update.REGISTRY + ':v1.28.0@sha256:' + 'b' * 64


class Fake(update.Updater):
    def __init__(self):
        super().__init__()
        self.calls = []
        self.current = 'old'
        self.mode = 'success'
        self.selected = OLD
        self.state_checks = 0

    def command(self, *args, **kw):
        self.calls.append(args)
        if args[:3] == ('docker', 'image', 'inspect'):
            return json.dumps([{'Id': 'old'}])
        if args[0] == 'cp':
            return super().command(*args, **kw)
        return ''

    def inspect(self):
        self.state_checks += 1
        count = self.state_checks if self.mode == 'crashloop' else 0
        return {'Image': self.current, 'State': {'Status': 'running', 'Restarting': False,
                'StartedAt': 'start'}, 'RestartCount': count}

    def compose(self, *args):
        self.calls.append(('compose', *args))
        if args[0] == 'config':
            return json.dumps({'services': {'anubis': {'container_name': 'anubis', 'image': self.selected}}})
        if args[0] == 'up':
            self.current = 'old' if self.selected == OLD else 'new'
            if self.current == 'new':
                (self.directory / 'state/anubis.bdb').write_text('new format')
                if self.mode == 'interrupted':
                    # Simulate SIGKILL: bypass run's rollback and leave persisted state.
                    raise SystemExit('kill')

    def select(self, reference):
        super().select(reference)
        self.selected = reference

    def candidate(self, before):
        if self.mode == 'network':
            raise OSError('network unavailable')
        return (OLD, 'old') if self.mode.startswith('unchanged') else (NEW, 'new')

    def backup(self):
        self.calls.append(('backup',))
        if self.mode == 'backup':
            raise RuntimeError('backup failed')

    def healthy(self, image):
        self.calls.append(('healthy', image))
        if image == 'new' and self.mode in ('bad', 'rollback-fails'):
            raise RuntimeError('bad candidate')
        if self.mode == 'rollback-fails' and self.selected == OLD and self.journal.exists():
            raise RuntimeError('rollback failed')
        if self.mode == 'unchanged-down' and len([c for c in self.calls if c[0] == 'healthy']) > 1:
            raise RuntimeError('stopped after pulling')


class Recovery(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        env = patch.dict(os.environ, DIR=str(self.root), UPDATE_STATE=str(self.root / 'update'), STABLE='0', WAIT='0')
        env.start()
        self.addCleanup(env.stop)
        (self.root / 'state').mkdir()
        (self.root / 'state/anubis.bdb').write_text('old cookies')
        self.up = Fake()

    def test_success_persists_the_resolved_pin(self):
        self.up.run()
        self.assertEqual(json.loads(self.up.override.read_text())['services']['anubis']['image'], NEW)
        self.assertFalse(self.up.journal.exists())
        self.assertFalse(self.up.hold.exists())
        self.assertEqual((self.up.saved / 'anubis.bdb').read_text(), 'old cookies')

    def test_failed_candidate_restores_image_and_state_and_is_held(self):
        self.up.mode = 'bad'
        with self.assertRaisesRegex(RuntimeError, 'bad candidate'):
            self.up.run()
        self.assertEqual(self.up.current, 'old')
        self.assertEqual((self.root / 'state/anubis.bdb').read_text(), 'old cookies')
        self.assertFalse(self.up.journal.exists())
        self.assertTrue(self.up.hold.exists())
        with self.assertRaisesRegex(RuntimeError, 'on hold'):
            self.up.run()
        self.assertEqual(self.up.calls.count(('backup',)), 1)

    def test_failure_to_restore_remains_sticky(self):
        self.up.mode = 'rollback-fails'
        with self.assertRaisesRegex(RuntimeError, 'rollback failed'):
            self.up.run()
        self.assertTrue(self.up.journal.exists())
        self.assertTrue(self.up.attention.exists())
        self.up.mode = 'success'
        with self.assertRaisesRegex(RuntimeError, 'operator'):
            self.up.run()

    def test_interrupted_update_recovers_from_persisted_journal(self):
        # Simulate death after replacement: no Python exception handler ran.
        original_recover = self.up.recover
        self.up.recover = lambda pending: None
        self.up.mode = 'interrupted'
        with self.assertRaises(SystemExit):
            self.up.run()
        self.assertTrue(self.up.journal.exists())
        self.up.recover = original_recover
        self.up.mode = 'success'
        with self.assertRaisesRegex(RuntimeError, 'recovered an interrupted'):
            self.up.run()
        self.assertEqual(self.up.current, 'old')
        self.assertEqual((self.root / 'state/anubis.bdb').read_text(), 'old cookies')
        self.assertTrue(self.up.hold.exists())

    def test_backup_or_network_failure_never_stops_service(self):
        for mode in ('backup', 'network'):
            self.up.mode = mode
            with self.assertRaises((RuntimeError, OSError)):
                self.up.run()
            self.assertNotIn(('compose', 'stop', 'anubis'), self.up.calls)
            self.assertFalse(self.up.journal.exists())

    def test_unchanged_still_checks_health_after_pull(self):
        self.up.mode = 'unchanged-down'
        with self.assertRaisesRegex(RuntimeError, 'stopped after pulling'):
            self.up.run()
        self.assertNotIn(('compose', 'stop', 'anubis'), self.up.calls)

    def test_crashloop_during_stability_window_is_rejected(self):
        self.up.mode = 'crashloop'
        self.up.stable = 1
        self.up.interval = .001
        self.up.probe = lambda: None
        with self.assertRaisesRegex(RuntimeError, 'restarted'):
            update.Updater.healthy(self.up, 'old')

    def test_changed_compose_does_not_silently_replace_running_image(self):
        self.up.current = 'unexpected'
        with self.assertRaisesRegex(RuntimeError, 'differs from Compose'):
            self.up.run()
        self.assertNotIn(('backup',), self.up.calls)

    def test_stable_release_only_and_no_injected_image_names(self):
        self.assertEqual(update.release_tag({'tag_name': 'v1.28.1'}), 'v1.28.1')
        for data in ({'tag_name': 'v2.0.0'}, {'tag_name': 'v1.28.0', 'prerelease': True},
                     {'tag_name': 'v1.28.0', 'draft': True}, {'tag_name': 'v1.28.0;echo bad'}, {}):
            with self.assertRaises(RuntimeError):
                update.release_tag(data)



class StackLock(unittest.TestCase):
    """One update of the git stack at a time, shared with forgejo-update.sh:
    the probes go through Anubis to the forge, so a forge being recreated
    would fail them and a good image would be rolled back and held."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.stack = self.root / 'stack.lock'
        env = patch.dict(os.environ, DIR=str(self.root), UPDATE_STATE=str(self.root / 'update'),
                         STACK_LOCK=str(self.stack), STACK_WAIT='0.5')
        env.start()
        self.addCleanup(env.stop)
        self.ran = []
        run = patch.object(update.Updater, 'run', lambda _self: self.ran.append(True))
        run.start()
        self.addCleanup(run.stop)

    def hold(self, path):
        stream = open(path, 'w')
        self.addCleanup(stream.close)
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return stream

    def test_gives_up_while_the_forge_is_being_updated(self):
        self.hold(self.stack)
        with self.assertRaisesRegex(RuntimeError, 'still being updated after 0.5s'):
            update.main()
        self.assertEqual(self.ran, [])

    def test_proceeds_once_the_forge_update_finishes(self):
        held = self.hold(self.stack)
        threading.Timer(0.2, held.close).start()
        with patch.dict(os.environ, STACK_WAIT='10'):
            update.main()
        self.assertEqual(self.ran, [True])

    def test_a_second_anubis_run_is_refused_at_once(self):
        (self.root / 'update').mkdir(mode=0o700)
        self.hold(self.root / 'update' / 'lock')
        with self.assertRaisesRegex(RuntimeError, 'another update is running'):
            update.main()
        self.assertEqual(self.ran, [])


if __name__ == '__main__':
    unittest.main()
