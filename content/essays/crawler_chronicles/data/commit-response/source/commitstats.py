"""Statistical mechanics for the commit-response study (numpy only).

Minute series are integer arrays indexed from the study origin. An episode at
minute index m has pre window [m-W, m-1] and post window [m+1, m+W]; the
episode minute itself is omitted.

The rotation null moves every episode of one block (a fixed 60-minute block,
UTC hours unless `origin` is offset) by one common shift s in 0..59, wrapping
inside the block. Shifts are drawn independently per block; the observed
placement is s = 0 for every block. Rotations form a group, so with the
observed statistic counted once among the draws, (1 + #{T* >= T}) / (1 + n)
is a valid Monte Carlo p-value under within-block rotation exchangeability.
"""
import numpy as np

BLOCK = 60


def cumulative(y):
    return np.concatenate([[0], np.cumsum(np.asarray(y, dtype=np.int64))])


def windows(c, pos, w):
    """(post, pre) sums for integer positions, given cumulative sums c."""
    pos = np.asarray(pos)
    pre = c[pos] - c[pos - w]
    post = c[pos + w + 1] - c[pos + 1]
    return post, pre


def blocks_for(positions, origin=0):
    """Group episode positions into fixed blocks [origin + 60k, origin + 60k + 60)."""
    out = {}
    for p in positions:
        k = (p - origin) // BLOCK
        out.setdefault(k, []).append((p - origin) % BLOCK)
    return [(origin + BLOCK * k, np.array(sorted(v))) for k, v in sorted(out.items())]


def block_eligible(ok, start, w):
    """True if every minute of [start - w, start + 60 + w) is usable (ok is a boolean array)."""
    lo, hi = start - w, start + BLOCK + w
    return lo >= 0 and hi <= len(ok) and bool(ok[lo:hi].all())


class Rotation:
    """Per-block tables of an additive per-episode statistic at all 60 shifts."""

    def __init__(self, blocks):
        self.blocks = blocks
        self.n_episodes = sum(len(o) for _, o in blocks)
        self.shift_positions = [start + (offsets[None, :] + np.arange(BLOCK)[:, None]) % BLOCK
                                for start, offsets in blocks]          # [60, k] per block

    def table(self, per_episode):
        """per_episode(positions array) -> values; returns [B, 60] block sums."""
        return np.stack([per_episode(p.ravel()).reshape(p.shape).sum(axis=1) for p in self.shift_positions])

    def positions(self, shifts=None):
        shifts = np.zeros(len(self.blocks), dtype=int) if shifts is None else shifts
        return np.concatenate([p[s] for p, s in zip(self.shift_positions, shifts)])

    def draws(self, rng, n):
        return rng.integers(0, BLOCK, size=(n, len(self.blocks)))

    @staticmethod
    def totals(table, shifts):
        return table[np.arange(table.shape[0])[None, :], shifts].sum(axis=1)


def mc_pvalue(observed, null, tol=1e-9):
    null = np.asarray(null)
    return (1 + np.sum(null >= observed - tol)) / (1 + len(null))


def diff_stat(c, w):
    return lambda pos: (lambda post_pre: post_pre[0] - post_pre[1])(windows(c, pos, w))


def positive_stat(c, w):
    return lambda pos: (lambda pp: (pp[0] > pp[1]).astype(float) + 0.5 * (pp[0] == pp[1]))(windows(c, pos, w))


def logratio_stat(c, w):
    return lambda pos: (lambda pp: np.log1p(pp[0]) - np.log1p(pp[1]))(windows(c, pos, w))


def rotation_test(c, blocks, w, n, seed, stat=diff_stat):
    """Observed mean statistic, Monte Carlo p, null mean (exact), null draws, per-episode excess."""
    rot = Rotation(blocks)
    f = stat(c, w)
    tab = rot.table(f)
    k = rot.n_episodes
    observed = tab[:, 0].sum() / k
    rng = np.random.default_rng(seed)
    null = Rotation.totals(tab, rot.draws(rng, n)) / k
    exact_mean = tab.mean(axis=1).sum() / k
    # Per-episode excess over that episode's own mean across its block's 60 rotations.
    excess = []
    for p in rot.shift_positions:
        values = f(p.ravel()).reshape(p.shape)
        excess.extend(values[0] - values.mean(axis=0))
    return {'observed': float(observed), 'p': float(mc_pvalue(observed, null)), 'null_mean_exact': float(exact_mean),
            'null_mean_draws': float(null.mean()), 'null_q95': float(np.quantile(null, 0.95)),
            'null_q025': float(np.quantile(null, 0.025)), 'null_q975': float(np.quantile(null, 0.975)),
            'excess': float(observed - exact_mean), 'episodes': int(k), 'blocks': len(blocks),
            'per_episode_excess': np.array(excess), 'null': null}


