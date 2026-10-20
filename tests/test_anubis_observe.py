"""Evidence preservation, rotation, reset and time-binning regressions."""
import contextlib
import gzip
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), ROOT / 'tools' / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


observe = module('anubis-observe')
traffic = module('anubis-traffic')


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'nginx').mkdir()
        self.manifest = {'archives': {}, 'cache': {}}
        self.source = self.root / 'forgejo.access.json.log'

    def line(self, stamp='2026-10-13T23:01:02+00:00', identity='one', **kwargs):
        return json.dumps({'time': stamp, 'request_id': identity, 'path': '/neuwirth/pmacs/src/commit/abc/a',
                           'remote_addr': '192.0.2.1', 'status': 200, 'bytes_sent': 100,
                           'method': 'GET', 'request_time': 0.1,
                           'ua': 'Mozilla/5.0 (X11; Linux x86_64) Chrome/155.0', **kwargs}) + '\n'

    def archive(self):
        return observe.archive_file(self.source, self.root, self.manifest, 'forgejo')

    def test_append_rotation_and_gzip_are_one_archive(self):
        self.source.write_text(self.line())
        self.assertTrue(self.archive())
        self.assertFalse(self.archive())
        with self.source.open('a') as stream:
            stream.write(self.line(identity='two'))
        self.assertTrue(self.archive())
        rotated = self.source.with_name(self.source.name + '.1.gz')
        with gzip.open(rotated, 'wb') as stream:
            stream.write(self.source.read_bytes())
        self.assertFalse(observe.archive_file(rotated, self.root, self.manifest, 'forgejo'))
        self.assertEqual(len(self.manifest['archives']), 1)
        archive = next(iter(self.manifest['archives'].values()))
        self.assertEqual(gzip.decompress((self.root / 'nginx' / archive['file']).read_bytes()).decode(), self.source.read_text())
        self.source.write_text(self.line(identity='new-day'))
        self.assertTrue(self.archive())
        self.assertEqual(len(self.manifest['archives']), 2)

    def test_changed_prefix_cannot_replace_retained_evidence(self):
        first = self.line()
        self.source.write_text(first + self.line(identity='two'))
        self.archive()
        before = list((self.root / 'nginx').glob('*'))[0].read_bytes()
        self.source.write_text(first + self.line(identity='BAD') + self.line(identity='three'))
        with self.assertRaisesRegex(RuntimeError, 'prefix changed'):
            self.archive()
        self.assertEqual(list((self.root / 'nginx').glob('*'))[0].read_bytes(), before)

    def test_shorter_source_never_erases_longer_archive(self):
        self.source.write_text(self.line() + self.line(identity='two'))
        self.archive()
        size = next(iter(self.manifest['archives'].values()))['raw_bytes']
        self.source.write_text(self.line())
        self.assertFalse(self.archive())
        self.assertEqual(next(iter(self.manifest['archives'].values()))['raw_bytes'], size)

    def test_restart_and_decreasing_counters_not_interpreted_as_rates(self):
        self.assertIsNone(observe.counter_delta({'a': 100}, {'a': 4}, False))
        self.assertEqual(observe.counter_delta({'a': 100, 'b': 2}, {'a': 4, 'b': 5}, True), {'b': 3})

    def test_metric_types_exclude_gauges_from_deltas(self):
        metrics = '# TYPE anubis_issued counter\nanubis_issued{rule="x"} 3\n# TYPE anubis_live gauge\nanubis_live 8\n# TYPE anubis_latency histogram\nanubis_latency_count 7\nanubis_latency_sum 2.4\n'
        self.assertEqual(observe.counter_values(metrics), {'anubis_issued{rule="x"}': 3.0,
                         'anubis_latency_count': 7.0, 'anubis_latency_sum': 2.4})

    def test_hourly_dedup_exclusions_unique_ips_and_sparse_coverage(self):
        self.source.write_text(self.line() + self.line() + self.line(identity='two') +
                               self.line(identity='check', ua='levineuwirth-anubis-d4-check') +
                               self.line('2026-10-14T00:01:00Z', identity='outside'))
        self.archive()
        (self.root / 'manifest.json').write_text(json.dumps(self.manifest))
        with contextlib.redirect_stdout(io.StringIO()):
            rows, summary, metadata = traffic.analyze(self.root, self.root / 'out',
                traffic.instant('2026-10-13T00:00:00Z'), traffic.instant('2026-10-14T00:00:00Z'))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['requests'], 2)
        self.assertEqual(rows[0]['unique_ips'], 1)
        self.assertEqual(rows[0]['hour_utc'], '2026-10-13T23:00:00+00:00')
        self.assertEqual(metadata['diagnostics']['duplicate_request_ids'], 1)
        self.assertEqual(metadata['diagnostics']['excluded_check_requests'], 1)
        self.assertEqual([r['http200'] for r in summary], [2, 2])

    def test_utc_normalization_and_cutover(self):
        self.assertEqual(traffic.instant('2026-10-14T01:12:00+02:00').hour, 23)
        self.assertEqual(traffic.phase(traffic.instant('2026-10-14T20:14:05Z')), 'difficulty-2')
        self.assertEqual(traffic.phase(traffic.instant('2026-10-14T20:14:06Z')), 'd4-cookie-transition')
        self.assertEqual(traffic.phase(traffic.instant('2026-10-14T20:45:24Z')), 'after-d4-cookie-fix')

    def test_millisecond_timestamp_wins_at_hour_boundary(self):
        self.source.write_text(self.line('2026-10-13T22:59:59Z', time_unix=traffic.instant('2026-10-13T23:00:00Z').timestamp() + .123))
        self.archive()
        (self.root / 'manifest.json').write_text(json.dumps(self.manifest))
        with contextlib.redirect_stdout(io.StringIO()):
            rows, _, _ = traffic.analyze(self.root, self.root / 'out', traffic.instant('2026-10-13T00:00:00Z'),
                                          traffic.instant('2026-10-14T00:00:00Z'))
        self.assertEqual(rows[0]['hour_utc'], '2026-10-13T23:00:00+00:00')

    def test_difficulty_five_transition_and_fresh_browser_probe_exclusion(self):
        self.assertEqual(traffic.phase(traffic.instant('2026-10-16T09:49:23.860855Z')), 'after-d4-cookie-fix')
        self.assertEqual(traffic.phase(traffic.instant('2026-10-16T09:49:23.860856Z')), 'd5-deployment-transition')
        self.assertEqual(traffic.phase(traffic.instant('2026-10-16T09:49:25.521649Z')), 'difficulty-5')
        self.source.write_text(self.line('2026-10-16T09:50:00Z', ua='Mozilla Chrome/155.0 levineuwirth-anubis-d5-check/2026-10-16'))
        self.archive()
        (self.root / 'manifest.json').write_text(json.dumps(self.manifest))
        with contextlib.redirect_stdout(io.StringIO()):
            rows, _, metadata = traffic.analyze(self.root, self.root / 'out', traffic.instant('2026-10-16T09:00:00Z'),
                                                 traffic.instant('2026-10-16T10:00:00Z'))
        self.assertEqual(rows, [])
        self.assertEqual(metadata['diagnostics']['excluded_check_requests'], 1)

    def test_legacy_parse_does_not_keep_query(self):
        row = traffic.parse('192.0.2.1 - - [01/Oct/2026:01:20:30 +0200] "GET /neuwirth/a?secret=1 HTTP/1.1" 200 20 "-" "test"', 'legacy')
        self.assertEqual(row['path'], '/neuwirth/a')
        self.assertEqual(traffic.instant(row['time']).isoformat(), '2026-09-30T23:20:30+00:00')


if __name__ == '__main__':
    unittest.main()
