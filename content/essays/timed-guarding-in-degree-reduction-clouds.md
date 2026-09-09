---
title: "Timed Guarding in Degree-Reduction Clouds"
subtitle: "A square-root transfer without the cloud-order factor"
date: 2026-09-09
abstract: >
  The actual Hosseini–Mohar–Gonzalez Hermosillo de la Maza stopping tower
  admits a square-root cop bound in the order of its base whenever the base
  satisfies the fixed multistage hypotheses used by the earlier occupation
  transfer. Fixed port anchors pay for timed retraction setup within the
  original five-layer accessibility margin. Synchronized setup leaves at most
  two exceptional clouds, handled by a reusable reserve. The resulting bound
  $c(H)\le C\sqrt N$ has no multiplicative dependence on cloud order or tower
  scale. The theorem retains the full remaining-ball Hall demand and does not
  give an all-graphs Meyniel bound.
tags:
  - research
  - research/mathematics
  - research/graph-theory
authors:
  - "Levi Neuwirth | /me.html"
bibliography: data/timed-guarding-in-degree-reduction-clouds.bib
preprint: /papers/timed-guarding-in-degree-reduction-clouds.pdf
no-collapse: true
status: "Durable"
confidence: proved
evidence: 5
peer-status: unreviewed
result-shape: mixed
history:
  - date: "2026-09-09"
    note: "Explicit whole-tower lower-transfer clock; isometric geodesic lifts, longer-walk cloud counts, and the exact adjacent-cloud retraction criterion. Direct internal two-cop proof. The timed upper theorem is unchanged."
  - date: "2026-09-09"
    note: "Initial paper: explicit cloud retractions, timed port-anchor deployment, synchronized cleanup and finishing, and the remaining Hall-capacity obstruction."
---

# Main result