def clusters(positions, w):
    """Cluster ids: episodes whose [m-w, m+w] windows overlap are chained together."""
    order = np.argsort(positions)
    ids = np.empty(len(positions), dtype=int)
    current, last = -1, None
    for i in order:
        if last is None or positions[i] - last > 2 * w:
            current += 1
        ids[i] = current
        last = positions[i]
    return ids


def cluster_bootstrap(values, ids, n, seed):
    """Percentile interval for the mean of values, resampling whole clusters."""
    rng = np.random.default_rng(seed)
    groups = [values[ids == g] for g in np.unique(ids)]
    sums = np.array([g.sum() for g in groups])
    sizes = np.array([len(g) for g in groups])
    pick = rng.integers(0, len(groups), size=(n, len(groups)))
    means = sums[pick].sum(axis=1) / sizes[pick].sum(axis=1)
    return float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))


def event_profile(y, rot, lags, shifts=None):
    """Mean of y at relative minutes `lags` across episodes, for given block shifts."""
    pos = rot.positions(shifts)
    return np.asarray(y)[pos[:, None] + np.asarray(lags)[None, :]].mean(axis=0)


def event_null(y, rot, lags, n, seed):
    """Event-profile draws under the rotation null: [n, len(lags)]."""
    y = np.asarray(y)
    lags = np.asarray(lags)
    tabs = np.stack([y[p[:, :, None] + lags[None, None, :]].sum(axis=1) for p in rot.shift_positions])  # [B,60,L]
    rng = np.random.default_rng(seed)
    shifts = rot.draws(rng, n)
    out = np.zeros((n, len(lags)))
    for b in range(len(rot.blocks)):
        out += tabs[b][shifts[:, b]]
    return out / rot.n_episodes


def referent_test(c, days, candidates, w, n, seed, stat=diff_stat):
    """Day relabelling null: each push day's episodes move, at their clock minutes, to a random
    candidate day (the observed day included). days: {day_index: [minute_of_day,...]};
    candidates: {day_index: [candidate day indices]}; positions are day*1440 + minute."""
    f = stat(c, w)
    rng = np.random.default_rng(seed)
    keys = sorted(days)
    tabs = []
    for d in keys:
        cand = np.array(candidates[d])
        minutes = np.array(days[d])
        vals = f((cand[:, None] * 1440 + minutes[None, :]).ravel()).reshape(len(cand), len(minutes)).sum(axis=1)
        tabs.append((cand, vals))
    k = sum(len(days[d]) for d in keys)
    observed = sum(vals[list(cand).index(d)] for d, (cand, vals) in zip(keys, tabs)) / k
    null = np.zeros(n)
    for cand, vals in tabs:
        null += vals[rng.integers(0, len(cand), size=n)]
    null /= k
    exact = sum(vals.mean() for _, vals in tabs) / k
    return {'observed': float(observed), 'p': float(mc_pvalue(observed, null)), 'null_mean_exact': float(exact),
            'excess': float(observed - exact), 'episodes': int(k), 'push_days': len(keys),
            'candidate_days': {int(d): len(candidates[d]) for d in keys}, 'null': null}


def holm(pvalues):
    p = np.asarray(pvalues, dtype=float)
    order = np.argsort(p)
    adjusted = np.empty_like(p)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (len(p) - rank) * p[i]))
        adjusted[i] = running
    return adjusted


def kaplan_meier(durations, observed):
    """Product-limit survival at the distinct event times. Returns (times, survival)."""
    durations = np.asarray(durations, dtype=float)
    observed = np.asarray(observed, dtype=bool)
    times = np.unique(durations[observed])
    surv, s = [], 1.0
    for t in times:
        at_risk = np.sum(durations >= t)
        events = np.sum((durations == t) & observed)
        s *= 1 - events / at_risk
        surv.append(s)
    return times, np.array(surv)


def km_at(times, surv, t):
    idx = np.searchsorted(times, t, side='right') - 1
    return 1.0 if idx < 0 else float(surv[idx])
