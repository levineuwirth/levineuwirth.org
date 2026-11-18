#!/usr/bin/env python3
"""Illustrative arithmetic, not an Arcana simulation or a personal game.

One emblem starts at zero Zombies. One Scute starts at one; six or more
lands are present at resolution, and all triggers settle before the next
land enters. Nothing dies. Wardens and doublers are already present.
Prints CSV to stdout; all arithmetic uses Python's arbitrary-size integers.
"""
import csv
import sys

def growth(events):
    return dict(events=events, liliana_zombies=2 ** (events + 1) - 2,
                scutes=2 ** events, scutes_one_token_doubler=3 ** events,
                life_gain_two_wardens=2 * (3 ** events - 1),
                life_gain_two_wardens_one_life_doubler=4 * (3 ** events - 1))

if __name__ == "__main__":
    rows = [growth(n) for n in range(9)]
    writer = csv.DictWriter(sys.stdout, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
