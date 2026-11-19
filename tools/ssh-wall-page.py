#!/usr/bin/env python3
"""Fill the Doorstep Ledger's generated blocks from a reviewed SSH wall snapshot.

  tools/ssh-wall-page.py SNAPSHOT.json [--page content/essays/crawler_chronicles/wall.md]

The snapshot is the reviewed `snapshot.json` from the private anubis-observations
repository (observations/<date>-ssh-wall/). It is copied, unchanged, to
data/ssh-wall/<since>_<until>.json, the page's own record; then every block in the
page between `<!-- ledger:NAME -->` and `<!-- /ledger:NAME -->` is rewritten. Prose
outside the blocks is the author's and is left as it is. Standard library only.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / 'content' / 'essays' / 'crawler_chronicles' / 'wall.md'
RECORDS = ROOT / 'data' / 'ssh-wall'
TOP_NETWORKS = 25
BLOCK = re.compile(r'(<!-- ledger:([a-z-]+) -->\n)(.*?)(<!-- /ledger:\2 -->)', re.S)
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
          'November', 'December']


def text(value):
    """Markdown-safe text: the characters Markdown acts on backslash-escaped, newlines flattened."""
    value = ' '.join(str(value).split())
    return re.sub(r'([\\`*_{}\[\]<>#+|~^$@!:=])', r'\\\1', value)


def prose(value):
    """A snapshot note as page text: ISO days written out."""
    return re.sub(r'\\?\b(\d{4})-(\d{2})-(\d{2})\b', lambda m: day(m[0].lstrip('\\')), text(value))


def code(value, title=None):
    """Inline code for a string the snapshot already limits to printable ASCII without backticks."""
    if '`' in value or not value.isprintable():
        raise ValueError(f'cannot show {value!r} as code')
    # The body text hyphenates (hyphens: auto); a username or version must not break inside.
    attr = f' title="{title}"' if title else ''
    return f'`{value}`{{style="hyphens: manual; white-space: nowrap"{attr}}}'


def number(n):
    return f'{n:,}'


def day(iso):
    y, m, d = (int(x) for x in iso.split('-'))
    return f'{MONTHS[m - 1]} {d}, {y}'


def flag(country):
    if country and re.fullmatch(r'[A-Z]{2}', country):
        return ''.join(chr(0x1F1E6 + ord(c) - ord('A')) for c in country) + ' ' + country
    return text(country or '—')


def network_name(row):
    if row.get('label'):
        return text(row['label'])
    if row.get('name'):
        return text(row.get('organization') or row['name'])
    return '*name withheld*'


def network_rows(rows):
    # The dashes set the columns' relative widths once a row is longer than Pandoc's 72 columns.
    out = ['| # | Network | AS | Country | Tries | Addresses |',
           '|---:|:--------------------|:--------|:------|-----:|------:|']
    for r in rows:
        note = f"^[{text(r['note'])}]" if r.get('note') else ''
        out.append(f"| {r['rank']} | {network_name(r)}{note} | [AS{r['asn']}](https://bgp.tools/as/{r['asn']}) "
                   f"| {flag(r['country'])} | {number(r['tried'])} | {number(r['addresses'])} |")
    # Phones scroll the table sideways instead of squeezing six columns into the text width.
    return '\n'.join(['::: {style="overflow-x: auto"}', '::: {style="min-width: 700px"}', *out, ':::', ':::'])


def blocks(snap, prose_text=''):
    t, other, period = snap['totals'], snap['other_networks'], snap['period']
    nets = snap['networks']
    since, until = day(period['since']), day(period['until'])
    plural = lambda n, one, many: f'{number(n)} {one if n == 1 else many}'
    out = {}
    out['totals'] = (f"From {since} to {until}: **{number(t['tried_username'])}** connections tried a username, "
                     f"from {number(t['addresses_tried'])} addresses in {plural(len(nets) + other['networks'], 'network', 'networks')}.")
    out['networks-top'] = network_rows(nets[:TOP_NETWORKS])
    rest = (f"Besides the {number(len(nets))} named networks, {plural(other['networks'], 'other network', 'other networks')} "
            f"with fewer than three addresses that tried made {number(other['tried'])} tries from "
            f"{number(other['addresses'])} addresses; they are counted together and not named.")
    if other.get('note'):
        rest += f" {text(other['note'])}"
    out['networks-all'] = '\n'.join([
        '<details class="ledger-all">', f'<summary>All {len(nets)} named networks</summary>', '',
        network_rows(nets), '', '</details>'])
    out['networks-rest'] = rest
    out['usernames'] = ' · '.join(code(u['username'], f"{number(u['sources'])} addresses") for u in snap['usernames'])
    out['software'] = ' · '.join(code(b['banner'], f"{number(b['sources'])} addresses") for b in snap['client_software'])
    coverage = [f'- The period is whole days in UTC, {since} to {until}.']
    # The page names no ports: the snapshot's notes about its own sources are said here in plain terms,
    # and a note the page's prose already makes is not repeated.
    backfill = snap['coverage'].get('sources', {}).get('backfill')
    if backfill:
        coverage.append(f"- Until {day(backfill['last_day'])} only the server's own SSH log was read: attempts on the "
                        f"git server's SSH, and connections that failed before a handshake, count from that day.")
    coverage += [f'- {prose(n)}' for n in snap['notes']
                 if n.rstrip('.') not in prose_text and not re.search(r'\bport \d+|sshd', n, re.I)]
    for run in snap['coverage']['empty_hour_runs']:
        hour, first = int(run['start'][11:13]), run['start'][:10]
        if first == period['since'] and hour == 0:
            coverage.append(f"- The records begin at {run['hours']:02d}:00 UTC on {day(first)}.")
        else:
            coverage.append(f"- No connections were recorded for {run['hours']} hours from {hour:02d}:00 UTC on {day(first)}.")
    table = snap.get('networks_table') or {}
    coverage.append(f"- Networks are origin ASes in the iptoasn.com table of {day(table['date'])}; the country is the AS's "
                    f"registration, not where an address is." if table.get('date') else
                    '- Networks are origin ASes; the country is the AS\'s registration, not where an address is.')
    coverage.append(f"- Snapshot taken {day(snap['generated'][:10])}.")
    out['coverage'] = '\n'.join(coverage)
    return out


def fill(page_text, values):
    seen = set()

    def replace(match):
        name = match[2]
        if name not in values:
            raise SystemExit(f'ssh-wall-page: unknown block {name!r} in the page')
        seen.add(name)
        return f'{match[1]}{values[name]}\n{match[4]}'

    result = BLOCK.sub(replace, page_text)
    if not seen:
        raise SystemExit('ssh-wall-page: the page has no ledger blocks')
    return result


def record(snapshot_path, records=RECORDS):
    raw = Path(snapshot_path).read_bytes()
    snap = json.loads(raw)
    if snap.get('kind') != 'ssh-wall-snapshot':
        raise SystemExit('ssh-wall-page: not an SSH wall snapshot')
    target = records / f"{snap['period']['since']}_{snap['period']['until']}.json"
    if target.exists() and hashlib.sha256(target.read_bytes()).digest() != hashlib.sha256(raw).digest():
        raise SystemExit(f'ssh-wall-page: {target.relative_to(ROOT) if target.is_relative_to(ROOT) else target} '
                         'already holds a different snapshot for this period')
    records.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    return snap, target


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('snapshot', type=Path)
    parser.add_argument('--page', type=Path, default=PAGE)
    args = parser.parse_args()
    snap, target = record(args.snapshot)
    current = args.page.read_text()
    outside = BLOCK.sub('', current)
    args.page.write_text(fill(current, blocks(snap, ' '.join(outside.split()))))
    print(f'ssh-wall-page: {target.name} recorded; {args.page} filled', file=sys.stderr)


if __name__ == '__main__':
    main()
