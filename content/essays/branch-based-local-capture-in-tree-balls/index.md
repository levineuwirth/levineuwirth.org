---
title: "Branch-Tube Persistence and Static Coverage in Tree-Ball Geometry"
date: 2026-07-21
abstract: >
  We analyze exhaustive static coverage by path tubes indexed by length-$t$
  nonbacktracking robber paths from $v_0$ in a finite-horizon local chase on a
  $d$-regular graph. An endpoint-sensitive geodesic lemma shows that, among
  possibly infinite $d$-regular graphs, radius $R+t$ is sharp for arbitrary
  pairs in $B_R(v_0)\times B_t(v_0)$, while synchronized witnesses along a
  prescribed path require only a radius-$R$ tree-ball. If every tube is
  occupied, each surviving round along every path in this class ends in
  capture, blockage, or branch-load support on at least two branches. The
  tubes partition the outer ball, so deterministic coverage has minimum cost
  $N_t=d(d-1)^{t-1}$; conditional on a specified root, i.i.d. uniform
  coverage has threshold $\Theta(N_t\log N_t)$ for fixed $d$. An augmented
  prefix-depth profile that retains the complete shallow configuration still
  need not determine later support. The result is local and root-dependent:
  it treats neither arbitrary robber walks nor a robber-independent cop
  strategy, and it gives no cop-number bound.
tags:
  - research
  - research/mathematics
  - research/graph-theory
authors:
  - "Levi Neuwirth | /me.html"
affiliation:
  - "Brown University | https://www.brown.edu"
bibliography: data/branch-capture-paper.bib
preprint: /papers/branch-capture-paper.pdf
no-collapse: true
status: "Durable"
confidence: proved
evidence: 5
peer-status: unreviewed
result-shape: mixed
further-reading:
  - Quilliot
  - NowakowskiWinkler
  - AignerFromme
  - Frankl
  - LuPeng
  - ScottSudakov
  - FriezeKrivelevichLoh
  - PralatWormald
  - BradshawHosseiniMoharStacho
  - HMG
history:
  - date: "2026-07-27"
  - date: "2026-07-21"
  - date: "2026-05-08"
  - date: "2026-05-06"

---

# Introduction

## Motivation

The cops-and-robbers game, introduced independently in its one-cop form by Quilliot and by Nowakowski–Winkler and developed in its multiple-cop form by Aigner–Fromme [@Quilliot; @NowakowskiWinkler; @AignerFromme], is a pursuit-evasion game on a graph in which $k$ cops attempt to capture one robber. The minimum such $k$ is the *cop number* $c(G)$. *Meyniel's conjecture*, attributed to Henri Meyniel and appearing in the early literature in Frankl's work [@Frankl], asserts that $c(G)=O(\sqrt n)$ for every connected graph on $n$ vertices and remains a central open problem in the area. The best general upper bound, $$c(G) \leq \frac{n}{2^{(1-o(1))\sqrt{\log_2 n}}},$$ was proved independently by Lu–Peng, Scott–Sudakov, and Frieze–Krivelevich–Loh [@LuPeng; @ScottSudakov; @FriezeKrivelevichLoh].

Prałat–Wormald's random-graph argument combines an initial random cop placement with assignments made after the robber's start is revealed: in different regimes, cop teams fully occupy a neighborhood or densely cover a sphere [@PralatWormald]. Tree-like geometry enters the literature in several other ways. Aigner–Fromme show that one moving cop can guard a fixed isometric path [@AignerFromme]. Frankl established a high-girth lower bound [@Frankl], and Bradshaw–Hosseini–Mohar–Stacho refine that line through a branch-weight argument in which unique local geodesics let the robber choose a sufficiently lightly controlled forward branch [@BradshawHosseiniMoharStacho]. Related bounded-degree reductions provide broader extremal context [@HMG]. These mechanisms motivate a path-conditioned local question: whether cops near the robber can coordinate their distance-decreasing moves along every prescribed length-$t$ nonbacktracking path starting at the robber's initial vertex.

The present paper instead isolates one rigid, root-dependent certificate: every length-$t$ nonbacktracking path from $v_0$ indexes an occupied descendant tube. Paths here index a static partition of the outer ball rather than a route guarded by one moving cop or an adaptively selected escape branch. We determine this certificate's guarantee and cost. Arbitrary robber walks, including stationary moves and reversals, are not analyzed, and exact tree geometry is not asserted to be necessary.

The uniform sampling below is conditional on the fixed root $v_0$: the root is specified before cop positions are sampled from $B_R(v_0)$. This measures the local cost of the certificate, not a legal initial placement in the standard game, where cops choose positions before the robber chooses its start. A global strategy would need comparable coverage simultaneously or adaptively for an unknown robber position. Accordingly, the results neither construct a robber-independent global strategy nor improve the cop-number bound.

## Setup and endpoint-sensitive tree-ball geodesics

Graphs are simple and undirected. The local results allow finite or infinite graphs unless finiteness is stated explicitly; discussion of the cop number and all $n$-vertex asymptotics concerns finite connected graphs. Throughout, $G$ denotes a $d$-regular graph with $d\geq3$, and $v_0\in V(G)$ is the robber's initial position in the rooted local experiment. All radii and time horizons are nonnegative integers, and $t,r\geq1$ whenever length-$t$ or order-$r$ objects are used. All unadorned logarithms are natural. We write $$B_R(v)=\{x\in V(G):\operatorname{dist}(x,v)\leq R\},
\qquad
S_j(v)=\{x\in V(G):\operatorname{dist}(x,v)=j\}.$$

