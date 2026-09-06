#!/usr/bin/env python3
"""Reader-facing computations for growing-radius domination.

This script accompanies the essay version of the preprint

    The Annealed Critical Window for Growing-Radius Domination
    in Random Regular Graphs.

The numerical table targets the earlier near-critical lower bound, retained
as a consequence of the current preprint.

It deliberately keeps the mathematical structure visible.  The core steps are:

1. compute the tree-ball volume B_h;
2. evaluate the conditioned local entropy s_d(a);
3. evaluate the exact compact microcanonical functional;
4. solve the unique stationary orbit by reverse transfer;
5. reconstruct density, activity, and free energy at the root;
6. target the near-critical coordinate C = alpha B_h;
7. gate every reported row by independent residual checks.

Only ``mpmath`` is required for the main calculations.  ``matplotlib`` is
optional and is used only by ``--plot``.

The code is expository, not optimized for maximum throughput.  Numerical
calculations illustrate the theorem and audit the identities; they are not
used in its proof.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import mpmath as mp


# ---------------------------------------------------------------------------
# 1. Geometry and the expected scale
# ---------------------------------------------------------------------------


def tree_ball_volume(d: int, h: int) -> mp.mpf:
    """Radius-h volume of the infinite d-regular tree."""
    if d < 3:
        raise ValueError("d must be at least 3")
    if h < 0:
        raise ValueError("h must be nonnegative")
    b = d - 1
    return mp.mpf(1) + d * (mp.power(b, h) - 1) / (d - 2)


def near_critical_coordinate(d: int, h: int, W: mp.mpf | None = None) -> mp.mpf:
    """Return C = log B_h - 2 log log B_h - W.

    The demonstration default W=log log B_h stays a diverging distance below
    the bounded critical window while remaining close enough to show the
    predicted second-order term.
    """
    B = tree_ball_volume(d, h)
    L = mp.log(B)
    if W is None:
        W = mp.log(L)
    return L - 2 * mp.log(L) - W


# ---------------------------------------------------------------------------
# 2. Exact local entropy and compact functional
# ---------------------------------------------------------------------------


def _conditioned_marginal(d: int, lam: mp.mpf) -> mp.mpf:
    """Marginal of one coordinate in a nonempty tilted subset of [d]."""
    log1p_lam = mp.log1p(lam)
    numerator = lam * mp.exp((d - 1) * log1p_lam)
    denominator = mp.expm1(d * log1p_lam)
    return numerator / denominator


def lambda_from_marginal(d: int, a: mp.mpf) -> mp.mpf:
    """Solve a = lambda(1+lambda)^(d-1)/((1+lambda)^d-1).

    A precision-scaled lower endpoint is important near the Moore corner,
    where a-1/d can be exponentially small.
    """
    a = mp.mpf(a)
    lower = mp.mpf(1) / d
    if a < lower or a > 1:
        raise ValueError("a must lie in [1/d, 1]")
    tol = mp.power(10, -(mp.mp.dps - 12))
    if abs(a - lower) <= tol:
        return mp.mpf(0)
    if abs(a - 1) <= tol:
        return mp.inf

    # Bisection in log lambda avoids an enormous dynamic range.
    lo = -mp.mpf(2) * mp.mp.dps * mp.log(10)
    hi = mp.mpf(2) * mp.mp.dps * mp.log(10)
    for _ in range(max(160, 3 * mp.mp.dps)):
        mid = (lo + hi) / 2
        lam = mp.exp(mid)
        if _conditioned_marginal(d, lam) < a:
            lo = mid
        else:
            hi = mid
    return mp.exp((lo + hi) / 2)


def conditioned_subset_entropy(d: int, a: mp.mpf) -> mp.mpf:
    r"""Maximum entropy s_d(a) on nonempty subsets with marginal a.

    s_d(a) = inf_{lambda>0} [log((1+lambda)^d-1)-da log lambda].
    """
    a = mp.mpf(a)
    lower = mp.mpf(1) / d
    tol = mp.power(10, -(mp.mp.dps - 12))
    if abs(a - lower) <= tol:
        return mp.log(d)
    if abs(a - 1) <= tol:
        return mp.mpf(0)
    lam = lambda_from_marginal(d, a)
    log_partition = mp.log(mp.expm1(d * mp.log1p(lam)))
    return log_partition - d * a * mp.log(lam)


def _xlogx(x: mp.mpf) -> mp.mpf:
    return mp.mpf(0) if x == 0 else x * mp.log(x)


def compact_microcanonical_value(
    d: int,
    h: int,
    x: Sequence[mp.mpf],
    ell: Sequence[mp.mpf],
) -> tuple[mp.mpf, mp.mpf]:
    r"""Evaluate the exact compact functional.

    Coordinates:
        x_i   = q_{i-1,i},  i=1,...,h,
        ell_i = q_{i,i},    i=0,...,h.

    The layer masses are p_i = ell_i + x_i + x_{i+1}, with x_0=x_{h+1}=0.
    Returns (F, alpha=p_0).
    """
    if len(x) != h or len(ell) != h + 1:
        raise ValueError("wrong coordinate lengths")
    xx = [mp.mpf(0)] + [mp.mpf(v) for v in x] + [mp.mpf(0)]
    ll = [mp.mpf(v) for v in ell]
    if any(v < 0 for v in xx) or any(v < 0 for v in ll):
        raise ValueError("coordinates must be nonnegative")

    p = [ll[i] + xx[i] + xx[i + 1] for i in range(h + 1)]
    if abs(sum(p) - 1) > mp.power(10, -(mp.mp.dps // 2)):
        raise ValueError("profile is not normalized")

    alpha = p[0]
    value = (d - 1) * _xlogx(alpha)
    for i in range(1, h + 1):
        if p[i] == 0:
            continue
        a_i = xx[i] / p[i]
        lower = mp.mpf(1) / d
        numerical_tol = mp.power(10, -(mp.mp.dps // 3))
        if a_i < lower - numerical_tol or a_i > 1 + numerical_tol:
            raise ValueError("descent marginal is infeasible")
        a_i = min(mp.mpf(1), max(lower, a_i))
        y_i = p[i] - xx[i]
        value += -_xlogx(p[i])
        value += p[i] * conditioned_subset_entropy(d, a_i)
        value += d * _xlogx(y_i)
    value -= mp.mpf(d) / 2 * sum(_xlogx(v) for v in ll)
    return value, alpha


# ---------------------------------------------------------------------------
# 3. Reverse transfer and stationary reconstruction
# ---------------------------------------------------------------------------


@dataclass
class StationaryPoint:
    d: int
    h: int
    terminal_t: mp.mpf
    terminal: mp.mpf
    z: mp.mpf
    alpha: mp.mpf
    phi_direct: mp.mpf
    psi_direct: mp.mpf
    phi_root: mp.mpf
    psi_root: mp.mpf
    kappa: mp.mpf
    r0: mp.mpf
    Zv: mp.mpf
    Ze: mp.mpf
    telescoping_residual: mp.mpf
    root_pressure_residual: mp.mpf
    root_micro_residual: mp.mpf
    stationarity_residual: mp.mpf
    compact_residual: mp.mpf
    rho: list[mp.mpf]
    u: list[mp.mpf]
    A: list[mp.mpf]
    Bmsg: list[mp.mpf]


def _w_e(rho: mp.mpf, b: int) -> tuple[mp.mpf, mp.mpf]:
    """Return w=(1-rho)^(1/b) and e=1-w without cancellation."""
    log_w = mp.log1p(-rho) / b
    return mp.exp(log_w), -mp.expm1(log_w)


def reverse_step(rho_next: mp.mpf, v_next: mp.mpf, b: int) -> tuple[mp.mpf, mp.mpf]:
    r"""Invert one stationary transfer step.

    Input lies in D={(rho,v): 0<rho<=v<=1, rho<1}.  The output is the
    unique predecessor in D; the singular endpoint (1,1) is excluded.
    """
    if not (0 < rho_next <= v_next <= 1 and rho_next < 1):
        raise ValueError("require 0 < rho <= v <= 1 and rho < 1")
    w, e = _w_e(rho_next, b)
    R = v_next * e / w
    M = mp.power(e + w / v_next, b)
    denominator = R + M
    rho = R / denominator
    v = (1 + R) / denominator
    return rho, v


def _stable_power_difference(S: mp.mpf, B: mp.mpf, power: int) -> mp.mpf:
    """Compute S^power-(S-B)^power stably when B/S is tiny."""
    ratio = B / S
    return mp.power(S, power) * (-mp.expm1(power * mp.log1p(-ratio)))


def stationary_from_terminal_t(
    d: int, h: int, terminal_t: mp.mpf, *, validate_compact: bool = True
) -> StationaryPoint:
    r"""Construct the unique positive stationary orbit.

    We use t=-log(1-s) rather than s directly.  At high density the terminal
    parameter s is extraordinarily close to one, while t remains numerically
    well scaled.
    """
    if d < 3 or h < 1:
        raise ValueError("require d>=3 and h>=1")
    b = d - 1
    t = mp.mpf(terminal_t)
    if t <= 0:
        raise ValueError("terminal_t must be positive")
    terminal = -mp.expm1(-t)

    rho = [mp.mpf(0)] * (h + 1)
    v = [mp.mpf(0)] * (h + 1)
    u = [mp.mpf(0)] * (h + 1)
    rho[h] = v[h] = terminal
    for i in range(h - 1, 0, -1):
        rho[i], v[i] = reverse_step(rho[i + 1], v[i + 1], b)
        u[i] = v[i] - rho[i]
    u[h] = mp.mpf(0)

    w1, e1 = _w_e(rho[1], b)
    if e1 == 0:
        raise ArithmeticError("root coordinate under-resolved; increase mp.dps")
    r0 = v[1] * e1 / w1
    kappa = mp.power(v[1] / w1, b)
    z = r0 * kappa / mp.power(1 + r0, b)

    # Normalize A_1=1 and reconstruct the messages.
    A = [mp.mpf(0)] * (h + 2)
    Bmsg = [mp.mpf(0)] * (h + 1)
    A[1] = mp.mpf(1)
    for i in range(1, h):
        A[i + 1] = u[i] * A[i]
    Bmsg[0] = r0
    for i in range(1, h + 1):
        Bmsg[i] = rho[i] * A[i]

    S = [mp.mpf(0)] * (h + 1)
    S[0] = Bmsg[0] + A[1]
    for i in range(1, h):
        S[i] = Bmsg[i - 1] + Bmsg[i] + A[i + 1]
    S[h] = Bmsg[h - 1] + Bmsg[h]

    vertex_terms = [z * mp.power(S[0], d)]
    for i in range(1, h + 1):
        vertex_terms.append(_stable_power_difference(S[i], Bmsg[i - 1], d))
    Zv = mp.fsum(vertex_terms)
    Ze = mp.fsum(v * v for v in Bmsg) + 2 * mp.fsum(
        Bmsg[i] * A[i + 1] for i in range(h)
    )

    alpha = Bmsg[0] * (Bmsg[0] + A[1]) / Ze
    phi_direct = mp.log(Zv) - mp.mpf(d) / 2 * mp.log(Ze)
    psi_direct = phi_direct - alpha * mp.log(z)

    # Correct, well-conditioned root-only formulas.
    phi_root = (
        mp.log(z)
        + mp.mpf(d) / 2 * mp.log((1 + r0) / r0)
        + mp.mpf(d - 2) / 2 * mp.log(alpha)
    )
    psi_root = (
        (1 - alpha) * mp.log(kappa)
        - (mp.mpf(d - 2) / 2 + alpha) * mp.log(r0)
        + mp.mpf(d - 2) / 2 * mp.log(alpha)
        + (mp.mpf(d - 1) * alpha - mp.mpf(d - 2) / 2) * mp.log(1 + r0)
    )

    stationarity = [abs(kappa * Bmsg[0] - z * mp.power(S[0], b))]
    for i in range(1, h + 1):
        stationarity.append(abs(kappa * A[i] - mp.power(S[i], b)))
        stationarity.append(
            abs(
                kappa * Bmsg[i]
                - _stable_power_difference(S[i], Bmsg[i - 1], b)
            )
        )

    # Reconstruct the compact profile only for final diagnostic points.
    if validate_compact:
        x = [Bmsg[i - 1] * A[i] / Ze for i in range(1, h + 1)]
        ell = [Bmsg[i] * Bmsg[i] / Ze for i in range(h + 1)]
        compact_value, compact_alpha = compact_microcanonical_value(d, h, x, ell)
        compact_residual = max(abs(compact_value - psi_root), abs(compact_alpha - alpha))
    else:
        compact_residual = mp.nan

    return StationaryPoint(
        d=d,
        h=h,
        terminal_t=t,
        terminal=terminal,
        z=z,
        alpha=alpha,
        phi_direct=phi_direct,
        psi_direct=psi_direct,
        phi_root=phi_root,
        psi_root=psi_root,
        kappa=kappa,
        r0=r0,
        Zv=Zv,
        Ze=Ze,
        telescoping_residual=Zv - kappa * Ze,
        root_pressure_residual=phi_direct - phi_root,
        root_micro_residual=psi_direct - psi_root,
        stationarity_residual=max(stationarity),
        compact_residual=compact_residual,
        rho=rho,
        u=u,
        A=A,
        Bmsg=Bmsg,
    )


# ---------------------------------------------------------------------------
# 4. Target-density solving and residual gates
# ---------------------------------------------------------------------------


def solve_for_alpha_B(
    d: int,
    h: int,
    C: mp.mpf,
    *,
    iterations: int | None = None,
) -> StationaryPoint:
    """Solve alpha B_h = C by bisection in terminal_t."""
    B = tree_ball_volume(d, h)
    target_alpha = mp.mpf(C) / B
    if not 0 < target_alpha < 1:
        raise ValueError("target density must lie in (0,1)")
    if iterations is None:
        iterations = max(140, 2 * mp.mp.dps)

    D = mp.mpf(d) / (d - 2)
    lo = mp.mpf("0.05") * C / D
    hi = mp.mpf("3.0") * C / D + 1
    while stationary_from_terminal_t(d, h, lo, validate_compact=False).alpha > target_alpha:
        lo /= 2
    while stationary_from_terminal_t(d, h, hi, validate_compact=False).alpha < target_alpha:
        hi *= 2

    for _ in range(iterations):
        mid = (lo + hi) / 2
        point = stationary_from_terminal_t(d, h, mid, validate_compact=False)
        if point.alpha < target_alpha:
            lo = mid
        else:
            hi = mid
    return stationary_from_terminal_t(d, h, (lo + hi) / 2, validate_compact=True)


def relative_residual(residual: mp.mpf, reference: mp.mpf) -> mp.mpf:
    return abs(residual) / max(abs(reference), mp.mpf(1))


def gate_point(point: StationaryPoint, route_tolerance: str = "1e-6") -> None:
    """Reject a row if an internal cross-check is too large to ignore.

    The direct partition-function route can be ill conditioned near criticality.
    The root-only formula is the reported value, but the direct route must still
    agree to the requested relative tolerance at the working precision.
    """
    tol = mp.mpf(route_tolerance)
    if point.psi_root == 0:
        raise RuntimeError("zero root-formula microcanonical exponent")
    route_disagreement = abs(point.root_micro_residual / point.psi_root)
    if route_disagreement > tol:
        raise RuntimeError(
            "microcanonical routes disagree: "
            f"relative discrepancy={route_disagreement}; increase mp.dps"
        )
    if point.compact_residual > mp.sqrt(tol):
        raise RuntimeError(
            f"compact-functional reconstruction failed: {point.compact_residual}"
        )


def diagnostic_row(d: int, h: int, W: mp.mpf | None = None) -> dict[str, str | int]:
    """Solve one near-critical case and return an audit-friendly record."""
    B = tree_ball_volume(d, h)
    L = mp.log(B)
    if W is None:
        W = mp.log(L)
    C = near_critical_coordinate(d, h, W)
    point = solve_for_alpha_B(d, h, C)
    gate_point(point)

    coupon = B * mp.power(1 - point.alpha, B)
    activity_ratio = (-mp.log(point.z) - mp.log(1 / point.alpha)) / coupon
    scale = mp.exp(-C)
    route_disagreement = abs(point.root_micro_residual / point.psi_root)

    return {
        "d": d,
        "h": h,
        "dps": mp.mp.dps,
        "B_h": mp.nstr(B, 30),
        "C": mp.nstr(C, 24),
        "alpha_B_h": mp.nstr(point.alpha * B, 24),
        "terminal_t": mp.nstr(point.terminal_t, 30),
        "activity_ratio": mp.nstr(activity_ratio, 20),
        "minus_psi_over_exp_minus_C": mp.nstr(-point.psi_root / scale, 20),
        "psi_root": mp.nstr(point.psi_root, 24),
        "psi_direct": mp.nstr(point.psi_direct, 24),
        "route_relative_disagreement": mp.nstr(route_disagreement, 12),
        "stationarity_residual": mp.nstr(point.stationarity_residual, 12),
        "telescoping_residual": mp.nstr(point.telescoping_residual, 12),
        "compact_residual": mp.nstr(point.compact_residual, 12),
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }


# ---------------------------------------------------------------------------
# 5. Tables and optional plotting
# ---------------------------------------------------------------------------


def default_cases() -> list[tuple[int, int, int]]:
    """(d,h,dps) cases chosen to keep a demonstration run manageable."""
    return [
        (3, 12, 90),
        (3, 20, 110),
        (3, 30, 130),
        (3, 40, 160),
        (4, 12, 100),
        (4, 20, 130),
        (4, 28, 160),
    ]


def make_table(
    cases: Iterable[tuple[int, int, int]],
    *,
    csv_path: str | None = None,
) -> list[dict[str, str | int]]:
    rows: list[dict[str, str | int]] = []
    for d, h, dps in cases:
        mp.mp.dps = dps
        row = diagnostic_row(d, h)
        rows.append(row)
        print(
            f"d={d} h={h:>2}  C={row['C']}  "
            f"activity={row['activity_ratio']}  "
            f"-Psi/e^-C={row['minus_psi_over_exp_minus_C']}"
        )
    if csv_path:
        with open(csv_path, "w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    return rows


def plot_rows(rows: Sequence[dict[str, str | int]], output: str) -> None:
    """Plot the two diagnostic ratios; matplotlib is optional."""
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError("install matplotlib to use --plot") from exc

    by_d: dict[int, list[dict[str, str | int]]] = {}
    for row in rows:
        by_d.setdefault(int(row["d"]), []).append(row)

    # Separate figures keep the diagnostics readable.
    for field, ylabel, suffix in [
        ("activity_ratio", "activity-law ratio", "activity"),
        ("minus_psi_over_exp_minus_C", r"$-\Psi/e^{-C}$", "free_energy"),
    ]:
        plt.figure()
        for d, group in sorted(by_d.items()):
            group = sorted(group, key=lambda r: int(r["h"]))
            plt.plot(
                [int(r["h"]) for r in group],
                [float(r[field]) for r in group],
                marker="o",
                label=f"d={d}",
            )
        plt.axhline(1.0, linestyle="--")
        plt.xlabel("radius h")
        plt.ylabel(ylabel)
        plt.legend()
        plt.tight_layout()
        path = str(Path(output).with_name(Path(output).stem + f"_{suffix}.png"))
        plt.savefig(path, dpi=180)
        plt.close()
        print(path)


# ---------------------------------------------------------------------------
# 6. Command line interface
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--d", type=int, default=3)
    parser.add_argument("--h", type=int, default=20)
    parser.add_argument("--dps", type=int, default=110)
    parser.add_argument(
        "--W",
        type=str,
        default=None,
        help="additive gap W; default is log log B_h",
    )
    parser.add_argument("--table", action="store_true", help="run the curated table")
    parser.add_argument("--csv", type=str, default=None, help="optional CSV output")
    parser.add_argument("--plot", type=str, default=None, help="plot prefix for table output")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.table:
        rows = make_table(default_cases(), csv_path=args.csv)
        if args.plot:
            plot_rows(rows, args.plot)
        return

    mp.mp.dps = args.dps
    W = None if args.W is None else mp.mpf(args.W)
    row = diagnostic_row(args.d, args.h, W)
    for key, value in row.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
