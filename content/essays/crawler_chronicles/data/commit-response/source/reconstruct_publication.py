#!/usr/bin/env python3
"""Reconstruct first Forgejo publication of every website commit.

Input: data/publication-snapshot.json (source/collect_publication.py, run on
the VPS) and data/github-push-events.json. Output: data/publication-episodes.csv,
data/commit-publication.csv and data/publication-audit.json. Standard library only.

Publication is processed chronologically over every ref: a commit is first
public at the first ref transaction that makes it reachable, whichever ref that
was. Reflogs give transaction seconds; a push without a retained reflog uses its
notification second, which lags the transaction by 0 to 20 s.
"""
import csv
import datetime as dt
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
UTC = dt.timezone.utc
ZERO = '0' * 40
NOTIFICATION_LAG = (0, 20)          # observed notification minus reflog second, seconds
MATCH_SECONDS = 30
JSON_LOG_START = 1791067375         # 2026-10-03T22:42:55Z, first forge JSON record
PHASES = [(None, 1791072000, 'before-anubis'), (1791072000, 1791158400, 'anubis-deployment-day'),
          (1791158400, 1792008845.044611, 'difficulty-2'), (1792008845.044611, 1792010723.046673, 'd4-cookie-transition'),
          (1792010723.046673, 1792144163.860856, 'after-d4-cookie-fix'),
          (1792144163.860856, 1792144165.521649, 'd5-transition'), (1792144165.521649, None, 'difficulty-5')]


def iso(t):
    return dt.datetime.fromtimestamp(t, UTC).isoformat().replace('+00:00', 'Z')


def phase(t):
    for lo, hi, name in PHASES:
        if (lo is None or t >= lo) and (hi is None or t < hi):
            return name


def ancestors(commits, tip):
    seen, stack = set(), [tip]
    while stack:
        sha = stack.pop()
        if sha in seen or sha not in commits:
            continue
        seen.add(sha)
        stack.extend(commits[sha]['parents'])
    return seen


