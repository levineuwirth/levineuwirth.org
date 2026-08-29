---
title: "The Annealed Critical Window for Growing-Radius Domination in Random Regular Graphs"
date: 2026-07-22
revised:
  - date: "2026-07-24"
    note: "Superseded by a proof of the full bounded critical window and its universal scaling function; retitled and restructured to match the new preprint."
abstract: >
  A complete determination of the bounded annealed critical window for
  growing-radius domination in random regular graphs, resolving the open
  problem left by an earlier near-critical bound. Writing L_h = log B_h for
  the radius-h tree-ball volume, the annealed exponent obeys a universal
  scaling law (B_h/L_h^2) Psi_{d,h}((L_h - 2 log L_h + s)/B_h) -> 1 - e^{-s},
  and its lower zero is pinned to within B_h^{-1/7+o(1)} of the scalar
  coupon-collector root H(C/B_h) = (1-C/B_h)^{B_h}, giving a complete
  fixed-order inverse-logarithmic expansion. The proof adds a quantitative
  reverse-transfer error analysis and an explicit capped-free profile whose
  only entropy loss is the cost of one terminal nonemptiness event,
  sharpening the earlier annealed lower bound into a two-sided window
  theorem. The result again strengthens to internally two-path domination, a
  graph-general parameter motivated by exhaustive static tube coverage in
  pursuit-evasion games. Quenched matching and the direct two-branch leading
  constant remain open.
tags:
  - research
  - research/mathematics
  - research/graph-theory
authors:
  - "Levi Neuwirth | /me.html"
bibliography: data/growing-radius-domination-preprint.bib
preprint: /papers/near-critical-growing-radius-domination-paper.pdf
no-collapse: true
status: "Durable"
confidence: proved
evidence: 5
peer-status: unreviewed
result-shape: mixed
further-reading:
  - AignerFromme
  - LuPeng
  - ScottSudakov
  - PralatWormald
  - PralatWormaldRegular
  - NeuwirthBranchCapture
  - Wormald
  - Janson
  - CohenHonkalaLitsynLobstein
  - Duckworth
  - DuckworthWormald
  - CutlerRadcliffe
  - GlebovLiebenauSzabo
  - ZhaoHabibullaZhou
  - HabibullaQin
  - RockafellarWets
history:
  - date: "2026-07-27"
  - date: "2026-07-24"
  - date: "2026-07-22"

---

# Introduction and Related Work {#sec-intro}

## Main result and scale

A set $S\subseteq V(G)$ is *distance-$h$ dominating* if every vertex of $G$ lies within graph distance $h$ of $S$; its minimum size is denoted $\gamma_h(G)$. For graphs of maximum degree $d$, one selected vertex can cover at most

$$
B_h=1+d\frac{(d-1)^h-1}{d-2}
$$

vertices, so the elementary volume bound is $\gamma_h(G)\ge n/B_h$. In ideal tree-ball geometry, independent selection and patching place the natural covering scale at $n\log B_h/B_h$.

The first-moment balance is subtler than the leading scale. If $\alpha=C/B_h$, subset entropy is approximately $C(\log B_h-\log C+1)/B_h$, while the probability that a tree ball is missed is approximately $e^{-C}$. Equating these terms predicts

$$
C=\log B_h-2\log\log B_h+O(1).
$$

This paper determines that bounded annealed window and its entire limiting profile. With $L_h=\log B_h$, uniformly for bounded $s$,

$$
\frac{B_h}{L_h^2}\Psi_{d,h}\!\left(\frac{L_h-2\log L_h+s}{B_h}\right)\longrightarrow 1-e^{-s}.
$$

Thus the annealed exponent changes sign at $s=0$, and its lower zero is governed, to power accuracy in $B_h$, by the scalar equation

$$
H(C/B_h)=(1-C/B_h)^{B_h}.
$$

This gives not only the first two terms but the complete fixed-order inverse-logarithmic expansion of the annealed transition.

For the random graph itself, the first moment yields a fixed-slack lower theorem: for every fixed $\omega>0$, subject to

$$
\frac{n(\log B_h)^2}{B_h}\gg h\log n,
$$

one has with high probability

$$
\gamma_h(G_{n,d})\ge \frac n{B_h}\bigl(\log B_h-2\log\log B_h-\omega\bigr).
$$

At the comparison scale $B_h\asymp\sqrt n$, this is

$$
\gamma_h(G_{n,d})\ge \frac n{B_h}\bigl(\tfrac12\log n-2\log\log n-\omega+O(1)\bigr)=\Omega(\sqrt n\log n).
$$

This is an annealed lower transition, not a quenched matching theorem. Proving the existence of dominating sets at the same coordinate remains separate.

The comparison scale is also relevant to pursuit-evasion: Meyniel's conjecture predicts that $O(\sqrt n)$ cops suffice in every connected $n$-vertex graph [@LuPeng; @ScottSudakov], and it is known for several random-graph models, including random regular graphs [@PralatWormald; @PralatWormaldRegular]. Our conclusion is not a cop-number lower bound. It says that one particular static exhaustive coverage mechanism can require a logarithmic factor more than the Meyniel scale.

## Why the first moment is difficult

For an independent random subset of density $\alpha$, a fixed tree-like radius-$h$ ball is missed with probability approximately $(1-\alpha)^{B_h}$. Balancing subset entropy against this coupon term predicts the coordinate

$$
\alpha B_h\approx \log B_h-2\log\log B_h.
$$

Turning that heuristic into a theorem is not a product-measure calculation. In the configuration model, coverage events for different vertices overlap heavily, and optimizing over the selected set allows highly organized profiles. A direct bounded-differences argument is also ineffective in the growing-radius regime: changing one pairing can alter the radius-$h$ coverage status of order $B_h$ vertices, so the natural Lipschitz constant grows on exactly the scale that must be resolved.

The key device is to label every vertex by its *exact* distance to the candidate set. Local consistency of these labels — adjacent labels differ by at most one, and every positive label has a neighbor one level lower — forces them to be genuine graph distances on any graph. This removes the need to approximate neighborhoods by trees and converts the first moment into an exact finite-dimensional method-of-types problem. The price is a nonconcave variational functional whose global optimizer must be identified uniformly as the number of distance levels grows.

## Related work

The configuration or pairing model and its transfer to uniformly random simple regular graphs are standard; see Wormald's survey [@Wormald] and Janson's simplicity theorem [@Janson]. Fixed-radius domination in random regular graphs has been studied algorithmically: Duckworth analyzed randomized greedy algorithms for distance-$k$ dominating sets [@Duckworth], while Duckworth and Wormald treated independent domination [@DuckworthWormald]. The broader covering viewpoint is classical in coding theory [@CohenHonkalaLitsynLobstein].

The closest message-passing antecedents are statistical-mechanical. Zhao, Habibulla, and Zhou developed a cavity-method and belief-propagation treatment of minimum dominating sets [@ZhaoHabibullaZhou]; Habibulla and Qin studied a distance-two version with distance-labeled messages [@HabibullaQin]. Those works are replica-symmetric and fixed-radius. The transfer equations below are closely related in spirit; the distinctions here are the exact graph-level type count, the proof of global optimization, and the growing-radius asymptotics.

Cutler and Radcliffe used Shearer entropy to obtain universal extremal bounds for domination polynomials of regular graphs [@CutlerRadcliffe]. Such universal bounds cannot by themselves detect the random-covering penalty: structured regular graphs may admit efficient covering codes. In the binomial random graph, Glebov, Liebenau, and Szabó proved two-point concentration at the first-moment threshold in a sufficiently dense regime [@GlebovLiebenauSzabo]. That result motivates, but does not supply, the corresponding quenched statement for random regular graphs.

