#!/usr/bin/env python3
"""Preserve private crawl evidence and sample Anubis without restarting it."""

import argparse
import datetime as dt
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

UTC = dt.timezone.utc
DEFAULT_STATE = Path('/root/anubis-observations/live')


def iso(value=None):
    return (value or dt.datetime.now(UTC)).isoformat()


def atomic_json(path, value):
    temporary = path.with_suffix(path.suffix + '.new')
    with temporary.open('w') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def timestamp(line):
    try:
        return dt.datetime.fromisoformat(json.loads(line)['time'].replace('Z', '+00:00')).astimezone(UTC)
    except (ValueError, KeyError, TypeError):
        match = re.search(rb'\[([^]]+)\]', line)
        if match:
            try:
                return dt.datetime.strptime(match[1].decode(), '%d/%b/%Y:%H:%M:%S %z').astimezone(UTC)
            except ValueError:
                pass
    return None


def archive_file(source, state, manifest, kind):
    """One growing archive per original log, independent of rotation filename."""
    source = Path(source)
    stat = source.stat()
    signature = f'{stat.st_dev}:{stat.st_ino}:{stat.st_size}:{stat.st_mtime_ns}'
    if signature in manifest['cache']:
        return False
    opener = gzip.open if source.suffix == '.gz' else open
    with opener(source, 'rb') as incoming:
        first = incoming.readline()
        if not first:
            return False
        key = hashlib.sha256(kind.encode() + b'\0' + first).hexdigest()
        previous = manifest['archives'].get(key)
        destination = state / 'nginx' / (key + '.log.gz')
        digest, prefix = hashlib.sha256(), hashlib.sha256()
        count = 0
        tail = b''
        fd, name = tempfile.mkstemp(prefix='.capture-', dir=destination.parent)
        temporary = Path(name)
        try:
            with os.fdopen(fd, 'wb') as raw, gzip.GzipFile(fileobj=raw, mode='wb', filename='', mtime=0, compresslevel=1) as outgoing:
                chunk = first
                remaining = None if source.suffix == '.gz' else max(0, stat.st_size - len(first))
                while chunk:
                    digest.update(chunk)
                    if previous and count < previous['raw_bytes']:
                        prefix.update(chunk[:previous['raw_bytes'] - count])
                    count += len(chunk)
                    outgoing.write(chunk)
                    tail = (tail + chunk)[-65536:]
                    chunk = incoming.read(65536 if remaining is None else min(65536, remaining))
                    if remaining is not None:
                        remaining -= len(chunk)
            if previous and count < previous['raw_bytes']:
                # A shorter source must never erase the retained longer prefix.
                temporary.unlink()
                manifest['cache'][signature] = key
                return False
            if previous and prefix.hexdigest() != previous['raw_sha256']:
                raise RuntimeError(f'log prefix changed for {source}; retained evidence was not replaced')
            if previous and digest.hexdigest() == previous['raw_sha256']:
                temporary.unlink()
                manifest['cache'][signature] = key
                return False
            temporary.replace(destination)
            candidates = tail.splitlines()
            last_time = next((value for line in reversed(candidates) if (value := timestamp(line))), None)
            first_time = timestamp(first)
            entry = {
                'file': destination.name, 'kind': kind, 'raw_bytes': count,
                'compressed_bytes': destination.stat().st_size, 'raw_sha256': digest.hexdigest(),
                'first_time': iso(first_time) if first_time else None,
                'last_time': iso(last_time) if last_time else None,
                'captured_at': iso(),
                'sources': sorted(set((previous or {}).get('sources', []) + [str(source)])),
            }
            manifest['archives'][key] = entry
            manifest['cache'][signature] = key
            return True
        finally:
            temporary.unlink(missing_ok=True)


def counter_values(metrics):
    cumulative = set()
    for line in metrics.splitlines():
        if line.startswith('# TYPE '):
            _, _, name, kind = line.split()
            if kind == 'counter':
                cumulative.add(name)
            elif kind == 'histogram':
                cumulative.update(name + suffix for suffix in ('_bucket', '_sum', '_count'))
    values = {}
    for line in metrics.splitlines():
        if line.startswith(('anubis_', 'process_cpu_seconds_total')):
            try:
                key, value = line.rsplit(None, 1)
                if key.split('{', 1)[0] in cumulative:
                    values[key] = float(value)
            except ValueError:
                continue
    return values


def counter_delta(previous, current, same_process):
    """Never turn a process reset into negative rates or a guessed full interval."""
    if not same_process:
        return None
    return {key: value - previous[key] for key, value in current.items()
            if key in previous and value >= previous[key]}


def command(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=90).stdout