::: {#def-tree-ball .exhibit .exhibit--definition data-exhibit-type="definition" data-exhibit-name="Definition 1 (Tree-ball)"}
**Definition 1** (Tree-ball). The ball $B_R(v_0)$ is a *tree-ball* if the induced subgraph $G[B_R(v_0)]$ is a tree.
:::

This is a local condition at the specified center. The global condition $\operatorname{girth}(G)>2R+1$ implies that every radius-$R$ ball is a tree-ball. Conversely, if every radius-$R$ ball is a tree-ball, then $\operatorname{girth}(G)>2R+1$.

An induced tree-ball does not control shortest paths between arbitrary pairs of its vertices: a competing path may leave the ball and re-enter. The required radius depends on the endpoint depths and on the length of their path inside the tree-ball.

::: {#lem-buffer .exhibit .exhibit--lemma data-exhibit-type="lemma" data-exhibit-name="Lemma 2 (Endpoint-sensitive tree-ball geodesics)"}
**Lemma 2** (Endpoint-sensitive tree-ball geodesics). *Suppose $B_q(v_0)$ is a tree-ball, let $x,y\in B_q(v_0)$, and let $L$ be the length of the $x$–$y$ path in $G[B_q(v_0)]$. If $$\operatorname{dist}(x,v_0)+\operatorname{dist}(y,v_0)+L\leq 2q,$$ then every ambient $x$–$y$ geodesic lies in $B_q(v_0)$. Consequently, that geodesic is unique and equals the $x$–$y$ path in $G[B_q(v_0)]$.*
:::

::: proof
*Proof.* Let $P$ be an ambient $x$–$y$ geodesic of length $\ell$. The path in $G[B_q(v_0)]$ gives $\ell\leq L$. For $z\in P$, write $h=\operatorname{dist}_P(x,z)$. Then $$\operatorname{dist}(z,v_0)
\leq \min\{\operatorname{dist}(x,v_0)+h,\ \operatorname{dist}(y,v_0)+\ell-h\}
\leq \frac{\operatorname{dist}(x,v_0)+\operatorname{dist}(y,v_0)+\ell}{2}
\leq q.$$ Thus $P\subseteq B_q(v_0)$. Since the induced graph on this ball is a tree, $P$ is its unique $x$–$y$ path. □
:::

::: {#rem-uniform-buffers .exhibit .exhibit--remark data-exhibit-type="remark" data-exhibit-name="Remark 3 (Uniform buffers versus chase endpoints)"}
**Remark 3** (Uniform buffers versus chase endpoints). For arbitrary $x\in B_R(v_0)$ and $y\in B_t(v_0)$, the walk from $x$ to $y$ through $v_0$ has length at most $R+t$. If $B_{R+t}(v_0)$ is a tree-ball, the path between $x$ and $y$ in the rooted tree $G[B_{R+t}(v_0)]$ is no longer than this walk, so Lemma [2](#lem-buffer) applies. For $R,t\geq1$, this uniform radius cannot in general be reduced. Put $L=R+t$, begin with the rooted $d$-regular tree truncated at depth $L-1$, and choose vertices $x$ and $y$ at depths $R$ and $t$ in distinct root branches. Choose descendants $a$ of $x$ and $b$ of $y$ in $S_{L-1}(v_0)$, allowing equality, add a new vertex $z$, and join $z$ to $a$ and $b$.

Complete the graph explicitly: for each remaining degree deficit at a vertex of $S_{L-1}(v_0)\cup\{z\}$, attach by one edge a separate infinite rooted $(d-1)$-ary tree. Every vertex then has degree $d$, and the resulting graph is infinite, simple, and connected. The induced ball $B_{L-1}(v_0)$ is still the original tree. The path from $x$ to $y$ through $v_0$ has length $L$, while the path through $z$ has length $$\operatorname{dist}(x,a)+2+\operatorname{dist}(b,y)=(t-1)+2+(R-1)=L.$$ Each attached infinite tree meets the displayed core at only one vertex, so it creates no additional route between $x$ and $y$. Thus the two displayed paths are distinct geodesics. This proves sharpness at radius $R+t-1$ among possibly infinite $d$-regular graphs.

The endpoint pairs used along a prescribed length-$t$ nonbacktracking path are more restricted. Their rooted-tree path and endpoint depths satisfy Lemma [2](#lem-buffer) with $q=R$, so the persistence result requires no tree-ball beyond the cop-placement radius. This does not assert that the radius-$R$ tree-ball hypothesis is necessary. Controlled cyclic geometry is not addressed here, and no cyclic extension is proved.
:::

Whenever $B_q(v_0)$ is a tree-ball, we root $G[B_q(v_0)]$ at $v_0$. Every vertex other than $v_0$ has a unique parent, and every vertex of depth less than $q$ has $d-1$ children.

::: {#def-cone .exhibit .exhibit--definition data-exhibit-type="definition" data-exhibit-name="Definition 4 (Geodesic cone)"}
**Definition 4** (Geodesic cone). Suppose $B_r(v)$ is a tree-ball and $u\in N(v)$. The *geodesic cone* through $u$ at radius $r$ is $$C_u(v,r):=\{x\in B_r(v)\setminus\{v\}:\text{the path from $x$ to $v$ in $B_r(v)$ has penultimate vertex $u$}\}.$$
:::

::: {#def-tube .exhibit .exhibit--definition data-exhibit-type="definition" data-exhibit-name="Definition 5 (Path tube)"}
**Definition 5** (Path tube). Let $R\geq t$, suppose $B_R(v_0)$ is a tree-ball, and let $$\sigma=(v_0,v_1,\ldots,v_t)$$ be a length-$t$ nonbacktracking path starting at $v_0$: consecutive vertices are adjacent and $v_{i+1}\neq v_{i-1}$ whenever the latter condition is defined. The *length-$t$ tube* associated with $\sigma$ is $$T_\sigma(R):=\{x\in B_R(v_0):\text{the rooted path from $x$ to $v_0$ contains $v_t,v_{t-1},\ldots,v_1$ in order}\}.$$ Equivalently, $T_\sigma(R)$ is the set of descendants of $v_t$ lying in $B_R(v_0)$.
:::

## Game conventions

A *cop configuration* $X$ is a finite multiset of vertices, represented by its finitely supported multiplicity function $X(v)\in\mathbb Z_{\geq0}$. For $A\subseteq V(G)$, set $$X(A):=\sum_{v\in A}X(v),
\qquad
|X|:=X(V(G)),
\qquad
\mathop{\mathrm{supp}}(X):=\{v:X(v)>0\}.$$ Thus counts of cops include multiplicity, several cops may occupy one vertex, and $A$ is occupied exactly when $X(A)>0$. We write $X=[x_1,\ldots,x_k]$ for a multiset of cop positions, with repeated entries allowed. Independent uniform sampling is with replacement and produces the multiset of sampled positions.

Capture occurs whenever a cop and the robber occupy the same vertex, including before the first cop move; once capture occurs, no further move is made. Conditional on no capture, the cops move first in each round, simultaneously, and each cop moves to a neighboring vertex minimizing its distance to the robber's current vertex. Ties may be broken arbitrarily. Some formulations also allow cops to pass; the results remain valid there by having the selected witnesses make the prescribed distance-decreasing moves. Under the tree-ball hypotheses below, Lemma [2](#lem-buffer) shows that each witness selected in our proofs has a unique distance-decreasing move.

We analyze only length-$t$ nonbacktracking robber paths starting at $v_0$. In the full game a robber walk may reverse an edge or, under common conventions, remain stationary. Neither behavior is covered here. Fix a prescribed path $$\tau=(v_0,v_1,\ldots,v_t).$$ It survives through round $0$ precisely when no initial capture occurs. If it has survived through round $s-1$, then the robber is at $v_{s-1}$ when round $s$ begins. After the cops move toward $v_{s-1}$, the robber is captured if a cop occupies $v_{s-1}$. Otherwise the prescribed move $v_{s-1}\to v_s$ is *legal* if no cop occupies $v_s$ after the cop move. The path survives through round $s$ if no capture or blockage has occurred through that move.

For a robber position $v$ and a neighbor $u\in N(v)$, an individual cop at $c\neq v$ whose $c$–$v$ geodesic is unique *contributes to branch $u$ at $v$* if that geodesic has penultimate vertex $u$. The *branch-load support* at $v$ is the set of branches receiving at least one contributing cop; its size counts branches, not cops.

## Main results and scope

Although $R+t$ is the sharp uniform radius for arbitrary endpoint pairs in $B_R(v_0)\times B_t(v_0)$, the synchronized pairs arising along a prescribed length-$t$ nonbacktracking path satisfy the endpoint-sensitive criterion already at radius $R$. Accordingly, the persistence theorem assumes only that the cop-placement ball $B_R(v_0)$ is a tree-ball.

Exact rooted-tree counts identify first-level cones as the $t=1$ path tubes and show that the length-$t$ tubes partition the outer ball. Conditional on the prescribed path continuing, a witness's initial depth determines a potential capture or blockage time within the horizon or certifies descendant pressure throughout it. This yields a persistence theorem uniform over all length-$t$ nonbacktracking paths starting at $v_0$, and only over that class.

The next results quantify the price of exhaustive static coverage. Exactly $$N_t=d(d-1)^{t-1}$$ cops are necessary and sufficient to occupy every tube at a fixed root. Along fixed-degree sequences with $t\to\infty$, conditional uniform sampling has a threshold of order $N_t\log N_t$; its leading factor depends explicitly on $R-t$ and tends to $1$ when $R-t\to\infty$.

Finally, Section [5](#sec-profile-loss) records information lost by finite-order tube profiles. Even after retaining every shallow cop multiplicity, such a profile need not determine branch support after $r+1$ rounds. This exact nondeterminacy does not rule out one-sided certificates that reject ambiguous profile fibers.

# Cone and Tube Counts

::: {#lem-shell .exhibit .exhibit--lemma data-exhibit-type="lemma" data-exhibit-name="Lemma 6 (Sharp shell and cone counts)"}
**Lemma 6** (Sharp shell and cone counts). *Let $G$ be $d$-regular with $d\geq3$, and suppose $B_r(v)$ is a tree-ball. Then for every $u\in N(v)$ and $1\leq j\leq r$, $$|C_u(v,r)\cap S_j(v)|=(d-1)^{j-1},
\qquad
|S_j(v)|=d(d-1)^{j-1}.$$ Hence $$|C_u(v,r)|=\sum_{j=1}^r(d-1)^{j-1}
=\frac{(d-1)^r-1}{d-2},$$ and $$|B_r(v)|=1+d\frac{(d-1)^r-1}{d-2}.$$*
:::

::: proof
*Proof.* The branch rooted at $u$ is a $(d-1)$-ary rooted tree of depth $r-1$. Its level $j-1$ contains $(d-1)^{j-1}$ vertices, giving the first formula. Summing over the $d$ branches gives the shell count, and the remaining identities follow by summing the geometric series. □
:::

For $t=1$, geodesic cones are exactly the path tubes. We now count the general length-$t$ objects that drive the persistence argument.

::: {#lem-tube-partition .exhibit .exhibit--lemma data-exhibit-type="lemma" data-exhibit-name="Lemma 7 (Tube count and partition)"}
**Lemma 7** (Tube count and partition). *Let $R\geq t$, and suppose $B_R(v_0)$ is a tree-ball. For every length-$t$ nonbacktracking path $\sigma$ starting at $v_0$, $$|T_\sigma(R)|
=\sum_{j=t}^R(d-1)^{j-t}
=\frac{(d-1)^{R-t+1}-1}{d-2}.$$ The length-$t$ tubes are pairwise disjoint and form a partition $$B_R(v_0)\setminus B_{t-1}(v_0)
=\bigsqcup_{\sigma}T_\sigma(R),$$ where $\sigma$ ranges over all length-$t$ nonbacktracking paths from $v_0$. Their number is $$N_t=d(d-1)^{t-1}.$$*
:::

::: proof
*Proof.* At total depth $j\geq t$, the descendants of the terminal vertex $v_t$ form the depth-$(j-t)$ level of a $(d-1)$-ary rooted tree and hence contribute $(d-1)^{j-t}$ vertices. Summing gives the tube size.

Every vertex of depth at least $t$ has a unique rooted prefix of length $t$, so it lies in exactly one tube. The first edge of such a prefix has $d$ choices, and every later edge has $d-1$ choices, giving $N_t=d(d-1)^{t-1}$. □
:::

For a fixed rooted tree-ball $(G,v_0,R)$, after the root has been specified, let $C$ be uniform on $B_R(v_0)$. The probability that $C$ lies in a prescribed length-$t$ tube is $$q_{t,R}:=\Pr(C\in T_\sigma(R)\mid G,v_0,R)
=\frac{|T_\sigma(R)|}{|B_R(v_0)|}.$$ The partition gives the exact identity $$
N_tq_{t,R}
=1-\frac{|B_{t-1}(v_0)|}{|B_R(v_0)|}.$$ Put $h=R-t$ and $b=d-1$. Lemmas [6](#lem-shell) and [7](#lem-tube-partition) give $$q_{t,R}=\frac{b^{h+1}-1}{(b+1)b^{t+h}-2}$$ and $$\frac{1}{N_tq_{t,R}}
=\frac{b^{h+1}-2/((b+1)b^{t-1})}{b^{h+1}-1}
=\frac{1}{1-b^{-(h+1)}}+O(b^{-t}),$$ uniformly for $h\geq0$. Thus $q_{t,R}=\Theta(N_t^{-1})$ uniformly over $R\geq t$, but its leading constant depends on $R-t$ when that difference remains bounded.

# Path-Tube Persistence

## The interception schedule

::: {#lem-interception .exhibit .exhibit--lemma data-exhibit-type="lemma" data-exhibit-name="Lemma 8 (Interception schedule along a tube)"}
**Lemma 8** (Interception schedule along a tube). *Let $R\geq t$, suppose $B_R(v_0)$ is a tree-ball, and let $$\sigma=(v_0,v_1,\ldots,v_t)$$ be a length-$t$ nonbacktracking path starting at $v_0$. Let a cop start at $c\in T_\sigma(R)$ at depth $j=\operatorname{dist}(c,v_0)$. Suppose the robber follows $\sigma$ for as long as the path survives. For every $s\in\{1,\ldots,t\}$ such that the path has survived through round $s-1$, after the cop move in round $s$:*

1.  *if $j=2s-1$, the cop reaches $v_{s-1}$ and captures the robber;*

2.  *if $j=2s$, the cop reaches $v_s$ and blocks the intended move;*

3.  *if $j\geq2s+1$, the cop remains a strict descendant of $v_s$.*

*The alternative $j\leq2s-2$ cannot occur: in that case the path was already captured or blocked by the end of round $s-1$.*
:::

::: proof
*Proof.* Set $s_*=\lceil j/2\rceil$. For every reached round $k\leq\min\{s_*,t\}$, an induction shows that before the cop move the cop is a descendant of $v_{k-1}$ and has depth $j-k+1$. This is true at $k=1$. At round $k$, the endpoint-depth sum for the cop and $v_{k-1}$ is $j$, while their rooted-path length is $j-2k+2$. Hence the left side of Lemma [2](#lem-buffer)'s inequality, with $q=R$, is $$j+(j-2k+2)=2(j-k+1)\leq2j\leq2R.$$ The rooted path is therefore the unique ambient geodesic, and the cop moves one step toward $v_0$, to depth $j-k$. If $k<s_*$, then $j-k\geq k+1$, so the cop remains a strict descendant of $v_k$, proving the induction step.

At $k=s_*$, if $j$ is odd then $j=2s_*-1$ and the cop reaches $v_{s_*-1}$; if $j$ is even then $j=2s_*$ and the cop reaches $v_{s_*}$. This proves the three cases. If $j\leq2s-2$, then $s_*\leq s-1$, so the scheduled capture or blockage prevents survival through round $s-1$. □
:::

::: {#rem-odd-even-depths .exhibit .exhibit--remark data-exhibit-type="remark" data-exhibit-name="Remark 9 (Odd and even initial depths as capture and blockage times)"}
**Remark 9**. Odd and even initial depths encode potential capture and blockage times, respectively. If the corresponding time is at most $t$ and the prescribed play reaches it, the event occurs then. If $\lceil j/2\rceil>t$, that time lies beyond the horizon and the cop remains descendant pressure throughout the first $t$ reached rounds.
:::

## Persistence along nonbacktracking paths

::: {#thm-persistence .exhibit .exhibit--theorem data-exhibit-type="theorem" data-exhibit-name="Theorem 10 (Nonbacktracking path-tube persistence)"}
**Theorem 10** (Nonbacktracking path-tube persistence). *Let $d\geq3$ and $1\leq t\leq R$, suppose $B_R(v_0)$ is a tree-ball, and let $X_0$ be any initial cop configuration satisfying $$X_0(T_\sigma(R))\geq1$$ for every length-$t$ tube. Cops outside $B_R(v_0)$ are permitted; the proof ignores them unless they cause capture, blockage, or additional branch support. If $X_0(\{v_0\})>0$, the robber is captured before any move. Otherwise, let $$\tau=(v_0,v_1,\ldots,v_t)$$ be any length-$t$ nonbacktracking path starting at $v_0$. At every round $s\in\{1,\ldots,t\}$ for which the robber has followed $\tau$ through round $s-1$, at least one of the following occurs during round $s$:*

1.  *on the cops' move, a cop captures the robber at $v_{s-1}$;*

2.  *after the cops' move, the robber is not captured, but a cop occupies $v_s$, so the intended move is illegal;*

3.  *the move to $v_s$ is legal, and after that move the branch-load support at $v_s$ has size at least $2$.*
:::

::: proof
*Proof.* Assume there was no initial capture, and fix a round $s$ reached along $\tau$. If a cop reaches $v_{s-1}$, then (a) holds. If no cop captures the robber but a cop occupies $v_s$, then (b) holds. Assume instead that the move to $v_s$ is legal and produce two branch witnesses.

*Descendant witness.* Choose a cop $c^\downarrow$ from $T_\tau(R)$ and let $j_\downarrow$ be its initial depth. Survival through round $s-1$ rules out $j_\downarrow\leq2s-2$, while the failure of alternatives (a) and (b) rules out $j_\downarrow\in\{2s-1,2s\}$. Hence $j_\downarrow\geq2s+1$, and Lemma [8](#lem-interception) implies that after the round-$s$ cop move it is a strict descendant of $v_s$, at depth $j_\downarrow-s$. Its rooted path to $v_s$ has length $j_\downarrow-2s$, so the endpoint-depth sum plus this length is $$(j_\downarrow-s)+s+(j_\downarrow-2s)
=2(j_\downarrow-s)\leq2R.$$ Lemma [2](#lem-buffer), with $q=R$, makes this the unique ambient geodesic. Thus the cop contributes to a child branch of $v_s$.

*Parent witness.* Choose $u_0\in N(v_0)\setminus\{v_1\}$, extend $(v_0,u_0)$ to a length-$t$ nonbacktracking path $\sigma'$, and choose a cop $c^\uparrow\in T_{\sigma'}(R)$ of initial depth $j$. Then $R\geq j\geq t\geq s$. We prove by induction on $k\in\{1,\ldots,s\}$ that before its move in round $k$, the cop has depth $j-k+1$ and lies in the root branch through $u_0$. This is immediate for $k=1$. At round $k$, the rooted path from the cop to $v_{k-1}$ passes through $v_0$; both its length and the sum of the endpoint depths equal $$(j-k+1)+(k-1)=j.$$ Lemma [2](#lem-buffer), with $q=R$, therefore forces one step toward $v_0$. If $k<s$, then $j-k\geq t-s+1\geq1$, so the cop remains in the $u_0$-branch and the induction continues.

After the move in round $s$, the cop has depth $j-s$. It either remains in the $u_0$-branch or, when $j=s$, is at $v_0$. Its rooted path to $v_s$ enters through $v_{s-1}$, and both the path length and endpoint-depth sum equal $(j-s)+s=j$. Lemma [2](#lem-buffer) again makes this the unique ambient geodesic, so the cop contributes to the parent branch of $v_s$. If $j=s=1$, the cop instead captures at $v_0$, a case already excluded.

The two witnesses contribute to distinct branches, proving (c). □
:::

## The one-round case

::: {#cor-one-round .exhibit .exhibit--corollary data-exhibit-type="corollary" data-exhibit-name="Corollary 11 (One-round persistence)"}
**Corollary 11** (One-round persistence). *Let $R\geq1$, suppose $B_R(v_0)$ is a tree-ball, and let $X_0$ be a cop configuration satisfying $$X_0(C_u(v_0,R))\geq1
\qquad\text{for every }u\in N(v_0).$$ For every proposed neighboring first move $v_0\to w$, the robber is captured at $v_0$ (initially or on the first cop move), blocked at $w$, or, after a legal move to $w$, faces branch-load support of size at least two.*
:::

::: proof
*Proof.* Initial capture gives the first alternative. Otherwise apply Theorem [10](#thm-persistence) with $t=1$. □
:::

# The Cost of Exhaustive Tube Coverage

Theorem [10](#thm-persistence) uses a strong static hypothesis: every length-$t$ nonbacktracking path starting at $v_0$ indexes an occupied tube. We now quantify the exact deterministic cost and the conditional random-sampling threshold of this local certificate. These costs are not cop-number bounds and do not establish a robber-independent global placement.

::: {#prop-deterministic-cost .exhibit .exhibit--proposition data-exhibit-type="proposition" data-exhibit-name="Proposition 12 (Deterministic coverage cost)"}
**Proposition 12** (Deterministic coverage cost). *Suppose $B_R(v_0)$ is a tree-ball with $R\geq t$, and let $X$ be any cop configuration. Then $X$ occupies every length-$t$ tube if and only if $$X(T_\sigma(R))\geq1$$ for every member of the family of $N_t=d(d-1)^{t-1}$ pairwise disjoint tubes. Consequently:*

1.  *every such configuration satisfies $|X|\geq N_t$, counting cops with multiplicity;*

2.  *equality suffices for this occupancy property, by choosing one cop position from each tube.*
:::

::: proof
*Proof.* This is immediate from Lemma [7](#lem-tube-partition). □
:::

::: {#thm-sampling-threshold .exhibit .exhibit--theorem data-exhibit-type="theorem" data-exhibit-name="Theorem 13 (Conditional uniform-sampling threshold)"}
**Theorem 13** (Conditional uniform-sampling threshold). *Fix $d\geq3$. For each positive integer $t$, let $G_t$ be a $d$-regular graph with distinguished vertex $v_{0,t}$, and let $R_t\geq t$ be such that $B_{R_t}^{G_t}(v_{0,t})$ is a tree-ball. Let $\mathcal P_t$ be the set of length-$t$ nonbacktracking paths from $v_{0,t}$, and let $T_{\sigma,t}$ be the tube of $\sigma\in\mathcal P_t$ in that ball. Set $$N_t:=|\mathcal P_t|=d(d-1)^{t-1},
\qquad
q_t:=\frac{|T_{\sigma,t}|}{|B_{R_t}^{G_t}(v_{0,t})|}.$$ For each $t$, after the rooted ball has been fixed, sample $m_t$ positions independently and uniformly with replacement from $B_{R_t}^{G_t}(v_{0,t})$. Let $\mathcal C_t$ be the event that every $T_{\sigma,t}$ contains at least one sample. For every fixed $\varepsilon$ with $0<\varepsilon<1$:*

1.  *if $$m_t\geq(1+\varepsilon)\frac{\log N_t}{q_t},$$ then $\Pr(\mathcal C_t)\to1$;*

2.  *if $$m_t\leq(1-\varepsilon)\frac{\log N_t}{q_t},$$ then $\Pr(\mathcal C_t)\to0$.*

*Writing $h_t=R_t-t$, one has, uniformly over $h_t\geq0$, $$\frac{\log N_t}{q_t}
=\left(\frac{1}{1-(d-1)^{-(h_t+1)}}+o(1)\right)N_t\log N_t.$$ If $h_t=k$ eventually, the leading factor relative to $N_t\log N_t$ is $[1-(d-1)^{-(k+1)}]^{-1}$; if $h_t\to\infty$, it tends to $1$. Uniformly over $R_t\geq t$, $$\frac{\log N_t}{q_t}
=\Theta(N_t\log N_t)
=\Theta\bigl((d-1)^{t-1}t\bigr).$$*
:::

::: proof
*Proof.* For a fixed $\sigma\in\mathcal P_t$, the probability that $T_{\sigma,t}$ receives no sample is $(1-q_t)^{m_t}$. Hence $$\Pr(\mathcal C_t^{\mathsf c})
\leq N_t(1-q_t)^{m_t}
\leq N_te^{-m_tq_t}.$$ Under (i), this is at most $N_t^{-\varepsilon}\to0$.

For (ii), let $$Z_t:=\sum_{\sigma\in\mathcal P_t}I_{\sigma,t},
\qquad
I_{\sigma,t}:=\mathbf 1_{\{T_{\sigma,t}\text{ receives no sample}\}}.$$ Then $\mathbb E Z_t=N_t(1-q_t)^{m_t}$. For distinct $\sigma,\tau\in\mathcal P_t$, disjointness gives $$\mathbb E[I_{\sigma,t}I_{\tau,t}]
=(1-2q_t)^{m_t}
\leq(1-q_t)^{2m_t}
=\mathbb E I_{\sigma,t}\,\mathbb E I_{\tau,t}.$$ Thus $$\operatorname{Var}(Z_t)
\leq\sum_{\sigma\in\mathcal P_t}\operatorname{Var}(I_{\sigma,t})
\leq\mathbb E Z_t.$$ Since $q_t=\Theta(N_t^{-1})$, one has $q_t\to0$, and under (ii), $$\mathbb E Z_t
\geq N_t(1-q_t)^{(1-\varepsilon)(\log N_t)/q_t}
=N_t^{\varepsilon+o(1)}\longrightarrow\infty.$$ Chebyshev's inequality therefore yields $$\Pr(\mathcal C_t)
\leq\frac{\operatorname{Var}(Z_t)}{(\mathbb E Z_t)^2}
\leq\frac1{\mathbb E Z_t}
\longrightarrow0.$$ Finally, the exact calculation preceding the theorem, with $R=R_t$, gives $$\frac1{N_tq_t}
=\frac1{1-(d-1)^{-(h_t+1)}}+O((d-1)^{-t})$$ uniformly for $h_t\geq0$, proving the remaining assertions. □
:::

::: {#cor-polylog-horizon .exhibit .exhibit--corollary data-exhibit-type="corollary" data-exhibit-name="Corollary 14 (Finite horizon from polylogarithmic conditional sampling)"}
**Corollary 14** (Finite horizon from polylogarithmic conditional sampling). *Fix $d\geq3$. Let $(G_n)$ be a sequence of $n$-vertex $d$-regular graphs with distinguished vertices $v_{0,n}$ and integers $1\leq t_n\leq R_n$ such that $B_{R_n}^{G_n}(v_{0,n})$ is a tree-ball. After each rooted ball is fixed, sample $m_n$ positions independently and uniformly with replacement from it, and let $\mathcal C_n$ be the event that every length-$t_n$ tube rooted at $v_{0,n}$ is occupied.*

*Call $(m_n)$ *polylogarithmic* if $m_n=O((\log n)^C)$ for some fixed $C>0$. If $(m_n)$ is polylogarithmic and $\Pr(\mathcal C_n)\to1$, then $t_n=O(\log\log n)$. If $t_n=\Theta(\log n)$ and $\Pr(\mathcal C_n)\to1$, then $$m_n=\Omega(N_{t_n}\log N_{t_n}),
\qquad
N_{t_n}=d(d-1)^{t_n-1};$$ in particular, $m_n\geq n^c$ eventually for some $c>0$.*
:::

::: proof
*Proof.* If $t_n\neq O(\log\log n)$, pass to a subsequence on which $t_n/\log\log n\to\infty$, and then to a further subsequence on which $t_n$ is strictly increasing. Apply the proof of Theorem [13](#thm-sampling-threshold) along this subsequence, with $t$ replaced by $t_n$. Now $t_n\to\infty$ and $N_{t_n}=(\log n)^{\omega(1)}$. Because the threshold is $\Theta(N_{t_n}\log N_{t_n})$ uniformly in $R_n\geq t_n$, polylogarithmic $m_n$ satisfies $$m_n\leq\frac12\frac{\log N_{t_n}}{q_n}$$ eventually on this subsequence, where $q_n$ is the common tube mass. Part (ii) of Theorem [13](#thm-sampling-threshold), with $\varepsilon=1/2$, then gives $\Pr(\mathcal C_n)\to0$, a contradiction. Hence $t_n=O(\log\log n)$.

If $t_n=\Theta(\log n)$ and $m_n=o(N_{t_n}\log N_{t_n})$ along a subsequence, pass if necessary to a further subsequence with strictly increasing horizons and apply the same subsequence argument. This contradicts $\Pr(\mathcal C_n)\to1$. Thus $m_n=\Omega(N_{t_n}\log N_{t_n})$. Since $N_{t_n}=n^{\Omega(1)}$, this is at least $n^c$ eventually for some $c>0$. □
:::

::: {#rem-partial-coverage .exhibit .exhibit--remark data-exhibit-type="remark" data-exhibit-name="Remark 15 (Partial coverage is cheaper)"}
**Remark 15** (Partial coverage is cheaper). At one fixed, known root, the expected fraction of length-$t$ tubes occupied by $m$ independent uniform samples is $$1-(1-q_{t,R})^m.$$ Since $q_{t,R}=\Theta(N_t^{-1})$, $m=\Theta(N_t)$ samples occupy a fixed positive fraction of the tubes in expectation, while $m=\omega(N_t)$ occupies a $1-o(1)$ fraction in expectation. Under uniform sampling, reducing the expected number of empty tubes to $O(1)$ requires $\Theta(N_t\log N_t)$ samples; the same order is required to leave at most $O(1)$ tubes empty with probability tending to one. These are occupancy statements only: they give neither an adversarial guarantee over all paths from that root nor a root-independent placement, and they do not show that partial coverage supports an adaptive chase.
:::

# Information Loss in Tube Profiles {#sec-profile-loss}

Fix integers $Q\geq r\geq1$ and $k\geq0$, and suppose $B_Q(v_0)$ is a tree-ball. Let $\mathcal P_r(v_0)$ be the set of length-$r$ nonbacktracking paths starting at $v_0$, and let $$\mathcal C_{Q,k}(v_0)
:=\{X: X\text{ is a $k$-cop multiset with }\mathop{\mathrm{supp}}(X)\subseteq B_Q(v_0)\}.$$ For $X\in\mathcal C_{Q,k}(v_0)$, $\sigma\in\mathcal P_r(v_0)$, and $r\leq j\leq Q$, set $$N_X(\sigma,j)
:=\sum_{\substack{x\in S_j(v_0)\\
\text{the rooted path from $v_0$ to $x$ begins with }\sigma}}X(x).$$ The *augmented order-$r$ tube profile* is $$\Pi_{r;Q,k}(X)
:=\left(
\bigl(X(x)\bigr)_{x\in B_{r-1}(v_0)},
\bigl(N_X(\sigma,j)\bigr)_{\substack{\sigma\in\mathcal P_r(v_0)\\ r\leq j\leq Q}}
\right).$$ It records the complete configuration through depth $r-1$ and the exact depth histogram in every length-$r$ tube; the $j=r$ coordinates also recover the multiplicities at depth $r$. It forgets only how cops at a fixed greater depth split among descendants below the terminal vertex of a length-$r$ prefix. For an admissible profile $P$, define its fixed-universe fiber by $$\mathcal F_{r;Q,k}(P)
:=\{X\in\mathcal C_{Q,k}(v_0):\Pi_{r;Q,k}(X)=P\}.$$

::: {#prop-profile-nondeterminacy .exhibit .exhibit--proposition data-exhibit-type="proposition" data-exhibit-name="Proposition 16 (Augmented tube profiles do not determine later support)"}
**Proposition 16** (Augmented tube profiles do not determine later support). *Fix $d\geq3$ and $r\geq1$, put $Q=2r+3$, and suppose $B_Q(v_0)$ is a tree-ball. There exist $X,Y\in\mathcal C_{Q,2}(v_0)$ and a length-$(r+1)$ nonbacktracking path $\tau=(v_0,\ldots,v_{r+1})$ such that $$\Pi_{r;Q,2}(X)=\Pi_{r;Q,2}(Y).$$ The path survives all $r+1$ rounds from both configurations, with all relevant cop moves unique, but immediately after the robber's legal move to $v_{r+1}$ the branch-load supports in $X$ and $Y$ have sizes $2$ and $1$, respectively. Hence, for this fixed path $\tau$, the predicate that the branch-load support after $r+1$ safe rounds has size at least $2$ does not factor through $\Pi_{r;Q,2}$.*
:::

::: proof
*Proof.* Choose $\tau$ and two distinct children $a,b$ of $v_{r+1}$. Choose descendants $x_a$ of $a$ and $x_b$ of $b$ at total depth $Q=2r+3$ from $v_0$, and choose two distinct descendants $y_a,y_a'$ of $a$ at the same total depth. Such choices exist because the vertices at descendant-distance $r+1$ below $a$ number $(d-1)^{r+1}\geq2$. Define $$X=[x_a,x_b],
\qquad
Y=[y_a,y_a'].$$ Both configurations have zero multiplicity on $B_{r-1}(v_0)$, and their only nonzero tube-depth coordinate is the cell indexed by $((v_0,\ldots,v_r),Q)$, where both have value $2$. Thus their augmented profiles agree.

Every robber position on $\tau$ is an ancestor of every cop in the construction. Immediately before the cop move in round $s$, each cop has total depth $Q-s+1$, while the robber is at $v_{s-1}$. Their rooted path has length $Q-2s+2$, and $$(Q-s+1)+(s-1)+(Q-2s+2)=2Q-2s+2\leq2Q.$$ Lemma [2](#lem-buffer), with $q=Q$, therefore makes this path the unique ambient geodesic and forces one step upward. After that move, the cop's distances to $v_{s-1}$ and $v_s$ are $$2r+4-2s\geq2
\qquad\text{and}\qquad
2r+3-2s\geq1$$ for $1\leq s\leq r+1$. Thus no capture or blockage occurs. After $r+1$ cop moves, the configurations are $[a,b]$ and $[a,a]$, so the branch-load support sizes after the robber moves to $v_{r+1}$ are $2$ and $1$. □
:::

For $r=1$, the profile includes the multiplicity at $v_0$ as well as the depth histogram in every first-level tube, yet it still does not determine the two-round outcome. Proposition [16](#prop-profile-nondeterminacy) identifies one ambiguous fiber, not a barrier to every one-sided certificate: a sound certificate may reject that fiber.

# Limitations and Further Directions {#sec-open}

The present arguments do not address five natural directions; no claim of novelty is made for the questions themselves.

## Arbitrary robber walks

Theorem [10](#thm-persistence) treats only length-$t$ nonbacktracking paths starting at $v_0$. Stationary moves and reversals destroy the monotone depth evolution used by the interception schedule.

::: question
**Question 17**. *Can a static or adaptive local certificate give an analogue of Theorem [10](#thm-persistence) for arbitrary length-$t$ robber walks from $v_0$, including stationary moves and reversals? How do repeated vertices and reversed edges change the required witnesses and coverage cost?*
:::

## Partial and adaptive coverage

Remark [15](#rem-partial-coverage) separates partial from exhaustive conditional coverage at one fixed root. Along a prescribed nonbacktracking path, the persistence proof uses its occupied tube for the descendant witness and a tube with a different first edge for the parent witness; exhaustive coverage supplies both uniformly. A large expected covered fraction alone gives no persistence or adaptive-chase guarantee.

::: question
**Question 18**. *For a fixed horizon $t$, is there a condition strictly weaker than occupancy of every length-$t$ tube that guarantees capture or a quantified decrease in the number of compatible future nonbacktracking continuations? Can it be updated after each move by reusing witnesses among tubes with a common shorter prefix?*
:::

## Uniformly favorable augmented-profile fibers

Fix integers $Q\geq r+1\geq2$ and $k\geq1$, suppose $B_Q(v_0)$ is a tree-ball, and fix a length-$(r+1)$ nonbacktracking path $\tau=(v_0,\ldots,v_{r+1})$. The graph, root, radius, cop number, allowed support region, and allowed distance-minimizing tie-breaks are thereby fixed.

::: question
**Question 19**. *For which admissible profiles $P$ do both of the following hold?*

1.  *Some $X\in\mathcal F_{r;Q,k}(P)$ and some allowed sequence of cop moves let $\tau$ survive through round $r+1$.*

2.  *For every $X\in\mathcal F_{r;Q,k}(P)$ and every allowed sequence of cop moves, the robber is captured or blocked by round $r+1$, or $\tau$ survives and its final branch-load support has size at least $2$.*
:::

## Global overlap of tube systems

Fix a graph $G$, integers $R\geq t\geq1$, a set $A$ of admissible roots whose radius-$R$ balls are tree-balls, and a root-independent set $W$ of allowed cop locations. For $v\in A$ and a length-$t$ nonbacktracking path $\sigma$ from $v$, write $T_\sigma^v(R)$ for its rooted tube. Define the global tube hypergraph $$\mathcal H_{R,t}(G,A;W)
:=\left(W,\{T_\sigma^v(R)\cap W:v\in A,\ \sigma\text{ is a length-$t$ nonbacktracking path from }v\}\right).$$ A root-independent set of cop positions supplies the exhaustive tube certificate simultaneously for every $v\in A$ exactly when it is a transversal of $\mathcal H_{R,t}$. This is the local-to-global gap absent from the conditional sampling theorem; multiplicity at an already selected vertex does not improve coverage.

::: question
**Question 20**. *How do girth, expansion, and nonbacktracking path counts bound the transversal number, fractional transversal number, and codegrees of $\mathcal H_{R,t}$? Can these estimates produce a root-independent placement with controlled cost?*
:::

## Beyond exact tree-balls

The persistence proof uses only the unique geodesics of synchronized witnesses inside $B_R(v_0)$. With cycles, rooted branches would have to give way to a shortest-path directed acyclic graph in which paths may split or merge. No persistence theorem or coverage bound is proved in that setting.

::: question
**Question 21**. *For a radius-$R$ ball obtained from a tree by adding one edge, can geodesic tubes and branch-load support be replaced by notions for which an analogue of Theorem [10](#thm-persistence) holds? More generally, how do the answer and the minimum exhaustive-coverage cost depend on bounded tree excess?*
:::

# Conclusion

We analyzed a local certificate indexed by length-$t$ nonbacktracking robber paths starting at a fixed root $v_0$ in radius-$R$ tree-ball geometry. The larger radius $R+t$ is sharp, among possibly infinite $d$-regular graphs, for uniform control of arbitrary endpoint pairs, but the synchronized chase witnesses require only $B_R(v_0)$. The length-$t$ tubes partition the outer ball into $N_t=d(d-1)^{t-1}$ parts, and occupying every tube gives the stated capture, blockage, or two-branch-support alternative along every prescribed path in this class.

At one fixed root the deterministic occupancy cost is $N_t$. Along fixed-degree rooted sequences with $t\to\infty$, the conditional uniform-sampling threshold is $$\left(\frac{1}{1-(d-1)^{-(h_t+1)}}+o(1)\right)N_t\log N_t,
\qquad h_t=R_t-t.$$ Because the sampling distribution is chosen after the root, it is not a legal standard-game initial placement and gives no cop-number bound. The arbitrary-walk, partial/adaptive, global, augmented-profile, and cyclic directions above are not a
