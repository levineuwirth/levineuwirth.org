"""The Doorstep Ledger's generator: escaping, flags, block filling and the snapshot record."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ssh_wall_page', ROOT / 'tools' / 'ssh-wall-page.py')
page = importlib.util.module_from_spec(spec)
spec.loader.exec_module(page)

SNAPSHOT = {
    'kind': 'ssh-wall-snapshot', 'generated': '2026-11-19T21:35:51.000000+00:00',
    'period': {'since': '2026-10-17', 'until': '2026-11-18'},
    'totals': {'tried_username': 1200, 'addresses_tried': 40, 'tried_by_port': {'22': 1000, '2222': 200}},
    'networks': [{'rank': 1, 'asn': 64500, 'name': 'EX-AS Example | Hosting *Ltd*', 'organization': 'Example | Hosting *Ltd*',
                  'country': 'NL', 'tried': 900, 'addresses': 30},
                 {'rank': 2, 'asn': 64501, 'name': None, 'organization': None, 'name_withheld': 'person-like',
                  'country': 'RU', 'tried': 200, 'addresses': 4},
                 {'rank': 3, 'asn': 64502, 'name': 'X - No.1 Street', 'organization': 'No.1 Street', 'label': 'Example Telecom',
                  'note': 'Relabeled [registry]', 'country': '', 'tried': 50, 'addresses': 3}],
    'other_networks': {'networks': 7, 'tried': 50, 'addresses': 3},
    'usernames': [{'username': 'root', 'sources': 30}, {'username': 'levineuwirth', 'sources': 3}],
    'client_software': [{'banner': 'SSH-2.0-Go', 'sources': 12}],
    'notes': ['Port 2222 is counted from 2026-10-23.', 'A note of the author.'],
    'coverage': {'sources': {'backfill': {'first_day': '2026-10-17', 'last_day': '2026-10-23'}}, 'empty_hour_runs': [{'start': '2026-10-17T00', 'hours': 16}, {'start': '2026-11-02T05', 'hours': 2}]},
    'networks_table': {'date': '2026-11-19'},
}


class LedgerTests(unittest.TestCase):
    def test_blocks_escape_names_and_render_rows(self):
        out = page.blocks(SNAPSHOT)
        self.assertIn('| 1 | Example \\| Hosting \\*Ltd\\* | [AS64500](https://bgp.tools/as/64500) | 🇳🇱 NL | 900 | 30 |',
                      out['networks-top'])
        self.assertIn('| 2 | *name withheld* |', out['networks-top'])
        self.assertIn('Example Telecom^[Relabeled \\[registry\\]]', out['networks-top'])
        self.assertIn('| — |', out['networks-top'])
        self.assertIn('<summary>All 3 named networks</summary>', out['networks-all'])
        self.assertIn('Besides the 3 named networks, 7 other networks', out['networks-rest'])
        self.assertEqual(out['usernames'].split(' · ')[0], '`root`{style="hyphens: manual; white-space: nowrap" title="30 addresses"}')
        self.assertNotIn('A note of', page.blocks(SNAPSHOT, 'A note of the author here')['coverage'])
        self.assertNotIn('2222', out['coverage'] + out['totals'])
        self.assertIn('Until October 23, 2026 only the server', out['coverage'])
        self.assertIn('- A note of the author.', out['coverage'])
        self.assertIn('The records begin at 16:00 UTC on October 17, 2026.', out['coverage'])
        self.assertIn('No connections were recorded for 2 hours from 05:00 UTC on November 2, 2026.', out['coverage'])
        self.assertIn('**1,200** connections tried a username', out['totals'])

    def test_fill_keeps_prose_and_refuses_unknown_blocks(self):
        text = 'Intro.\n\n<!-- ledger:totals -->\nold\n<!-- /ledger:totals -->\n\nOutro.\n'
        filled = page.fill(text, {'totals': 'new'})
        self.assertEqual(filled, 'Intro.\n\n<!-- ledger:totals -->\nnew\n<!-- /ledger:totals -->\n\nOutro.\n')
        self.assertEqual(page.fill(filled, {'totals': 'new'}), filled)
        with self.assertRaises(SystemExit):
            page.fill('<!-- ledger:other -->\n<!-- /ledger:other -->', {'totals': 'x'})
        with self.assertRaises(SystemExit):
            page.fill('no blocks', {'totals': 'x'})

    def test_code_refuses_backticks(self):
        with self.assertRaises(ValueError):
            page.code('a`b')

    def test_record_is_written_once_per_period(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'snapshot.json'
            source.write_text(json.dumps(SNAPSHOT))
            _, target = page.record(source, root / 'records')
            self.assertEqual(target.name, '2026-10-17_2026-11-18.json')
            page.record(source, root / 'records')  # the same snapshot again is fine
            source.write_text(json.dumps({**SNAPSHOT, 'generated': 'later'}))
            with self.assertRaises(SystemExit):
                page.record(source, root / 'records')
            source.write_text(json.dumps({'kind': 'other'}))
            with self.assertRaises(SystemExit):
                page.record(source, root / 'elsewhere')


if __name__ == '__main__':
    unittest.main()