The [earlier occupation transfer](/essays/ball-occupation-under-coarse-projections.html#adaptive-multistage) places a squad of $P$ cops at each sampled base vertex, where $P$ bounds the size of a replacement cloud. Under fixed multistage hypotheses on an $N$-vertex base, it proves $c(H)\le CP\sqrt N$ for every occupation projection. The [new paper](/papers/timed-guarding-in-degree-reduction-clouds.pdf) removes that factor for the actual degree-reduction construction of Hosseini, Mohar, and Gonzalez Hermosillo de la Maza (HMGHM) [@HMG]. Its proof uses the internal geometry of those clouds and keeps the original five-layer accessibility requirement.

::: {#thm-cloud-transfer .exhibit .exhibit--theorem data-exhibit-type="theorem" data-exhibit-name="Theorem 1 (Timed guarding in the stopping tower)"}
**Theorem 1** (Timed guarding in the stopping tower). *Fix an integer $d\ge2$ and fixed constants $a_0\ge0$ and $\delta,J,a_1,\ldots,a_5>0$. Let $G$ be a connected simple graph of order $N$ satisfying the five-layer multistage hypotheses below. Form $H$ by the actual all-vertex HMGHM replacement rule, stopping when the whole graph is subcubic. For sufficiently large $N$,*

$$
\boxed{c(H)\le C\sqrt N.}
$$

*The constant depends only on the fixed multistage parameters. It is independent of the maximum base degree $D$, the maximum cloud order $P$, and the tower scale $\lambda=3^k$. The bound concerns $N=|V(G)|$, the order of the base. No bound of the earlier form on capture time is asserted.*
:::

Here $d$ is the fixed branching parameter in the growth hypotheses. It is not a new assumption that the maximum degree $D$ is fixed.

The base hypotheses are exactly [Definition 24 with $s=5$](/essays/ball-occupation-under-coarse-projections.html#def-multistage-base). There is a set $X$ of at most $a_0\sqrt N$ exceptional base vertices. The sphere bounds

$$
a_1|V'|d^{r'}\le |S_G(V',r')|\le a_2|V'|d^{r'}
$$

hold for every eligible source set $V'\subseteq B_G(v,r)\setminus X$, with $v\notin X$, $r,r'\ge1$, $d^r,d^{r'}<N^{1/2+\delta}$, and $|V'|d^{r'}\le N/(\log N)^J$. These are uniform bounds over source sets, rather than estimates for a single chosen ball.

The reservoir condition applies to every eligible frontier $A\subseteq S_G(v,r)\setminus X$ with $|A|>N^{1/4-\delta}$, where both $(d+1)d^r$ and $(d+1)d^{r'}$ lie between $N^{1/4-\delta}$ and $N^{1/4+\delta}$. Put $U=\bigcup_{a\in A}S_G(a,r')$ and require $|U|d^{r+r'}<a_3N$. After deleting a set $Q$ meeting each $S_G(a,r')$ in fewer than $N^{1/4-2\delta}$ vertices, each target $w\in U\setminus Q$ has a reservoir

$$
W(w)\subseteq B_G(w,r+r'-4),\qquad
|W(w)|\ge a_4\min\left\{d^{r+r'-4},\frac{a_5N}{|U|}\right\},
$$

and the reservoirs are pairwise disjoint. Connectivity supplies the remaining condition. These hypotheses and the multistage probability argument come from Prałat–Wormald's framework; the earlier paper derives the required early levels from their fixed-degree random-regular construction [@PralatWormald, Theorem 4.1; @PralatWormaldRegular, Lemma 3.2 and Sub-lemma 3.4].

# Why the tower retains the base cop number {#lower-transfer-clock}

The lower comparison $c(G)\le c(H)$ holds for every actual HMGHM tower, with no growth or accessibility assumptions [@HMG, Theorem 3(a)]. The revised paper gives a self-contained proof for the entire tower. Its timing matters: after the first actual cop move, the checkpoints occur immediately after cop moves, when it is the robber's turn.

At a checkpoint the robber occupies a designated port $p\in F_v$. A base escape strategy selects $w\in N_G[v]$ at distance at least two from every current cop shadow. For any actual cop position $z$, the metric lower bound gives

$$
\operatorname{dist}_H(z,F_w)\ge\lambda+1.
$$

For a move $v\to w$, let $a$ be the port of $F_v$ toward $w$. Follow a length-$L$ port path to $a$, or wait $L$ times if already there, then cross into $F_w$. The block runs

$$
R_1,C_1,\ldots,R_\lambda,C_\lambda.
$$

The starting cop distance to $a$ is at least $\lambda$. At the robber's intermediate position $r_j$, the remaining route to $a$ has length at most $L-j$, so

$$
\operatorname{dist}_H(z,r_j)\ge\lambda-(L-j)=j+1.
$$

This excludes capture even after the $j$th cop reply. The last position is safe through reply $\lambda$ by the distance to $F_w$. A base wait is handled by waiting $\lambda$ times in its safe cloud. During these $\lambda$ cop moves, each cop visits at most two clouds, so its endpoint shadows give one legal base cop move. The invariant repeats against arbitrary cop walks, including paths through shared hubs.

The initial base escape placement is at distance at least two from the initial cop shadows, making the first actual cop move safe. Thus the construction respects the original cop-first game. Giving a cop an additional move from an exterior door into the departure cloud before $R_1$ changes the checkpoint: its shadow would already coincide with the base robber. That interception does not invalidate the lower comparison. No private-tunnel assumption is needed.

# Why one cop can guard a cloud

Write $F_v$ for the final ancestry cloud of a base vertex $v$, and put $L=\lambda-1$. Distinct designated ports in one cloud are at intrinsic distance exactly $L$. The paper constructs a retraction $\rho_v:H\to H[F_v]$ fixing every vertex of the cloud. A cop that reaches the robber's retracted image can subsequently follow that image, capturing any actual entry into the cloud on the next cop move. Guarding through a retracted robber image is a standard method [@RetractCover2013, p. 2]; the issue here is its timed implementation in these clouds.

The setup also has a useful clock. Choose a designated port as anchor and a common breadth-first tree for its paths to the other ports. While the robber stays outside the cloud, the explicit retraction sends her walk to a lazy walk along this tree, whose depth is at most $L$. A cop starting at the anchor meets that exterior shadow within $L$ cop moves. This claim concerns the edges of the projected walk: merely placing its vertices in a spanning tree would not suffice.

A robber can cross an external cloud edge in one move, so setup cannot be postponed until that crossing threatens. The proof instead dispatches fresh cops to their anchors and starts setup only after both anchor arrival and revelation of the relevant round root. Either event may occur first; a cop arriving after the root is revealed still receives its full setup allowance.

# When one guard can cover two clouds {#adjacent-cloud-criterion}

For a nontrivial tower, the induced union $H[F_u\cup F_v]$ of two adjacent clouds is a retract exactly when the base edge $uv$ lies in no triangle. In that case the two port trees can be joined across their unique bridge. The paper extends the retraction through exterior distance regions and obtains a tree shadow of height at most $L+1$. One cop starting at either bridge endpoint establishes the guard within that many moves, provided the robber stays outside the union throughout setup. This is a guard-setup statement, not a one-cop internal pursuit bound.

If a triangle contains $uv$, its two ports toward the third cloud have intrinsic distance $2L+1$ in the union and an exterior route of length $L+2$. For $L\ge2$ the shortcut excludes a retract. Triangles elsewhere in the base do not matter. The restriction to nontrivial towers is necessary: at $k=0$ the union is an ordinary edge and is always a lazy retract.

The proposed neighborhood extension at girth five fails. In $C_5$, the three clouds over a closed neighborhood have two outward-facing ports at intrinsic distance $3L+2$, whereas the complementary route has length $2L+3$. A high-degree tree attached outside that neighborhood forces a nontrivial stopping tower while preserving the obstruction.

# Port anchors pay for the setup

Place every sampled cop initially at a fixed designated port of its source cloud, and leave unused teams there until dispatch. For source and target anchors over vertices at base distance $q$, following a base geodesic costs at most

$$
q+(q+1)L=\lambda q+L.
$$

The $q$ external edges and the endpoint and intermediate port traversals account for every move. If the endpoint ports are specifically those of the first and last edges of a base geodesic, both endpoint traversals vanish. The lift then has length $\lambda(q-1)+1$, attains the ambient lower bound, and is an isometric path. Arbitrary endpoint anchors need not have that property. Compared with deployment to arbitrary vertices, this saves the $L$ moves needed for exterior-shadow setup.

For successive round radii $r,r'$, the existing reservoirs lie at radius $t=r+r'-4$. All assigned cops reach their target anchors by cop move

$$
B=\lambda t+L=\lambda(r+r'-3)-1.
$$

Let the first round end at robber move $q_0$, revealing the next root $u$. Activate only targets in the actual next sphere, starting their $L$-move chases together after robber move $\sigma=\max(B,q_0)$. The first possible entry into any such cloud occurs at a robber move $m$ with

$$
m\ge q_0+\lambda(r'-1)+1\ge\lambda(r+r'-2)+2.
$$

Since $B+L\le m-4$ and $q_0+L\le m-2$ when $r'\ge2$, setup ends before entry. The cop moves first in each turn. Waiting, reversal, and the delayed revelation of $u$ are all included in this comparison. No sixth accessibility layer is needed.

The random event still concerns reservoir hits and observed base-exit sequences. The guarding motions depend on the full robber walk, but the deterministic setup argument succeeds for every such walk once the assigned reservoirs are hit. It therefore adds no hidden conditioning on within-round behavior and no new probabilistic history count. Every sampled team is placed before the original robber start and stays at its source ports until its own dispatch, including during the initial setup of the exceptional guards.

# Synchronized setup handles waiting and finishing

The finishing targets form a union of remaining balls, since a robber can stay inside a cloud. Their cops arrive at the anchors and begin setup at one common time. During $L$ robber moves, at most two ancestry clouds can be visited: reaching a third would require two external edges and an intervening traversal between distinct ports, costing at least $L+2$ moves.

More generally, a walk of at most $j\lambda$ edges visits at most $j+1$ ancestry clouds. For a window of $T\ge1$ moves, the exact general upper bound used here is $2+\lfloor(T-1)/\lambda\rfloor$. This bounds the number of exceptions in a longer setup window; keeping them confined still requires a guarded boundary.

Every unvisited target cloud acquires a persistent guard. The finishing clock ends strictly before the robber can reach the relevant ball's boundary, so the at most two visited exceptions lie in its interior. All their other neighboring clouds are guarded. If two exceptions remain, their union has exactly one joining edge because the base is simple.

Let $K=\max_v c(H[F_v])$. One reusable reserve of $K+1$ cops now suffices: one guards that joining edge, and $K$ deploy and pursue within the observed robber side. The same synchronized procedure supplies reusable cleanup in each ordinary round. Travel after the exceptional union has been isolated may take arbitrary finite time; the established guards remain active throughout.

The internal cloud bound is $K\le2D$ for the actual stopping tower. Its proof gives a direct two-cop strategy on a once-subdivided clique, preserves that bound through independent twin classes, and then uses recursive setup through descendant-cloud retractions. Before the multistage rounds start, the exceptional $X$ clouds receive their own retained guards using the same reserve, while all sampled teams remain at their initial ports. Thus the intermediate cop budget is

$$
C\sqrt N+K+1\le C\sqrt N+2D+1.
$$

H1 itself absorbs the remaining degree term. For $v\notin X$, its radius-one and radius-two bounds give $|S_G(v,1)|\le a_2d$ and $|S_G(v,2)|\le a_2d^2$. A vertex of $X$ adjacent to $v$ consequently has degree at most $1+a_2d+a_2d^2$; a vertex of $X$ without an outside neighbor has degree at most $|X|-1$. Hence

$$
D\le a_0\sqrt N+1+a_2d+a_2d^2,
$$

and the total is $C'\sqrt N$ with fixed constants.

# What remains between this theorem and Meyniel

The theorem applies to the actual stopping tower over the stated multistage base class. The unconditional lower comparison above preserves feedback to the base; the unproved universal extension is the upper strategy under weaker base hypotheses. It does not transfer an arbitrary winning strategy on an arbitrary base, improve the growing-degree hard-family estimate, or establish uniformity for a growing branching parameter $d$ in the random-regular input. The maximum degree $D$ may grow subject to H1 and is absorbed by the bound above. A late transition team restricted to the old side can still miss a five-turn handoff; the successful schedule pays for travel before that deadline.

The remaining demand condition is a separate obstruction. For a nonempty target set $U$, define

$$
R_t(U)=\min_{\varnothing\ne A\subseteq U}\frac{|B_G(A,t)|}{|A|},
\qquad
V=\max_{w\in U}|B_G(w,t)|.
$$

If $U$ contains an ambient ball $B_G(a,u)$ of size $M$, with $u\ge1$, then the paper proves

$$
R_t(U)\le1+V\frac{\log M}{u}.
$$

Consequently an all-subsets Hall demand can be incompatible with a slowly growing remaining ball even after the cost inside each cloud has been removed. The proof still assigns a separate cop to every base vertex in its finishing demand; it does not bypass that capacity constraint.

The next question is whether a smaller frontier or boundary demand can support a comparable timed strategy under shrinking expansion, including capture when the robber waits. The answer must supply both enough accessible cops and a legal retained-guard invariant. The present theorem establishes the cloud mechanism under fixed multistage hypotheses; Meyniel's conjecture for all graphs remains open. The bounded source comparison does not establish priority for every component lemma.
