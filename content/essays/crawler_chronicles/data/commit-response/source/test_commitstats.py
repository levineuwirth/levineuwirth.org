#!/usr/bin/env python3
"""Synthetic checks of the study mechanics. Run: python source/test_commitstats.py

Covers window indexing, block rotation, eligibility invariance, Monte Carlo
p-value validity under a realistic null (bursts, day trend, minute-of-hour
periodicity), a planted response, a documented failure mode, Holm and
Kaplan-Meier. Prints the calibration numbers the report quotes.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import commitstats as cs  # noqa: E402


def test_windows():
    y = np.zeros(200, dtype=int)
    y[99] = 5        # last pre minute
    y[100] = 1000    # episode minute: omitted
    y[101] = 7       # first post minute
    y[100 + 30] = 11  # last post minute (W=30)
    y[100 - 30] = 13  # first pre minute
    y[100 + 31] = 999
    y[100 - 31] = 999
    post, pre = cs.windows(cs.cumulative(y), np.array([100]), 30)
    assert post[0] == 7 + 11 and pre[0] == 5 + 13, (post, pre)


def test_rotation_positions():
    rot = cs.Rotation([(120, np.array([5, 50]))])
    assert list(rot.positions(np.array([0]))) == [125, 170]
    assert sorted(rot.positions(np.array([20]))) == [130, 145]     # 25 and (70 mod 60)=10
    assert rot.shift_positions[0].shape == (60, 2)
    # Spacing preserved modulo 60 for every shift.
    for s in range(60):
        a, b = rot.shift_positions[0][s]
        assert (b - a) % 60 == 45


def test_eligibility_is_block_property():
    ok = np.ones(600, dtype=bool)
    ok[95] = False
    # Block starting at 120 with W=30 needs [90, 210): fails for every placement inside the block.
    assert not cs.block_eligible(ok, 120, 30)
    assert cs.block_eligible(ok, 180, 30)            # needs [150, 270)
    assert not cs.block_eligible(ok, 0, 30)          # lo < 0


def synthetic_requests(rng, days=13, cron=True, trend=True):
    """Bursty, nonstationary minute counts with optional :00-:04 cron peaks."""
    n = days * 1440
    level = np.ones(n)
    if trend:
        level *= np.repeat(rng.lognormal(0, 1, days), 1440)
    hour_of_day = (np.arange(n) // 60) % 24
    level *= 1 + 0.8 * np.sin(2 * np.pi * hour_of_day / 24)
    state = np.zeros(n)
    on = False
    for i in range(n):          # two-state bursts with mean lengths of ~40 and ~200 minutes
        if on and rng.random() < 1 / 40:
            on = False
        elif not on and rng.random() < 1 / 200:
            on = True
        state[i] = on
    level *= 0.2 + 8 * state
    if cron:
        level *= np.where(np.arange(n) % 60 < 5, 4.0, 1.0)
    return rng.poisson(level)


def place_pushes(rng, n, k, minute_rule=None):
    hours = rng.choice(np.arange(5, n // 60 - 5), size=k, replace=False)
    minutes = rng.integers(0, 60, size=k) if minute_rule is None else np.full(k, minute_rule)
    return np.sort(hours * 60 + minutes)


def calibration(rng, reps, k=30, planted=0.0, minute_rule=None, cron=True, draws=999):
    rejections = 0
    for r in range(reps):
        y = synthetic_requests(rng, cron=cron)
        pos = place_pushes(rng, len(y), k, minute_rule)
        if planted:
            for p in pos:
                y[p + 1:p + 11] += rng.poisson(planted, 10)
        res = cs.rotation_test(cs.cumulative(y), cs.blocks_for(pos), 30, draws, 1000 + r)
        rejections += res['p'] <= 0.05
    return rejections / reps


def test_exactness_on_constructed_null():
    """Exactness: a request series fixed, pushes drawn by uniform rotation inside their blocks."""
    rng = np.random.default_rng(7)
    y = synthetic_requests(rng)
    base = place_pushes(rng, len(y), 25)
    blocks = cs.blocks_for(base)
    rot = cs.Rotation(blocks)
    pvalues = []
    for r in range(400):
        shifts = rng.integers(0, 60, size=len(blocks))
        pos = rot.positions(shifts)
        res = cs.rotation_test(cs.cumulative(y), cs.blocks_for(pos), 30, 199, 5000 + r)
        pvalues.append(res['p'])
    pvalues = np.array(pvalues)
    return float(np.mean(pvalues <= 0.05)), float(np.mean(pvalues <= 0.10))


def test_holm_and_km():
    assert np.allclose(cs.holm([0.01, 0.04, 0.03]), [0.03, 0.06, 0.06])
    t, s = cs.kaplan_meier([1, 2, 2, 3, 4], [1, 1, 0, 1, 0])
    assert np.allclose(t, [1, 2, 3]) and np.allclose(s, [0.8, 0.6, 0.3])
    assert np.isclose(cs.km_at(t, s, 2.5), 0.6) and cs.km_at(t, s, 0.5) == 1.0


def test_clusters():
    ids = cs.clusters(np.array([100, 150, 400, 159]), 30)
    assert ids[0] == ids[1] == ids[3] and ids[2] != ids[0]


def main():
    test_windows()
    test_rotation_positions()
    test_eligibility_is_block_property()
    test_holm_and_km()
    test_clusters()
    rng = np.random.default_rng(20261020)
    report = {}
    report['exactness_constructed_null_rate_at_05_and_10'] = test_exactness_on_constructed_null()
    report['null_bursty_cron_trend_rejection_rate'] = calibration(rng, 200)
    report['planted_response_power'] = {str(lam): calibration(rng, 100, planted=lam) for lam in (0.5, 1, 2, 4)}
    report['failure_mode_pushes_at_58_with_00_cron_rejection_rate'] = calibration(rng, 100, minute_rule=58)
    report['control_pushes_at_58_without_cron_rejection_rate'] = calibration(rng, 100, minute_rule=58, cron=False)
    print(json.dumps(report, indent=1))
    rate05, rate10 = report['exactness_constructed_null_rate_at_05_and_10']
    assert rate05 <= 0.05 + 2 * np.sqrt(0.05 * 0.95 / 400), rate05
    assert report['null_bursty_cron_trend_rejection_rate'] <= 0.05 + 2 * np.sqrt(0.05 * 0.95 / 200)
    power = [report['planted_response_power'][k] for k in ('0.5', '1', '2', '4')]
    assert power[-1] > 2 * report['null_bursty_cron_trend_rejection_rate'] and power[-1] >= power[0], power
    out = Path(__file__).resolve().parent.parent / 'results'
    out.mkdir(exist_ok=True)
    (out / 'synthetic-checks.json').write_text(json.dumps(report, indent=1) + '\n')
    print('all synthetic checks passed')


if __name__ == '__main__':
    main()
