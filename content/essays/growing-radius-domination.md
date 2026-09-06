---
title: "From Path Tubes to a Near-Critical Domination Bound"
date: 2026-07-22
revised:
  - date: "2026-09-05"
    note: "Clarified the scope of the tube interpretation, linked the corrected current preprint, and recorded the resolved bounded critical window."
abstract: >
  A first-person, code-heavy companion tracing the near-critical bound that
  led to *The Annealed Critical Window for Growing-Radius Domination in
  Random Regular Graphs*. Rather than reproducing its theorem-and-proof form, this page
  traces where the problem came from — a cops-and-robbers hypergraph question
  that collapsed into a domination bound — why the answer carries an
  unnecessary coupon-collector logarithm, and how a chain of computational
  detours (a failed concavity conjecture, a catastrophic cancellation, an
  independent audit that caught a stale constant) repeatedly redirected the
  proof before it reached its final shape.
tags:
  - research
  - research/mathematics
  - research/graph-theory
  - tech/python
authors:
  - "Levi Neuwirth | /me.html"
preprint: /papers/near-critical-growing-radius-domination-paper.pdf
status: "Durable"
confidence: proved
evidence: 5
peer-status: unreviewed
result-shape: mixed
history:
  - date: "2026-09-05"
    note: "Corrected the global tube interpretation and reconciled the companion with the bounded-window preprint."
  - date: "2026-07-24"
  - date: "2026-07-22"

---

This page traces the near-critical argument that led to the preprint [**The Annealed Critical Window for Growing-Radius Domination in Random Regular Graphs**](/papers/near-critical-growing-radius-domination-paper.pdf) — [the full theorem-and-proof form is here](/essays/near-critical-growing-radius-domination.html). The earlier download URL also serves the corrected current paper. A complete, runnable version — [`growing-radius-domination-demo.py`](/papers/growing-radius-domination-demo.py) — ships alongside this page, together with [the CSV of diagnostic output](/papers/growing-radius-domination-demo-output.csv) it produces.

The theorem followed by the computations below is the earlier near-critical bound, retained as a consequence of the current result. The bounded critical window has since been proved; Section 14 records that stronger conclusion. Fix a degree $d\ge 3$ and let

$$
B_h=1+d\frac{(d-1)^h-1}{d-2}
$$

be the number of vertices in a radius-$h$ ball of the infinite $d$-regular tree. For a graph $G$, write $\gamma_h(G)$ for the minimum size of a set whose distance-$h$ neighborhoods cover every vertex. If $G_{n,d}$ is a uniformly random simple $d$-regular graph and $h=h(n)\to\infty$, then for every $W_h\to\infty$ for which the displayed coordinate stays a positive fraction of $\log B_h$ and the type-counting error stays asymptotically below the coupon term,

::: {.exhibit .exhibit--equation}
$$
\gamma_h(G_{n,d})\ge
\frac{n}{B_h}
\left(
\log B_h-2\log\log B_h-W_h
\right)
$$
:::

with high probability.

The $-W_h$ is deliberate. Letting $W_h$ diverge arbitrarily slowly walks this earlier bound arbitrarily close to the bounded critical window. Resolving the window itself required the additional argument described in Section 14. At the comparison scale $B_h\asymp\sqrt n$, with such a slowly growing $W_h$, the lower bound has order

$$
\sqrt n\log n,
$$

not merely $\sqrt n$. That single extra logarithm is QUITE LITERALLY the entire reason this project exists, and it is why the whole thing began, improbably, inside a cops-and-robbers calculation. Before I return to pursuit-evasion, the domination problem deserves to be seen on its own terms.

---

## 1. The first calculation: how large is a ball?

The geometry starts with a one-line function. I mean that literally.

```python
import mpmath as mp


def tree_ball_volume(d: int, h: int) -> mp.mpf:
    """Radius-h volume of the infinite d-regular tree."""
    if d < 3:
        raise ValueError("d must be at least 3")
    if h < 0:
        raise ValueError("h must be nonnegative")
    b = d - 1
    return mp.mpf(1) + d * (mp.power(b, h) - 1) / (d - 2)
```

If every chosen vertex covers at most $B_h$ vertices, pure volume counting gives

$$
\gamma_h(G)\ge \frac{n}{B_h}.
$$

That bound is occasionally attainable, on graphs organized precisely enough to make it tight — perfect covering codes are the cleanest examples of what such organization looks like. A typical random graph is not organized. Its neighborhoods overlap wastefully, and covering the last few stubborn vertices costs extra. The question is how much extra, and the coupon heuristic gives the first honest guess.

For a random selected set of density $\alpha$, a particular radius-$h$ ball is missed with probability roughly