The pursuit application comes from branch-based local coverage. Aigner and Fromme introduced the multiple-cop game in its modern graph-theoretic form [@AignerFromme]; Prałat and Wormald later combined random placement with deterministic pursuit in random graphs [@PralatWormald; @PralatWormaldRegular]. The local tube certificate in [the branch-tube persistence theorem](/essays/branch-based-local-capture-in-tree-balls/index.html#thm-persistence) of [@NeuwirthBranchCapture] motivates a root-independent two-witness covering problem. [Section 2.1](#connection-with-static-tube-coverage) states the exact graph-general parameter used here and carefully limits the resulting obstruction.

## Proof architecture and contributions

The proof has four acts.

**Act I: exact types and a compact functional.** Exact distance labels produce a two-sided type estimate

$$
\log \mathbb E N_{\mathbf n}=n\Phi_{d,h}(\mathbf n/n)+O_d(h\log n).
$$

Optimizing the local profile entropy at fixed tridiagonal edge masses reduces $\Phi_{d,h}$ exactly to a compact functional $\mathcal F_{d,h}$ in $2h+1$ variables. The lower side of the type estimate also yields the pointwise entropy anchor $\Psi_{d,h}(\alpha)\le H(\alpha)$.

**Act II: globality without concavity.** The compact functional is genuinely nonconcave. Nevertheless, entropy singularities repel every maximizing profile from the boundary. Interior KKT points are equivalent to positive message solutions. An exact reverse transfer reconstructs every positive stationary solution from one terminal parameter, and the associated activity is strictly increasing from $0$ to $\infty$. Hence the grand-canonical optimizer is unique at every activity, and duality gives

$$
\Psi_{d,h}(\alpha)=\Psi^{\mathrm{stat}}_{d,h}(\alpha),\qquad \Psi_{d,h}'(\alpha)=-\log z(\alpha).
$$

**Act III: quantitative orbit matching.** The reverse orbit has exact stable and free outer solutions. They overlap over linearly many levels. Retaining the actual transverse errors gives, for $c=\alpha B_h/\log B_h<4/3$,

$$
-\log z(\alpha)-\log\frac1\alpha=B_h(1-\alpha)^{B_h}\left(1+B_h^{-c/4+o(1)}\right)+B_h^{-c/4+o(1)}.
$$

The restriction $c<4/3$ is exactly where the additive reconstruction error remains smaller than the coupon term.

**Act IV: one terminal conditioning cost.** An explicit capped-free profile agrees with the free Bernoulli tree law at every nonterminal layer. Its only entropy loss comes from conditioning the terminal lower-neighbor set to be nonempty. That loss is exactly

$$
p_h\Delta_d(\varepsilon_h),\qquad p_h\varepsilon_h^d=(1-\alpha)^{B_h},\qquad \Delta_d(\varepsilon)=\varepsilon^d(1+o(1)).
$$

This supplies the sharp upper bound on $H-\Psi$. Integrating the quantitative activity law supplies the matching lower bound and the universal scaling function $1-e^{-s}$.

The principal contributions are therefore: an exact growing-radius type count with no local-tree assumption; an exact compact reduction; a global solution of a nonconcave annealed variational problem; quantitative stable/free matching; and a bounded-window theorem anchored by a self-contained feasible profile. Quenched matching and direct two-branch asymptotics remain separate problems.

---

# Models, Notation, and Main Results {#sec-main}

Fix $d\ge 3$ throughout and put

$$
b=d-1,\qquad D=\frac{b+1}{b-1}=\frac{d}{d-2},
$$

$$
B_h=1+d\frac{b^h-1}{b-1}=Db^h-\frac{2}{b-1}.
$$

For a probability vector $r=(r_1,\ldots,r_k)$, write

$$
H(r)=-\sum_{j=1}^k r_j\log r_j,
$$

with $0\log 0=0$; for a scalar $a\in[0,1]$, $H(a)$ denotes the binary entropy $H(a,1-a)$.

| Notation | Meaning |
|---|---|
| $B_h$ | maximum radius-$h$ ball volume at degree $d$ |
| $\gamma_h(G)$ | minimum size of a distance-$h$ dominating set |
| $\Phi_{d,h}$ | full local-profile type functional |
| $\mathcal F_{d,h}$ | compact tridiagonal profile functional |
| $\Psi_{d,h}(\alpha)$ | microcanonical annealed exponent at density $\alpha$ |
| $z=e^\theta$ | grand-canonical activity |
| $b=d-1,\ D=d/(d-2)$ | recurring degree constants |

::: {#def-two-path .exhibit .exhibit--definition data-exhibit-type="definition" data-exhibit-name="Definition 1 (Internally two-path (h,2) domination)"}
**Definition 1** (Internally two-path $(h,2)$ domination). A set $S\subseteq V(G)$ is *internally two-path $(h,2)$ dominating* if every vertex $v\notin S$ has two $v$–$S$ paths of length at most $h$ whose only common vertex is $v$. In particular, the paths begin through distinct neighbors of $v$. Let $\gamma_{h,2}^{\mathrm{int}}(G)$ denote the minimum size of such a set.
:::

Every internally two-path $(h,2)$-dominating set is distance-$h$ dominating, since either witness path alone ends in $S$ within distance $h$. Therefore

$$
\gamma_{h,2}^{\mathrm{int}}(G)\ge \gamma_h(G).
$$

## Connection with static tube coverage

In the tree-ball setting of [@NeuwirthBranchCapture], a length-$t$ tube with residual depth $h=R-t$ depends, after the root is allowed to vary, only on its terminal directed edge. The resulting forward cone excludes one branch at its head. A root-independent set meets every such directed cone exactly when, at every unselected vertex, at least two distinct branches contain a selected vertex within distance $h$; in a tree-ball these are precisely the two internally disjoint paths of [Definition 1](#def-two-path). Thus internally two-path domination is a graph-general strengthening of the global exhaustive tube certificate.

Combining the displayed inequality above with the main theorem shows that any such exhaustive static certificate has size $\Omega(\sqrt n\log n)$ at the comparison scale $B_h\asymp\sqrt n$. Meyniel's conjecture concerns the existence of a fully adaptive winning strategy with $O(\sqrt n)$ cops, so there is no contradiction: the lower bound applies only to this static exhaustive mechanism. Partial coverage, adaptive reassignment, and epoch-based pursuit remain outside the argument.

The pairing model consists of $n$ labeled buckets of $d$ half-edges paired uniformly at random; conditioning the resulting multigraph on simplicity gives the uniformly random simple $d$-regular graph $G_{n,d}$, for $dn$ even. Let $Z_{n,d,h}(m)$ count distance-$h$ dominating $m$-sets in the pairing model.

For a distance-$h$ dominating set $S$, assign each vertex its exact label $\operatorname{dist}(v,S)\in\{0,\ldots,h\}$. The local consistency used below is equivalent to genuine distance: adjacent labels differ by at most one, and every positive label has a neighbor one level lower. The descending condition gives a path to label zero of the displayed length, while the Lipschitz condition gives the reverse inequality. No tree-neighborhood assumption is involved.

The type count developed below gives

$$
\log \mathbb E Z_{n,d,h}(m)\le n\Psi_{d,h}(m/n)+O_d(h\log(n+1)),
$$

uniformly in $h$. Here $\Psi_{d,h}$ is the exact annealed variational exponent.

::: {#thm-bounded-critical-window .exhibit .exhibit--theorem data-exhibit-type="theorem" data-exhibit-name="Theorem 2 (Bounded annealed critical window)"}
**Theorem 2** (Bounded annealed critical window). *Put $L_h=\log B_h$. For every fixed $M<\infty$, uniformly for*

$$
C=L_h-2\log L_h+s,\qquad |s|\le M,\qquad \alpha=C/B_h,
$$

*one has*

$$
H(\alpha)-\Psi_{d,h}(\alpha)=(1-\alpha)^{B_h}\left(1+o(1)\right).
$$

*More precisely,*

$$
1-B_h^{-1/7+o(1)}\le \frac{H(\alpha)-\Psi_{d,h}(\alpha)}{(1-\alpha)^{B_h}}\le 1+B_h^{-(d-2)/d+o(1)}.
$$

*All $o(1)$ terms are uniform over the displayed window.*
:::

::: {#cor-critical-scaling-function .exhibit .exhibit--corollary data-exhibit-type="corollary" data-exhibit-name="Corollary 3 (Critical scaling function)"}
**Corollary 3** (Critical scaling function). *Uniformly for bounded $s$,*

$$
\boxed{
\frac{B_h}{(\log B_h)^2}\Psi_{d,h}\!\left(\frac{\log B_h-2\log\log B_h+s}{B_h}\right)\longrightarrow 1-e^{-s}.
}
$$
:::

::: {#cor-annealed-zero-expansion .exhibit .exhibit--corollary data-exhibit-type="corollary" data-exhibit-name="Corollary 4 (Annealed zero and scalar expansion)"}
**Corollary 4** (Annealed zero and scalar expansion). *Let*

$$
\alpha_h^{\mathrm{ann}}=\inf\{\alpha:\Psi_{d,h}(\alpha)\ge0\},\qquad C_h^{\mathrm{ann}}=B_h\alpha_h^{\mathrm{ann}},
$$

*and let $\widehat C_{B_h}$ be the solution near $\log B_h-2\log\log B_h$ of*

$$
H(C/B_h)=(1-C/B_h)^{B_h}.
$$

*Then*

$$
C_h^{\mathrm{ann}}=\widehat C_{B_h}+O\!\left(B_h^{-1/7+o(1)}\right).
$$

*Writing $L=\log B_h$ and $\ell=\log L$,*

$$
C_h^{\mathrm{ann}}=L-2\ell+\frac{3\ell-1}{L}+\frac{5\ell^2-12\ell+3}{2L^2}+\frac{18\ell^3-81\ell^2+84\ell-17}{6L^3}+O\!\left(\frac{\ell^4}{L^4}\right).
$$
:::

::: {#thm-fixed-slack-random .exhibit .exhibit--theorem data-exhibit-type="theorem" data-exhibit-name="Theorem 5 (Fixed-slack random-regular lower bound)"}
**Theorem 5** (Fixed-slack random-regular lower bound). *Fix $\omega>0$. If $h=h(n)\to\infty$ and*

$$
\frac{n(\log B_h)^2}{B_h}\gg h\log n,
$$

*then, with high probability,*

$$
\gamma_h(G_{n,d})\ge \frac n{B_h}\left(\log B_h-2\log\log B_h-\omega\right).
$$

*The same conclusion holds for every stronger feasible-set notion, including internally two-path $(h,2)$ domination.*
:::

The following older-form consequences retain uniform information deeper in the subcritical region and will be useful for comparison.

::: {#thm-near-critical .exhibit .exhibit--theorem data-exhibit-type="theorem" data-exhibit-name="Theorem 6 (Near-critical annealed negativity)"}
**Theorem 6** (Near-critical annealed negativity). *Fix $\eta\in(0,1)$, put $L_h=\log B_h$, and let $W_h\to\infty$. Uniformly for real $C$ satisfying*

$$
\eta L_h\le C\le L_h-2\log L_h-W_h,
$$

*one has*

$$
\Psi_{d,h}(C/B_h)\le -\left(\frac12-o(1)\right)e^{-C}\qquad(h\to\infty),
$$

*where the $o(1)$ may depend on $d$, $\eta$, and the prescribed sequence $W_h$, but is uniform over the displayed interval.*
:::

::: remark
**Remark 7** (The coefficient $1/2$). The coefficient $1/2$ is not predicted to be sharp. It comes from the symmetric choice of the upper integration point in [Section 16](#sec-integration). The activity law and the diagnostics in [Section 17](#sec-numerics) are consistent with the normalized ratio approaching $1-O(e^{-W_h})$ deeper in the near-critical window.
:::

::: {#cor-fixed-fraction-slack .exhibit .exhibit--corollary data-exhibit-type="corollary" data-exhibit-name="Corollary 8 (Fixed-fraction slack)"}
**Corollary 8** (Fixed-fraction slack). *For every fixed $0<c_-\le c_+<1$, uniformly for $c\in[c_-,c_+]$,*

$$
\Psi_{d,h}\!\left(c\,\frac{\log B_h}{B_h}\right)\le -\left(\frac12-o(1)\right)B_h^{-c}.
$$
:::

::: {#thm-random-near-critical .exhibit .exhibit--theorem data-exhibit-type="theorem" data-exhibit-name="Theorem 9 (Random-regular near-critical lower bound)"}
**Theorem 9** (Random-regular near-critical lower bound). *Let $h=h(n)\to\infty$ and $W_h\to\infty$. Define*

$$
C_h^*=L_h-2\log L_h-W_h,
$$

*and suppose*

$$
\liminf_{n\to\infty}\frac{C_h^*}{L_h}>0,\qquad \frac{ne^{W_h}L_h^2}{B_h}\gg h\log n.
$$

*Then, with high probability,*

$$
\gamma_h(G_{n,d})\ge \frac{n}{B_h}\left(L_h-2\log L_h-W_h\right).
$$

*The same conclusion holds for every parameter whose feasible sets are necessarily distance-$h$ dominating, including internally two-path $(h,2)$ domination.*
:::

::: {#cor-fixed-fraction-random .exhibit .exhibit--corollary data-exhibit-type="corollary" data-exhibit-name="Corollary 10 (Fixed-fraction random lower bound)"}
**Corollary 10** (Fixed-fraction random lower bound). *For every fixed $\varepsilon\in(0,1)$, if*

$$
\frac{n}{B_h^{1-\varepsilon}}\gg h\log n,
$$

*then, with high probability,*

$$
\gamma_h(G_{n,d})\ge (1-\varepsilon)\frac{n\log B_h}{B_h}.
$$
:::

When $B_h\asymp\sqrt n$, one has $\log B_h=\tfrac12\log n+O(1)$, and [Theorem 9](#thm-random-near-critical) gives

$$
\gamma_h(G_{n,d})\ge \frac{n}{B_h}\left(\tfrac12\log n-2\log\log n-W_h+O(1)\right)=\Omega(\sqrt n\log n).
$$

The implicit constant in the final order statement depends on the comparison constants in $B_h\asymp\sqrt n$; no exact prefactor $\sqrt n$ is asserted.

---

# Two-Sided Exact Type Counting and the Entropy Anchor {#sec-types}

For completeness, we record the exact local-profile count that underlies both the variational formula and the pointwise entropy bound used later.

Let $\mathcal T_{d,h}$ be the finite set of local profiles

$$
\tau=(i,\mathbf c),\qquad i\in\{0,\ldots,h\},\quad \mathbf c=(c_0,\ldots,c_h),\quad \sum_jc_j=d,
$$

with

$$
c_j=0\quad\text{if }|i-j|>1,\qquad c_{i-1}\ge1\quad\text{if }i>0.
$$

For a probability vector $\xi=(\xi_\tau)_{\tau\in\mathcal T_{d,h}}$, put

$$
q_{ij}(\xi)=\frac1d\sum_{\tau=(i,\mathbf c)}\xi_\tau c_j,
$$

and call $\xi$ *feasible* when $q_{ij}=q_{ji}$. Its selected density is

$$
\alpha(\xi)=\sum_{\tau:\,i(\tau)=0}\xi_\tau.
$$

Define

$$
\Phi_{d,h}(\xi)=-\sum_\tau\xi_\tau\log\xi_\tau+\sum_\tau\xi_\tau\log\binom d{\mathbf c(\tau)}+\frac d2\sum_{i,j}q_{ij}(\xi)\log q_{ij}(\xi),
$$

with $0\log0=0$. The exact variational exponent is

$$
\Psi_{d,h}(\alpha)=\max\{\Phi_{d,h}(\xi):\xi\text{ feasible},\ \alpha(\xi)=\alpha\}.
$$

[Section 4.1](#exact-local-entropy-reduction) proves the exact reduction from this full profile functional to the compact tridiagonal functional of [Proposition 15](#prop-compact-functional).

::: {#thm-two-sided-count .exhibit .exhibit--theorem data-exhibit-type="theorem" data-exhibit-name="Theorem 11 (Two-sided count for one integer type)"}
**Theorem 11** (Two-sided count for one integer type). *There is a constant $K_d$ such that the following holds for every $h,n$ and every admissible integer profile $(n_\tau)_{\tau\in\mathcal T_{d,h}}$. Put*

$$
\xi_\tau=\frac{n_\tau}{n},\qquad H_{ij}=\sum_{\tau=(i,\mathbf c)}n_\tau c_j=dnq_{ij}(\xi).
$$

*Assume $\sum_\tau n_\tau=n$, $H_{ij}=H_{ji}$, and every $H_{ii}$ is even; these conditions define admissibility here. Let $N_{\mathbf n}$ denote the number of vertex sets whose exact-distance local-profile counts equal $\mathbf n$ in the $d$-regular pairing model. Then*

$$
\mathbb E N_{\mathbf n}=\frac{n!}{\prod_\tau n_\tau!}\prod_\tau\binom d{\mathbf c(\tau)}^{n_\tau}\cdot\frac{\displaystyle\prod_{0\le i<j\le h}H_{ij}!\ \prod_{i=0}^h(H_{ii}-1)!!}{(dn-1)!!},
$$

*and*

$$
\left|\log\mathbb E N_{\mathbf n}-n\Phi_{d,h}(\xi)\right|\le K_d(h+1)\log(n+1).
$$

*Here $(-1)!!=1$ when a diagonal mass is zero.*
:::

::: proof
*Proof.* First assign the $n$ labeled vertices to their local-profile classes, giving $n!/\prod_\tau n_\tau!$ choices. At a vertex of profile $(i,\mathbf c)$, assign the $d$ labeled half-edges their neighbor labels in $\binom d{\mathbf c}$ ways. There are then $H_{ij}$ half-edges of ordered type $(i,j)$. For $i<j$, pairing the $(i,j)$ half-edges bijectively with the $(j,i)$ half-edges gives $H_{ij}!$ choices; the $H_{ii}$ diagonal half-edges admit $(H_{ii}-1)!!$ pairings. Division by the total number $(dn-1)!!$ of pairings proves the displayed count.

Every resulting pairing has the prescribed exact distance labels. Indeed, the allowed edge types make the label function $1$-Lipschitz, while every positive label has a neighbor one level lower. Following a descending edge reaches label zero in exactly the displayed number of steps, and following any path from label zero cannot increase the label by more than one per edge. Thus the label equals graph distance to its zero set.

Use, uniformly for integers $r\ge0$,

$$
\log(r!)=r\log r-r+O(\log(r+1))
$$

and, for even $r$,

$$
\log((r-1)!!)=\frac r2\log r-\frac r2+O(\log(r+1)).
$$

There are $O_d(h+1)$ profile classes and nonzero tridiagonal edge types. Substitution into the displayed exact count cancels every $\log n$, $\log d$, and linear term, leaving exactly $n\Phi_{d,h}(\xi)$ with error $O_d(h\log(n+1))$. This proves the displayed bound. □
:::

::: {#cor-entropy-anchor .exhibit .exhibit--corollary data-exhibit-type="corollary" data-exhibit-name="Corollary 12 (Pointwise subset-entropy bound)"}
**Corollary 12** (Pointwise subset-entropy bound). *For every $d,h$ and every $\alpha\in[0,1]$,*

$$
\boxed{\Psi_{d,h}(\alpha)\le H(\alpha).}
$$
:::

::: proof
*Proof.* First let $\xi$ be a rational feasible profile. Passing to arbitrarily large multiples of a common denominator, and multiplying once more if necessary to make every diagonal half-edge count even, realizes $\xi$ as an integer type. Since $N_{\mathbf n}$ counts only subsets of size $\alpha n$,

$$
\mathbb E N_{\mathbf n}\le\binom n{\alpha n}.
$$

The lower inequality in [Theorem 11](#thm-two-sided-count), followed by $n\to\infty$, gives

$$
\Phi_{d,h}(\xi)\le H(\alpha).
$$

The feasible set is a rational polytope, so rational feasible profiles are dense. The functional $\Phi_{d,h}$ is continuous on it under the convention $0\log0=0$. Hence the same inequality holds for every feasible profile. Taking the maximum at fixed selected density proves the corollary. □
:::

::: remark
**Remark 13** (Uniform upper type estimate). Summing [Theorem 11](#thm-two-sided-count) over the at most $(n+1)^{O_d(h)}$ integer profiles gives

$$
\log\mathbb E Z_{n,d,h}(m)\le n\Psi_{d,h}(m/n)+O_d(h\log(n+1)),
$$

uniformly as $h$ varies. [Theorem 11](#thm-two-sided-count) also gives a matching lower estimate along every sequence realizing a prescribed rational profile. No local-tree assumption is involved.
:::

---

# The Exact Compact Variational Problem {#sec-compact}

Let $q_{ij}$ be the directed-edge distribution of exact distance labels $i,j\in\{0,\dots,h\}$. Exact distance consistency makes $q$ symmetric and tridiagonal. Write

$$
x_i=q_{i-1,i}\quad(1\le i\le h),\qquad \ell_i=q_{ii}\quad(0\le i\le h),
$$

with $x_0=x_{h+1}=0$. The label masses are

$$
p_i=\ell_i+x_i+x_{i+1},\qquad \sum_{i=0}^h p_i=1.
$$

For $i\ge1$, put

$$
y_i=p_i-x_i=\ell_i+x_{i+1},\qquad a_i=\frac{x_i}{p_i}.
$$

Every positive-label vertex has at least one lower-label neighbor, so

$$
a_i\ge\frac1d,\qquad\text{equivalently}\qquad d x_i\ge p_i.
$$

Let $s_d(a)$ be the maximum entropy of a distribution on nonempty subsets of $[d]$ for which each coordinate is present with marginal $a$. Its dual formula is

$$
s_d(a)=\inf_{\lambda>0}\left\{\log\bigl((1+\lambda)^d-1\bigr)-da\log\lambda\right\},\qquad \frac1d\le a\le1.
$$

The minimizing parameter is characterized by

$$
a=\frac{\lambda(1+\lambda)^{d-1}}{(1+\lambda)^d-1}.
$$

## Exact local entropy reduction

The passage from the full profile functional to $\mathcal F_{d,h}$ is exact.

::: {#lem-conditional-product .exhibit .exhibit--lemma data-exhibit-type="lemma" data-exhibit-name="Lemma 14 (Conditional-product reduction)"}
**Lemma 14** (Conditional-product reduction). *Fix a symmetric tridiagonal directed-edge distribution $q$, and write $x_i,\ell_i,p_i,y_i,a_i$ as above, with $x_{h+1}=0$. Among all feasible local-profile laws inducing $q$, the maximum of the vertex entropy and arrangement terms is*

$$
H(p_0,\ldots,p_h)+p_0\,d\,H\!\left(\frac{\ell_0}{p_0},\frac{x_1}{p_0}\right)+\sum_{i=1}^h p_i\left[s_d(a_i)+d(1-a_i)H\!\left(\frac{\ell_i}{y_i},\frac{x_{i+1}}{y_i}\right)\right].
$$

*The maximizing law is unique whenever all displayed masses are positive. Conditional on label $i\ge1$, the set of lower-label half-edges has the entropy-maximizing tilted nonempty-subset law with coordinate marginal $a_i$; conditional on that set, every remaining half-edge independently receives label $i$ or $i+1$ with probabilities $\ell_i/y_i$ and $x_{i+1}/y_i$.*
:::

::: proof
*Proof.* First expose the central label. Its entropy is $H(p_0,\ldots,p_h)$. Conditional on the central label $i$, choosing a local count vector and then assigning the $d$ labeled half-edges contributes exactly the entropy of the induced law on words of length $d$ over the allowed neighboring labels.

For $i=0$, only labels $0$ and $1$ are allowed and their coordinate marginals are $\ell_0/p_0$ and $x_1/p_0$. Subadditivity of entropy is sharp only for independent coordinates, giving the first term above.

Fix $i\ge1$. Mark the coordinates whose neighbor label is $i-1$. Their random subset is nonempty and has common coordinate marginal

$$
a_i=\frac{q_{i,i-1}}{p_i}=\frac{x_i}{p_i}.
$$

By definition, its entropy is at most $s_d(a_i)$, with equality for the exponential tilt $\Pr(A)\propto\lambda^{|A|}$, $\varnothing\ne A\subseteq[d]$, where $\lambda$ satisfies the marginal characterization above; this also proves the dual formula for $s_d$. Given the lower-neighbor set, the remaining $d-|A|$ coordinates must split between labels $i$ and $i+1$. Conditional entropy is maximized by independent splitting with probabilities $\ell_i/y_i$ and $x_{i+1}/y_i$. Its expectation is

$$
d(1-a_i)H\!\left(\frac{\ell_i}{y_i},\frac{x_{i+1}}{y_i}\right).
$$

The chain rule for entropy proves the displayed reduction; strict entropy concavity gives uniqueness in the positive interior. □
:::

::: {#prop-compact-functional .exhibit .exhibit--proposition data-exhibit-type="proposition" data-exhibit-name="Proposition 15 (Exact compact functional)"}
**Proposition 15** (Exact compact functional). *For every feasible tridiagonal $q$, maximizing the full profile functional over local-profile laws inducing $q$ gives exactly*

$$
\mathcal F_{d,h}(x,\ell)=(d-1)p_0\log p_0+\sum_{i=1}^h\left[-p_i\log p_i+p_is_d(a_i)+dy_i\log y_i\right]-\frac d2\sum_{i=0}^h\ell_i\log\ell_i.
$$

*Consequently the compact and full variational values agree at every selected density.*
:::

::: proof
*Proof.* Insert [Lemma 14](#lem-conditional-product) into the full profile functional $\Phi_{d,h}$. The edge term is

$$
\frac d2\left(\sum_{i=0}^h\ell_i\log\ell_i+2\sum_{i=1}^hx_i\log x_i\right).
$$

Expanding the two categorical entropies in [Lemma 14](#lem-conditional-product), the $x_i\log x_i$ terms cancel against the off-diagonal edge terms. The remaining $p_i$, $y_i$, and $\ell_i$ terms collect to $\mathcal F_{d,h}$, including the root contribution $(d-1)p_0\log p_0$. Since every full feasible profile induces a feasible $q$ and [Lemma 14](#lem-conditional-product) constructs a maximizing profile for every feasible $q$, the variational values coincide. □
:::

For activity $z=e^\theta>0$, the grand-canonical functional is

$$
\mathcal F_{d,h}^{(z)}(x,\ell)=\mathcal F_{d,h}(x,\ell)+p_0\log z.
$$

Define the feasible polytope

$$
\mathcal P_{d,h}=\left\{(x,\ell):x_i,\ell_i\ge0,\ \sum_ip_i=1,\ dx_i\ge p_i\ (1\le i\le h)\right\}.
$$

The exact variational values are

$$
\Psi_{d,h}(\alpha)=\max_{\substack{(x,\ell)\in\mathcal P_{d,h}\\p_0=\alpha}}\mathcal F_{d,h}(x,\ell),\qquad
\phi_{d,h}(z)=\max_{(x,\ell)\in\mathcal P_{d,h}}\mathcal F_{d,h}^{(z)}(x,\ell)=\max_\alpha\{\Psi_{d,h}(\alpha)+\alpha\log z\}.
$$

The polytope is compact, so all maxima exist.

## The feasible density interval

The local capacities imply the Moore lower bound. First,

$$
p_1\le dx_1\le dp_0.
$$

For $i\ge2$, symmetry and the preceding descent edge give

$$
x_i\le p_{i-1}-x_{i-1}\le\frac{d-1}{d}p_{i-1},
$$

so

$$
p_i\le dx_i\le(d-1)p_{i-1}.
$$

Therefore

$$
1=\sum_{i=0}^hp_i\le B_hp_0,\qquad p_0\ge\frac1{B_h}.
$$

Equality is feasible in the type polytope: take

$$
p_0=\frac1{B_h},\qquad p_i=\frac{d(d-1)^{i-1}}{B_h},\qquad x_i=\frac{(d-1)^{i-1}}{B_h},
$$

with $\ell_i=0$ for $i<h$ and $\ell_h=(d-1)^h/B_h$. The upper endpoint $p_0=1$ is also feasible. Hence the density projection of $\mathcal P_{d,h}$ is exactly $[1/B_h,1]$.

---

# Boundary Repulsion and Full Interiority {#sec-boundary}

The proof that all grand-canonical maximizers are interior rests on the endpoint behavior of $s_d$.

::: {#lem-endpoint-expansions .exhibit .exhibit--lemma data-exhibit-type="lemma" data-exhibit-name="Lemma 16 (Endpoint expansions)"}
**Lemma 16** (Endpoint expansions). *As $\delta\downarrow0$,*

$$
s_d\!\left(\frac1d+\delta\right)=\log d+d\delta\log\frac1\delta+O_d(\delta),
$$

$$
s_d(1-\delta)=d\delta\log\frac1\delta+O_d(\delta).
$$
:::

::: proof
*Proof.* The envelope theorem applied to the dual formula for $s_d$ gives

$$
s_d'(a)=-d\log\lambda(a).
$$

Expanding the marginal characterization at $\lambda=0$ gives

$$
\lambda(a)=\frac{2d}{d-1}\left(a-\frac1d\right)+O_d\!\left(\left(a-\frac1d\right)^2\right).
$$

At the other endpoint, $\lambda(a)=(1-a)^{-1}(1+O_d(1-a))$. Integrating $s_d'$ from the known endpoint values $s_d(1/d)=\log d$ and $s_d(1)=0$ gives the result. □
:::

If $p_i=0$ at one level, then $x_{i+1}=0$, and the capacity inequality forces $p_{i+1}=0$. Thus every feasible profile has an effective horizon $k=\max\{i:p_i>0\}$, and its positive support is the prefix $\{0,\ldots,k\}$.

::: {#lem-boundary-repulsion .exhibit .exhibit--lemma data-exhibit-type="lemma" data-exhibit-name="Lemma 17 (Relative boundary repulsion)"}
**Lemma 17** (Relative boundary repulsion). *Fix a finite activity $z>0$. A maximizer of $\mathcal F_{d,h}^{(z)}$ cannot lie on any proper local face within its effective horizon. More precisely, if its effective horizon is $k$, then*

$$
\ell_i>0\ (0\le i\le k),\qquad a_i>\frac1d\ (1\le i\le k).
$$

*In particular, $a_k<1$.*
:::

::: proof
*Proof.* For each $k\ge1$, a strictly interior feasible profile exists. Choose $1/d<\chi<1/2$, $0<r<\chi^{-1}-1$, put $p_i$ proportional to $r^i$, and set $x_i=\chi p_i$. Then

$$
\ell_0=p_0-x_1>0,\qquad \ell_i=p_i-x_i-x_{i+1}>0\ (1\le i<k),\qquad \ell_k=p_k-x_k>0.
$$

Mix a proposed boundary maximizer with such an interior profile. If $a_i=1/d$, [Lemma 16](#lem-endpoint-expansions) contributes a strictly positive multiple of $t\log(1/t)$. If $\ell_i=0$, the term $-\tfrac d2\ell_i\log\ell_i$ contributes a strictly positive multiple of $t\log(1/t)$. All terms that remain away from their endpoints change by only $O(t)$.

The only apparent negative singularity occurs if $a_k=1$, equivalently $y_k=\ell_k=0$. In that case, with $y_k(t)=\beta t+O(t^2)$ for some $\beta>0$,

$$
p_k(t)s_d\!\left(1-\frac{y_k(t)}{p_k(t)}\right)+dy_k(t)\log y_k(t)=O(t)
$$

by [Lemma 16](#lem-endpoint-expansions); the two logarithmic singularities cancel. The remaining diagonal-edge term contributes

$$
-\frac d2y_k(t)\log y_k(t)=\frac d2\beta t\log\frac1t+O(t),
$$

which is strictly positive. If several faces are active simultaneously, all leading $t\log(1/t)$ coefficients are nonnegative and at least one is positive. Hence every proper relative boundary point admits an improving inward direction. □
:::

The horizon itself is also repelling.

::: {#lem-horizon-extension .exhibit .exhibit--lemma data-exhibit-type="lemma" data-exhibit-name="Lemma 18 (Horizon extension)"}
**Lemma 18** (Horizon extension). *A maximizer of $\mathcal F_{d,h}^{(z)}$ cannot have effective horizon $k<h$.*
:::

::: proof
*Proof.* By [Lemma 17](#lem-boundary-repulsion), a maximizer is strictly interior on its effective prefix. Choose $a_*\in(\max\{1/d,1-2/d\},1)$. For small $\tau>0$, introduce a new level of mass $p_{k+1}=\tau$ with

$$
x_{k+1}=a_*\tau,\qquad y_{k+1}=\ell_{k+1}=(1-a_*)\tau.
$$

Keep $p_k$ fixed by reducing $\ell_k$ by $a_*\tau$, and preserve total mass by reducing $\ell_0$ by $\tau$. All old variables remain feasible for sufficiently small $\tau$. When $k=0$, take instead

$$
p_0=1-\tau,\qquad x_1=a_*\tau,\qquad \ell_0=1-(1+a_*)\tau.
$$

The new level contributes

$$
\left[1-\frac d2(1-a_*)\right]\tau\log\frac1\tau+O(\tau).
$$

The coefficient is positive by the choice of $a_*$. All changes to previously positive coordinates are $O(\tau)$. Thus the extension strictly increases the grand functional. □
:::

::: {#thm-full-interiority .exhibit .exhibit--theorem data-exhibit-type="theorem" data-exhibit-name="Theorem 19 (Full interiority)"}
**Theorem 19** (Full interiority). *For every $d\ge3$, $h\ge1$, and $z>0$, every maximizer of the exact grand-canonical functional $\mathcal F_{d,h}^{(z)}$ has full effective horizon $h$ and satisfies*

$$
x_i>0,\qquad \ell_i>0,\qquad a_i>\frac1d
$$

*for all applicable indices.*
:::

::: proof
*Proof.* Combine [Lemma 17](#lem-boundary-repulsion) and [Lemma 18](#lem-horizon-extension). □
:::

---

# Stationary Messages and Exact KKT Reconstruction {#sec-kkt}

Recall $b=d-1$. For $1\le i\le h$, let $A_i$ be the cavity weight when the recipient edge already supplies a lower-label neighbor, and let $B_i$ be the weight when it does not. For label zero use $B_0$, and set $A_{h+1}=0$. Define

$$
S_0=B_0+A_1,\qquad S_i=B_{i-1}+B_i+A_{i+1}\quad(1\le i\le h),
$$

where the terminal convention makes $S_h=B_{h-1}+B_h$. The positive stationary system is

$$
\kappa B_0=zS_0^b,\qquad \kappa A_i=S_i^b\ (1\le i\le h),\qquad \kappa B_i=S_i^b-(S_i-B_{i-1})^b\ (1\le i\le h).
$$

The following subsection derives this system directly from the compact exact functional and proves the converse reconstruction.

## Full KKT-to-message correspondence

Let $\lambda_i$ be the minimizer in the dual formula for $s_d(a_i)$. Then

$$
s_d'(a_i)=-d\log\lambda_i,\qquad s_d(a_i)-a_is_d'(a_i)=\log((1+\lambda_i)^d-1).
$$

At an interior grand-canonical KKT point, let $\mu$ be the multiplier for $\sum_{i=0}^h\ell_i+2\sum_{i=1}^hx_i=1$. Since $\ell_i$ enters one layer mass and $x_i$ enters two, the KKT equations are

$$
\frac{\partial\mathcal F^{(z)}}{\partial\ell_i}=\mu,\qquad \frac{\partial\mathcal F^{(z)}}{\partial x_i}=2\mu.
$$

The analytic derivatives used below are, at the root,

$$
g_0=(d-1)(\log p_0+1)+\log z-\frac d2(\log\ell_0+1),
$$

and, for $i\ge1$,

$$
g_i=-\log p_i-1+s_d(a_i)-a_is_d'(a_i)+d(\log y_i+1)-\frac d2(\log\ell_i+1).
$$

Thus $\partial\mathcal F^{(z)}/\partial\ell_i=g_i$. The derivative with respect to $x_i$ is the sum of the layer contribution immediately to its left and the $x_i$-derivative of the layer-$i$ contribution; explicitly, for $i\ge2$,

$$
\frac{\partial\mathcal F^{(z)}}{\partial x_i}=g_{i-1}+\frac d2(\log\ell_{i-1}+1)+g_i+s_d'(a_i)-d(\log y_i+1)+\frac d2(\log\ell_i+1),
$$

with the same formula at $i=1$ after replacing the left layer expression by its root analogue.

Define, up to a common positive scale,

$$
B_i=\sqrt{\ell_i},\qquad A_i=\frac{x_i}{B_{i-1}}\quad(1\le i\le h),\qquad A_{h+1}=0.
$$

Then $y_i=B_i(B_i+A_{i+1})$.

::: {#lem-edge-kkt .exhibit .exhibit--lemma data-exhibit-type="lemma" data-exhibit-name="Lemma 20 (Edge KKT identifies the local tilt)"}
**Lemma 20** (Edge KKT identifies the local tilt). *For every $1\le i\le h$,*

$$
\lambda_i=\frac{B_{i-1}}{B_i+A_{i+1}}.
$$
:::

::: proof
*Proof.* For $i\ge2$, the derivative of $\mathcal F$ with respect to $x_i$ is the sum of the $p_{i-1}$ and $p_i$ contributions. Subtract the two diagonal equations above, use the dual-formula identities for $s_d'$, and cancel the common constants. The result is

$$
\frac d2\log\ell_{i-1}-d\log\left(\lambda_i\frac{y_i}{\sqrt{\ell_i}}\right)=0.
$$

Thus $\lambda_iy_i=\sqrt{\ell_{i-1}\ell_i}$, which is the displayed identity. The root contribution at $i=1$ has the same algebra, with the activity term cancelling through the root diagonal equation. □
:::

::: {#prop-kkt-stationarity .exhibit .exhibit--proposition data-exhibit-type="proposition" data-exhibit-name="Proposition 21 (Compact KKT equals two-message stationarity)"}
**Proposition 21** (Compact KKT equals two-message stationarity). *Every strict interior KKT point determines positive messages satisfying the stationary system above. Conversely, every positive message solution reconstructs a strict interior KKT point by*

$$
q_{ii}=\frac{B_i^2}{Z_e},\qquad q_{i-1,i}=\frac{B_{i-1}A_i}{Z_e}.
$$
:::

::: proof
*Proof.* Put $T_i=B_i+A_{i+1}$, $S_i=B_{i-1}+T_i$. By [Lemma 20](#lem-edge-kkt), $\lambda_i=B_{i-1}/T_i$. Exponentiating the diagonal KKT equation and using the entropy dual-formula identities shows that one common constant $\kappa>0$ satisfies

$$
\kappa=\frac{((1+\lambda_i)^d-1)y_i^d}{p_iB_i^d}=\frac{S_i^d-T_i^d}{p_i}
$$

for every $i\ge1$. Hence $p_i=(S_i^d-T_i^d)/\kappa$. The descent marginal formula gives $x_i=a_ip_i=B_{i-1}S_i^b/\kappa$. Since $x_i=B_{i-1}A_i$, this is the stationary equation for $A_i$. Subtracting $x_i$ from $p_i$ gives $y_i=T_i(S_i^b-T_i^b)/\kappa$. Since $y_i=B_iT_i$, this is the stationary equation for $B_i$. At the root, the diagonal KKT equation gives $\kappa=zp_0^b/B_0^d$. Because $p_0=B_0(B_0+A_1)=B_0S_0$, this is the stationary equation for $B_0$.

Conversely, let positive messages satisfy the stationarity equations. Put $\sigma=Z_e^{-1/2}$ and introduce normalized messages $\widehat A_i=\sigma A_i$, $\widehat B_i=\sigma B_i$, $\widehat\kappa=\sigma^{b-1}\kappa$. Then

$$
\widehat\kappa\widehat A_i=\widehat S_i^b,\qquad \widehat\kappa\widehat B_i=\widehat S_i^b-(\widehat S_i-\widehat B_{i-1})^b,\qquad \widehat\kappa\widehat B_0=z\widehat S_0^b.
$$

The reconstructed beliefs are simply $\ell_i=\widehat B_i^2$, $x_i=\widehat B_{i-1}\widehat A_i$. They have total mass one by the definition of $Z_e$. Writing $\widehat T_i=\widehat B_i+\widehat A_{i+1}$, $\lambda_i=\widehat B_{i-1}/\widehat T_i$, the message equations give the exact row identities

$$
p_i=\frac{\widehat S_i^d-\widehat T_i^d}{\widehat\kappa},\qquad x_i=\frac{\widehat B_{i-1}\widehat S_i^b}{\widehat\kappa},\qquad y_i=\frac{\widehat T_i(\widehat S_i^b-\widehat T_i^b)}{\widehat\kappa}.
$$

Consequently $a_i=x_i/p_i$ is exactly the tilted conditioned-binomial marginal with parameter $\lambda_i$, and $\lambda_iy_i=\widehat B_{i-1}\widehat B_i=\sqrt{\ell_{i-1}\ell_i}$. Substitution into the diagonal derivative gives, for every $i\ge1$, $g_i=\log\widehat\kappa+(d-2)/2$. The root equation gives the same value for $g_0$. Finally, the displayed edge identity and $s_d'(a_i)=-d\log\lambda_i$ make the difference between the $x_i$ derivative and $g_{i-1}+g_i$ vanish exactly. Thus, with $\mu=\log\widehat\kappa+(d-2)/2$, one has $\partial\mathcal F^{(z)}/\partial\ell_i=\mu$ and $\partial\mathcal F^{(z)}/\partial x_i=2\mu$. Positivity makes the point strict interior, and common message scaling cancels from the beliefs. □
:::

## One-dimensional positive stationary locus

The equations are homogeneous: common message scaling changes $\kappa$ but not $z$ or the reconstructed profile. In the gauge $\kappa=1$, choosing $B_h>0$ determines all preceding messages uniquely by

$$
A_i=B_i+(B_i+A_{i+1})^b,\qquad B_{i-1}=A_i^{1/b}-B_i-A_{i+1},
$$

for $i=h,h-1,\ldots,1$. Positivity is automatic because

$$
B_{i-1}=\left((B_i+A_{i+1})^b+B_i\right)^{1/b}-(B_i+A_{i+1})>0.
$$

Thus the positive stationary locus is one dimensional before the activity is imposed.

---

# Exact Reverse Transfer and Monotone Activity Shooting {#sec-reverse}

Normalize $A_1=1$ and put

$$
\rho_i=\frac{B_i}{A_i},\qquad u_i=\frac{A_{i+1}}{A_i},\qquad v_i=\rho_i+u_i.
$$

At the terminal level, $u_h=0$, so $\rho_h=v_h=:s\in(0,1)$. Let $\mathcal D=\{(\rho,v):0<\rho\le v\le1\}$.

::: {#prop-reverse-map .exhibit .exhibit--proposition data-exhibit-type="proposition" data-exhibit-name="Proposition 22 (Exact reverse map)"}
**Proposition 22** (Exact reverse map). *Given a next-level state $(\rho',v')\in\mathcal D$, define*

$$
w=(1-\rho')^{1/b},\qquad e=1-w,\qquad R=v'\frac ew,\qquad M=\left(e+\frac w{v'}\right)^b.
$$

*Then its unique positive predecessor is*

$$
\boxed{
\rho=\frac{R}{R+M},\qquad v=\frac{1+R}{R+M}.
}
$$

*The remaining coordinates are*

$$
u=\frac1{R+M},\qquad q=\frac{M-1}{R+M}.
$$

*The map sends $\mathcal D$ into itself.*
:::

::: proof
*Proof.* The forward transfer identities imply $\rho/u=v'e/w=R$. The next lower-neighbor fraction also gives

$$
e=\frac{\rho(1-\rho)^{1/b}}{u^{1/b}(u+\rho)}.
$$

Substituting $\rho=Ru$ and solving yields $u=1/(R+M)$, which gives the displayed formulas for $\rho,v$. Uniqueness follows from the algebraic solution. Since $e+w/v'\ge e+w=1$, we have $M\ge1$, and therefore $0<\rho<v\le1$. □
:::

::: {#prop-order-preservation .exhibit .exhibit--proposition data-exhibit-type="proposition" data-exhibit-name="Proposition 23 (Order preservation)"}
**Proposition 23** (Order preservation). *The reverse map is coordinatewise nondecreasing on $\mathcal D$, and its $\rho$ coordinate is strictly increasing whenever either input coordinate increases. Along the diagonal terminal family $(s,s)$, every earlier $\rho_i$ is strictly increasing in $s$, and every $v_i$ is nondecreasing.*
:::

::: proof
*Proof.* The quantity $R=v'e/w$ is strictly increasing in both $\rho'$ and $v'$. Put $N=e+w/v'$, $M=N^b$. As $v'$ increases, $N$ strictly decreases. Since $w'(\rho')<0$ and $e'=-w'$, one has

$$
\frac{\partial N}{\partial\rho'}=w'(\rho')\left(\frac1{v'}-1\right)\le0.
$$

Thus $M$ is nonincreasing in both inputs. The function $\rho=R/(R+M)$ increases with $R$ and decreases with $M$. Likewise $v=(1+R)/(R+M)$ increases with $R$ when $M\ge1$ and decreases with $M$. The asserted monotonicity follows, and strictness of $\rho$ propagates under iteration. □
:::

At the root, write

$$
m=\frac{1-(1-\rho_1)^{1/b}}{(1-\rho_1)^{1/b}}.
$$

Then

$$
r_0:=\frac{B_0}{A_1}=v_1m,\qquad \kappa=\bigl(v_1(1+m)\bigr)^b,
$$

and the root equation gives

$$
\boxed{
z=v_1^{b+1}m\left(\frac{1+m}{1+v_1m}\right)^b.
}
$$

::: {#lem-activity-monotonicity .exhibit .exhibit--lemma data-exhibit-type="lemma" data-exhibit-name="Lemma 24 (Strict activity monotonicity)"}
**Lemma 24** (Strict activity monotonicity). *The root activity above is strictly increasing in both $v_1$ and $m$. Consequently, the terminal-to-activity map $s\mapsto z_h(s)$ is strictly increasing on $(0,1)$.*
:::

::: proof
*Proof.* Direct differentiation gives

$$
\frac{\partial}{\partial v}\log z=\frac{b+1+vm}{v(1+vm)}>0,\qquad \frac{\partial}{\partial m}\log z=\frac1m+\frac{b(1-v)}{(1+m)(1+vm)}>0.
$$

The quantity $m$ is strictly increasing in $\rho_1$, so [Proposition 23](#prop-order-preservation) completes the proof. □
:::

::: {#lem-endpoint-activities .exhibit .exhibit--lemma data-exhibit-type="lemma" data-exhibit-name="Lemma 25 (Endpoint activities)"}
**Lemma 25** (Endpoint activities). *For fixed $d,h$,*

$$
\lim_{s\downarrow0}z_h(s)=0,\qquad \lim_{s\uparrow1}z_h(s)=\infty.
$$
:::

::: proof
*Proof.* For terminal $(\rho',v')=(s,s)$ with $s\downarrow0$, one reverse step has $R=O(s^2)$ and $M=\Theta(s^{-b})$, so the predecessor tends to $(0,0)$. The reverse map is continuous at every interior state and has the displayed boundary limit; induction over the fixed number $h-1$ of reverse steps therefore sends every earlier state to $(0,0)$. The root equation then gives $z\to0$.

As $s\uparrow1$, one has $w\to0$, $R\to\infty$, and $M\to1$, so one reverse step tends to $(1,1)$. The same finite-step induction sends every earlier state to $(1,1)$. Hence $m\to\infty$, $v_1\to1$, and the root equation gives $z\to\infty$. Continuity of the reverse map and of the root equation also makes $s\mapsto z_h(s)$ continuous. □
:::

::: {#thm-unique-stationary .exhibit .exhibit--theorem data-exhibit-type="theorem" data-exhibit-name="Theorem 26 (Unique positive stationary point)"}
**Theorem 26** (Unique positive stationary point). *For every $d\ge3$, $h\ge1$, and $z>0$, the exact grand-canonical stationarity equations have exactly one positive solution up to common message scaling.*
:::

::: proof
*Proof.* Every positive solution has one terminal parameter $s=\rho_h\in(0,1)$ and is uniquely reconstructed by [Proposition 22](#prop-reverse-map). [Lemma 24](#lem-activity-monotonicity) and [Lemma 25](#lem-endpoint-activities) show that $s\mapsto z_h(s)$ is a strictly increasing bijection from $(0,1)$ to $(0,\infty)$. □
:::

For a positive stationary message profile whose reconstructed selected density is $\alpha$, define $\Psi^{\mathrm{stat}}_{d,h}(\alpha):=\mathcal F_{d,h}(x,\ell)$, where $(x,\ell)$ is its normalized compact profile. [Theorem 26](#thm-unique-stationary) shows that this value is single-valued along the positive reverse-transfer branch.

---

# Exact Grand- and Microcanonical Globality {#sec-globality}

Although $\mathcal F_{d,h}$ is nonconcave, the preceding interiority and uniqueness results determine its global optimizer.

::: {#thm-grand-canonical-globality .exhibit .exhibit--theorem data-exhibit-type="theorem" data-exhibit-name="Theorem 27 (Grand-canonical globality)"}
**Theorem 27** (Grand-canonical globality). *For every $d\ge3$, $h\ge1$, and $z>0$, the exact grand-canonical functional $\mathcal F_{d,h}^{(z)}$ has a unique global maximizer. It is the positive stationary profile corresponding to the unique terminal parameter $s$ satisfying $z_h(s)=z$.*
:::

::: proof
*Proof.* A maximizer exists by compactness. [Theorem 19](#thm-full-interiority) places every maximizer in the strict interior, so every maximizer satisfies the interior stationarity equations. [Theorem 26](#thm-unique-stationary) gives only one such point. □
:::

The microcanonical problem follows by duality.

::: {#thm-microcanonical-globality .exhibit .exhibit--theorem data-exhibit-type="theorem" data-exhibit-name="Theorem 28 (Microcanonical globality)"}
**Theorem 28** (Microcanonical globality). *For every density $1/B_h<\alpha<1$, the exact microcanonical functional has a unique global maximizer, and it is the positive stationary profile on the reverse-transfer branch with selected density $\alpha$. Equivalently,*

$$
\boxed{
\Psi_{d,h}(\alpha)=\Psi^{\mathrm{stat}}_{d,h}(\alpha)
}
$$

*throughout the interior feasible interval.*
:::

::: proof
*Proof.* Write $\theta=\log z$ and $\phi_{d,h}(\theta)=\max_{(x,\ell)\in\mathcal P_{d,h}}\{\mathcal F_{d,h}(x,\ell)+\theta p_0\}$.

By [Theorem 27](#thm-grand-canonical-globality), the maximizer is unique for every $\theta$. Danskin's theorem [@RockafellarWets] therefore gives $\phi_{d,h}'(\theta)=\alpha(\theta)$, the density of that maximizer. The derivative of a differentiable convex function is continuous here (equivalently, one may use continuity of the unique optimizer). It is also strictly increasing. Indeed, if $\theta_1<\theta_2$ had the same maximizing density, the two optimality inequalities would force each optimizer to maximize at both activities. Grand-canonical uniqueness would make the profiles equal, but the root equation assigns one activity to an interior stationary profile, a contradiction. To identify the endpoint limits, let $\theta_k\to-\infty$ and pass, by compactness, to a convergent subsequence of optimizers. Comparing with a feasible profile of density $1/B_h$ shows that any limit must minimize $p_0$ over the polytope, hence has density $1/B_h$. Similarly, along $\theta_k\to\infty$, comparison with the all-selected profile forces every subsequential limit to have density $1$. Therefore

$$
\alpha(\theta)\to\frac1{B_h}\ (\theta\to-\infty),\qquad \alpha(\theta)\to1\ (\theta\to\infty).
$$

Hence every interior density is attained.

Fix $\alpha$ and choose $\theta$ with $\alpha(\theta)=\alpha$. For every profile $P$ of density $\alpha$, $\mathcal F(P)+\theta\alpha\le \mathcal F(P_\theta)+\theta\alpha$, so $P_\theta$ is the microcanonical maximizer. Uniqueness follows from grand-canonical uniqueness. □
:::

::: {#cor-envelope-identity .exhibit .exhibit--corollary data-exhibit-type="corollary" data-exhibit-name="Corollary 29 (Concavity and the envelope identity)"}
**Corollary 29** (Concavity and the envelope identity). *The exact value function $\Psi_{d,h}$ is strictly concave on $(1/B_h,1)$ and differentiable there. If $z(\alpha)$ is the activity exposing density $\alpha$, then*

$$
\boxed{
\Psi_{d,h}'(\alpha)=-\log z(\alpha).
}
$$
:::

::: proof
*Proof.* This is the standard differentiable Legendre correspondence produced by the unique maximizers in [Theorem 27](#thm-grand-canonical-globality) and [Theorem 28](#thm-microcanonical-globality). Strict monotonicity of $\alpha(\theta)$ gives strict concavity. □
:::

For later use, we collect the two conclusions as

$$
\Psi_{d,h}(\alpha)=\Psi^{\mathrm{stat}}_{d,h}(\alpha),\qquad \Psi_{d,h}'(\alpha)=-\log z(\alpha).
$$

Explicit positive Hessian directions at stratified profiles do not contradict these theorems: they occur at nonstationary stratified profiles. The compact functional is genuinely nonconcave, but no competing stationary maximum exists.

---

# Corrected Stationary Telescoping and Root Formulas {#sec-telescoping}

Define

$$
Z_v=zS_0^d+\sum_{i=1}^h\left[S_i^d-(S_i-B_{i-1})^d\right],\qquad Z_e=\sum_{i=0}^hB_i^2+2\sum_{i=0}^{h-1}B_iA_{i+1}.
$$

The stationary vertex and edge normalizers satisfy the following exact telescoping identity.

::: {#prop-telescoping .exhibit .exhibit--proposition data-exhibit-type="proposition" data-exhibit-name="Proposition 30 (Corrected telescoping identity)"}
**Proposition 30** (Corrected telescoping identity). *Every positive stationary solution satisfies*

$$
\boxed{Z_v=\kappa Z_e.}
$$
:::

::: proof
*Proof.* For $1\le i\le h$, put $V_i=S_i^d-(S_i-B_{i-1})^d$. Using the stationary equations for $A_i,B_i$,

$$
V_i=\kappa\left(B_{i-1}A_i+B_i^2+B_iA_{i+1}\right).
$$

The root contribution is $zS_0^d=\kappa(B_0^2+B_0A_1)$. After summation, every square $B_i^2$ appears once and every cross term $B_iA_{i+1}$ appears twice: once from each adjacent vertex contribution, with the root supplying the first copy of $B_0A_1$. This is exactly $\kappa Z_e$. □
:::

Normalize $A_1=1$ and write $r=B_0$. [Proposition 30](#prop-telescoping) gives

$$
\alpha=\frac{r(1+r)}{Z_e}.
$$

The pressure is $\phi=\log Z_v-\tfrac d2\log Z_e$, and the root equation is $\log z=\log\kappa+\log r-(d-1)\log(1+r)$. Eliminating $Z_e$ gives the corrected root-only formulas

$$
\boxed{
\phi=\log z+\frac d2\log\frac{1+r}r+\frac{d-2}2\log\alpha,
}
$$

$$
\boxed{
\Psi=(1-\alpha)\log\kappa-\left(\frac{d-2}2+\alpha\right)\log r+\frac{d-2}2\log\alpha+\left((d-1)\alpha-\frac{d-2}2\right)\log(1+r).
}
$$

The corrected formulas are used throughout this paper. Calculations made directly from $Z_v$ and $Z_e$ are unaffected, provided the power differences are evaluated stably as discussed in [Section 17](#sec-numerics).

For later diagnostics, the same telescope gives a cancellation-free identity for the entropy defect. Put

$$
u=u_1=\frac{A_2}{A_1},\qquad c_0=\frac{d-2}2,
$$

and define

$$
E_{\mathrm{root}}:=\log\kappa-b\log u,\qquad N_e:=\log Z_e-(D+1)\log u.
$$

::: {#prop-defect-identity .exhibit .exhibit--proposition data-exhibit-type="proposition" data-exhibit-name="Proposition 31 (Exact entropy-defect identity)"}
**Proposition 31** (Exact entropy-defect identity). *Every positive stationary solution of selected density $\alpha$ satisfies*

$$
\boxed{
H(\alpha)-\Psi_{d,h}(\alpha)=-(1-\alpha)\log(1-\alpha)-E_{\mathrm{root}}+c_0N_e+\alpha\log\frac z\alpha.
}
$$
:::

::: proof
*Proof.* [Proposition 30](#prop-telescoping) gives $\phi=\log\kappa-c_0\log Z_e$. Since $c_0(D+1)=b$, this is $\phi=E_{\mathrm{root}}-c_0N_e$. Now use $\Psi=\phi-\alpha\log z$ and expand $H(\alpha)=-\alpha\log\alpha-(1-\alpha)\log(1-\alpha)$. □
:::

---

# Terminal Logarithmic Coordinate and Exact Outer Orbits {#sec-terminal}

Retain the normalization $A_1=1$ and the reverse-transfer coordinates $\rho_i=B_i/A_i$, $u_i=A_{i+1}/A_i$, $v_i=\rho_i+u_i$, $q_i=1-v_i$. At the terminal wall $u_h=0$. We write

$$
\rho_h=v_h=s=1-e^{-t},\qquad q_h=e^{-t}.
$$

The exact reverse dynamics are those of [Proposition 22](#prop-reverse-map).

Two boundary orbits are exact. On the **stable boundary** $\rho=0$, the forward map is $u\mapsto u^{1/b}$ and the reverse map is $u'\mapsto (u')^b$. On the **free boundary** $q=0$, the forward map is $u\mapsto u^b$ and the reverse map is $u'\mapsto (u')^{1/b}$.

For terminal parameter $t$, define the free density

$$
a_h(t):=1-e^{-t/b^h}.
$$

The exact free orbit with this density is

$$
\bar u_i=e^{-t/b^{h-i}},\qquad \bar\rho_i=1-\bar u_i,\qquad \bar q_i=0.
$$

---

# Uniform One-Step Estimates {#sec-onestep}

The window theorem requires terminal parameters linear in $h$ and uniformly below the critical coefficient, tracked with quantitative — not merely qualitative — error terms.

::: {#def-subcritical-window .exhibit .exhibit--definition data-exhibit-type="definition" data-exhibit-name="Definition 32 (Subcritical terminal window)"}
**Definition 32** (Subcritical terminal window). Fix constants $0<\tau_-\le\tau_+<\dfrac{4\log b}{3D}$. A sequence of terminal parameters is in the *subcritical linear window* if

$$
\tau_-h\le t\le \tau_+h.
$$
:::

All constants below may depend on $d,\tau_-,\tau_+$ but not on $h$ or $t$ in this window.

## Free-side perturbations

At one reverse step, keep $\rho'$ fixed and write $q'=1-v'$. The free predecessor with the same $\rho'$ has $w=(1-\rho')^{1/b}$, $\rho_0=1-w$, $u_0=w$, $q_0=0$.

::: {#lem-free-side-step .exhibit .exhibit--lemma data-exhibit-type="lemma" data-exhibit-name="Lemma 33 (Uniform free-side step)"}
**Lemma 33** (Uniform free-side step). *There are $\delta_0,C>0$ such that, whenever $0\le q'\le\delta_0$, the actual predecessor satisfies*

$$
1-\rho=w(1+\eta_\rho),\qquad q=bw^2q'(1+\eta_q),
$$

*with $|\eta_\rho|+|\eta_q|\le Cq'$. The estimates are uniform for $0<w\le1$.*
:::

::: proof
*Proof.* Put $\delta=q'$. Since $v'=1-\delta$,

$$
R=(1-\delta)\frac{1-w}w,\qquad M=\left(1-w+\frac w{1-\delta}\right)^b=\left(1+\frac{w\delta}{1-\delta}\right)^b.
$$

For $\delta\le1/2$, the binomial expansion with a uniform remainder gives $M=1+bw\delta+O_d(\delta^2)$. Furthermore,

$$
w(R+M)=(1-\delta)(1-w)+wM=1+O_d(\delta).
$$

Now $1-\rho=u+q=M/(R+M)$, $q=(M-1)/(R+M)$. Substitution gives the displayed expansions. □
:::

## Stable-side perturbations

For a reverse step near the stable manifold, write the next state as $v'=V$, $\rho'=V\delta$, $u'=V(1-\delta)$. The stable predecessor with the same $V$ is $(\rho_0,u_0)=(0,V^b)$.

::: {#lem-stable-side-step .exhibit .exhibit--lemma data-exhibit-type="lemma" data-exhibit-name="Lemma 34 (Uniform stable-side step)"}
**Lemma 34** (Uniform stable-side step). *There are $\delta_1,C>0$ such that, whenever $0\le\delta\le\delta_1$, the predecessor satisfies*

$$
\log u=b\log V+O_d(V\delta),\qquad \frac\rho v=\frac{V^2}b\delta(1+O_d(\delta)).
$$

*Put $\widetilde a_i:=\rho_i/(b^iu_i^D)$. Then*

$$
\frac{\widetilde a_i}{\widetilde a_{i+1}}=1+O_d(\delta).
$$

*For sufficiently small $\delta_1$, the transverse ratios contract backward:*

$$
\frac{\rho_i}{v_i}\le\frac{1+o(1)}b\,\frac{\rho_{i+1}}{v_{i+1}}.
$$
:::

::: proof
*Proof.* Here $w=(1-V\delta)^{1/b}$, $e=1-w=(V\delta/b)(1+O_d(\delta))$, so $R=V(e/w)=(V^2\delta/b)(1+O_d(\delta))$. Also

$$
e+\frac wV=\frac1V(w+Ve)=\frac1V(1-e(1-V)),
$$

whence $M=V^{-b}(1+O_d(V\delta))$. Since $R/M=O_d(V^{b+2}\delta)$, the reverse-map formula for $u$ yields the displayed expansion for $\log u$; moreover $\rho/u=R$, which gives the displayed expansion for $\rho/v$.

For the transverse-ratio estimate, use $\rho=uR$ and compute $\widetilde a_i/\widetilde a_{i+1}=bRu^{1-D}(u')^D/\rho'$. The preceding expansions give $bR/\rho'=V(1+O_d(\delta))$ and $u^{1-D}(u')^D=V^{-1}(1+O_d(\delta))$, because $(b-1)D=b+1$. Their product is $1+O_d(\delta)$. □
:::

---

# Free Shadowing to an Overlap Layer {#sec-free-shadow}

In the quantitative statements below, notation of the form $1+B_h^{-\eta+o(1)}$ denotes $1+\epsilon_h$ with $|\epsilon_h|\le B_h^{-\eta+o(1)}$; no sign is implied. For $t$ in the terminal window, choose

$$
H=\left\lfloor\frac{3Dt}{4\log b}\right\rfloor,\qquad m=h-H.
$$

Then $H,m$ are both linear in $h$. Define the formal free transverse sequence, for $m\le i\le h$, by

$$
\bar q_i=b^{h-i}\exp\left\{-Dt+\frac{2t}{b-1}b^{i-h}\right\}.
$$

It satisfies $\bar q_h=e^{-t}$ and $\bar q_i=b\bar u_i^2\bar q_{i+1}$.

::: {#prop-free-shadow .exhibit .exhibit--proposition data-exhibit-type="proposition" data-exhibit-name="Proposition 35 (Uniform free shadow)"}
**Proposition 35** (Uniform free shadow). *Uniformly in every subcritical terminal window, for every $m\le i\le h$,*

$$
q_i=\bar q_i\left(1+O\!\left(h e^{-Dt/4}\right)\right),\qquad 1-\rho_i=\bar u_i\left(1+O\!\left(e^{-Dt/4}\right)\right).
$$

*In particular,*

$$
q_m=b^H\exp\left\{-Dt+\frac{2t}{b-1}b^{-H}\right\}\left(1+O\!\left(h e^{-Dt/4}\right)\right),\qquad
\rho_m=t b^{-H}\left(1+O\!\left(t b^{-H}+e^{-Dt/4}\right)\right),
$$

$$
\frac{\rho_m}{q_m}=\exp\{-Dt/2+o(h)\}.
$$

*If $L=\log B_h$ and $c_t=Dt/L$, then, uniformly when $c_t$ stays in a compact subset of the terminal window,*

$$
\boxed{
q_m=B_h^{-c_t/4+o(1)},\qquad \rho_m=B_h^{-3c_t/4+o(1)},\qquad \frac{\rho_m}{q_m}=B_h^{-c_t/2+o(1)}.
}
$$
:::

::: proof
*Proof.* Let $E_i=\log\bigl((1-\rho_i)/\bar u_i\bigr)$. [Lemma 33](#lem-free-side-step) gives $E_i=\tfrac1bE_{i+1}+O(q_{i+1})$, and

$$
\log\frac{q_i}{\bar q_i}=\log\frac{q_{i+1}}{\bar q_{i+1}}+\frac2bE_{i+1}+O(q_{i+1}).
$$

Both errors vanish at $i=h$.

Write $r=h-i$. The logarithm of the formal transverse sequence is

$$
f(r)=r\log b-Dt+\frac{2t}{b-1}b^{-r}.
$$

The function $f$ is convex, so its maximum on $0\le r\le H$ occurs at an endpoint. At $r=0$, $f(0)=-t$, while the definition of $H$ gives $f(H)\le-\tfrac14Dt+O_d(1)$. Since $D/4<1$, it follows that $\max_{m\le i\le h}\bar q_i=O_d(e^{-Dt/4})$.

A first-failure bootstrap now gives

$$
\max_i|E_i|=O(e^{-Dt/4}),\qquad \max_i\left|\log\frac{q_i}{\bar q_i}\right|=O(h e^{-Dt/4}).
$$

For large $h$ these estimates prevent the first failure, proving the displayed shadow estimates and the stated formula for $q_m$. Furthermore, $1-e^{-t/b^H}=t b^{-H}\left(1+O(t b^{-H})\right)$, which gives the formula for $\rho_m$. Finally,

$$
\log\frac{\rho_m}{q_m}=\log t-2H\log b+Dt+o(h)=-\frac12Dt+o(h).
$$

Because $H=3Dt/(4\log b)+O(1)$ and $L=h\log b+O(1)$, the three quantitative estimates follow. □
:::

---

# Stable Shadowing from the Overlap to the Root {#sec-stable-shadow}

Put

$$
x=-\log u_1,\qquad \widetilde a=\widetilde a_1=\frac{\rho_1}{b u_1^D}.
$$

::: {#prop-stable-shadow .exhibit .exhibit--proposition data-exhibit-type="proposition" data-exhibit-name="Proposition 36 (Uniform stable shadow)"}
**Proposition 36** (Uniform stable shadow). *Under the terminal-window assumptions and the matching choice of $H,m$ from [Section 12](#sec-free-shadow), put*

$$
\chi_m:=q_m+\frac{\rho_m}{q_m}.
$$

*Then*

$$
x=b^{m-1}q_m\left(1+O(\chi_m)\right),\qquad \widetilde a=\frac{\rho_m}{b^m}\left(1+O(q_m+\rho_m)\right).
$$

*If the messages are normalized by $A_1=1$, then*

$$
\log A_m=\frac{b}{b-1}\left(1-b^{-(m-1)}\right)\log u_1+O(m\rho_m),
$$

*and*

$$
B_0=\widetilde a\,A_m^2\left(1+O(q_m+m\rho_m)\right).
$$

*All constants are uniform in the terminal window.*
:::

::: proof
*Proof.* Set $\delta_i=\rho_i/v_i$. [Proposition 35](#prop-free-shadow) gives $\delta_m=O(\rho_m)$, and [Lemma 34](#lem-stable-side-step) implies geometric backward contraction. Hence

$$
\sum_{i=2}^m\delta_i=O(\rho_m).
$$

Iteration of the transverse-ratio contraction gives $\widetilde a=\rho_m/(b^m u_m^D)\,(1+O(\rho_m))$. Since $u_m=1-q_m-\rho_m$, this proves the displayed formula for $\widetilde a$.

The stable-step estimate also gives $\log v_i=b\log v_{i+1}+O(\rho_{i+1})$. After iteration,

$$
-\log v_1=b^{m-1}[-\log v_m]+O\left(\sum_{j=2}^m b^{j-2}\rho_j\right)=b^{m-1}[-\log v_m]+O(b^{m-1}\rho_m).
$$

Since $v_m=1-q_m$, $-\log v_m=q_m(1+O(q_m))$. Backward contraction gives $\delta_1=O(b^{-(m-1)}\rho_m)$, and therefore

$$
0\le\log\frac{v_1}{u_1}=\log\left(1+\frac{\rho_1}{u_1}\right)=O(b^{-(m-1)}\rho_m).
$$

This is absorbed by the preceding error. Dividing by the main term $b^{m-1}q_m$ proves the displayed formula for $x$.

Likewise, the stable-side expansion for $\log u$ and the contraction of $\delta_i$ give $\log u_i=b^{-(i-1)}\log u_1+O(\rho_m)$ uniformly for $1\le i<m$. Summing the message ratios gives the displayed formula for $\log A_m$.

At the root, $B_0=v_1\bigl(1-(1-\rho_1)^{1/b}\bigr)/(1-\rho_1)^{1/b}=\widetilde a\,u_1^{D+1}(1+O(\rho_m))$. Since $D+1=2b/(b-1)$, the displayed formulas for $x$ and $\log A_m$ give

$$
\log\frac{B_0}{\widetilde a A_m^2}=-\frac{2b}{b-1}\frac{x}{b^{m-1}}+O(m\rho_m)=O(q_m+m\rho_m),
$$

which proves the last assertion. □
:::

---

# Density and Activity Asymptotics {#sec-density-activity}

The free and stable shadows now match without an additional hypothesis.

::: {#thm-terminal-matching .exhibit .exhibit--theorem data-exhibit-type="theorem" data-exhibit-name="Theorem 37 (Terminal-window matching)"}
**Theorem 37** (Terminal-window matching). *Let $L=\log B_h$ and $c_t=Dt/L$. Uniformly for $t$ in every subcritical linear window,*

$$
\widetilde a=a_h(t)\left(1+B_h^{-c_t/4+o(1)}\right),\qquad
\frac{x}{b^{h-1}}=(1-a_h(t))^{B_h}\left(1+B_h^{-c_t/4+o(1)}\right),
$$

$$
B_h\lvert\widetilde a-a_h(t)\rvert=B_h^{-c_t/4+o(1)}.
$$
:::

::: proof
*Proof.* The formula for $\rho_m$, the stable shadow's formula for $\widetilde a$, and the quantitative overlap scales of [Proposition 35](#prop-free-shadow) give

$$
\widetilde a=\frac{t}{b^h}\left(1+B_h^{-c_t/4+o(1)}\right)=a_h(t)\left(1+B_h^{-c_t/4+o(1)}\right).
$$

Since $a_h(t)B_h=Dt(1+o(1))=B_h^{o(1)}$, this also proves the last displayed identity.

Combining the formula for $q_m$ with the stable shadow's formula for $x$ yields

$$
\frac{x}{b^{h-1}}=\exp\left\{-Dt+\frac{2t}{b-1}b^{-H}\right\}\left(1+B_h^{-c_t/4+o(1)}\right).
$$

On the other hand, by the definitions of $B_h$ and $a_h(t)$,

$$
(1-a_h(t))^{B_h}=\exp\left\{-Dt+\frac{2t}{b-1}b^{-h}\right\}.
$$

The exponent difference is $O(tb^{-H})=B_h^{-3c_t/4+o(1)}$, which is smaller than the displayed error. This proves the second identity. □
:::

To pass from $\widetilde a$ to the actual selected density, reconstruct the edge partition function $Z_e=\sum_{i=0}^hB_i^2+2\sum_{i=0}^{h-1}B_iA_{i+1}$.

::: {#lem-edge-normalizer .exhibit .exhibit--lemma data-exhibit-type="lemma" data-exhibit-name="Lemma 38 (Edge-normalizer localization)"}
**Lemma 38** (Edge-normalizer localization). *With the matching index $m$,*

$$
Z_e=A_m^2\left(1+O(hq_m+\rho_m)\right).
$$

*Consequently, with $c_t=Dt/\log B_h$,*

$$
\alpha=\widetilde a\left(1+B_h^{-c_t/4+o(1)}\right)=a_h(t)\left(1+B_h^{-c_t/4+o(1)}\right),\qquad
B_h|\alpha-a_h(t)|=B_h^{-c_t/4+o(1)}.
$$
:::

::: proof
*Proof.* For $i\ge m$, $B_i^2+2B_iA_{i+1}=(B_i+A_{i+1})^2-A_{i+1}^2$. Since $B_i+A_{i+1}=A_i(1-q_i)$, summation gives the exact tail identity

$$
\sum_{i=m}^h(B_i^2+2B_iA_{i+1})=A_m^2(1-q_m)^2-\sum_{i=m+1}^hA_i^2q_i(2-q_i).
$$

[Proposition 35](#prop-free-shadow) bounds the relative tail error by $O(hq_m)$.

For the left part, [Proposition 36](#prop-stable-shadow) and the stable invariant give, uniformly for $i<m$, $\rho_i=\widetilde a\,b^iu_i^D(1+O(\rho_m))$, while $A_i^2u_i^{D+1}/A_m^2=1+O(q_m+m\rho_m)$. Therefore

$$
\frac1{A_m^2}\sum_{i=1}^{m-1}2B_iA_{i+1}=O\!\left(\widetilde a\sum_{i=1}^{m-1}b^i\right)=O(\widetilde a b^m)=O(\rho_m).
$$

The square terms are smaller by a factor $\rho_i/u_i$, and the root term is $O(\widetilde a A_m^2)$. This proves the displayed formula for $Z_e$.

The exact root belief is $\alpha=B_0(B_0+A_1)/Z_e$. Use $A_1=1$, the stable shadow's formula for $B_0$, the displayed formula for $Z_e$, and $B_0=o(1)$ to obtain

$$
\alpha=\widetilde a\left(1+O(hq_m+\rho_m)\right).
$$

Now apply [Theorem 37](#thm-terminal-matching) and the quantitative overlap scales. Polynomial factors in $h$ are $B_h^{o(1)}$, which proves the last two displayed identities. □
:::

The root reconstruction formulas are

$$
B_0=v_1\frac{1-(1-\rho_1)^{1/b}}{(1-\rho_1)^{1/b}},\qquad \kappa=\left(\frac{v_1}{(1-\rho_1)^{1/b}}\right)^b,\qquad z=\frac{B_0\kappa}{(1+B_0)^b}.
$$

::: {#thm-activity-law .exhibit .exhibit--theorem data-exhibit-type="theorem" data-exhibit-name="Theorem 39 (Quantitative uniform activity law)"}
**Theorem 39** (Quantitative uniform activity law). *Fix constants $0<c_-<c_+<4/3$. Uniformly for densities satisfying*

$$
c_-\log B_h\le\alpha B_h\le c_+\log B_h,\qquad c=\frac{\alpha B_h}{\log B_h},
$$

*one has*

$$
-\log z(\alpha)-\log\frac1\alpha=B_h(1-\alpha)^{B_h}\left(1+B_h^{-c/4+o(1)}\right)+B_h^{-c/4+o(1)}.
$$

*Consequently,*

$$
\boxed{
-\log z(\alpha)=\log\frac1\alpha+B_h(1-\alpha)^{B_h}\left(1+B_h^{-\delta+o(1)}\right),
}
$$

*where*

$$
\delta=\min\left\{\frac{c_-}{4},1-\frac{3c_+}{4}\right\}>0.
$$

*In particular, for all sufficiently large $h$,*

$$
-\log z(\alpha)\ge\log\frac1\alpha+\frac12B_h(1-\alpha)^{B_h}
$$

*uniformly on the displayed interval.*
:::

::: proof
*Proof.* First work in a terminal window and put $c_t=Dt/\log B_h$. We spell out the quantitative root reconstruction because its additive error is later compared with a vanishing coupon term. [Proposition 36](#prop-stable-shadow) and the exact root formulas give

$$
B_0=\widetilde a\,u_1^{D+1}\left(1+O(q_m+m\rho_m)\right),\qquad \kappa=u_1^b\left(1+O(\rho_m)\right).
$$

Since $z=B_0\kappa/(1+B_0)^b$, $x=-\log u_1$, and $B_0=B_h^{-1+o(1)}$, it follows that

$$
-\log z=\log\frac1{\widetilde a}+Kx+O(q_m+m\rho_m+B_0)=\log\frac1{\widetilde a}+Kx+B_h^{-c_t/4+o(1)},\qquad K=b+D+1=bD.
$$

The arithmetic identity $Kb^{h-1}=Db^h=B_h+2/(b-1)$ and [Theorem 37](#thm-terminal-matching) yield

$$
Kx=B_h(1-a_h(t))^{B_h}\left(1+B_h^{-c_t/4+o(1)}\right).
$$

[Lemma 38](#lem-edge-normalizer) gives $\log(\alpha/\widetilde a)=B_h^{-c_t/4+o(1)}$ and $B_h|\alpha-a_h(t)|=B_h^{-c_t/4+o(1)}$. The latter estimate changes the coupon term relatively by $1+B_h^{-c_t/4+o(1)}$. Hence

$$
-\log z-\log\frac1\alpha=B_h(1-\alpha)^{B_h}\left(1+B_h^{-c_t/4+o(1)}\right)+B_h^{-c_t/4+o(1)}.
$$

It remains to identify the terminal range corresponding to the displayed density interval. By [Lemma 38](#lem-edge-normalizer), uniformly in every terminal window, $\alpha B_h=Dt\left(1+B_h^{-c_t/4+o(1)}\right)$. Since $\log B_h=h\log b+O(1)$, choose constants $\delta_-,\delta_+>0$ such that $\underline\tau=(c_--\delta_-)\log b/D>0$ and $\overline\tau=(c_++\delta_+)\log b/D<4\log b/(3D)$. Uniformly on this broader terminal window, $\alpha B_h=Dt(1+o(1))$. At $t=\underline\tau h$ the resulting density is below $c_-\log B_h/B_h$, while at $t=\overline\tau h$ it is above $c_+\log B_h/B_h$. The terminal parameter increases the activity by [Lemma 24](#lem-activity-monotonicity), and activity increases the selected density by [Theorem 28](#thm-microcanonical-globality); hence every density in the displayed interval is exposed by a terminal parameter in the broader window. Uniformly there, $c_t=c+o(1)$, and the terminal-window estimate becomes the additive quantitative identity above.

Finally, $B_h(1-\alpha)^{B_h}=B_h^{1-c+o(1)}$. The additive error is therefore relatively $B_h^{3c/4-1+o(1)}$, while the multiplicative orbit error is $B_h^{-c/4+o(1)}$. Taking the worst exponent over $[c_-,c_+]$ proves the boxed activity law and the value of $\delta$; the lower-bound inequality follows immediately. □
:::

---

# A Capped-Free Profile and the Bounded Critical Window {#sec-bounded-window}

Put

$$
B=B_h,\qquad L=\log B,\qquad \mathcal D_h(\alpha):=H(\alpha)-\Psi_{d,h}(\alpha),\qquad Q_h(\alpha):=(1-\alpha)^B.
$$

We now construct a feasible profile whose only entropy loss is the conditioning event at the terminal wall.

Put $r=1-\alpha$ and

$$
T_j=1+b+\cdots+b^j=\frac{b^{j+1}-1}{b-1}.
$$

For $h\ge2$, define

$$
A_i=r^{T_{i-1}}\quad(1\le i\le h),\qquad A_{h+1}=0,
$$

$$
B_0=\alpha,\qquad B_i=A_i-A_{i+1}\quad(1\le i<h),\qquad B_h=A_h,
$$

and set

$$
\ell_i=B_i^2,\qquad x_i=B_{i-1}A_i.
$$

::: {#lem-capped-free-feasible .exhibit .exhibit--lemma data-exhibit-type="lemma" data-exhibit-name="Lemma 40 (Capped-free normalization and feasibility)"}
**Lemma 40** (Capped-free normalization and feasibility). *The profile above is normalized and has selected density $p_0=\alpha$. For $i<h$, its lower-neighbor marginal is the nonempty conditioned-binomial marginal with tilt $B_{i-1}/A_i$ and is strictly larger than $1/d$. At the terminal level,*

$$
p_h=A_{h-1}A_h,\qquad a_h=1-\varepsilon_h,\qquad \varepsilon_h:=\frac{A_h}{A_{h-1}}=r^{b^{h-1}}.
$$

*Consequently the profile is feasible whenever $\varepsilon_h\le(d-1)/d$.*

*More explicitly, for the window $|s|\le M$ in [Theorem 2](#thm-bounded-critical-window), feasibility holds for every $h\ge h_0(d,M)$, where*

$$
h_0(d,M):=\min\left\{h\ge2:L_h-2\log L_h-M\ge \frac{d(d-1)}{d-2}\log\frac d{d-1}\right\}.
$$
:::

::: proof
*Proof.* Since $B_0+A_1=1$ and $B_i+A_{i+1}=A_i$ for $i\ge1$,

$$
B_0^2+2B_0A_1=1-A_1^2,\qquad B_i^2+2B_iA_{i+1}=A_i^2-A_{i+1}^2.
$$

Summing gives total directed-edge mass one, and $p_0=B_0(B_0+A_1)=\alpha$.

For $i<h$, put $S_i=B_{i-1}+B_i+A_{i+1}$. The messages satisfy

$$
\kappa A_i=S_i^b,\qquad \kappa B_i=S_i^b-A_i^b,\qquad \kappa=1/r.
$$

It follows that $\kappa p_i=S_i^d-A_i^d$, $\kappa x_i=B_{i-1}S_i^b$, which is exactly the conditioned-binomial row identity with tilt $B_{i-1}/A_i$. A positive tilt gives expected nonempty-subset size strictly larger than one, hence lower-neighbor marginal strictly larger than $1/d$. The terminal formulas follow directly from $B_h=A_h$ and $B_{h-1}=A_{h-1}-A_h$.

It remains to verify the explicit threshold. Since $B_h<Db^h$,

$$
\alpha b^{h-1}>\frac{C}{Db}=\frac{d-2}{d(d-1)}C.
$$

Under the displayed threshold and $|s|\le M$, this is at least $\log(d/(d-1))$. Therefore

$$
\varepsilon_h=(1-\alpha)^{b^{h-1}}\le e^{-\alpha b^{h-1}}\le\frac{d-1}{d},
$$

as required. □
:::

Define

$$
\Delta_d(\varepsilon):=dH(\varepsilon)-s_d(1-\varepsilon).
$$

::: {#lem-capped-free-loss .exhibit .exhibit--lemma data-exhibit-type="lemma" data-exhibit-name="Lemma 41 (Exact capped-free entropy loss)"}
**Lemma 41** (Exact capped-free entropy loss). *Let $\mathcal F_{d,h}^{\mathrm{cap}}(\alpha)$ be the compact functional at the capped-free profile above. Then*

$$
\boxed{
H(\alpha)-\mathcal F_{d,h}^{\mathrm{cap}}(\alpha)=p_h\Delta_d(\varepsilon_h),
}
$$

*and*

$$
p_h\varepsilon_h^d=(1-\alpha)^B.
$$

*Moreover, as $\varepsilon\downarrow0$,*

$$
\Delta_d(\varepsilon)=\varepsilon^d\left(1+O_d(\varepsilon^{d-1})\right).
$$
:::

::: proof
*Proof.* First replace the terminal entropy $s_d(a_h)$ by the unconstrained coordinate entropy $dH(a_h)=dH(\varepsilon_h)$. For every nonterminal layer, and for the relaxed terminal layer, the dual entropy identity and the message row identities reduce the layer contribution to

$$
p_i\log\kappa-d x_i\log B_{i-1}+d x_{i+1}\log B_i,\qquad x_{h+1}=0.
$$

The sum over $i=1,\ldots,h$ telescopes to $(1-\alpha)\log\kappa-dx_1\log B_0$. The root contribution is $(d-1)\alpha\log\alpha-\tfrac d2\alpha^2\log(\alpha^2)$. Using $\kappa=1/r$, $x_1=\alpha r$, and $B_0=\alpha$, the relaxed total is exactly $H(\alpha)$. Restoring the nonempty terminal condition subtracts the displayed capped-free entropy loss.

Since $A_h=rA_{h-1}^b$,

$$
p_h\varepsilon_h^d=A_{h-1}A_h\left(\frac{A_h}{A_{h-1}}\right)^d=rA_h^d=r^{1+dT_{h-1}}=r^B,
$$

which proves the coupon identity.

For the asymptotic expansion, let $\eta$ be the coordinate-exclusion probability before conditioning on a nonempty subset. Then

$$
\varepsilon=\frac{\eta-\eta^d}{1-\eta^d},\qquad 1-\varepsilon=\frac{1-\eta}{1-\eta^d},\qquad \eta-\varepsilon=(1-\varepsilon)\eta^d,
$$

so $\eta=\varepsilon+O(\varepsilon^d)$. Substituting the first two identities into the entropy of the conditioned product measure gives

$$
\Delta_d(\varepsilon)=-\log(1-\eta^d)-d\,\mathrm{KL}\!\left(\operatorname{Ber}(\varepsilon)\Vert\operatorname{Ber}(\eta)\right).
$$

The Bernoulli chi-square bound makes the KL term $O_d(\varepsilon^{2d-1})$, while $-\log(1-\eta^d)=\varepsilon^d(1+O_d(\varepsilon^{d-1}))$. □
:::

::: proof
*Proof of [Theorem 2](#thm-bounded-critical-window).* The upper type anchor gives $\Psi_{d,h}(\alpha)\le H(\alpha)$, while [Lemma 40](#lem-capped-free-feasible) supplies a feasible compact profile for every sufficiently large $h$, uniformly in the displayed window. Hence [Lemma 41](#lem-capped-free-loss) implies

$$
0\le \mathcal D_h(\alpha)\le Q_h(\alpha)\left(1+O_d(\varepsilon_h^{d-1})\right).
$$

There, $\varepsilon_h=(1-\alpha)^{b^{h-1}}=B^{-\frac{d-2}{d(d-1)}+o(1)}$, which proves the upper bound in the theorem's two-sided estimate.

For the lower bound, define $\mathcal A_h(a):=-\log z(a)-\log(1/a)$. The envelope identity of [Corollary 29](#cor-envelope-identity) gives

$$
-\mathcal D_h'(a)=-\log(1-a)+\mathcal A_h(a).
$$

Put

$$
C_0=L-2\log L+s,\quad \alpha_0=C_0/B,\qquad C_1=\frac87L,\quad \alpha_1=C_1/B.
$$

For all large $h$, the interval lies in the fixed density window with $c_-=3/4$ and $c_+=8/7$. [Theorem 39](#thm-activity-law) applies uniformly there with relative error $B^{-1/7+o(1)}$. Since $-\log(1-a)\ge0$ and $\mathcal D_h(\alpha_1)\ge0$,

$$
\mathcal D_h(\alpha_0)\ge \left(1-B^{-1/7+o(1)}\right)B\int_{\alpha_0}^{\alpha_1}(1-a)^B\,da
=\left(1-B^{-1/7+o(1)}\right)\frac{B}{B+1}\left[(1-\alpha_0)^{B+1}-(1-\alpha_1)^{B+1}\right].
$$

Finally, $(1-\alpha_1)^B/(1-\alpha_0)^B=B^{-1/7}L^{-2}e^{s+o(1)}$, and $\alpha_0=O(L/B)$. This proves the lower bound in the two-sided estimate and hence the bounded-window identity. □
:::

::: proof
*Proof of [Corollary 3](#cor-critical-scaling-function).* Uniformly for bounded $s$,

$$
H\!\left(\frac{L-2\log L+s}{B}\right)=\frac{L^2}{B}(1+o(1)),
$$

whereas

$$
\left(1-\frac{L-2\log L+s}{B}\right)^B=e^{-s}\frac{L^2}{B}(1+o(1)).
$$

Apply [Theorem 2](#thm-bounded-critical-window). □
:::

::: proof
*Proof of [Corollary 4](#cor-annealed-zero-expansion).* For every fixed $\epsilon>0$, [Corollary 3](#cor-critical-scaling-function) gives opposite signs at $s=-\epsilon$ and $s=\epsilon$ for all large $h$; because strict concavity makes the superlevel set $\{\alpha:\Psi_{d,h}(\alpha)\ge0\}$ an interval, its lower endpoint satisfies $C_h^{\mathrm{ann}}=L-2\log L+o(1)$.

Let $F_B(C):=H(C/B)-(1-C/B)^B$. [Theorem 2](#thm-bounded-critical-window) gives

$$
\Psi_{d,h}(C/B)=F_B(C)+O\!\left((1-C/B)^B B^{-1/7+o(1)}\right)
$$

uniformly in a fixed neighborhood of the scalar root. There, $F_B'(C)=(1+o(1))(1-C/B)^B$, uniformly and with positive sign. A two-sided mean-value comparison therefore proves $C_h^{\mathrm{ann}}=\widehat C_{B_h}+O(B_h^{-1/7+o(1)})$.

It remains to invert the scalar equation. For $C=L+O(\ell)$, the scalar coupon root equation is equivalent to

$$
C+\log C+\log(L-\log C+1)=L+O(L^2/B).
$$

The equation first gives $C=L-2\ell+O(\ell/L)$; substituting this estimate successively into the two logarithms determines the coefficients through order $L^{-3}$. If $P_3$ denotes the degree-3 polynomial in the corollary's expansion, direct expansion gives

$$
P_3+\log P_3+\log(L-\log P_3+1)-L=O(\ell^4/L^4),
$$

while the derivative of the left side of the scalar log-equation is $1+O(1/L)$. Thus the mean-value theorem yields $\widehat C_B-P_3=O(\ell^4/L^4+L^2/B)=O(\ell^4/L^4)$, which supplies the claimed bootstrap remainder. Finally, $B^{-1/7+o(1)}$ is smaller than every fixed inverse power of $L$, so the graph-scalar comparison transfers the expansion to $C_h^{\mathrm{ann}}$. Repeating the same formal substitution and mean-value estimate yields the expansion to any prescribed fixed inverse power of $L$. □
:::

---

# Near-Critical Integration and the Random-Graph Deduction {#sec-integration}

We first prove [Theorem 6](#thm-near-critical). The pointwise anchor is [Corollary 12](#cor-entropy-anchor).

::: proof
*Proof of [Theorem 6](#thm-near-critical).* Put $B=B_h$ and $L=\log B$. For a value $C$ in the theorem's hypothesis, set

$$
\alpha_-=\frac CB,\qquad C^\sharp=\frac{L+C}2,\qquad \alpha_+=\frac{C^\sharp}B.
$$

For large $h$, the interval $[\alpha_-,\alpha_+]$ lies in a fixed density window $\eta L/(2B)\le a\le L/B$, so [Theorem 39](#thm-activity-law) applies uniformly. Exact globality and the envelope identity of [Corollary 29](#cor-envelope-identity) give

$$
\Psi(\alpha_-)=\Psi(\alpha_+)+\int_{\alpha_-}^{\alpha_+}\log z(a)\,da.
$$

[Corollary 12](#cor-entropy-anchor) and [Theorem 39](#thm-activity-law)'s displayed inequality imply

$$
\Psi(\alpha_-)\le H(\alpha_+)-\int_{\alpha_-}^{\alpha_+}\log\frac1a\,da-\frac12\int_{\alpha_-}^{\alpha_+}B(1-a)^Bda
\le H(\alpha_-)-\frac1{2}\frac{B}{B+1}\left[(1-\alpha_-)^{B+1}-(1-\alpha_+)^{B+1}\right].
$$

The second inequality uses $H'(a)=\log(1/a)+\log(1-a)$.

Write $W(C):=L-2\log L-C$. By hypothesis $W(C)\ge W_h\to\infty$. Uniformly over the theorem's interval,

$$
H(\alpha_-)=O\!\left(\frac{L^2}B\right)=o(e^{-C}),
$$

because $e^{-C}=e^{W(C)}L^2/B$. Also $C=O(L)$ gives $(1-\alpha_-)^{B+1}=e^{-C}(1+o(1))$. Finally, $C^\sharp-C=(L-C)/2\ge \log L+W_h/2$, so

$$
(1-\alpha_+)^{B+1}=e^{-C^\sharp}(1+o(1))=o(e^{-C}).
$$

All estimates are uniform, proving the theorem. □
:::

::: proof
*Proof of [Corollary 8](#cor-fixed-fraction-slack).* For $C=cL$ with $c\in[c_-,c_+]$, one has $L-2\log L-C=(1-c)L-2\log L\to\infty$ uniformly. [Theorem 6](#thm-near-critical) gives $e^{-C}=B^{-c}$. □
:::

::: proof
*Proof of [Theorem 5](#thm-fixed-slack-random).* Put $C_h^*=L_h-2\log L_h-\omega$, $T_n=nC_h^*/B_h$. If $T_n\le1$, then the real-valued lower bound follows from $\gamma_h(G)\ge1$. Otherwise set $m_n=\lceil T_n\rceil-1$, $C_n=m_nB_h/n$. The theorem's growth condition implies $B_h/n=o(1)$. Indeed, $h=\Theta_d(L_h)$. If $B_h\ge n$ along a subsequence and $x=B_h/n\ge1$, then

$$
\frac{nL_h^2/B_h}{h\log n}=\Theta_d\!\left(\frac{L_h}{x\log n}\right)=\Theta_d\!\left(\frac{1+\log x/\log n}{x}\right)=O_d(1),
$$

contradicting the growth condition. Hence $B_h<n$ eventually, so $L_h\le\log n$; the same displayed ratio tends to infinity only if $n/B_h\to\infty$. Therefore $C_n=C_h^*+o(1)$, $C_n\le C_h^*$.

The scaling-function convergence is uniform on compact $s$-intervals; hence

$$
\Psi_{d,h}(C_n/B_h)=-\left(e^\omega-1+o(1)\right)\frac{L_h^2}{B_h}.
$$

The uniform type estimate in [Remark 13](#sec-types) now gives

$$
\log \mathbb E Z_{n,d,h}(m_n)\le -\left(e^\omega-1+o(1)\right)\frac{nL_h^2}{B_h}+O_d(h\log n)\longrightarrow-\infty.
$$

Thus the pairing model has no dominating set of size exactly $m_n$ with high probability. Any smaller dominating set can be padded to size $m_n$, so $\gamma_h(G)\ge m_n+1=\lceil T_n\rceil\ge T_n$. Conditioning on simplicity transfers the conclusion to the uniformly random simple $d$-regular graph, and the domination inequality following [Definition 1](#def-two-path) gives the final assertion. □
:::

::: proof
*Proof of [Theorem 9](#thm-random-near-critical).* Set $T_n=nC_h^*/B_h$. For large $n$, $C_h^*>0$. If $T_n\le1$, the real-valued lower bound follows from $\gamma_h(G)\ge1$. Otherwise put $m_n=\lceil T_n\rceil-1$, $C_n=m_nB_h/n$. Then $m_n<T_n$ and $m_n/T_n\ge1/2$. Choose $\eta>0$ such that $C_h^*\ge2\eta L_h$ eventually. Then, for large $h$, $\eta L_h\le C_n\le C_h^*$.

Apply [Theorem 6](#thm-near-critical) with this $\eta$ and the same $W_h$. Since $e^{-C_n}\ge e^{-C_h^*}=e^{W_h}L_h^2/B_h$ and $\tfrac12-o(1)\ge\tfrac13$ for sufficiently large $h$,

$$
\log \mathbb E Z_{n,d,h}(m_n)\le -\frac13\frac{ne^{W_h}L_h^2}{B_h}+O_d(h\log n),
$$

which tends to $-\infty$ by the growth hypothesis. Markov's inequality shows that the configuration model has no dominating set of size exactly $m_n$ with high probability. Any smaller dominating set could be padded to size $m_n$, so $\gamma_h(G)\ge m_n+1=\lceil T_n\rceil\ge T_n$. Conditioning on simplicity transfers the conclusion to the uniformly random simple $d$-regular graph. □
:::

::: proof
*Proof of [Corollary 10](#cor-fixed-fraction-random).* Choose $W_h=\varepsilon L_h-2\log L_h$. Then $W_h\to\infty$, $C_h^*=(1-\varepsilon)L_h$, $C_h^*/L_h=1-\varepsilon>0$, and $e^{W_h}L_h^2/B_h=B_h^{-(1-\varepsilon)}$. Thus [Theorem 9](#thm-random-near-critical) applies directly. □
:::

---

# Numerical Verification and Conditioning {#sec-numerics}

The proofs above do not use numerical evidence. The accompanying package nevertheless checks every stationary identity, the one-step shadowing expansions, the density targeting, and the activity law with controlled-precision arithmetic.

A cancellation issue discovered during numerical verification is important for reproducibility. Direct evaluation of $\phi=\log Z_v-\tfrac d2\log Z_e$ can be ill-conditioned near criticality: both logarithms are large, and individual vertex terms of the form $S_i^d-(S_i-B_{i-1})^d$ may lose precision. The consolidated solver evaluates these differences as

$$
S_i^d\bigl[-\operatorname{expm1}(d\log(1-B_{i-1}/S_i))\bigr]
$$

and reports the microcanonical exponent through the corrected root-only formula of [Section 9](#sec-telescoping). The direct partition-function route is retained as an independent comparison. A row is rejected unless

$$
\frac{|\Psi_{Z_v}-\Psi_{\mathrm{root}}|}{|\Psi_{\mathrm{root}}|}\le 10^{-6}.
$$

Thus a cross-check residual comparable to the reported quantity gates the record rather than remaining hidden in an internal data structure.

For the diagnostic choice $W_h=\log\log B_h$, the regenerated cubic values are

| $h$ | $C$ | $-\Psi/e^{-C}$ | activity-law ratio |
|---:|---:|---:|---:|
| 20 | 6.8451 | 0.6484 | 0.5873 |
| 30 | 12.6345 | 0.9418 | 0.9520 |
| 40 | 18.7408 | 0.9757 | 0.9956 |
| 52 | 26.2980 | 0.9819 | 0.9997 |

The activity-law ratio is $\bigl(-\log z-\log(1/\alpha)\bigr)/\bigl(B_h(1-\alpha)^{B_h}\bigr)$. The effective onset is slower when $C/\log B_h$ is small, consistent with uniformity only on compact intervals bounded away from zero. Every numerical row records the checker hash, solver hash, precision, stationarity residual, telescoping residual, and the discrepancy between the direct and root-only free-energy routes.

The bounded-window audit evaluates both the true stationary optimizer and the capped-free profile at the center $s=0$. The two quantities approach the coupon term from opposite sides:

| $(d,h)$ | $(H-\Psi)/Q_h$ | cap loss$/Q_h$ | $C_h^{\mathrm{ann}}-\widehat C_{B_h}$ |
|---|---:|---:|---:|
| $(3,20)$ | 0.8750056 | 1.0593258 | $-1.03077\times10^{-1}$ |
| $(3,30)$ | 0.9902396 | 1.0076650 | $-8.00386\times10^{-3}$ |
| $(3,40)$ | 0.9990005 | 1.0009330 | $-8.57353\times10^{-4}$ |
| $(4,24)$ | 0.9999148 | 1.0000702 | $-6.78418\times10^{-5}$ |
| $(4,32)$ | 0.9999988 | 1.0000012 | $-1.01763\times10^{-6}$ |

The cap-loss and product identities are evaluated independently from the compact functional; their recorded residuals are below $10^{-120}$ in the displayed high-precision runs. The stationary entropy-defect identity of [Proposition 31](#prop-defect-identity) and the graph-zero computations provide separate checks of the two sides of the proof.

A companion, more narrative account of the underlying numerical package — including the code itself and the story of the concavity conjecture it killed — is at [From Path Tubes to a Near-Critical Domination Bound](/essays/growing-radius-domination.html). That page predates the bounded-window result proved here and still frames the project around the earlier near-critical slack theorem; the stationary-orbit machinery it walks through, however, is exactly the machinery this paper sharpens.

---

# Consequences and Open Problems {#sec-open}

[Theorem 2](#thm-bounded-critical-window) and [Theorem 5](#thm-fixed-slack-random) determine the annealed transition, its bounded window, and its universal scaling function. The capped-free construction also isolates the mechanism behind the coupon term: at the critical scale, the leading entropy defect is the cost of forbidding one empty terminal branch set. Two harder frontiers remain logically separate.

## Quenched matching

The random-regular theorem is a first-moment lower bound. A matching upper bound near $C_h^{\mathrm{ann}}$ would require proving that dominating sets actually exist above the annealed crossing. Plausible routes include a second-moment analysis with an overlap variational problem, small-subgraph conditioning, or an algorithmic construction whose output reaches the scalar coupon coordinate. The bounded-window theorem now supplies a precise target and separates any quenched correction from uncertainty in the annealed calculation.

## Direct two-branch asymptotics

Internally two-path $(h,2)$ domination is defined in [Definition 1](#def-two-path) and is stronger than ordinary distance domination, so the present lower bound transfers automatically. It does not identify the parameter's own leading constant or critical correction. A direct treatment must remember branch information without falsely treating two paths that later merge as internally disjoint. Directed nonbacktracking cavity states are a natural exact intermediary, but the corresponding type system and variational reduction remain to be developed.

The exponent $1/7$ in the graph–scalar comparison of [Corollary 4](#cor-annealed-zero-expansion) is a bookkeeping exponent rather than a predicted optimum. Improving it would sharpen finite-$h$ convergence but would not change the scaling function or any fixed-order inverse-logarithmic term.
</content>
