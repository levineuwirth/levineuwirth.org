#!/usr/bin/env python3
"""Recompute hourly forge aggregates from the private, deduplicated archive."""

import argparse
from collections import Counter
import csv
import datetime as dt
import gzip
import json
import os
from pathlib import Path
import re

UTC = dt.timezone.utc
CHECKS = ('anubis-update', 'anubis-d4-check', 'anubis-d4-deploy', 'anubis-d4-git-check',
          'anubis-d5-check', 'anubis-d5-deploy')
LEGACY = re.compile(r'^(\S+) \S+ \S+ \[([^]]+)\] "(\S+) ([^ ]*) [^"]*" (\d+) (\d+|-) "[^"]*" "([^"]*)"')


def instant(value):
    return dt.datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(UTC)


def parse(line, kind):
    if kind == 'legacy':
        match = LEGACY.search(line)
        if not match:
            raise ValueError('unrecognized combined log')
        ip, stamp, method, path, status, size, ua = match.groups()
        return {'time': dt.datetime.strptime(stamp, '%d/%b/%Y:%H:%M:%S %z').isoformat(),
                'remote_addr': ip, 'method': method, 'path': path.split('?', 1)[0],
                'status': int(status), 'bytes_sent': int(size) if size != '-' else 0, 'ua': ua}
    return json.loads(line)


def cohort(ua):
    ua = ua.lower()
    if re.search(r'meta-external|facebook|facebot|meta-webindexer', ua):
        return 'meta-declared'
    if 'amazonbot' in ua:
        return 'amazon-declared'
    if 'x11; linux x86_64' in ua and re.search(r'chrome/(150|155)\.', ua):
        return 'linux-chrome-150-155'
    if re.search(r'bot|crawler|spider', ua):
        return 'other-declared-crawler'
    return 'other'


def route(path):
    parts = path.split('/')
    if len(parts) > 2 and parts[1] == 'neuwirth' and parts[2]:
        endpoint = parts[3] if len(parts) > 3 and parts[3] else 'root'
        if len(parts) > 4 and parts[4] in ('commit', 'branch', 'tag'):
            endpoint += '/' + parts[4]
        return 'repository', parts[2].removesuffix('.git'), endpoint
    if 'pass-challenge' in path:
        return 'challenge-pass', '', 'pass-challenge'
    if path.startswith('/.within.website/'):
        return 'anubis', '', 'anubis'
    return 'other', '', 'other'


def phase(stamp):
    if stamp < PHASE_TIMES[0]:
        return 'before-anubis'
    if stamp < PHASE_TIMES[1]:
        return 'anubis-deployment-day-mixed'
    if stamp < PHASE_TIMES[2]:
        return 'difficulty-2'
    if stamp < PHASE_TIMES[3]:
        return 'd4-cookie-transition'
    if stamp < PHASE_TIMES[4]:
        return 'after-d4-cookie-fix'
    if stamp < PHASE_TIMES[5]:
        return 'd5-deployment-transition'
    return 'difficulty-5'


PHASE_TIMES = [instant(value) for value in ('2026-10-04T00:00:00Z', '2026-10-05T00:00:00Z',
                                          '2026-10-14T20:14:05.044611Z', '2026-10-14T20:45:23.046673Z',
                                          '2026-10-16T09:49:23.860856Z', '2026-10-16T09:49:25.521649Z')]