$$
(1-\alpha)^{B_h}\approx e^{-\alpha B_h}.
$$

There are about $\exp(nH(\alpha))$ sets of density $\alpha$, with $H$ the binary entropy. Balancing the entropy of choosing the set against the probability that it happens to cover everything predicts the coordinate

$$
\alpha B_h
\approx
\log B_h-2\log\log B_h.
$$

The helper below computes a point just below that predicted transition.

```python

def near_critical_coordinate(
    d: int,
    h: int,
    W: mp.mpf | None = None,
) -> mp.mpf:
    """Return C = log B_h - 2 log log B_h - W."""
    B = tree_ball_volume(d, h)
    L = mp.log(B)
    if W is None:
        W = mp.log(L)
    return L - 2 * mp.log(L) - W
```

The theorem says this heuristic scale survives optimization over the selected set, and that survival is the whole difficulty. A minimum dominating set is not sampled independently of anything. It sees the graph and gets to arrange itself around the overlaps, and there is no a priori reason a clever arrangement could not beat the coupon prediction.

---

## 2. Where the problem came from

The [preceding project](/essays/branch-based-local-capture-in-tree-balls/) studied a rigid local certificate in the cops-and-robbers game. Around a fixed robber position, every outward nonbacktracking path indexed a descendant "tube," and if every tube held a cop, then every surviving round ended in capture, blockage, or pressure from at least two branches. It was a clean local statement, and it left an obvious global question hanging over it: could one cop placement, chosen once, hit every such tube for every possible robber root at the same time?