def main():
    snap = json.loads((HERE / 'data/publication-snapshot.json').read_text())
    github = json.loads((HERE / 'data/github-push-events.json').read_text())['events']
    commits = snap['commits']
    pushes = [a for a in snap['actions'] if a['op_type'] == 5 and a.get('compare_new')]
    deletions = [a for a in snap['actions'] if a['op_type'] == 17]
    creations = [a for a in snap['actions'] if a['op_type'] == 5 and not a['content_present']]
    reflog_start = min(r['time_unix'] for r in snap['reflogs'])

    # HEAD's reflog in a bare Forgejo repository mirrors the default branch.
    heads = [r for r in snap['reflogs'] if r['ref'].startswith('refs/heads/')]
    head_log = sorted((r['time_unix'], r['old'], r['new']) for r in snap['reflogs'] if r['ref'] == 'HEAD')
    main_log = sorted((r['time_unix'], r['old'], r['new']) for r in heads if r['ref'] == 'refs/heads/main')
    audit = {'head_reflog_mirrors_main': head_log == main_log, 'reflog_start': iso(reflog_start)}

    transactions, used = [], set()
    for r in heads:
        ref = 'refs/heads/' + r['ref'].removeprefix('refs/heads/')
        match = [a for a in pushes if a['ref'] == ref and a['compare_new'] == r['new']
                 and abs(a['time_unix'] - r['time_unix']) <= MATCH_SECONDS]
        chosen = min(match, key=lambda a: abs(a['time_unix'] - r['time_unix'])) if match else None
        if chosen:
            used.add(chosen['id'])
        transactions.append({'ref': ref, 'old': r['old'], 'new': r['new'], 'time': r['time_unix'],
                             'time_lo': r['time_unix'], 'time_hi': r['time_unix'], 'source': 'reflog',
                             'action_id': chosen['id'] if chosen else None,
                             'notification_lag': chosen['time_unix'] - r['time_unix'] if chosen else None,
                             'reported_len': chosen['reported_len'] if chosen else None})
    unmatched = [a for a in pushes if a['id'] not in used]
    for a in unmatched:
        in_graph = a['compare_new'] in commits
        if a['time_unix'] < reflog_start and not in_graph:
            continue                  # rewritten history: object no longer exists
        source = 'notification-before-reflogs' if a['time_unix'] < reflog_start else 'notification-unmatched'
        transactions.append({'ref': a['ref'], 'old': a['compare_old'], 'new': a['compare_new'], 'time': a['time_unix'],
                             'time_lo': a['time_unix'] - NOTIFICATION_LAG[1], 'time_hi': a['time_unix'] - NOTIFICATION_LAG[0],
                             'source': source, 'action_id': a['id'], 'notification_lag': None,
                             'reported_len': a['reported_len']})
    audit['pre_reflog_notifications'] = sum(a['time_unix'] < reflog_start for a in pushes)
    audit['pre_reflog_notifications_absent_from_graph'] = sum(a['time_unix'] < reflog_start and a['compare_new'] not in commits for a in pushes)
    audit['unmatched_notifications_after_reflog_start'] = [
        {'id': a['id'], 'ref': a['ref'], 'time': iso(a['time_unix']), 'reported_len': a['reported_len'],
         'old': a['compare_old'], 'new': a['compare_new']} for a in unmatched if a['time_unix'] >= reflog_start]
    audit['reflog_updates_without_notification'] = [t['ref'] + '@' + iso(t['time']) for t in transactions
                                                      if t['source'] == 'reflog' and t['action_id'] is None]
    lags = sorted(t['notification_lag'] for t in transactions if t['notification_lag'] is not None)
    audit['notification_lag_seconds'] = {'n': len(lags), 'min': lags[0], 'median': lags[len(lags) // 2], 'max': lags[-1]}
    audit['branch_creation_notifications'] = [{'id': a['id'], 'ref': a['ref'], 'time': iso(a['time_unix'])} for a in creations]
    audit['branch_deletions'] = [{'id': a['id'], 'ref': a['ref'], 'time': iso(a['time_unix'])} for a in deletions]
    audit['tags_or_releases'] = snap['table_counts']['release_or_tag_rows']
    audit['commits_in_store'] = len(commits)
    audit['commits_unreachable_from_refs_or_reflogs'] = sum(not c['reachable_from_refs_or_reflogs'] for c in commits.values())
    audit['root_commits'] = [s for s, c in commits.items() if not c['parents']]

    # GitHub: a commit is public there from the first push event whose head contains it.
    gh_first = {}
    for event in sorted(github, key=lambda e: e['created_at']):
        when = dt.datetime.fromisoformat(event['created_at'].replace('Z', '+00:00')).timestamp()
        if event['head'] not in commits:
            continue
        for sha in ancestors(commits, event['head']):
            gh_first.setdefault(sha, when)
    gh_window_start = min(dt.datetime.fromisoformat(e['created_at'].replace('Z', '+00:00')).timestamp() for e in github)

    # Chronological novelty over all refs. Transactions in the same second form one episode.
    transactions.sort(key=lambda t: (t['time'], t['ref']))
    public, published = set(), {}
    episodes = []
    for t in transactions:
        reach = ancestors(commits, t['new']) if t['new'] != ZERO else set()
        novel = reach - public
        public |= reach
        before_tip = ancestors(commits, t['old']) if t['old'] and t['old'] != ZERO else set()
        t['novel'] = sorted(novel, key=lambda s: commits[s]['committer_unix'])
        t['graph_count_old_to_new'] = len(reach - before_tip) if t['old'] and t['old'] != ZERO else None
        t['created_ref'] = t['old'] in (None, ZERO) or any(a['ref'] == t['ref'] and abs(a['time_unix'] - t['time']) <= MATCH_SECONDS for a in creations)
        t['deleted_ref'] = any(a['ref'] == t['ref'] and 0 <= a['time_unix'] - t['time'] <= MATCH_SECONDS for a in deletions)
        if episodes and episodes[-1]['time'] == t['time']:
            episodes[-1]['transactions'].append(t)
        else:
            episodes.append({'time': t['time'], 'transactions': [t]})
    rows, commit_rows = [], []
    for n, ep in enumerate(episodes, 1):
        ts = ep['transactions']
        novel = [s for t in ts for s in t['novel']]
        lo, hi = min(t['time_lo'] for t in ts), max(t['time_hi'] for t in ts)
        ep_id = f'E{n:03d}'
        gh_times = [gh_first[s] for s in novel if s in gh_first and gh_first[s] < ep['time'] - NOTIFICATION_LAG[1]]
        minute = dt.datetime.fromtimestamp(ep['time'], UTC).replace(second=0)
        rows.append({
            'episode': ep_id, 'time_utc': iso(ep['time']), 'time_unix': ep['time'],
            'time_lo_unix': lo, 'time_hi_unix': hi,
            'minute_utc': minute.isoformat().replace('+00:00', 'Z'),
            'minute_certain': dt.datetime.fromtimestamp(lo, UTC).replace(second=0) == dt.datetime.fromtimestamp(hi, UTC).replace(second=0),
            'time_source': '+'.join(sorted({t['source'] for t in ts})),
            'refs': ' '.join(t['ref'].removeprefix('refs/heads/') for t in ts),
            'ref_updates': len(ts),
            'created_refs': sum(t['created_ref'] for t in ts), 'deleted_refs': sum(t['deleted_ref'] for t in ts),
            'novel_commits': len(novel),
            'reported_len_sum': sum(t['reported_len'] or 0 for t in ts),
            'graph_old_to_new_sum': sum(t['graph_count_old_to_new'] or 0 for t in ts) if all(t['graph_count_old_to_new'] is not None for t in ts) else '',
            'action_ids': ' '.join(str(t['action_id']) for t in ts if t['action_id']),
            'notification_lag_s': ' '.join(str(t['notification_lag']) for t in ts if t['notification_lag'] is not None),
            'new_tips': ' '.join(t['new'] for t in ts),
            'github_first_novel_lead_s': round(ep['time'] - min(gh_times)) if gh_times else '',
            'github_preceded_novel_commits': len(gh_times),
            'github_events_cover': ep['time'] >= gh_window_start,
            'phase': phase(ep['time']), 'date_utc': minute.date().isoformat(),
            'log_regime': 'forge-json' if ep['time'] >= JSON_LOG_START else 'legacy-mixed-host',
        })
        for t in ts:
            for sha in t['novel']:
                published[sha] = ep_id
                commit_rows.append({
                    'sha': sha, 'episode': ep_id, 'ref': t['ref'].removeprefix('refs/heads/'),
                    'first_forgejo_unix': t['time'], 'first_forgejo_lo_unix': t['time_lo'], 'first_forgejo_hi_unix': t['time_hi'],
                    'first_forgejo_utc': iso(t['time']), 'precision': t['source'],
                    'committer_unix': commits[sha]['committer_unix'], 'author_unix': commits[sha]['author_unix'],
                    'commit_to_publication_s': t['time'] - commits[sha]['committer_unix'],
                    'github_first_unix': round(gh_first[sha]) if sha in gh_first else '',
                    'github_known': gh_first.get(sha, 0) >= gh_window_start if sha in gh_first else False,
                    'on_current_main': sha in ancestors(commits, next(r['object'] for r in snap['refs'] if r['ref'] == 'refs/heads/main')),
                })
    missing = [s for s in commits if s not in published]
    audit['commits_without_publication'] = missing
    audit['episodes'] = len(rows)
    audit['len_vs_graph'] = [{'episode': r['episode'], 'refs': r['refs'], 'reported_len_sum': r['reported_len_sum'],
                              'graph_old_to_new_sum': r['graph_old_to_new_sum'], 'novel_commits': r['novel_commits']}
                             for r in rows if str(r['reported_len_sum']) != str(r['graph_old_to_new_sum']) or r['novel_commits'] != r['reported_len_sum']]
    audit['github_window_start'] = iso(gh_window_start)
    audit['github_events_heads_absent_from_graph'] = sum(e['head'] not in commits for e in github)
    for name, data in (('publication-episodes.csv', rows), ('commit-publication.csv', commit_rows)):
        with (HERE / 'data' / name).open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(data[0]))
            writer.writeheader()
            writer.writerows(data)
    (HERE / 'data/publication-audit.json').write_text(json.dumps(audit, indent=1) + '\n')
    print(json.dumps({k: v for k, v in audit.items() if k not in ('len_vs_graph',)}, indent=1)[:3000])
    print('len/graph/novel differences:')
    for item in audit['len_vs_graph']:
        print(' ', item)


if __name__ == '__main__':
    main()