def collect(args):
    os.umask(0o077)
    state = args.state
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    state.chmod(0o700)
    for name in ('nginx', 'samples', 'events', 'config'):
        (state / name).mkdir(exist_ok=True, mode=0o700)
    with (state / 'lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('anubis-observe: another collection is running')
            return
        if shutil.disk_usage(state).free < args.min_free_gib * 1024 ** 3:
            raise RuntimeError('free space below collection floor; no retained data was deleted')
        started = time.time()
        manifest_path = state / 'manifest.json'
        manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {'schema': 1, 'archives': {}, 'cache': {}}
        previous_path = state / 'last-sample.json'
        previous = json.loads(previous_path.read_text()) if previous_path.exists() else {}
        now = dt.datetime.now(UTC)
        sample = {'schema': 1, 'time_utc': iso(now), 'unix_seconds': now.timestamp(), 'config': {}}
        for source in (Path('/root/anubis-server/policy.yaml'), Path('/root/anubis-server/docker-compose.yml'),
                       Path('/root/anubis-server/docker-compose.override.yml'),
                       Path('/etc/nginx/conf.d/access-log-format.conf')):
            if source.exists():
                contents = source.read_bytes()
                digest = hashlib.sha256(contents).hexdigest()
                target = state / 'config' / (source.name + '.' + digest)
                if not target.exists():
                    target.write_bytes(contents)
                sample['config'][str(source)] = digest
        inspected = json.loads(command('docker', 'inspect', 'anubis'))[0]
        sample['container'] = {
            'id': inspected['Id'], 'image_id': inspected['Image'], 'image': inspected['Config']['Image'],
            'started_at': inspected['State']['StartedAt'], 'status': inspected['State']['Status'],
            'health': inspected['State'].get('Health', {}).get('Status'), 'restarts': inspected['RestartCount'],
        }
        with urllib.request.urlopen('http://127.0.0.1:9091/metrics', timeout=10) as response:
            sample['metrics_prometheus'] = response.read().decode()
        sample['counters'] = counter_values(sample['metrics_prometheus'])
        same = (previous.get('container', {}).get('id') == sample['container']['id']
                and previous.get('container', {}).get('started_at') == sample['container']['started_at'])
        sample['same_process_as_previous'] = same
        sample['elapsed_seconds'] = now.timestamp() - previous['unix_seconds'] if previous else None
        sample['counter_delta'] = counter_delta(previous.get('counters', {}), sample['counters'], same)
        sample['config_changed'] = bool(previous) and previous.get('config') != sample['config']
        since = (dt.datetime.fromtimestamp(previous['unix_seconds'], UTC) - dt.timedelta(seconds=2)
                 if previous else now - dt.timedelta(hours=2))
        event_name = now.strftime('%Y%m%dT%H%M%S.%fZ') + '.jsonl.gz'
        proc = subprocess.run(['docker', 'logs', '--since', iso(since), 'anubis'],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True, timeout=60)
        with gzip.open(state / 'events' / event_name, 'wb', compresslevel=1) as stream:
            stream.write(proc.stdout)
        sample['events'] = {'file': event_name, 'requested_since': iso(since),
                            'overlap_seconds': 2, 'deduplicate_by': 'SHA-256 of the original JSON line',
                            'gap_possible': not previous or not same or sample['elapsed_seconds'] > 360,
                            'availability': 'Docker retention bounds apply; completeness is not guaranteed'}
        # Write cheap samples before larger log captures, so slow archival cannot lose counters.
        with gzip.open(state / 'samples' / (now.strftime('%Y-%m-%d') + '.jsonl.gz'), 'at', compresslevel=1) as stream:
            stream.write(json.dumps(sample, sort_keys=True) + '\n')
        atomic_json(previous_path, sample)

        hour = now.strftime('%Y-%m-%dT%H')
        active_due = args.force_archive or manifest.get('active_hour') != hour
        changed = 0
        patterns = (('forgejo.access.json.log*', 'forgejo'), ('site.access.json.log*', 'site'),
                    ('csp-report.log*', 'csp'), ('access.log.1', 'legacy'))
        current_signatures = set()
        for pattern, kind in patterns:
            for source in sorted(args.log_dir.glob(pattern)):
                st = source.stat()
                current_signatures.add(f'{st.st_dev}:{st.st_ino}:{st.st_size}:{st.st_mtime_ns}')
                if source.name.endswith('.log') and not active_due:
                    continue
                changed += archive_file(source, state, manifest, kind)
        manifest['cache'] = {key: value for key, value in manifest['cache'].items() if key in current_signatures}
        manifest['active_hour'] = hour
        manifest['last_archive_check'] = iso()
        atomic_json(manifest_path, manifest)
        if active_due:
            report = Path(__file__).with_name('anubis-traffic.py')
            if report.exists():
                subprocess.run([sys.executable, os.fspath(report), '--state', os.fspath(state), '--output', os.fspath(state / 'recent'),
                                '--lookback-hours', '72'], check=True, timeout=600)
        (state / 'last-success').touch(mode=0o600)
        print(f'anubis-observe: {changed} archives updated; {len(manifest["archives"])} retained; '
              f'{time.time() - started:.1f}s; process_continued={same}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, default=DEFAULT_STATE)
    parser.add_argument('--log-dir', type=Path, default=Path('/var/log/nginx'))
    parser.add_argument('--force-archive', action='store_true')
    parser.add_argument('--min-free-gib', type=float, default=2)
    collect(parser.parse_args())


if __name__ == '__main__':
    main()