At first this looked like a monstrous hypergraph problem — many roots, exponentially many paths through each — and I spent far longer than I would like to admit intimidated by it. There is a useful simplification: a tube from an admissible tree-ball root remembers nothing^[I think we mathematicians should really have a term for amnesia. We have the [Markov Property](https://en.wikipedia.org/wiki/Markov_property), but can we facetciously generalize further?] about the interior of its indexing path. It remembers only its **terminal directed edge** and the unused residual radius

$$
h=R-t.
$$

For a directed edge $p\to w$, the associated set is the forward cone from $w$ of depth $h$, with the branch back through $p$ excluded. If every incoming directed edge at every vertex is represented, and the relevant balls are trees, hitting those cones is equivalent to having selected vertices in at least two branches at every unselected vertex.

There is a qualification I originally missed: allowing every *admissible* root does not ensure that every directed edge is represented. The original hypergraph includes only roots whose radius-$R$ balls are trees. Its tubes can all be hit while other vertices remain undominated; the [branch paper's global-overlap section](/essays/branch-based-local-capture-in-tree-balls/#rem-admissible-roots) gives an explicit cubic counterexample. The terminal-edge simplification therefore motivates a stronger graph-general question, rather than identifying the unrestricted transversal problem with domination.

A set $S$ is **internally two-path $(h,2)$-dominating** if every $v\notin S$ has two paths of length at most $h$ from $v$ to $S$ whose only shared vertex is $v$. Any such set is automatically ordinary distance-$h$ dominating, because either path on its own already witnesses a selected vertex within distance $h$.

So, a lower bound for ordinary distance-$h$ domination is, for free, a lower bound for internally two-path domination. This stronger all-vertex certificate keeps its logarithmic overhead. Transferring that conclusion to the original tube hypergraph requires an additional hypothesis ensuring its coverage condition implies domination; tree geometry at only the admissible roots does not supply it.

It does **not** say that cops need $\sqrt n\log n$ in the actual game. Adaptive strategies, partial coverage, motion between epochs, and entirely different certificates all remain outside the argument, exactly as they did in the previous paper. I will return to how narrow this obstruction is, deliberately, at the end. For now it is enough that the pursuit question handed the domination problem a reason to care about the scale $B_h\asymp\sqrt n$, and then got out of the way.

---

## 3. Why the coupon heuristic is not a proof

The direct concentration approach dies on the scale of the problem, and it dies quickly. Changing a single pairing in the configuration model can flip the radius-$h$ coverage status of on the order of $B_h$ vertices. The natural Lipschitz constant therefore grows on precisely the scale I need to resolve, which means the usual bounded-differences machinery is not merely weak here, but rather calibrated to lose.

The overlap is just as unforgiving. The events "the ball around $v$ is uncovered" and "the ball around $w$ is uncovered" share most of their mass. At $B_h\asymp\sqrt n$ this is exactly the birthday-collision scale for random regular neighborhoods. What made the problem exact was giving up on balls entirely and tracking **distances** instead.

Given a candidate set $S$, label every vertex by

$$
\ell(v)=\operatorname{dist}(v,S)\in\{0,1,\ldots,h\}.
$$

These labels obey two entirely local rules:

1. labels on adjacent vertices differ by at most one;
2. every vertex of positive label $i$ has a neighbor of label $i-1$.

And the rules run in reverse: any labeling obeying them is forced to be genuine graph distance. Descending labels trace a path down to label zero of exactly the stated length, and no path leaving label zero can climb by more than one per edge. The two inequalities pin the label to the distance from both sides.

That observation may come across as elementary, but it is the hinge of the whole paper. It removes any need to pretend random neighborhoods are trees. The labels are honest distances on the honest graph, and it turns the first moment into an exact method-of-types calculation. The price, which I did not appreciate until much later, is a nonconcave variational problem whose optimizer I would have to pin down uniformly as the number of levels grew. I traded an intractable probabilistic estimate for a hard but finite optimization.

---

## 4. The local entropy that appears in the type count

At a vertex of label $i>0$, at least one of its $d$ incident half-edges has to descend to label $i-1$. Suppose each coordinate carries descending marginal $a$. The maximum-entropy distribution over nonempty subsets of the $d$ half-edges is then an exponentially tilted law, and its marginal and entropy are

$$
a=
\frac{\lambda(1+\lambda)^{d-1}}
{(1+\lambda)^d-1},
$$

$$
s_d(a)=
\log\big((1+\lambda)^d-1\big)
-da\log\lambda.
$$

The numerics need care near the Moore-growth boundary $a=1/d$, where $\lambda$ can be exponentially small and a naive inversion silently underflows.

```python

def _conditioned_marginal(d: int, lam: mp.mpf) -> mp.mpf:
    """Marginal in a nonempty tilted subset of [d]."""
    log1p_lam = mp.log1p(lam)
    numerator = lam * mp.exp((d - 1) * log1p_lam)
    denominator = mp.expm1(d * log1p_lam)
    return numerator / denominator


def lambda_from_marginal(d: int, a: mp.mpf) -> mp.mpf:
    """Invert the conditioned-subset marginal in log lambda."""
    a = mp.mpf(a)
    lower = mp.mpf(1) / d
    if a < lower or a > 1:
        raise ValueError("a must lie in [1/d, 1]")

    tol = mp.power(10, -(mp.mp.dps - 12))
    if abs(a - lower) <= tol:
        return mp.mpf(0)
    if abs(a - 1) <= tol:
        return mp.inf

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
    """Maximum entropy s_d(a) with the all-zero pattern excluded."""
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
```

The precision-scaled endpoint is not fussiness for its own sake. An early independent audit by [Claude Fable 5](https://www.anthropic.com/claude/fable) found that a fixed lower cutoff in the $\lambda$ solver was quietly clamping the deep layers and manufacturing false KKT residuals. The whole computation lives exactly where the asymptotic coordinates separate exponentially. How you handle the endpoints *is* part of the mathematics, not just an implementation detail beneath it.[^audit]

[^audit]: I have come to treat "it's just a numerical detail" as a (not so) small alarm bell. For this problem in particular, it was never once true.

---

## 5. The exact compact functional

Let

$$
x_i=q_{i-1,i},\qquad 1\le i\le h,
$$

be the directed-edge mass between adjacent distance levels, and let

$$
\ell_i=q_{i,i},\qquad 0\le i\le h,
$$

be the same-level edge mass. The layer masses are

$$
p_i=\ell_i+x_i+x_{i+1},
$$

with $x_0=x_{h+1}=0$. Put

$$
a_i=\frac{x_i}{p_i},
\qquad
 y_i=p_i-x_i.
$$

After optimizing out the full local neighbor-count profile, the exact annealed functional collapses to

$$
\begin{aligned}
\mathcal F_{d,h}
={}&(d-1)\alpha\log\alpha\\
&+\sum_{i=1}^h
\left[
-p_i\log p_i
+p_i s_d(a_i)
+d y_i\log y_i
\right]\\
&-\frac d2\sum_{i=0}^h\ell_i\log\ell_i,
\end{aligned}
$$

with $\alpha=p_0$. The reduction from the full profile to this $2h+1$-variable object is exact, not an approximation I am hoping is harmless. The exactness is proved in the preprint and it is what lets me trust the code below to be computing the real thing.

The implementation follows the displayed formula line for line.

```python

def _xlogx(x: mp.mpf) -> mp.mpf:
    return mp.mpf(0) if x == 0 else x * mp.log(x)


def compact_microcanonical_value(d, h, x, ell):
    """Evaluate the exact compact functional."""
    xx = [mp.mpf(0)] + [mp.mpf(v) for v in x] + [mp.mpf(0)]
    ll = [mp.mpf(v) for v in ell]
    p = [ll[i] + xx[i] + xx[i + 1] for i in range(h + 1)]

    if abs(sum(p) - 1) > mp.power(10, -(mp.mp.dps // 2)):
        raise ValueError("profile is not normalized")

    alpha = p[0]
    value = (d - 1) * _xlogx(alpha)

    for i in range(1, h + 1):
        if p[i] == 0:
            continue
        lower = mp.mpf(1) / d
        a_i = xx[i] / p[i]
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
```

The full type count is two-sided. For each integer type, its expected count in the pairing model is an explicit ratio of factorials; uniform Stirling estimates identify its exponential rate with $\mathcal F_{d,h}$ up to $O_d(h\log n)$. The lower side of that estimate is the one I nearly overlooked. Because the expected number of any single type cannot exceed the total number of subsets of the corresponding size, it hands over the pointwise anchor

$$
\Psi_{d,h}(\alpha)\le H(\alpha).
$$

An earlier working note of mine called this "the trivial counting bound" and moved on. It was not trivial, and it was not something to move on from. It turned out to be the last missing lemma in the first-moment theorem, and I had worked it out long before I understood I already had it.[^trivial]

[^trivial]: There is probably a general lesson here about the things one labels "trivial" in one's own notes. I have chosen not to learn it and will surely repeat the mistake.

---

## 6. A failed concavity conjecture

Once the profile was down to $2h+1$ variables, the functional looked numerically docile near the low density stationary branch. The obvious conjecture, and the one I wanted to be true, was that it might simply be concave throughout the slack region. 

An adversarial Hessian search turned up profiles with genuinely positive constrained curvature. They had a recognizable shape: most layers sitting near capacity-saturated Moore growth, with a few isolated layers carrying much heavier same-level edge mass. Finite differences confirmed the positive eigenvalues of the analytic Hessian, so this was not a precision artifact, and the outcome I had wished for was, as is often the case in mathematics, completely dead.

The failure was, perhaps, the most useful thing that happened to the proof. It is interesting how failure is often the most useful outcome, contrary to how we perceive it. The positive curvature profiles were not stationary, as they were bumps off to the side, not competing maxima. This meant the right target was never concavity at all. It was **uniqueness of stationary points, together with boundary repulsion**. The proof then reassembled itself into something much cleaner than the one I had been trying to force:

- entropy singularities repel every boundary face;
- so every maximizer is an interior KKT point;
- the stationary equations admit an exact reverse transfer;
- that reverse transfer is order preserving;
- activity increases strictly along its single terminal parameter;
- so there is exactly one stationary point at each activity;
- and it has to be the unique global maximizer.

A nonconcave function is perfectly entitled to a unique global optimizer. Here it is monotone dynamics, not curvature, that supplies globality. I do not think I would ever have gone looking for the dynamics had the concavity conjecture not first embarrassed me out of the supposed easy route.

---

## 7. The exact reverse transfer

The stationary equations can be carried by two positive messages per distance level. Taking ratios, let

$$
\rho_i=\frac{B_i}{A_i},
\qquad
u_i=\frac{A_{i+1}}{A_i},
\qquad
v_i=\rho_i+u_i.
$$

At the terminal wall, $u_h=0$ and $v_h=\rho_h$. Given the next state $(\rho',v')$, the preceding state is fully explicit.

```python

def _w_e(rho: mp.mpf, b: int):
    """w=(1-rho)^(1/b), e=1-w, evaluated stably."""
    log_w = mp.log1p(-rho) / b
    return mp.exp(log_w), -mp.expm1(log_w)


def reverse_step(rho_next: mp.mpf, v_next: mp.mpf, b: int):
    """Invert one stationary transfer step, excluding the endpoint (1,1)."""
    if not (0 < rho_next <= v_next <= 1 and rho_next < 1):
        raise ValueError("require 0 < rho <= v <= 1 and rho < 1")
    w, e = _w_e(rho_next, b)
    R = v_next * e / w
    M = mp.power(e + w / v_next, b)
    denominator = R + M
    rho = R / denominator
    v = (1 + R) / denominator
    return rho, v
```

This map is coordinatewise order preserving, and that single property does most of the load-bearing work in the globality proof. (I couldn't help myself quoting Fable here -- world, take note, THIS was the result out of them all that Fable, under the role of auditor, called load-bearing.)^[This is a humorous interjection, for those of you who don't use Claude often. Claude models have a tendency to call anything that has some type of impact on the bigger picture "load-bearing," using this phrase obsessively to the point that it should probably be considered the new em dash. It is somewhat less of a tragedy; at least I and other reasonable humans greatly enjoyed usage of the dash in our personal writing. I don't think I've ever used the phrase "load bearing" in an organic sense, ever.] Start from a larger terminal value and every preceding $\rho$ coordinate comes out larger. The reconstructed activity is strictly increasing right along with it. The entire positive stationary family is therefore one-dimensional and uniquely parametrized by activity, which is exactly the uniqueness the failed concavity conjecture had been standing in for.

For computation, it is far better to parametrize the terminal value as

$$
t=-\log(1-s),
\qquad s=1-e^{-t}.
$$

Near high density, $s$ becomes indistinguishable from one at ordinary precision while $t$ stays comfortably moderate. This is a small change with a large payoff, the kind of thing one only learns by watching a doomed solver quietly and blissfully lose all its digits at large $h$.

---

## 8. Reconstructing the stationary point

The central routine does four things in order:

1. reverse-iterate from the terminal wall;
2. reconstruct the messages $A_i,B_i$;
3. compute density and activity at the root;
4. evaluate the free energy through *both* a direct partition-function route and a stable root-only route.

The shipped file carries the full dataclass with all the residual fields; the core calculation is below.

```python
from dataclasses import dataclass


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


def _stable_power_difference(S, B, power):
    """Compute S^power-(S-B)^power without cancellation."""
    ratio = B / S
    return mp.power(S, power) * (
        -mp.expm1(power * mp.log1p(-ratio))
    )
```

```python

def stationary_from_terminal_t(
    d: int,
    h: int,
    terminal_t: mp.mpf,
    *,
    validate_compact: bool = True,
) -> StationaryPoint:
    b = d - 1
    t = mp.mpf(terminal_t)
    terminal = -mp.expm1(-t)

    rho = [mp.mpf(0)] * (h + 1)
    v = [mp.mpf(0)] * (h + 1)
    u = [mp.mpf(0)] * (h + 1)
    rho[h] = v[h] = terminal

    for i in range(h - 1, 0, -1):
        rho[i], v[i] = reverse_step(rho[i + 1], v[i + 1], b)
        u[i] = v[i] - rho[i]
    u[h] = mp.mpf(0)

    # Root reconstruction.
    w1, e1 = _w_e(rho[1], b)
    r0 = v[1] * e1 / w1
    kappa = mp.power(v[1] / w1, b)
    z = r0 * kappa / mp.power(1 + r0, b)

    # Normalize A_1=1 and rebuild the messages.
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
        vertex_terms.append(
            _stable_power_difference(S[i], Bmsg[i - 1], d)
        )

    Zv = mp.fsum(vertex_terms)
    Ze = mp.fsum(value * value for value in Bmsg)
    Ze += 2 * mp.fsum(Bmsg[i] * A[i + 1] for i in range(h))

    alpha = Bmsg[0] * (Bmsg[0] + A[1]) / Ze
    phi_direct = mp.log(Zv) - mp.mpf(d) / 2 * mp.log(Ze)
    psi_direct = phi_direct - alpha * mp.log(z)
```

The exact telescoping identity is

$$
Z_v=\kappa Z_e.
$$

It is what lets me trade the direct partition-function route for root-only formulas that are far better conditioned than subtracting two enormous logarithms and praying.

```python
    phi_root = (
        mp.log(z)
        + mp.mpf(d) / 2 * mp.log((1 + r0) / r0)
        + mp.mpf(d - 2) / 2 * mp.log(alpha)
    )

    psi_root = (
        (1 - alpha) * mp.log(kappa)
        - (mp.mpf(d - 2) / 2 + alpha) * mp.log(r0)
        + mp.mpf(d - 2) / 2 * mp.log(alpha)
        + (
            mp.mpf(d - 1) * alpha
            - mp.mpf(d - 2) / 2
        ) * mp.log(1 + r0)
    )
```

The routine then checks the stationary equations, reconstructs the compact profile

$$
x_i=\frac{B_{i-1}A_i}{Z_e},
\qquad
\ell_i=\frac{B_i^2}{Z_e},
$$

and confirms that the compact functional agrees with the root-only free energy.

```python
    stationarity = [
        abs(kappa * Bmsg[0] - z * mp.power(S[0], b))
    ]
    for i in range(1, h + 1):
        stationarity.append(
            abs(kappa * A[i] - mp.power(S[i], b))
        )
        stationarity.append(
            abs(
                kappa * Bmsg[i]
                - _stable_power_difference(
                    S[i], Bmsg[i - 1], b
                )
            )
        )

    if validate_compact:
        x = [
            Bmsg[i - 1] * A[i] / Ze
            for i in range(1, h + 1)
        ]
        ell = [
            Bmsg[i] * Bmsg[i] / Ze
            for i in range(h + 1)
        ]
        compact_value, compact_alpha = compact_microcanonical_value(
            d, h, x, ell
        )
        compact_residual = max(
            abs(compact_value - psi_root),
            abs(compact_alpha - alpha),
        )
    else:
        compact_residual = mp.nan
```

This is in many ways the computational core. It finds one exact finite-$h$ stationary orbit and audits every identity that the theory says must hold on it. The asymptotic proof does not lean on any of these numbers. What the code provides is thus a hostile, independent witness that the analytic estimates are describing the object I think they are.

---

## 9. Solving for a target density

The theorem is phrased in terms of

$$
C=\alpha B_h.
$$

Because terminal parameter, activity, and density all increase together, I can solve $\alpha B_h=C$ by bisection in the stable coordinate $t$ and never worry about which branch I am on.

```python

def solve_for_alpha_B(d, h, C, iterations=None):
    """Solve alpha B_h = C by bisection in terminal_t."""
    B = tree_ball_volume(d, h)
    target_alpha = mp.mpf(C) / B
    if iterations is None:
        iterations = max(140, 2 * mp.mp.dps)

    D = mp.mpf(d) / (d - 2)
    lo = mp.mpf("0.05") * C / D
    hi = mp.mpf("3.0") * C / D + 1

    while stationary_from_terminal_t(
        d, h, lo, validate_compact=False
    ).alpha > target_alpha:
        lo /= 2

    while stationary_from_terminal_t(
        d, h, hi, validate_compact=False
    ).alpha < target_alpha:
        hi *= 2

    for _ in range(iterations):
        mid = (lo + hi) / 2
        point = stationary_from_terminal_t(
            d, h, mid, validate_compact=False
        )
        if point.alpha < target_alpha:
            lo = mid
        else:
            hi = mid

    return stationary_from_terminal_t(
        d, h, (lo + hi) / 2, validate_compact=True
    )
```

At the near-critical coordinate, the activity law is

$$
-\log z
=
\log\frac1\alpha
+B_h(1-\alpha)^{B_h}(1+o(1)),
$$

so the quantity

$$
\frac{-\log z-\log(1/\alpha)}
{B_h(1-\alpha)^{B_h}}
$$

ought to tend to one.

---

## 10. Numerical conditioning is part of the result

Two computational failures materially shaped how I worked, and I am keeping them in the write-up rather than sanding them out. This is the spirit of the website; much like the [living documents](https://levineuwirth.org/colophon.html#living-documents) that the Colophon describes, I will not hide the work that I supersede.

The first was the infuriating variant of mundane. An early comparison table mixed stationary values generated by two different solver versions, and one cubic $h=12$ entry came out wrong by about $2\times10^{-4}$. The asymptotic conclusion was untouched, as the error was far too small to matter for the theorem, but the table was no longer reproducible from the shipped code, which is its own kind of unacceptable.

The second was more serious. Direct evaluation of

$$
\Psi=
\log Z_v-\frac d2\log Z_e-\alpha\log z
$$

turned catastrophically ill-conditioned near criticality. The expression subtracts two large logarithms to recover a very small number, and at cubic $h=52$, simply raising the working precision changed the reported ratio visibly. This is a glaring red flag. Lost digits! The stable root-only formula was right, and the direct route was quietly bleeding precision the whole time.

My response was the small principle that this section is really about: make the residuals **gate** the output rather than merely decorate it.

```python

def gate_point(point, route_tolerance="1e-6"):
    """Reject a row if independent routes disagree too much."""
    tol = mp.mpf(route_tolerance)
    if point.psi_root == 0:
        raise RuntimeError("zero root-formula exponent")

    route_disagreement = abs(
        point.root_micro_residual / point.psi_root
    )
    if route_disagreement > tol:
        raise RuntimeError(
            "microcanonical routes disagree: "
            f"relative discrepancy={route_disagreement}; "
            "increase mp.dps"
        )

    if point.compact_residual > mp.sqrt(tol):
        raise RuntimeError(
            "compact reconstruction failed: "
            f"{point.compact_residual}"
        )
```

The diagnostic row then keeps both routes, every major residual, the working precision, and a SHA-256 digest of the source file (aren't you amazed I didn't use BLAKE3?), so that any number I report can be traced back to the exact bytes that produced it.

```python

def diagnostic_row(d, h, W=None):
    B = tree_ball_volume(d, h)
    L = mp.log(B)
    if W is None:
        W = mp.log(L)
    C = near_critical_coordinate(d, h, W)

    point = solve_for_alpha_B(d, h, C)
    gate_point(point)

    coupon = B * mp.power(1 - point.alpha, B)
    activity_ratio = (
        -mp.log(point.z) - mp.log(1 / point.alpha)
    ) / coupon
    scale = mp.exp(-C)

    return {
        "d": d,
        "h": h,
        "dps": mp.mp.dps,
        "B_h": mp.nstr(B, 30),
        "C": mp.nstr(C, 24),
        "alpha_B_h": mp.nstr(point.alpha * B, 24),
        "terminal_t": mp.nstr(point.terminal_t, 30),
        "activity_ratio": mp.nstr(activity_ratio, 20),
        "minus_psi_over_exp_minus_C": mp.nstr(
            -point.psi_root / scale, 20
        ),
        "psi_root": mp.nstr(point.psi_root, 24),
        "psi_direct": mp.nstr(point.psi_direct, 24),
        "route_relative_disagreement": mp.nstr(
            abs(point.root_micro_residual / point.psi_root), 12
        ),
        "stationarity_residual": mp.nstr(
            point.stationarity_residual, 12
        ),
        "telescoping_residual": mp.nstr(
            point.telescoping_residual, 12
        ),
        "compact_residual": mp.nstr(
            point.compact_residual, 12
        ),
        "source_sha256": hashlib.sha256(
            Path(__file__).read_bytes()
        ).hexdigest(),
    }
```

> If an internal cross-check is comparable in size to the quantity you are reporting, it should be a gate, not an unprinted field in a dataclass.

---

## 11. What the computation shows

Running the demonstration script with $W_h=\log\log B_h$ gives the following.

| $d$ | $h$ | $C$ | activity-law ratio | $-\Psi/e^{-C}$ |
|---:|---:|---:|---:|---:|
| 3 | 12 | 2.6889 | 0.4376 | 0.3870 |
| 3 | 20 | 6.8451 | 0.5873 | 0.6484 |
| 3 | 30 | 12.6345 | 0.9520 | 0.9418 |
| 3 | 40 | 18.7408 | 0.9956 | 0.9757 |
| 4 | 12 | 5.9859 | 0.6816 | 0.7285 |
| 4 | 20 | 13.3029 | 0.9915 | 0.9706 |
| 4 | 28 | 21.1087 | 0.9999 | 0.9800 |

The asymptotic theorem asks only for a conservative negative bound, so in a sense these numbers are more than it needs. But I'd argue they clearly earn their place: both ratios march toward one, and the convergence is visibly slow precisely when the coefficient $C/\log B_h$ is small. This is exactly what the proof's fixed-compact-window uniformity predicts, and exactly what a claim of uniformity all the way down to zero would *not* look like. The table is quietly consistent with the shape of the theorem, not just its sign.

The generator is satisfyingly short.

```python

def make_table(cases, csv_path=None):
    rows = []
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
            writer = csv.DictWriter(
                handle,
                fieldnames=list(rows[0].keys()),
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(rows)
    return rows
```

The complete script also carries optional plotting for the activity-law and free-energy ratios, for those  who would rather watch the convergence than read it off a table.

---

## 12. How the proof uses the orbit

The code finds one exact finite-$h$ stationary orbit. The proof has to understand that orbit *uniformly* as $h\to\infty$, which is a different and harder demand, and it is where the analysis actually happens.

There are two exact outer regimes. On the **free side**, a transverse defect $q_i$ is tiny and the main coordinate rides the free-coverage orbit. On the **stable side**, the occupied-message coordinate $\rho_i$ is tiny and the orbit approaches the empty-root manifold. I choose a matching layer where both transverse quantities are exponentially small at once, and shadow the true orbit against whichever exact outer solution is nearby.

The reverse map supplies one-step estimates that stay uniform even as the main coordinate itself shrinks toward nothing. A small error in $1-\rho_i$ alone does not control the much smaller $\rho_i$: the proof transports $\lambda_i=-\log(1-\rho_i)$ multiplicatively and sums the transverse errors. That extra estimate supplies the relative accuracy needed at the matching layer. It yields

$$
\alpha=a_h(t)(1+o(1)),
$$

with

$$
a_h(t)=1-e^{-t/(d-1)^h},
$$

and

$$
\frac{x}{(d-1)^{h-1}}
=(1-\alpha)^{B_h}(1+o(1)),
$$

where $x=-\log u_1$ is the stable root coordinate. The edge normalizer localizes at the overlap layer, which is what converts the transported message density into the actual selected density. Root reconstruction then delivers the activity law

$$
-\log z(\alpha)
=
\log\frac1\alpha
+B_h(1-\alpha)^{B_h}(1+o(1)).
$$

The globality theorem supplies the envelope identity

$$
\Psi'_{d,h}(\alpha)=-\log z(\alpha),
$$

and integrating it from a slightly larger density, anchored at the upper endpoint by

$$
\Psi_{d,h}(\alpha)\le H(\alpha),
$$

gives

$$
\Psi_{d,h}(C/B_h)
\le
-\left(\frac12-o(1)\right)e^{-C}
$$

uniformly across the near-critical window. The first moment then closes the random-graph statement, provided the exponential negative term outweighs the $O_d(h\log n)$ type-counting error — which is precisely the growth condition on $W_h$ that the theorem carries out front, now visibly earning its place.

---

## 13. What the theorem says about the stronger all-vertex certificate

The pursuit application now has a precise scope.

The original local certificate placed a cop in every path tube at a *known* admissible root. Its global hypergraph tests the terminal directed edges reachable from such roots. If those edges exhaust all directed edges and the relevant balls are trees, coverage gives the two-branch condition at every unselected vertex. Without that additional coverage hypothesis, the original hypergraph need not even imply ordinary domination.

Internally two-path $(h,2)$-domination imposes its condition at every vertex and implies ordinary distance-$h$ domination on every graph. At $B_h\asymp\sqrt n$, the theorem therefore requires

$$
\Omega(\sqrt n\log n)
$$

selected vertices with high probability for this stronger certificate. That obstructs a Meyniel-scale placement based on internally two-path domination. It does not close the original admissible-root transversal problem, nor does the comparison scale make all radius-$R$ balls in a random regular graph trees.

---

## 14. The bounded window and the remaining problems

### The bounded critical window is now proved

The near-critical argument above reaches

$$
\log B_h-2\log\log B_h-W_h
$$

for every $W_h\to\infty$. The current preprint goes further: with $L_h=\log B_h$, uniformly for bounded $s$,

$$
\frac{B_h}{L_h^2}\Psi_{d,h}\!\left(
\frac{L_h-2\log L_h+s}{B_h}\right)\longrightarrow1-e^{-s}.
$$

The additional ingredient is an explicit capped-free profile whose entropy loss supplies the matching upper bound on the entropy defect. Together with quantitative orbit matching, this pins the annealed transition to the scalar balance

$$
H(C/B_h)=(1-C/B_h)^{B_h},
$$

to within $B_h^{-1/7+o(1)}$ in the coordinate $C$. In particular,

$$
C=
L_h-2\log L_h+\frac{3\log L_h-1}{L_h}
+O\!\left(\frac{(\log L_h)^2}{L_h^2}\right).
$$

The corresponding random-regular lower bound now allows any fixed slack $\omega>0$ in place of $W_h$, under $nL_h^2/B_h\gg h\log n$. This settles the annealed window; existence of dominating sets near that crossing remains a separate question.

### Quenched matching

What I have for the random graph is a lower bound. In ideal tree-ball geometry, a simple random placement followed by patching the uncovered vertices gives an upper bound of order

$$
\frac{n\log B_h}{B_h},
$$

but it does not pin the actual domination number to the annealed transition. A matching quenched result likely wants a second moment, small-subgraph conditioning, or a genuinely problem-specific construction. I do not yet know which, so let me know if you do.

### The direct two-branch constant

Ordinary distance domination is only a relaxation of internally two-path domination, so the direct branch problem should carry its own coupon balance and, quite possibly, a different leading constant. One has to remember branch multiplicity, and cycles can make the message representations non-unique — I have left it as its own piece of work rather than forcing it into this one.

---

## 15. Why I am showing so much Python

The code was never a numerical appendix bolted onto a finished proof. It kept reaching back into the mathematics and rearranging it, and I can name some of the specific occasions:

- exact ILPs exposed the terminal-edge structure of the tube hypergraph and motivated the stronger all-vertex domination problem;
- transfer numerics suggested the $\log B_h-2\log\log B_h$ scale before I could prove it;
- an independent implementation caught a stale stationary value hiding in a comparison table;
- Hessian probes killed a plausible, load-bearing, and entirely false concavity conjecture;
- that dead conjecture is what redirected the proof toward boundary repulsion and reverse shooting;
- KKT checks exposed the last mechanical gap in the globality argument;
- residual-gated near-critical runs caught catastrophic cancellation in the direct free-energy route;
- and the stable root-only formula that fixed it became both a proof tool and the canonical way to evaluate everything.

The formal theorem depends on none of these numbers. The path to the theorem depended on almost nothing else — on code explicit enough to be reimplemented by some AI system who (rightfully so) did not trust me, and hostile enough to keep trying to break whatever conjecture I was currently in love with.

That is the role I want this page to preserve, and it is the reason it exists apart from the preprint at all. The paper records what turned out to be true. This page records how I found out which statements were even worth trying to prove — which is the part no theorem-and-proof ever shows you, and, if I am honest, the part I would most have wanted to read.
