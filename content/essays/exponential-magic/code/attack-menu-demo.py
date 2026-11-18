#!/usr/bin/env python3
"""Minimal reproduction of the historical attack-list ordering.

All eligible attackers have four legal defenders. No attack taxes or
must-attack requirements are modeled. Each entry stores its attacker count.
This demonstrates the cap; it does not simulate a Magic game.
"""
import csv
import sys

def attack_sizes(eligible, defenders=4, cap=1024):
    choices = [0]  # decline to attack
    for attacker in range(eligible):
        for defender in range(defenders):
            if len(choices) >= cap:
                return choices
            choices.append(1)
    for defender in range(defenders):
        if len(choices) >= cap:
            return choices
        choices.append(eligible)
    return choices

if __name__ == "__main__":
    writer = csv.writer(sys.stdout)
    writer.writerow(["eligible_attackers", "declarations", "largest_attack", "multi_attacks"])
    for eligible in [56, 114, 227, 256, 455, 7256]:
        choices = attack_sizes(eligible)
        writer.writerow([eligible, len(choices), max(choices), sum(n > 1 for n in choices)])