def write_csv(path, fields, rows):
    temporary = path.with_suffix('.csv.new')
    with temporary.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def analyze(state, output, since, until, include_checks=False):
    os.umask(0o077)
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    manifest = json.loads((state / 'manifest.json').read_text())
    json_first = min((instant(e['first_time']) for e in manifest['archives'].values()
                      if e['kind'] == 'forgejo' and e.get('first_time')), default=until)
    counts, summary = {}, {}
    seen, diagnostics, sources = set(), Counter(), []
    bounds = []
    for entry in manifest['archives'].values():
        if entry['kind'] not in ('forgejo', 'legacy'):
            continue
        first = instant(entry['first_time']) if entry.get('first_time') else None
        last = instant(entry['last_time']) if entry.get('last_time') else None
        if first and last:
            bounds.append((first, last))
            # A margin avoids losing requests whose completion ordering differs slightly.
            if last < since - dt.timedelta(hours=1) or first >= until + dt.timedelta(hours=1):
                continue
        sources.append({k: entry[k] for k in ('file', 'kind', 'raw_sha256', 'first_time', 'last_time')})
        with gzip.open(state / 'nginx' / entry['file'], 'rt', errors='replace') as stream:
            for line in stream:
                try:
                    row = parse(line, entry['kind'])
                    stamp = (dt.datetime.fromtimestamp(float(row['time_unix']), UTC)
                             if 'time_unix' in row else instant(row['time']))
                    if not since <= stamp < until:
                        continue
                    scope, repo, endpoint = route(row['path'])
                    # Old logs mix hosts; only repository routes can be assigned to the forge.
                    # JSON forge logging began on Oct 3; exclude legacy overlap after that cutover.
                    if entry['kind'] == 'legacy' and (scope != 'repository' or stamp >= json_first):
                        continue
                    ua = row.get('ua', '')
                    if not include_checks and any(check in ua.lower() for check in CHECKS):
                        diagnostics['excluded_check_requests'] += 1
                        continue
                    request_id = row.get('request_id')
                    if request_id:
                        if request_id in seen:
                            diagnostics['duplicate_request_ids'] += 1
                            continue
                        seen.add(request_id)
                    hour = stamp.replace(minute=0, second=0, microsecond=0).isoformat()
                    group, status = cohort(ua), int(row['status'])
                    basis = 'body-only' if entry['kind'] == 'legacy' else 'including-headers'
                    key = (hour, phase(stamp), group, scope, repo, endpoint, row.get('method', ''), status, basis)
                    cell = counts.setdefault(key, {'requests': 0, 'bytes_sent': 0, 'ips': set(),
                                                  'latency_n': 0, 'latency_sum_seconds': 0.0})
                    cell['requests'] += 1
                    cell['bytes_sent'] += int(row.get('bytes_sent', 0))
                    if row.get('remote_addr'):
                        cell['ips'].add(row['remote_addr'])
                    if row.get('request_time') not in (None, ''):
                        cell['latency_n'] += 1
                        cell['latency_sum_seconds'] += float(row['request_time'])
                    if scope == 'repository':
                        for label in ('all', group):
                            total = summary.setdefault((hour, label), {'requests': 0, 'http200': 0, 'http403': 0, 'ips': set()})
                            total['requests'] += 1
                            total['http200'] += status == 200
                            total['http403'] += status == 403
                            if row.get('remote_addr'):
                                total['ips'].add(row['remote_addr'])
                    diagnostics['included_requests'] += 1
                except (ValueError, KeyError, TypeError, OverflowError):
                    diagnostics['malformed_records'] += 1
                    diagnostics['malformed_' + entry['kind']] += 1
    dimensions = ['hour_utc', 'historical_phase', 'cohort', 'scope', 'repository', 'endpoint', 'method', 'status', 'bytes_basis']
    rows = []
    for key, cell in sorted(counts.items()):
        value = {**dict(zip(dimensions, key)), **{k: v for k, v in cell.items() if k != 'ips'},
                 'unique_ips': len(cell['ips']), 'weekday_utc': instant(key[0]).strftime('%A'),
                 'window_seconds': max(0, (min(until, instant(key[0]) + dt.timedelta(hours=1)) - max(since, instant(key[0]))).total_seconds())}
        rows.append(value)
    write_csv(output / 'hourly.csv', dimensions + ['weekday_utc', 'window_seconds', 'requests', 'bytes_sent',
              'unique_ips', 'latency_n', 'latency_sum_seconds'], rows)
    summary_rows = [dict(hour_utc=h, cohort=c, **{k: v for k, v in cell.items() if k != 'ips'}, unique_ips=len(cell['ips']))
                    for (h, c), cell in sorted(summary.items())]
    write_csv(output / 'hourly-summary.csv', ['hour_utc', 'cohort', 'requests', 'http200', 'http403', 'unique_ips'], summary_rows)
    metadata = {
        'schema': 1, 'generated_at': dt.datetime.now(UTC).isoformat(), 'since_inclusive': since.isoformat(),
        'until_exclusive': until.isoformat(), 'include_checks': include_checks, 'sources': sources,
        'diagnostics': dict(diagnostics), 'retained_log_spans': [[a.isoformat(), b.isoformat()] for a, b in sorted(bounds)],
        'notes': [
            'Sparse rows: absent hours are not certified zero-traffic hours. Log spans do not prove uptime.',
            'window_seconds is the requested hour intersection, not verified logging exposure or phase exposure.',
            'Unique IPs cannot be summed across cells. Request timestamps are completion times.',
            'Cohorts are user-agent claims, not verified identities. Raw UA, paths and addresses remain in private logs.',
            'historical_phase annotates known October changes; future policy state is recorded in five-minute config hashes.',
            'Counts are correlated and nonstationary; do not treat requests as independent experimental replicates.',
            'Malformed-record counts include selected source files outside the requested time window when timestamps could not be parsed.',
            'Legacy records at or after the first forge JSON second are omitted to avoid overlap; the cutover second is ambiguous at old timestamp precision.',
        ],
    }
    (output / 'metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(json.dumps({'output': str(output), 'cells': len(rows), **diagnostics}))
    return rows, summary_rows, metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, default=Path('/root/anubis-observations/live'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--lookback-hours', type=int, default=72)
    parser.add_argument('--since', type=instant)
    parser.add_argument('--until', type=instant)
    parser.add_argument('--include-checks', action='store_true')
    args = parser.parse_args()
    until = args.until or dt.datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    since = args.since or until - dt.timedelta(hours=args.lookback_hours)
    if since >= until:
        parser.error('--since must precede --until')
    analyze(args.state, args.output, since, until, args.include_checks)


if __name__ == '__main__':
    main()
