#!/usr/bin/env python3
"""Exploratory: bursts of declared-crawler successful GETs before Anubis, and their lag from the last push.

A burst is a run of 10-minute bins with at least 3 x max(median, 50) requests, Sep 27 to Oct 3 (UTC).
Chosen after seeing the Oct 1 11:40 burst; descriptive only. Writes results/declared-crawler-bursts.json.
"""
import csv
import datetime as dt
import gzip
import json
import statistics
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
UTC = dt.timezone.utc

rows = [r for r in csv.DictReader(gzip.open(HERE / 'data/minute-series.csv.gz', 'rt')) if r['minute_utc'] < '2026-10-04T00']
episodes = [dt.datetime.fromisoformat(e['time_utc'].replace('Z', '+00:00')) for e in csv.DictReader(open(HERE / 'data/publication-episodes.csv'))]
bins = Counter()
for r in rows:
    bins[r['minute_utc'][:15] + '0'] += int(r['w_get200_otherbot'])
keys = sorted(bins)
values = [bins[k] for k in keys]
median = statistics.median(values)
threshold = 3 * max(median, 50)
bursts, i = [], 0
while i < len(keys):
    if values[i] >= threshold:
        j = i
        while j < len(keys) and values[j] >= threshold:
            j += 1
        start = dt.datetime.fromisoformat(keys[i] + ':00+00:00')
        before = [e for e in episodes if e <= start]
        bursts.append({'start_utc': start.isoformat().replace('+00:00', 'Z'), 'minutes': 10 * (j - i),
                       'peak_per_10min': max(values[i:j]), 'requests': sum(values[i:j]),
                       'minutes_since_last_episode': round((start - max(before)).total_seconds() / 60) if before else None})
        i = j
    else:
        i += 1
out = {'note': __doc__.strip(), 'median_per_10min': median, 'threshold_per_10min': threshold, 'bursts': bursts}
(HERE / 'results/declared-crawler-bursts.json').write_text(json.dumps(out, indent=1) + '\n')
print(json.dumps(out, indent=1))
