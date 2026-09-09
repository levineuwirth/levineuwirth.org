---
title: "Timed Guarding in Degree-Reduction Clouds"
subtitle: "A square-root transfer without the cloud-order factor"
date: 2026-09-09
abstract: >
  The actual Hosseini–Mohar–Gonzalez Hermosillo de la Maza stopping tower
  admits a square-root cop bound in the order of its base whenever the base
  satisfies the fixed multistage hypotheses used by the earlier occupation
  transfer. Every ancestry cloud is a retract, so a region that would cost
  many cops to occupy costs one cop to guard. Fixed port anchors pay for
  timed retraction setup within the original five-layer accessibility
  margin. Synchronized setup leaves at most two exceptional clouds, handled
  by a reusable reserve. The resulting bound $c(H)\le C\sqrt N$ has no
  multiplicative dependence on cloud order or tower scale. A 104-vertex
  stopped tower shows that the timing gain is a hypothesis and not a
  consequence of adjacency, and a Hall-capacity inequality shows why full
  remaining-ball demand stays incompatible with slow growth. The theorem
  retains the full remaining-ball Hall demand and does not give an
  all-graphs Meyniel bound.
tags:
  - research
  - research/mathematics
  - research/graph-theory
authors:
  - "Levi Neuwirth | /me.html"
affiliation:
  - "Brown University | https://www.brown.edu"
bibliography: data/timed-guarding-in-degree-reduction-clouds.bib
preprint: /papers/timed-guarding-in-degree-reduction-clouds.pdf
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
  - LuPeng
  - ScottSudakov
  - BollobasKunLeader
  - BradshawHosseiniMoharStacho
  - BoseEsperetHodorJoretMicekRambaud
history:
  - date: "2026-09-09"
    note: "First version."
---

# Main result

A region may require many cops to occupy and only one cop to guard. For a graph retract, a pursuit team can catch the retracted image of the robber and then leave a single cop tracking that image. Turning this structural fact into a timed strategy needs two further ingredients: a legal route to the guard's starting position, and a setup schedule that survives while the robber keeps moving. This article supplies both for the ancestry clouds of the degree-reduction construction of Hosseini, Mohar, and Gonzalez Hermosillo de la Maza (HMGHM) [@HMG].

The [companion occupation paper](/essays/ball-occupation-under-coarse-projections.html) transfers the multistage strategy of Prałat and Wormald [@PralatWormald] through abstract coarse projections. With base order $N$ and cloud order at most $P$, it fills whole fibers with squads and obtains $CP\sqrt N$. Its deployment bound at base radius $t$ is $\lambda(t+2)-2$. Here a cop initially placed at a *designated port* reaches a target port in at most $\lambda t+(\lambda-1)$ moves, and the remaining $\lambda-1$ moves suffice to establish a guard while the robber stays outside the target cloud:

$$
\underbrace{\lambda t+(\lambda-1)}_{\text{port travel}}
+\underbrace{(\lambda-1)}_{\text{exterior setup}}
=\lambda(t+2)-2.
$$

This identity consumes exactly the old deployment allowance. It does not exhaust the entry deadline: the proof retains four moves before the earliest possible entry, and at least two once root-dependent activation is included.

The exterior condition during setup needs a separate argument for the finishing balls. In a $k$-round tower, write $\lambda=3^k$ and $L=\lambda-1$. A walk of at most $L$ edges visits at most two original ancestry clouds, so simultaneous setup guards every unvisited cloud. At the finishing deadline the boundary is still unvisited, so the at most two exceptions are interior. Simplicity of the base leaves one joining edge between two adjacent exceptions; one reserve cop blocks it while an internal-pursuit team captures on the observed side.

The quantitative conclusion before absorbing the reserve is

$$
c(H)\le C_0\sqrt N+K+1,
\qquad
K=\max_{v\in V(G)}c(H[F_v])\le2\Delta(G),
$$

and the same fixed-parameter growth hypotheses force $\Delta(G)=O(\sqrt N)$, including the degrees inside the exceptional set. The formal statement is [Theorem 19](#thm-cloud-transfer); it concerns $N=|V(G)|$, the order of the base, and its constant depends on none of $P$, $\lambda$, or $\Delta(G)$.

## Attribution and scope

The degree-reduction gadget and its lower cop-number transfer are due to Hosseini–Mohar–Gonzalez Hermosillo de la Maza [@HMG]. [Theorem 7](#thm-lower-transfer) gives a self-contained proof of that comparison for the entire tower, with the cop and robber turns explicit. The multistage radius schedule, fresh random teams, contracting uncovered frontiers, and finishing Hall estimate are inherited from Prałat–Wormald [@PralatWormald]. The five-layer accessibility hypothesis and its fixed-degree random-regular application are developed in the companion paper, using intermediate levels in [@PralatWormaldRegular]; that hypothesis is kept unchanged. The retract setup principle is standard, and the proof is included only to make its resource account explicit [@RetractCover2013]. The two-cop bound inside one gadget is proved directly.

The cloud retractions, port travel, synchronized exterior setup, and their use in this timed transfer are the derivations studied here. The theorem supplies neither a simulation of every base pursuit strategy nor a stronger bound for arbitrary coarse projections. The branching parameter remains fixed. No uniformity for a growing branching parameter or shrinking expansion is asserted. The full remaining-ball Hall condition is retained, and the [Hall-capacity section](#hall-boundary) proves a concrete obstruction to one proposed weakening. No novelty claim follows merely from the bounded source audit.

## Game convention and notation

All graphs are finite, undirected, and simple. The cops choose their vertices before the robber chooses hers; multiple cops may share a vertex. Each cop may move along one edge or stay, followed by one robber move of the same kind. Capture occurs when a cop and the robber occupy the same vertex, and the least winning cop count is $c(G)$. For $U\subseteq V(G)$, $B_G(U,r)$ and $S_G(U,r)$ are the closed radius-$r$ neighborhood and the set at distance exactly $r$ from $U$; a singleton argument is written $B_G(v,r)$ or $S_G(v,r)$. A *lazy graph homomorphism* maps every edge to an edge or to one vertex. A *retraction* onto an induced subgraph fixes that subgraph pointwise.

A retained guard need not occupy every vertex of its cloud. It remains inside the cloud and tracks a retracted robber image, so entry by the robber is captured no later than the next cop move. Phase roots and surviving exits are considered after this compulsory capture check.

# The replacement geometry

We use the HMGHM construction with the all-vertex convention made explicit [@HMG, Section 2]. Distances in an induced subgraph are intrinsic unless an ambient graph is specified.

::: {#def-hmghm-tower .exhibit .exhibit--definition data-exhibit-type="definition" data-exhibit-name="Definition 1 (All-vertex HMGHM tower)"}
**Definition 1** (All-vertex HMGHM tower).
For $r\ge2$, form a graph $A_r(m)$ from $r$ independent vertices, called *ports*, partitioned into $m$ nonempty classes $X_1,\ldots,X_m$ whose sizes differ by at most one. For each $1\le i<j\le m$, add a vertex $y_{ij}$ adjacent to every port in $X_i\cup X_j$, and add no other internal edges. Use

$$
m(2)=2,\qquad m(3)=3,\qquad m(4)=3,\qquad
m(r)=\lceil\sqrt{2r}\rceil\quad(r\ge5).
$$

Thus the degree-two gadget is a three-vertex path, the degree-three gadget is a six-cycle, and the degree-four gadget has class sizes $2,1,1$ and seven vertices. A vertex of degree zero or one is replaced by a singleton; in the degree-one case that singleton is its port.

Starting from a connected base graph, in one round replace every vertex $v$ by its gadget, associate its ports bijectively with its incident edges, and retain each old edge as one edge between the corresponding ports. This includes vertices of degree two or three whenever a round is performed. Let

$$
G=G_0,G_1,\ldots,G_k=H
$$

be $k$ such rounds. The *ancestry cloud* $F_v$ consists of all final vertices descended from $v\in V(G)$. Each edge incident with $v$ determines one edge from $F_v$ to another ancestry cloud, and hence one *designated port* of $F_v$. Put

$$
\lambda=3^k,\qquad L=\lambda-1,\qquad D_j=\Delta(G_j),\qquad D=D_0.
$$

The *stopping tower* stops at the first $k$ with $D_k\le3$; in particular $k=0$ if the base is already subcubic. Statements about a specified number of rounds do not require this stopping rule.
:::

Every cloud is connected, and exactly one edge remains between the ancestry clouds of each adjacent pair of base vertices. Both assertions follow inductively from the connectedness of the gadgets and the retention of every old edge. For $k=0$, all ports associated with one base vertex coincide at that vertex.

::: {#lem-equilateral-ports .exhibit .exhibit--lemma data-exhibit-type="lemma" data-exhibit-name="Lemma 2 (Equilateral designated ports)"}
**Lemma 2** (Equilateral designated ports). *Suppose $k\ge1$. In a cloud $F_v$, ports associated with two distinct base edges have intrinsic distance exactly $L=3^k-1$.*
:::

::: proof
*Proof.* In one gadget, ports in different classes share $y_{ij}$, and two ports in the same class share a pair vertex involving that class and another nonempty class. Ports are independent, so their distance is exactly two. This proves the assertion for one round.

Suppose it holds after $j$ rounds, with distance $L_j=3^j-1$. Consider two designated final ports after one further round and a shortest path between them within their enlarged ancestry cloud. Its sequence of edges between the new gadgets projects to a walk between the old designated ports. If that sequence uses $q$ edges, then $q\ge L_j$. The first new designated port differs from the port used by the first internal old edge: the former represents an edge leaving the old ancestry cloud, whereas the latter represents an edge within it. The analogous statement holds at the other endpoint, so each endpoint traversal costs at least two. Each intermediate traversal also joins distinct ports; otherwise the path immediately reverses an external edge and is not shortest. The new path therefore has length at least

$$
q+2(q-1)+4=3q+2\ge3L_j+2.
$$

Conversely, lift an old intrinsic geodesic and use length-two port paths at both endpoints and every intermediate gadget. This realizes $3L_j+2=3^{j+1}-1$, completing the induction.

◻
:::

The usual normalized metric bounds also hold without any stopping assumption. We record them in the detail needed to distinguish them from the stronger endpoint statement used below.

::: {#lem-cloud-metric .exhibit .exhibit--lemma data-exhibit-type="lemma" data-exhibit-name="Lemma 3 (Cloud metric bounds)"}
**Lemma 3** (Cloud metric bounds). *For every $v\in V(G)$,*

$$
\operatorname{diam}_{H[F_v]}(F_v)\le2L,
\qquad
\operatorname{dist}_{H[F_v]}(x,p)\le\tfrac32L
\quad(x\in F_v,\ p\text{ a designated port}).
$$

*For distinct $u,v\in V(G)$, $x\in F_u$, and $y\in F_v$,*

$$
\lambda\bigl(\operatorname{dist}_G(u,v)-1\bigr)+1
\le\operatorname{dist}_H(x,y)
\le\lambda\bigl(\operatorname{dist}_G(u,v)+2\bigr)-2.
$$
:::

::: proof
*Proof.* In a one-round gadget every vertex is within three of each specified port, and the diameter is at most four. For a pair vertex and a port outside its two classes, a three-edge route uses one intermediate port and a second pair vertex. Two pair vertices with intersecting class pairs have a common port; disjoint class pairs can be joined in four edges. Singleton gadgets satisfy the same upper bounds.

Lifting an old path of length $q$ between arbitrary vertices costs at most $3q+4$, including both endpoint costs; when both old endpoints coincide, the one-round diameter bound applies. If one new endpoint is a designated port for an edge leaving the ancestry cloud, its endpoint cost is at most two instead of three, so lifting costs at most $3q+3$. Consequently the intrinsic diameter and designated-port eccentricity satisfy the recurrences

$$
d_{j+1}\le3d_j+4,\qquad e_{j+1}\le3e_j+3,\qquad d_0=e_0=0,
$$

whose solutions are $d_j\le2(3^j-1)$ and $e_j\le\tfrac32(3^j-1)$.

Let $r=\operatorname{dist}_G(u,v)$. A shortest ambient path between $F_u$ and $F_v$ uses $q\ge r$ external edges. Every intermediate segment joins distinct designated ports, so [Lemma 2](#lem-equilateral-ports) gives length at least $q+(q-1)L\ge\lambda(r-1)+1$. For the upper bound follow a base geodesic: its endpoint costs sum to at most $3L$, its intermediate costs sum to $(r-1)L$, and it uses $r$ external edges, for a total of at most $r+(r+2)L=\lambda(r+2)-2$. When $k=0$ the assertions reduce directly to ordinary base distances.

◻
:::

::: {#lem-port-travel .exhibit .exhibit--lemma data-exhibit-type="lemma" data-exhibit-name="Lemma 4 (Designated-port travel)"}
**Lemma 4** (Designated-port travel). *Let $p\in F_z$ and $a\in F_w$ be designated ports, and suppose $\operatorname{dist}_G(z,w)\le t$. Then*

$$
\operatorname{dist}_H(p,a)\le\lambda t+L=\lambda(t+1)-1.
$$

*This includes $z=w$ and $t=0$. Choosing one common anchor per cloud makes the same-cloud travel cost zero.*
:::

::: proof
*Proof.* If $z\ne w$, follow a base geodesic of length $q\le t$. Each endpoint port traversal costs either zero or $L$, and each of the $q-1$ intermediate traversals costs $L$. Including the $q$ external edges gives

$$
q+(q+1)L=\lambda q+L\le\lambda t+L.
$$

When $z=w$, two designated ports coincide or have intrinsic distance $L$. A degree-one cloud is a singleton and has zero endpoint cost. When $k=0$, all clouds are singletons and the assertion is the ordinary distance bound. If the connected base consists of one isolated vertex, designate that vertex as its anchor and handle its capture directly.

◻
:::

The hypothesis in [Lemma 4](#lem-port-travel) concerns the cops' actual positions when they are dispatched. Unused sampled teams may wait at their initially chosen ports through earlier rounds. Cops moved for a previous guard or pursuit cannot be reused under this bound without paying for their redeployment.

::: {#lem-short-walk-clouds .exhibit .exhibit--lemma data-exhibit-type="lemma" data-exhibit-name="Lemma 5 (Clouds visited by a walk)"}
**Lemma 5** (Clouds visited by a walk). *A walk in $H$ of $T\ge1$ edges visits at most*

$$
2+\left\lfloor\frac{T-1}{\lambda}\right\rfloor
$$

*distinct ancestry clouds. In particular, at most $j\lambda$ edges visit at most $j+1$ clouds for every integer $j\ge0$, and at most $L+1$ edges visit at most two clouds.*
:::

::: proof
*Proof.* Record the successive directed external crossings. If there are $a$ external crossings and $b$ consecutive pairs that are not opposite, the walk visits at most $b+2$ clouds: the first crossing visits at most one new cloud, a crossing immediately reversing its predecessor visits none, and every other crossing visits at most one. Each of the $b$ intervals joins distinct ports within a single cloud and costs at least $L$, so

$$
T\ge a+bL\ge(b+1)+bL=b\lambda+1.
$$

Thus the number of visited clouds is at most $2+\lfloor(T-1)/\lambda\rfloor$. With no external crossing it is one. For $T\le j\lambda$ this gives $j+1$; the zero-length case is immediate.

◻
:::

::: {#lem-geodesic-lift .exhibit .exhibit--lemma data-exhibit-type="lemma" data-exhibit-name="Lemma 6 (Isometric lifts of base geodesics)"}
**Lemma 6** (Isometric lifts of base geodesics). *Let $v_0,\ldots,v_q$ be a base geodesic with $q\ge1$. Start at the designated port of $F_{v_0}$ toward $v_1$, end at the designated port of $F_{v_q}$ toward $v_{q-1}$, and join the appropriate ports in each intermediate cloud by an intrinsic geodesic. The resulting path is ambient-isometric and has length $\lambda(q-1)+1$.*
:::

::: proof
*Proof.* Its length is $q+(q-1)L=\lambda(q-1)+1$, which equals the lower bound of [Lemma 3](#lem-cloud-metric) for its endpoints. Every subpath of a shortest path is shortest. The endpoint ports are prescribed by the first and last edges; arbitrary designated endpoints can cost more.

◻
:::

# Why the tower retains the base cop number {#lower-transfer-clock}

The lower comparison holds for every actual HMGHM tower, with no growth or accessibility assumptions [@HMG, Theorem 3(a)]. The proof below is self-contained for the entire tower, and its timing matters: after the first actual cop move, the checkpoints occur immediately after cop moves, when it is the robber's turn.

::: {#thm-lower-transfer .exhibit .exhibit--theorem data-exhibit-type="theorem" data-exhibit-name="Theorem 7 (HMGHM lower transfer, with explicit turns)"}
**Theorem 7** (HMGHM lower transfer, with explicit turns). *For every tower in [Definition 1](#def-hmghm-tower), including an arbitrary fixed number of rounds,*

$$
c(G)\le c(H).
$$

*No growth, stopping, or accessibility assumption is needed.*
:::

::: proof
*Proof.* The case $k=0$ is immediate. Fix $h<c(G)$ and a winning robber strategy against $h$ cops on $G$. For any initial placement of $h$ cops on $H$, use their ancestry vertices as the initial base cop positions. The base strategy chooses a vertex $v$ at distance at least two from each of them; otherwise the first base cop move could capture it. Place the actual robber at any designated port of $F_v$. The metric lower bound of [Lemma 3](#lem-cloud-metric) puts every actual cop at distance at least $\lambda+1$ from $F_v$, so the first actual cop move is safe and projects to a legal first base cop move. The singleton base, for which the conclusion is trivial, may be excluded when choosing ports.

Take checkpoints immediately after cop moves. At a checkpoint the actual robber is at a designated port $p\in F_v$, and the cop shadows and $v$ form the corresponding uncaptured base position on the robber's turn. Let $w\in N_G[v]$ be the base strategy's response. Its distance from every current cop shadow is at least two, since the base strategy must survive the next base cop move. Write $z$ for any actual cop's current position. Then

$$
\operatorname{dist}_H(z,F_w)\ge\lambda+1.
$$

If $w=v$, let the actual robber wait for $\lambda$ moves; the displayed bound makes all those waits safe. Otherwise let $a\in F_v$ be the designated port toward $w$ and let $b\in F_w$ be its external neighbor. If $p\ne a$, follow a port path of length $L$ from $p$ to $a$; if $p=a$, wait $L$ times. Then cross $ab$. Denote the resulting positions by $r_1,\ldots,r_\lambda$, with $r_\lambda=b$. The move order in this block is

$$
R_1,C_1,R_2,C_2,\ldots,R_\lambda,C_\lambda,
$$

so the robber's $j$th move precedes the $j$th cop reply. Since $a$ has a neighbor in $F_w$, the displayed safety bound implies $\operatorname{dist}_H(z,a)\ge\lambda$. For $1\le j\le L$, the remaining path from $r_j$ to $a$ has length at most $L-j$, and hence

$$
\operatorname{dist}_H(z,r_j)\ge\lambda-(L-j)=j+1.
$$

Thus neither the $j-1$ preceding cop moves nor the $j$th reply can capture $r_j$. The last position $b$ is safe through the $\lambda$th reply by the same bound. This checks every intermediate position against arbitrary cop walks, including those through shared hubs.

During the block each cop takes $\lambda$ moves. By [Lemma 5](#lem-short-walk-clouds), its endpoint shadows are equal or adjacent, so these endpoints give a legal next base cop move. The actual robber is now at a designated port over $w$, safely after that move. This restores the checkpoint invariant and permits indefinite iteration. Therefore $h$ cops cannot win on $H$.

◻
:::

The three-move argument in [@HMG, Theorem 3(a)] is read with these robber-turn checkpoints. An interception starting with a cop outside the departure cloud, and giving it an additional move before $R_1$, changes the phase. If that extra move enters the departure cloud, its current shadow already coincides with the base robber, contradicting the checkpoint invariant. Shared transit hubs do not invalidate the comparison; the safety estimate above does not require private tunnels.

# Retractions and exterior tree shadows

A *lazy graph retraction* from a graph $J$ onto an induced subgraph $R$ is a map $\rho:V(J)\to V(R)$ fixing $R$ such that the images of the endpoints of each edge are equal or adjacent. Thus every robber walk, including waiting and reversal, has a legal projected walk in $R$.

::: {#lem-cloud-exterior-distance .exhibit .exhibit--lemma data-exhibit-type="lemma" data-exhibit-name="Lemma 8 (Exterior port separation)"}
**Lemma 8** (Exterior port separation). *Let $x_i,x_j$ be distinct designated ports of $F_v$, and let $a_i,a_j$ be their respective neighbors outside $F_v$. Then*

$$
\operatorname{dist}_{H-F_v}(a_i,a_j)\ge2L+1,
$$

*where the distance is infinite when the two vertices lie in different components.*
:::

::: proof
*Proof.* The exterior neighbors lie in different ancestry clouds because the base is simple. Any path between them avoiding $F_v$ uses at least one external edge. In its first ancestry cloud it starts at the designated port toward $v$ and exits through a different port, at intrinsic cost at least $L$; the same holds in the last cloud. The external edge or edges contribute at least one more, and additional intermediate segments only increase the length. For $k=0$ the asserted lower bound is one.

◻
:::

::: {#thm-cloud-retraction .exhibit .exhibit--theorem data-exhibit-type="theorem" data-exhibit-name="Theorem 9 (Retractions onto ancestry clouds)"}
**Theorem 9** (Retractions onto ancestry clouds). *Every ancestry cloud $F_v$ is an induced retract of $H$. The same holds for descendant clouds at intermediate tower levels. Restricting such a retraction to an enclosing ancestry cloud is again a retraction.*
:::

::: proof
*Proof.* Assume first that $k\ge1$ and that $v$ has at least two incident base edges. Fix a designated anchor port $x_0$. For each other port $x_i$ choose an intrinsic geodesic

$$
p_i(0),p_i(1),\ldots,p_i(L),
\qquad p_i(0)=x_i,\quad p_i(L)=x_0,
$$

and let $p_0$ be the constant path at $x_0$. Write $a_i$ for the exterior neighbor of $x_i$. Fix $F_v$ pointwise, and for $z\notin F_v$ set

$$
\rho_v(z)=
\begin{cases}
p_i(j),&j=\operatorname{dist}_{H-F_v}(z,a_i)<L\text{ for some }i,\\
x_0,&\text{otherwise}.
\end{cases}
$$

The index in the first case is unique by [Lemma 8](#lem-cloud-exterior-distance): two such sources would have distance at most $2L-2$.

No edge joins two different regions on which the first case applies, since it would give source distance at most $2L-1$. Within one region, distance from its source changes by at most one along an edge, so its images are equal or consecutive along $p_i$. An edge leaving such a region has its inner endpoint at distance $L-1$ from the source, and the other endpoint maps to $x_0=p_i(L)$. Finally an edge $x_ia_i$ crossing the boundary of $F_v$ has both endpoints mapped to $x_i$. Therefore $\rho_v$ is a lazy graph homomorphism fixing $F_v$.

For a degree-one base vertex, map the exterior constantly to its unique port. If $k=0$, each cloud is a singleton and its constant map is a retraction; a connected singleton base is immediate. The construction applies with any intermediate graph as the base of its remaining tower. If $F'$ is a descendant cloud contained in $F_v$, the restriction to $H[F_v]$ of a retraction $H\to H[F']$ still fixes $F'$ and preserves edges, proving the final assertion.

◻
:::

::: {#lem-exterior-tree .exhibit .exhibit--lemma data-exhibit-type="lemma" data-exhibit-name="Lemma 10 (Exterior tree shadows)"}
**Lemma 10** (Exterior tree shadows). *For any designated anchor $x_0\in F_v$, the retraction in [Theorem 9](#thm-cloud-retraction) can be chosen with a tree $T_v\subseteq H[F_v]$, rooted at $x_0$ and of height at most $L$, such that its restriction to $H-F_v$ is a lazy graph homomorphism into $T_v$. A cop initially at $x_0$ aligns with this retracted robber within $L$ cop moves whenever the actual robber stays outside $F_v$ throughout that setup interval. Once aligned, the cop can maintain a guard of $F_v$ against all subsequent robber walks.*
:::

::: proof
*Proof.* Choose a breadth-first spanning tree of $H[F_v]$ rooted at $x_0$ and let $T_v$ be the union of its root paths to the designated ports. By [Lemma 2](#lem-equilateral-ports), those paths have length $L$, except for the constant path to $x_0$. Use their reversals as the paths $p_i$ in the retraction formula. The proof of that formula shows more than containment of the exterior image in $T_v$: the images of every exterior edge are equal or consecutive along a tree path. Thus an exterior robber has a legal lazy shadow in this tree.

Starting at its root, a cop follows the unique tree path toward the current shadow. Until alignment occurs, each cop move goes one level deeper, and the shadow cannot leave the rooted subtree below the cop without first coinciding with it. Since the height is at most $L$, alignment occurs within $L$ cop moves. If it occurs immediately after a robber move, the next cop move can wait to establish the same alignment after a cop move; this does not exceed the bound, since a nonaligned move to depth $L$ is impossible.

After alignment, on every subsequent cop move follow the robber's current image under the full retraction $\rho_v$. This move is legal even when the robber has entered $F_v$; in that case its image is its actual position, so the cop captures it on the next cop move. The setup hypothesis that the robber remains outside is needed only for the bounded-time tree chase, not for maintaining an established guard. Singleton clouds have a height-zero tree and require no setup.

◻
:::

## When one guard can cover two clouds {#adjacent-cloud-criterion}

::: {#thm-adjacent-clouds .exhibit .exhibit--theorem data-exhibit-type="theorem" data-exhibit-name="Theorem 11 (Exact adjacent-cloud criterion)"}
**Theorem 11** (Exact adjacent-cloud criterion). *Suppose $k\ge1$ and $uv\in E(G)$. The induced union $R=H[F_u\cup F_v]$ is a lazy retract of $H$ if and only if $uv$ lies in no triangle of $G$. In that case its exterior shadow can be chosen in a tree of height at most $L+1$, rooted at either endpoint of the unique edge joining the clouds. One cop at that root establishes a guard within $L+1$ cop moves if the robber stays outside $R$ throughout setup.*
:::

::: proof
*Proof.* Write $ab$ for the joining edge, with $a\in F_u$ and $b\in F_v$. First assume that $uv$ lies in no triangle. Root breadth-first trees of the two clouds at $a,b$. For each boundary edge $p_iz_i$ of $R$, let $P_i$ be the tree path from $p_i$ to $a$ if $p_i\in F_u$, or the tree path from $p_i$ to $b$ followed by $ba$ otherwise; its length $h_i$ is $L$ or $L+1$, respectively. These paths lie in one actual tree $T$ rooted at $a$, of height at most $L+1$.

The exterior sources $z_i$ lie in distinct ancestry clouds: a shared neighbor of $u$ and $v$ would complete a triangle. As in [Lemma 8](#lem-cloud-exterior-distance), any path outside $R$ between distinct sources pays two endpoint traversals of length $L$ and an external edge, so their exterior distance is at least $2L+1$. Fix $R$ pointwise and define outside it

$$
\rho(z)=
\begin{cases}
P_i(j),&j=\operatorname{dist}_{H-R}(z,z_i)<h_i\text{ for some }i,\\
a,&\text{otherwise}.
\end{cases}
$$

The index is unique since two candidate distances would sum to at most $2L$. If an exterior edge joins different source regions, its endpoint distances $j,j'$ satisfy $2L+1\le j+1+j'\le2L+1$; thus $j=j'=L$, both sources attach to $F_v$, and both images are $b$. Within a source region images follow its tree path, and an edge to the default region maps to the last tree edge toward $a$. Every boundary edge $p_iz_i$ maps to the single vertex $p_i$. This proves the retraction property and the exterior homomorphism into $T$, and the root chase of [Lemma 10](#lem-exterior-tree) gives the setup bound.

Conversely, suppose $uvw$ is a triangle, and choose the ports $p\in F_u$, $q\in F_v$ toward $w$. Their intrinsic distance in $R$ is $2L+1$, since every such path uses $ab$, whereas the route through $F_w$ has length $L+2$. For $k\ge1$, $L\ge2$ makes this a strict shortcut. A retract is ambient-isometric, so no retraction onto $R$ exists.

◻
:::

For $k=0$ any two-cloud union is an edge and is a lazy retract, regardless of triangles. The exterior condition in the setup bound is essential: a retract need not be cop-win internally. Nor does girth five suffice for a union over a closed base neighborhood. In $C_5$, that neighborhood is a three-vertex path; between its two ports toward the complement, the three-cloud union has intrinsic distance $3L+2$, whereas the exterior route has length $2L+3$. For $k\ge1$ this excludes a retraction. Attaching a degree-four tree at a base vertex outside the chosen neighborhood preserves the obstruction and forces a nontrivial stopped tower. None of this changes the two-exception cleanup used below.

# Internal pursuit and reusable setup

We distinguish the cops needed to establish a guard from those retained after establishment. Retraction bounds for cop number are standard; the retract-cover bound is recalled, with attribution to earlier work, in [@RetractCover2013]. The following elementary game argument gives the specific accounting used here.

::: {#lem-retract-setup .exhibit .exhibit--lemma data-exhibit-type="lemma" data-exhibit-name="Lemma 12 (Reusable retract setup)"}
**Lemma 12** (Reusable retract setup). *Let $R$ be a nonempty connected induced retract of a finite connected graph $J$. A team of $c(R)$ cops initially anywhere in $J$ can, after finite setup, capture the robber or leave one cop maintaining a guard of $R$; the other setup cops may then be reused. In particular, for nonempty connected induced retracts $R_1,\ldots,R_s$, put $K=\max_ic(R_i)$ and let $C$ range over the components of $J-\bigcup_iV(R_i)$. Then*

$$
c(J)\le s+\max\left\{K-1,\ \max_Cc(C)\right\},
$$

*with $\max_Cc(C)=0$ when the complement is empty.*
:::

::: proof
*Proof.* Deploy the setup team to a winning initial placement in $R$. This takes finite time because $J$ is connected, and the robber may move arbitrarily during deployment. Thereafter pursue its image under a retraction $\rho:J\to R$ using a winning strategy in $R$; that image is a legal robber walk. After finite time some cop reaches $\rho(r)$ immediately after a cop move, where $r$ is the actual robber position. If $r\in R$ this is capture. Otherwise retain that cop and let it follow $\rho(r)$ on each later cop move: the retraction property makes every such move legal, and any actual entry into $R$ is captured on the next cop move.

For the displayed budget, establish the retracts one at a time and retain one guard after each successful setup. Before the final setup there are at least $K$ uncommitted cops. After all $s$ guards are established, at least $\max_Cc(C)$ cops remain for the component containing the robber; they may deploy there from arbitrary positions while all guards remain active, and a surviving robber cannot change components. If the complement is empty, the final setup or the next cop move captures it. No uniform bound on the setup or cleanup time is asserted.

◻
:::

::: {#lem-twin-blowup .exhibit .exhibit--lemma data-exhibit-type="lemma" data-exhibit-name="Lemma 13 (Independent twin blowups)"}
**Lemma 13** (Independent twin blowups). *Let $Q$ be connected with at least two vertices. Replace each vertex by a nonempty independent set, joining two such sets completely exactly when the corresponding vertices of $Q$ are adjacent. The resulting graph $B(Q)$ satisfies*

$$
c(B(Q))\le\max\{c(Q),2\}.
$$
:::

::: proof
*Proof.* Use a winning strategy on $Q$, representing cop positions by vertices in the corresponding twin classes. Every simulated move is legal because adjacent classes are joined completely. If virtual capture occurs without actual capture, the robber and the capturing cop occupy different vertices of the same independent twin class. Keep that cop fixed: any move of the robber out of the class can be captured by it on the next cop move. A second cop travels to a neighbor of the robber and captures if the robber keeps waiting; such a neighbor exists since $Q$ is connected and nontrivial. Thus a virtual capture can be completed using an existing second cop when $c(Q)\ge2$, and one extra cop otherwise.

◻
:::

::: {#lem-one-round-cop .exhibit .exhibit--lemma data-exhibit-type="lemma" data-exhibit-name="Lemma 14 (One-round internal pursuit)"}
**Lemma 14** (One-round internal pursuit). *Every one-round HMGHM cloud has cop number at most two. Singleton and star clouds have cop number one.*
:::

::: proof
*Proof.* The graph $A_r(m)$ is the independent twin blowup of the graph obtained by subdividing every edge of $K_m$ once: the original vertex $i$ becomes $X_i$, and each subdivision vertex remains the singleton $y_{ij}$. Here is a direct two-cop strategy on that subdivided clique for $m\ge2$. Start at distinct original vertices $a,b$. A robber on a subdivision vertex incident with either is captured immediately. For a robber on the subdivision of $rs$ with $r,s\notin\{a,b\}$, move the cops to the subdivisions of $ar,bs$; moving to $r$ or $s$ then loses on the next cop move, and if the robber waits, advance to $r,s$ and capture next. For a robber starting at an original vertex $r\notin\{a,b\}$, move the first cop to the subdivision of $ar$ and keep the second at $b$. Waiting or entering the subdivision of $ar$ or $br$ loses immediately or on the next cop move. If the robber moves to the subdivision of $rs$ for another $s$, move the cops to $r$ and the subdivision of $bs$; waiting, moving to $r$, and moving to $s$ all lose by the following cop move. [Lemma 13](#lem-twin-blowup) preserves this two-cop upper bound. The singleton and $m=2$ HMGHM cases are trees.

◻
:::

::: {#prop-cloud-cop-bound .exhibit .exhibit--proposition data-exhibit-type="proposition" data-exhibit-name="Proposition 15 (Internal cloud budget)"}
**Proposition 15** (Internal cloud budget). *For a tower of $k\ge1$ rounds,*

$$
\max_{v\in V(G)}c(H[F_v])\le2+\sum_{j=0}^{k-2}D_j.
$$

*If the stopping rule is used and $D\ge4$, then*

$$
K:=\max_{v\in V(G)}c(H[F_v])\le2D.
$$

*If the base is already subcubic, $k=0$ and $K=1$.*
:::

::: proof
*Proof.* The case $k=1$ is [Lemma 14](#lem-one-round-cop). For more rounds, consider the first gadget of an ancestor $v$ of degree $r\ge2$. Its $r$ port vertices and its pair vertices each have a descendant cloud in the final graph. By [Theorem 9](#thm-cloud-retraction), every child cloud is a retract of the parent cloud. Suppose their internal cop numbers are at most $K'$. Guard the $r$ port-descendant clouds using [Lemma 12](#lem-retract-setup). Removing them leaves each pair-descendant cloud as a separate component, since pair vertices are independent in $A_r(m)$. Therefore the parent cloud needs at most $r+K'$ cops. An ancestor of degree zero or one has just one child and needs no separator charge. Induction on the remaining number of rounds gives the degree-sum bound.

For the stopping bound, the gadget degrees give

$$
D_{j+1}\le f(D_j),\qquad f(4)=3,\qquad
f(x)=2\left\lceil\sqrt{x/2}\right\rceil\quad(x\ge5).
$$

Indeed a port has total degree $m(r)$ after its external edge is attached, and a pair vertex has degree at most $2\lceil r/m(r)\rceil$; these are bounded by the displayed expression when the current maximum degree is $x\ge5$. The special degree-four gadget has maximum degree three. This is the one-round bound of [@HMG, Theorem 3].

Define $T(x)=2$ for integers $x\le4$ and $T(x)=x+T(f(x))$ for $x\ge5$. The sequence is well defined because $f(x)<x$ for $x\ge5$, and $T$ is nondecreasing by induction. The actual degree sequence in the degree-sum bound is bounded by this envelope. For $5\le x\le8$ one has $T(x)=x+2$, and for $9\le x\le15$ one has $T(x)=x+8$, so $T(x)\le2x$ in these cases. For $x\ge16$,

$$
f(x)\le\sqrt{2x}+2\le x/2,
$$

so strong induction gives $T(x)=x+T(f(x))\le x+2f(x)\le2x$. This proves the stopping bound. The $k=0$ statement follows from the singleton fibers.

◻
:::

The geometry and retractions above hold for any specified number of rounds. The simplification to $2D$ uses the stopping rule: gratuitous rounds on an already subcubic graph are not covered by that degree-sum estimate.

# A late handoff cannot be repaired by five local moves

The timing gains from port placement are necessary hypotheses of the prepared strategy, rather than consequences of adjacency alone. The next example quantifies that distinction while retaining the old guard.

::: {#prop-late-handoff .exhibit .exhibit--proposition data-exhibit-type="proposition" data-exhibit-name="Proposition 16 (A late-trigger obstruction)"}
**Proposition 16** (A late-trigger obstruction). *There is a 104-vertex subcubic stopping tower with $\lambda=9$, adjacent ancestry clouds $F_A,F_B$, a legal retained guard of $F_A$, and an allowed starting side for an arbitrarily large transition team, with the following properties. No transition cop can align with the robber's image under any retraction onto $F_B$ within five moves. Moreover, after a deadline at the end of round five, a legal entry into $F_B$ in round six remains uncaught on the next cop move, in round seven.*
:::

::: proof
*Proof.* Take the nine-vertex tree formed from the path $A-B-C$, a second leaf $C'$ adjacent to $B$, an edge $AD$, and four leaves adjacent to $D$. The degree of $D$ is five. The all-vertex stopping tower has maximum degrees $5,4,3$, so it performs exactly two rounds. Its $A$ cloud has $3\cdot3=9$ vertices. In the first $B$ gadget, three ports have total degree three and three pair vertices have degree two, giving a final $B$ cloud of order $3\cdot6+3\cdot3=27$. The first $D$ gadget has five ports of total degree four, three pair vertices of degree three, and three pair vertices of degree two, so its final cloud has order $5\cdot7+3\cdot6+3\cdot3=62$. The six original leaves remain singletons, so the total order is $9+27+62+6=104$.

Write $b_-,b_+$ for the ports of $F_B$ toward $A,C$, respectively, and $a$ for the port of $F_A$ adjacent to $b_-$. Let $c,c'$ denote the singleton descendants of the two leaves at $B$, and set

$$
W=V(H)\setminus\bigl(F_B\cup\{c,c'\}\bigr).
$$

The edge $ab_-$ is the only edge from $W$ to its complement. Each exterior component of $F_B$ attaches at just one port, so leaving the cloud cannot shorten a path between its ports. [Lemma 2](#lem-equilateral-ports) gives

$$
\operatorname{dist}_H(W,b_-)=1,\qquad
\operatorname{dist}_H(W,b_+)=9,\qquad
\operatorname{dist}_H(W,y)\ge8\quad(y\in N_H[b_+]\cap F_B),
$$

with equality in the last minimum attained by the neighbor of $b_+$ preceding it on an intrinsic geodesic from $b_-$.

Place all transition cops anywhere in $W$, and retain an additional old guard at $a$. Choose the robber initially at $c$; this placement is legal with the cops chosen before the robber. The old guard can remain stationary, since every surviving walk from the robber's component into $F_A$ would enter at the occupied vertex $a$.

For any retraction $\rho:H\to F_B$, the edge $cb_+$ and the identity $\rho(b_+)=b_+$ imply $\rho(c)\in N_H[b_+]\cap F_B$. Every such image is at distance at least eight from every allowed transition-cop starting position. Therefore five moves cannot establish alignment while the robber waits at $c$, regardless of the team size or the chosen retraction.

Number each round as a cop move followed by a robber move. Let the robber wait at $c$ through round five, enter $b_+$ on its move in round six, and wait there in round seven. No transition cop reaches $b_+$ in fewer than nine moves, so the entry is safe both when it occurs and on the next cop move. The old guard remains valid throughout.

◻
:::

::: {#rem-late-handoff-scope .exhibit .exhibit--remark data-exhibit-type="remark" data-exhibit-name="Remark 17 (Scope and larger scales)"}
*Remark 17* (Scope and larger scales).
This is a starting-location and deadline obstruction, not a cop-number lower bound; the robber in the example can eventually be captured. Earlier deployment, cops prepositioned outside $W$, and prepared source anchors all evade the specified hypothesis. In particular, the proposition does not contradict a schedule that pays for anchor travel and the $L$-move exterior-tree setup before the deadline.

For any prescribed $k\ge1$, replace the degree-five star center by one of degree $2^{2^{k-1}+1}$. Its descendants realize the maximum-degree sequence

$$
2^{2^{k-1}+1},\ 2^{2^{k-2}+1},\ \ldots,\ 4,\ 3,
$$

so the stopping rule performs exactly $k$ rounds. For each degree $r=2^{2^j+1}$ above four, $m=\sqrt{2r}$ is an integer, all port classes have size $m/2$, and both port and pair degrees are exactly $m$; this verifies the sequence. The target's ports have intrinsic distance $\lambda-1$, so retraction alignment from the old side needs at least $\lambda-1$ moves. After a deadline at the end of round $T$, entry in robber round $T+1$ remains safe through the following cop move whenever $\lambda>T+2$. These are exact distance lower bounds; the upper bound $\operatorname{diam}(F_v)\le2(\lambda-1)$ alone would establish no such delay.
:::

# Multistage bases and the transfer theorem

For a vertex set $A$ in a graph $G$, write $B_G(A,r)=\{x:\operatorname{dist}_G(x,A)\le r\}$ and $S_G(A,r)=\{x:\operatorname{dist}_G(x,A)=r\}$; for a singleton source we omit its braces, and an empty source has empty neighborhoods. A set $U\subseteq V(G)$ is *$(t,c_1,c_2)$-accessible* if there are pairwise disjoint sets $W(w)\subseteq B_G(w,t)$, one for each $w\in U$, satisfying

$$
|W(w)|\ge c_1\min\{d^t,c_2N/|U|\}.
$$

Here $N=|V(G)|$ and $d$ is the branching parameter specified below.

::: {#def-multistage-base .exhibit .exhibit--definition data-exhibit-type="definition" data-exhibit-name="Definition 18 (Five-layer multistage base)"}
**Definition 18** (Five-layer multistage base).
Fix an integer $d\ge2$, a constant $a_0\ge0$, and positive constants $\delta,J,a_1,\ldots,a_5$. A connected simple graph $G$ on $N$ vertices is a *five-layer multistage base* if there is a set $X\subseteq V(G)$, with $|X|\le a_0\sqrt N$, such that:

- [**(H1)**]{#cloud-h1} for every $v\notin X$, all integers $r,r'\ge1$ with
  $d^r,d^{r'}<N^{1/2+\delta}$, and every $V'\subseteq B_G(v,r)\setminus X$ of
  order $m$ satisfying $md^{r'}\le N/(\log N)^J$,
  $$
   a_1md^{r'}\le|S_G(V',r')|\le a_2md^{r'};
  $$

- [**(H2)**]{#cloud-h2} for all integers $r,r'$ such that
  $$
   N^{1/4-\delta}<(d+1)d^r<N^{1/4+\delta},\qquad
   N^{1/4-\delta}<(d+1)d^{r'}<N^{1/4+\delta},
  $$
  every $v\notin X$, and every $A\subseteq S_G(v,r)\setminus X$ with
  $|A|>N^{1/4-\delta}$, put $U=\bigcup_{a\in A}S_G(a,r')$. If
  $d^{r+r'}<a_3N/|U|$, there is a set $Q\subseteq V(G)$ such that
  $|S_G(a,r')\cap Q|<N^{1/4-2\delta}$ for every $a\in A$, and $U\setminus Q$ is
  $(r+r'-4,a_4,a_5)$-accessible;

- [**(H3)**]{#cloud-h3} $G-X$ is contained in one component of $G$.

:::

These are exactly the $s=5$ hypotheses of the [occupation transfer](/essays/ball-occupation-under-coarse-projections.html#def-multistage-base). They are the hypotheses of Prałat–Wormald [@PralatWormald, Theorem 4.1], with accessibility required five layers earlier. We keep [(H3)](#cloud-h3) to make the correspondence explicit; it is automatic for a connected base. The target spheres in [(H1)](#cloud-h1) are *not* trimmed by $X$, although the sources are. All parameters in the definition are fixed as $N$ tends to infinity.

::: {#thm-cloud-transfer .exhibit .exhibit--theorem data-exhibit-type="theorem" data-exhibit-name="Theorem 19 (Timed transfer through actual clouds)"}
**Theorem 19** (Timed transfer through actual clouds). *For the fixed parameters of [Definition 18](/essays/timed-guarding-in-degree-reduction-clouds.html#def-multistage-base), there are constants $C,C_*,N_0$ with the following property. Let $G$ be a five-layer multistage base of order $N\ge N_0$, and let $H$ be its actual all-vertex HMGHM tower, stopped when its maximum degree first becomes at most three. Write $D=\Delta(G)$, let $F_v$ be the original ancestry clouds, and put $K=\max_vc(H[F_v])$. Then*

$$
c(H)\le(a_0+2C+3)\sqrt N+K+1\le(a_0+2C+3)\sqrt N+2D+1,
$$

*and, in fact,*

$$
\boxed{c(H)\le C_*\sqrt N.}
$$

*The constants depend only on the listed multistage parameters, and not on the cloud order, the tower scale, or $D$. All cops are placed before the robber chooses her initial vertex. The strategy captures every lazy robber walk after finitely many moves.*
:::

Here $d$ is the fixed branching parameter in the growth hypotheses. It is not a new assumption that the maximum base degree $D$ is fixed: $D$ may grow within [(H1)](#cloud-h1), and the distinction between these two parameters is used below.

The theorem retains the full remaining-ball Hall requirement of the occupation argument. It does not assert a transfer for an arbitrary coarse projection, or for a base satisfying only a lower expansion bound. Nor does it retain the occupation theorem's explicit capture-time bound. The constant is not asserted uniform when the branching parameter $d$ grows.

# Synchronization and local cleanup

Throughout this section the tower has at least one round. Set $\lambda=3^k$ and $L=\lambda-1$, and choose a designated original-edge port $a_v$ as a fixed anchor in each cloud $F_v$. Fresh sampled cops start at these anchors and remain there until their team's dispatch.

::: {#lem-exit-time .exhibit .exhibit--lemma data-exhibit-type="lemma" data-exhibit-name="Lemma 20 (Exit lower bound)"}
**Lemma 20** (Exit lower bound). *If a robber starts in $F_u$ and first reaches a cloud over $S_G(u,r)$ after $m$ moves, then $m\ge\lambda(r-1)+1$. Before that move her base shadow lies in $B_G(u,r-1)$.*
:::

::: proof
*Proof.* The base shadow moves along an edge or stays. A path joining clouds whose base distance is $r$ uses at least $r$ inter-cloud edges. After erasing immediate reversals from a shortest such path, its intermediate cloud traversals join distinct designated ports and cost at least $L$ each, so its length is at least $r+(r-1)L=\lambda(r-1)+1$. The assertion about earlier shadows follows from their lazy motion.

◻
:::

::: {#lem-sync-deadline .exhibit .exhibit--lemma data-exhibit-type="lemma" data-exhibit-name="Lemma 21 (Synchronized two-round deadline)"}
**Lemma 21** (Synchronized two-round deadline). *Suppose a round of radius $r$ is followed by a round of radius $r'\ge2$, and $r+r'\ge4$. At the start of the first round, a cop at a fixed source anchor is assigned to $F_w$, with source base distance at most $t=r+r'-4$ from $w$. She travels to $a_w$ and waits there if she arrives before the next base root $u$ is observed. Once both arrival and root observation have occurred, activate this cop if $w\in S_G(u,r')$, using the exterior-tree pursuit. Every assigned cloud of this actual sphere can be guarded before the first sphere entry, simultaneously for all assigned targets and every robber walk.*
:::

::: proof
*Proof.* Number cop and robber moves after dispatch so that cop move $j$ immediately precedes robber move $j$. [Lemma 4](#lem-port-travel) gives anchor arrival by

$$
B=\lambda t+L=\lambda(r+r'-3)-1.
$$

Let $q$ be the robber move ending the first round, and let $m$ be the first subsequent sphere-entry move. [Lemma 20](#lem-exit-time) gives

$$
q\ge\lambda(r-1)+1,\qquad
m\ge q+\lambda(r'-1)+1\ge\lambda(r+r'-2)+2.
$$

Use the common activation time $\sigma=\max\{B,q\}$, after robber move $\sigma$, and use cop moves $\sigma+1,\ldots,\sigma+L$ for setup. The two relevant bounds are

$$
B+L=\lambda(r+r'-2)-2\le m-4,\qquad q+L\le m-2,
$$

the second using $r'\ge2$. Hence $\sigma+L\le m-2$. Every target cloud remains unentered throughout its setup, so [Lemma 10](#lem-exterior-tree) establishes every assigned guard, and the guards then track their retracted shadows permanently.

◻
:::

The destinations and source anchors are chosen before the unknown root $u$ is revealed; only activation depends on $u$. Earlier visits to a target, before the first round ends, cause no problem because the cop waits at the anchor. The saving in [Lemma 4](#lem-port-travel) is essential to this calculation: arbitrary fiber representatives have only the generic bound $\lambda t+2L$, which would consume a sixth layer for the same setup uniformly in $\lambda$.

::: {#lem-region-cleanup .exhibit .exhibit--lemma data-exhibit-type="lemma" data-exhibit-name="Lemma 22 (Cleanup with a reusable reserve)"}
**Lemma 22** (Cleanup with a reusable reserve). *Let $R\subseteq V(G)$ be a specified set of base vertices. A team of $|R|$ anchor cops and $K+1$ reserve cops, initially anywhere in the connected ambient graph, can force capture or an exit from $\bigcup_{v\in R}F_v$ after finitely many moves.*
:::

::: proof
*Proof.* Assign one cop to each target anchor, wait until all have arrived, and start their exterior-tree pursuits simultaneously. Record the clouds visited by the robber during the next $L$ robber moves, including the starting cloud. By [Lemma 5](#lem-short-walk-clouds), at most two distinct original clouds are visited. If the robber exits the prescribed region, the exit alternative has occurred. Otherwise all unvisited target clouds acquire guards within $L$ cop moves by [Lemma 10](#lem-exterior-tree). Every visited target is marked exceptional, whether or not its assigned cop has already aligned; if it has not aligned, that cop can remain idle, so no pursuit toward an image outside its tree is prescribed. Every successful guard remains active.

If one exceptional cloud remains, the reserve can deploy $K$ cops to a winning initial configuration of its induced graph and play there. If two remain, they are adjacent and their induced union has exactly one joining edge, since the base is simple. Send one reserve cop to an endpoint of that edge; once it is occupied, the surviving robber is in one observed side, where the other $K$ reserve cops deploy and pursue. During this deployment, or during pursuit, leaving the exceptional union either enters a guarded cloud or exits the prescribed region. All travel is finite, and the known cop bound on each induced cloud gives finite capture under continued confinement. No retraction onto the union of the exceptional clouds is needed.

◻
:::

The setup cops in this lemma can be reused after an actual round exit; the continuing-round guards belong to different teams and are retained. For finishing we apply the reserve argument only after proving that the two exceptional clouds are interior to a fully guarded boundary, which removes the exit alternative.

# Proof of the multistage transfer

We reproduce the radius, reservoir, and Hall estimates of Prałat–Wormald [@PralatWormald, Theorem 4.1 and Claim 4.2], with the five-layer reservoirs and remaining-ball target of the [companion occupation paper](/essays/ball-occupation-under-coarse-projections.html#thm-multistage). These are probabilistic estimates on the base. The deterministic replacement of occupation by timed guards is proved above; we do not infer it from the earlier cop-number conclusion.

## Placement, radii, and finite rounds

Put $F=J+2$ and $i_f=\lceil F\log\log N\rceil$. Independently for each $1\le i\le i_f$, sample $Z_i\subseteq V(G)$ by including each vertex with probability $c_i/N$, where

$$
c_i=Ce^{-i}\sqrt N\quad(i<i_f),\qquad c_{i_f}=\sqrt N.
$$

Team $i$ consists of one cop at $a_z$ for each $z\in Z_i$. There are also $|X|$ exceptional-guard cops, $\lceil N^{1/3}\rceil$ cleanup anchor cops, and $K+1$ reserve cops. All are placed before the original robber start, and the last three groups may start anywhere.

First establish a guard on every $X$ cloud using the sequential retract setup of [Lemma 12](#lem-retract-setup). The $|X|$ assigned cops and the $K+1$ reserve suffice: each established cloud retains one cop, and at least $K$ mobile cops remain available for the next setup, so at the end there are still $K+1$ mobile reserve cops. Sampled teams stay at their chosen source anchors throughout this prephase and all earlier rounds. The prephase either captures the robber or finishes with her outside all $X$ clouds; let $v_1$ be her actual base shadow at that time.

By Chernoff's inequality, with probability $1-o(1)$ every sampled team has at most $2c_i$ members. On this event the total number of cops is at most

$$
|X|+2\sqrt N\left(C\sum_{i\ge1}e^{-i}+1\right)+\lceil N^{1/3}\rceil+K+1
\le(a_0+2C+3)\sqrt N+K+1
$$

for sufficiently large $N$.

Choose a sufficiently small fixed $\varepsilon_0>0$ and define

$$
r_1=\left\lfloor\tfrac14\log_d(\varepsilon_0N)\right\rfloor,
\qquad
r_{i+1}=\left\lfloor\log_d(\varepsilon_0e^{2i}\sqrt N)\right\rfloor-r_i,
$$

so that the source radius condition is

$$
\varepsilon_0e^{2i}\sqrt N/d<d^{r_i+r_{i+1}}\le\varepsilon_0e^{2i}\sqrt N.
$$

Each parity subsequence is nondecreasing, since $r_{i+2}-r_i$ is the difference of two successive increasing floor terms. Moreover $r_1,r_2=\tfrac14\log_dN+O(1)$, so, uniformly for $i\le i_f+1$,

$$
d^{r_i}=\Omega(N^{1/4}),\qquad d^{r_i}=O(e^{2i}N^{1/4}),
$$

with all implicit constants depending only on the fixed parameters. In particular every needed radius is at least two, and successive pairs lie in the window of [(H2)](#cloud-h2), for sufficiently large $N$. The ceiling in $i_f$ causes only the harmless bound $e^{2i_f}\le e^2(\log N)^{2F}$.

Round $i$ starts at the actual base shadow $v_i\notin X$ and ends at its first subsequent visit to $S_G(v_i,r_i)$, with next root $v_{i+1}$. If the robber enters an $X$ cloud she is captured on the next cop move, so we restrict attention to surviving walks avoiding them. The exit lower bound is [Lemma 20](#lem-exit-time).

To prevent an infinite round, apply [Lemma 22](#lem-region-cleanup) to $R=B_G(v_i,r_i)\setminus X$. By [(H1)](#cloud-h1) with a singleton source and the radius estimates,

$$
|R|\le1+2a_2d^{r_i}=O(N^{1/4}(\log N)^{2F})\le N^{1/3}.
$$

If the round has not already ended, the robber is inside $B_G(v_i,r_i-1)\setminus X$. Cleanup forces capture or an exit from $R$, which must first end the round. At any actual round exit the cleanup attempt is aborted and its anchor cops and reserve are reused. There are only finitely many rounds in the argument, so no uniform cleanup time is required. Waiting and reversal are included in these alternatives.

## Reservoir assignments and vulnerability

Let $S_0=S_G(v_1,r_1)\setminus X$. Team $i$ is dispatched at the start of round $i$, unless the finishing trigger below has already occurred. For $i\ge1$, define

$$
S_i=\{w\in S_G(v_{i+1},r_{i+1})\setminus X:\text{team $i$ has no cop assigned to }F_w\}.
$$

A root $v_i$ is *vulnerable* if

$$
|S_{i-1}|\le e^{-5(i-1)}|S_G(v_i,r_i)|.
$$

The initial root is vulnerable, and [Lemma 21](#lem-sync-deadline) ensures that a surviving end of round $i$ belongs to $S_{i-1}$.

Fix a vulnerable root and a possible $A=S_{i-1}$ before exposing team $i$, and suppose

$$
|A|>e^{-5(i_f-1)}|S_G(v_i,r_i)|.
$$

Put $r=r_i$, $r'=r_{i+1}$, and $U=\bigcup_{a\in A}S_G(a,r')$. By [(H1)](#cloud-h1) and the two displayed conditions, $|A|=\Omega(N^{1/4}(\log N)^{-5F})>N^{1/4-\delta}$. Also

$$
|U|\le e^{-5(i-1)}a_2^2d^{r+r'},
\qquad
|U|d^{r+r'}\le a_2^2\varepsilon_0^2e^{5-i}N<a_3N
$$

when $\varepsilon_0$ is small enough. Hypothesis [(H2)](#cloud-h2) supplies its exceptional set $Q$ and disjoint reservoirs of radius $t=r+r'-4$, whose sizes satisfy

$$
|W(w)|\ge\kappa e^{2i}\sqrt N\quad(w\in U\setminus Q),
\qquad
\kappa=a_4\min\left\{\varepsilon_0d^{-5},\frac{a_5}{a_2^2\varepsilon_0e^5}\right\}>0.
$$

The first term follows from the radius schedule; for the second, the union bound above gives $N/|U|\ge e^{3i-5}\sqrt N/(a_2^2\varepsilon_0)\ge e^{2i}\sqrt N/(a_2^2\varepsilon_0e^5)$.

Fix an ordering of base vertices and choose every reservoir family deterministically from the finitely many admissible choices. Assign to $w$ the cop at the first member of $W(w)\cap Z_i$, when this intersection is nonempty; disjointness makes the assignment injective. The empty-hit events $E_w$ are mutually independent and satisfy

$$
\Pr(E_w)\le\exp(-C\kappa e^i)\le\tfrac12e^{-5i}
$$

for all $i\ge1$ once $C\ge\max\{1,6/(e\kappa)\}$. Targets in $X$ need not be activated, because their prephase guards remain; including them in this assignment and count only wastes available cops.

For fixed $u\in A$, set $H_u=S_G(u,r')\setminus Q$. By [(H1)](#cloud-h1), [(H2)](#cloud-h2), and the radius estimates, $|H_u|\ge\tfrac12a_1d^{r'}=\Omega(N^{1/4})$ for large $N$. The number of empty-hit targets in $H_u$ is stochastically dominated by a binomial variable of mean $\mu=\tfrac12e^{-5i}|H_u|=\Omega(N^{1/4}(\log N)^{-5F})$, and Chernoff's inequality gives at most $\tfrac23e^{-5i}|H_u|$ such targets except with probability $\exp(-\mu/27)$. Moreover

$$
|Q\cap S_G(u,r')|<N^{1/4-2\delta}\le\tfrac13e^{-5i}|S_G(u,r')|
$$

for large $N$. A union bound over $u\in A$ therefore shows that, with failure probability $O(N^{-\log N})$, every possible actual next sphere has at most an $e^{-5i}$ fraction of unassigned targets outside $X$. No restriction on the size of the fixed positive $\delta$ is needed for this estimate.

Send the assigned cops to their fixed anchors immediately at the start of round $i$. When its actual next root $u=v_{i+1}\in A$ is observed, [Lemma 21](#lem-sync-deadline) activates the assigned cops on $S_G(u,r')\setminus X$ and establishes their guards before any entry to that sphere. Therefore the next root is vulnerable, or capture occurs. The four-move and two-move margins hold for every possible duration of the first round.

We must make this assertion simultaneous despite the robber seeing all sampled teams. Expose teams successively for the analysis. Conditional on the earlier samples, deterministic assignment choices specify a unique set $S_{i-1}$ for each base exit history $(v_1,\ldots,v_i)$, and there are at most $N^i$ histories; a union bound over those histories and $i<i_f=O(\log\log N)$ gives failure probability $o(1)$. The assignments depend only on these histories and samples. Their subsequent motions may depend on the entire robber walk, but the deterministic synchronization lemma succeeds uniformly over every such walk, so it introduces no extra probability event. In particular $v_1$ may depend on all the samples through the preprocessing: the event already holds for every possible initial root. This is the same all-history exposure argument as [@PralatWormald, Claim 4.2].

## The full remaining-ball matching and capture

Dispatch the still-unmoved final team $i_f$ at the start of the first round $i^*$ for which

$$
|S_{i^*-1}|\le e^{-5(i_f-1)}|S_G(v_{i^*},r_{i^*})|.
$$

The preceding argument ensures $i^*\le i_f$, unless capture occurred earlier, and teams $i^*,\ldots,i_f-1$ are then unnecessary. Write $r=r_{i^*}$ and put

$$
r''=r_{i_f}+r_{i_f+1}-r,
\qquad
\widehat r=r_{i_f}+r_{i_f+1}+1,
\qquad
\widehat t=\widehat r-5=r+r''-4,
$$

$$
U_{\mathrm{fin}}=\bigcup_{u\in S_{i^*-1}}B_G(u,r'')\setminus X.
$$

Monotonicity of the parity subsequences implies $r''\ge\min\{r_{i_f},r_{i_f+1}\}\ge2$ for large $N$. Also the radius schedule gives $d^{r''}=O(N^{1/4}(\log N)^{2F})$, so all singleton sphere bounds through radius $r''$ used next are admissible in [(H1)](#cloud-h1). The target consists of balls, not just spheres: arbitrary waiting requires the interior targets in the finishing argument. Summing the singleton sphere upper bounds in [(H1)](#cloud-h1) gives

$$
|U_{\mathrm{fin}}|\le e^{-5(i_f-1)}a_2d^r\,3a_2d^{r''}\le3a_2^2e^5\varepsilon_0e^{-3i_f}\sqrt N.
$$

For Hall's theorem, take any nonempty $V''\subseteq U_{\mathrm{fin}}$ of order $m$ and apply [(H1)](#cloud-h1) with center $v_{i^*}$, containing radius $\widehat r-1$, and neighborhood radius $\widehat t$. Its source condition holds because

$$
V''\subseteq B_G(v_{i^*},r+r'')\setminus X=B_G(v_{i^*},\widehat r-1)\setminus X,
$$

and both radius powers are below $N^{1/2+\delta}$ by the radius schedule. The size condition follows from the displayed bound on $|U_{\mathrm{fin}}|$:

$$
md^{\widehat t}\le|U_{\mathrm{fin}}|d^{\widehat r}=O(Ne^{-i_f})\le N/(\log N)^J.
$$

Consequently

$$
|S_G(V'',\widehat t)|\ge a_1md^{\widehat t}\ge a_1\varepsilon_0d^{-5}m\sqrt N(\log N)^{2F}.
$$

The final team samples each base vertex with probability $N^{-1/2}$, so its number of starting vertices in this sphere is binomial with mean at least $a_1\varepsilon_0d^{-5}m(\log N)^{2F}$, which exceeds $m(\log N)^2$ for large $N$. The probability of fewer than $m$ cops is at most $\exp(-m(\log N)^2/8)$, and summing over the at most $N^m$ source sets of each size gives failure probability $O(\exp(-(\log N)^2/9))$. Conditional on earlier samples, the possible finishing sets are indexed by $N^{O(i_f)}$ base exit histories, so the additional union bound still gives failure probability $o(1)$.

Thus, simultaneously for every feasible finishing history, Hall's theorem assigns a distinct final-team cop to every target $w\in U_{\mathrm{fin}}$, from a starting base vertex within distance $\widehat t$ of $w$. Choose such a matching deterministically. Each assigned cop starts at its original port anchor and arrives at the target anchor by

$$
B=\lambda\widehat t+L=\lambda(r+r''-3)-1
$$

cop moves after dispatch.

If round $i^*$ never ends, cleanup captures the robber. Otherwise let $q$ be its actual end, and let $u=v_{i^*+1}\in S_{i^*-1}$. At time $\sigma=\max\{B,q\}$, activate the anchor cops for the actual ball $B_G(u,r'')\setminus X$ simultaneously. The calculation in [Lemma 21](#lem-sync-deadline), with $r''$ in place of $r'$, finishes setup strictly before the first possible entry to $S_G(u,r'')$. At most two clouds are visited during setup, by [Lemma 5](#lem-short-walk-clouds), and both are interior to the ball. Every other target is guarded, and every boundary cloud is guarded either by a successful target cop or by its retained $X$ guard.

Keep these guards active and use the $K+1$ reserve as in [Lemma 22](#lem-region-cleanup) to pursue within the one or two exceptional clouds. An exit from their union inside the ball enters a guarded cloud; an exit from the ball must cross its guarded boundary. Hence the exit alternative is unavailable to a surviving robber, and capture follows. The reserve may begin this final deployment anywhere, since the boundary guards remain in place during all travel. This proves the first inequality of [Theorem 19](#thm-cloud-transfer) using the cop count above, and [Proposition 15](#prop-cloud-cop-bound) gives its second inequality.

## Absorbing the internal setup budget

::: {#lem-degree-absorption .exhibit .exhibit--lemma data-exhibit-type="lemma" data-exhibit-name="Lemma 23 (Degree control from the exact sphere bounds)"}
**Lemma 23** (Degree control from the exact sphere bounds). *For sufficiently large $N$, a base in [Definition 18](#def-multistage-base) satisfies*

$$
\Delta(G)\le\max\{|X|-1,\ 1+a_2d+a_2d^2\}.
$$
:::

::: proof
*Proof.* For $v\notin X$, apply [(H1)](#cloud-h1) to $V'=\{v\}$ with containing radius $1$ and neighborhood radii $1$ and $2$. All fixed-radius admissibility conditions hold for large $N$, giving $|S_G(v,1)|\le a_2d$ and $|S_G(v,2)|\le a_2d^2$. If $x\in X$ has a neighbor $v\notin X$, then

$$
N_G(x)\subseteq\{v\}\cup S_G(v,1)\cup S_G(v,2),
$$

so $\deg_G(x)\le1+a_2d+a_2d^2$. This uses the untrimmed target spheres in [(H1)](#cloud-h1). If $x$ has no neighbor outside $X$, its degree is at most $|X|-1$. Vertices outside $X$ already have degree at most $a_2d$.

◻
:::

Since $|X|\le a_0\sqrt N$, [Lemma 23](#lem-degree-absorption) absorbs the additive $2D+1$ and gives the boxed bound of [Theorem 19](#thm-cloud-transfer). If the tower has zero rounds, $H=G$ and its clouds are singletons; the same construction then uses $\lambda=1$ and $L=0$, so an anchor cop occupies its entire target cloud, cleanup is ordinary vertex occupation, and the finishing targets are all occupied at activation. Thus the same bounds hold without a shadow setup. Equivalently, [@PralatWormald, Theorem 4.1] applies after replacing its accessibility constant $a_4$ by $a_4d^{-5}$. This completes the proof of [Theorem 19](#thm-cloud-transfer).

::: {#cor-random-regular .exhibit .exhibit--corollary data-exhibit-type="corollary" data-exhibit-name="Corollary 24 (Fixed-degree random regular bases)"}
**Corollary 24** (Fixed-degree random regular bases). *Fix an integer $d\ge2$. With probability tending to one, a uniformly random $(d+1)$-regular base on $N$ vertices is connected and its actual stopping-rule HMGHM tower has cop number $O_d(\sqrt N)$, with the cloud order absent from the transfer constant.*
:::

::: proof
*Proof.* The random-regular expansion and reservoir estimates of Prałat–Wormald [@PralatWormaldRegular, Theorem 3.1, Lemma 3.2, and Sub-lemma 3.4] give the base hypotheses, with the five-layer reading of their reservoir trees and repaired exceptional set established in the companion paper's [early-accessibility proposition and random-regular corollary](/essays/ball-occupation-under-coarse-projections.html#cor-regular). Apply [Theorem 19](#thm-cloud-transfer). This use is for fixed degree and a fixed level shift.

◻
:::

# The remaining Hall-demand obstruction {#hall-boundary}

Timed guards reduce the cost of protecting an assigned cloud. They do not supply the distinct-cop assignment demanded by the finishing step. The following elementary inequality isolates a limitation of full-region demand, and it uses actual graph neighborhoods, without a thin-sphere hypothesis.

For nonempty $U\subseteq V(G)$ and an integer $t\ge0$, define

$$
\mathcal R_t(U)=\min_{\varnothing\ne D\subseteq U}\frac{|B_G(D,t)|}{|D|},
\qquad
V_t(U)=\max_{w\in U}|B_G(w,t)|.
$$

If every target in $U$ has an assigned disjoint reservoir of common integer size $m$ inside its radius-$t$ ball, then $m\le\lfloor\mathcal R_t(U)\rfloor$. Conversely Hall's theorem, applied to $m$ copies of each target, gives such reservoirs whenever $m\le\mathcal R_t(U)$. This observation concerns a uniform reservoir certificate, rather than every possible sampled matching.

::: {#prop-hall-capacity .exhibit .exhibit--proposition data-exhibit-type="proposition" data-exhibit-name="Proposition 25 (Capacity of a region containing a ball)"}
**Proposition 25** (Capacity of a region containing a ball). *Suppose $B_G(a,u)\subseteq U$, where $u\ge1$ is an integer, and put $M=|B_G(a,u)|$. Then*

$$
\mathcal R_t(U)\le1+V_t(U)\bigl(1-M^{-1/u}\bigr)\le1+V_t(U)\frac{\log M}{u}.
$$
:::

::: proof
*Proof.* For $D\subseteq V(G)$ let $\partial_{\rm in}D$ consist of the vertices of $D$ with a neighbor outside $D$. Any path from $D$ to a vertex outside $D$ passes through this inner boundary, so $B_G(D,t)\subseteq D\cup B_G(\partial_{\rm in}D,t)$. If $D\subseteq U$, it follows that

$$
|B_G(D,t)|\le|D|+V_t(U)|\partial_{\rm in}D|.
$$

Write $b_j=|B_G(a,j)|$ for $0\le j\le u$. Since $b_0=1$, $\prod_{j=1}^ub_{j-1}/b_j=M^{-1}$, and some $j$ has $b_{j-1}/b_j\ge M^{-1/u}$. For $D=B_G(a,j)\subseteq U$, the inner boundary is contained in $S_G(a,j)$, whence

$$
\frac{|\partial_{\rm in}D|}{|D|}\le1-\frac{b_{j-1}}{b_j}\le1-M^{-1/u}.
$$

The first bound follows by using this $D$ in the capacity minimum. The second is $1-e^{-x}\le x$ with $x=(\log M)/u$.

◻
:::

::: {#cor-slow-hall .exhibit .exhibit--corollary data-exhibit-type="corollary" data-exhibit-name="Corollary 26 (An incompatible slow-growth certificate)"}
**Corollary 26** (An incompatible slow-growth certificate). *Fix $a_*,C_b>0$. There is no sequence of demand regions containing $B_G(a,u)$ with $q\ge1$, $q\to1$, $u\to\infty$, and $Z\to\infty$ that simultaneously satisfies*

$$
|B_G(a,u)|\le1+C_bq^{u+1},\qquad
V_t(U)\le1+C_bqZ,\qquad
\mathcal R_t(U)\ge a_*Z.
$$
:::

::: proof
*Proof.* The ball upper bound implies $\log M/u\le\log q+u^{-1}\log(1+C_bq)$. By [Proposition 25](#prop-hall-capacity), the three inequalities require

$$
a_*\le Z^{-1}+(Z^{-1}+C_bq)\left(\log q+\frac{\log(1+C_bq)}{u}\right),
$$

and the right side tends to zero.

◻
:::

In the exception-free proposed shrinking-base model, the finishing union contains a full remaining ball. The corollary therefore obstructs the uniform Hall demand even after optional sphere bounds at the remaining and finishing radii are removed. It does not assume any intermediate-radius growth law: the inner balls used in the proof are merely subsets of the same demand region, and the Hall radius stays $t$. With a trimmed region $U=(\bigcup_aB_G(a,u))\setminus X$, the conclusion applies only to ambient balls actually contained in $U$; a path avoiding $X$ alone does not supply such a ball. Neither statement lower-bounds the cop number of the graph.

# What remains between this theorem and Meyniel

The lower comparison $c(G)\le c(H)$ is unconditional for these towers by [Theorem 7](#thm-lower-transfer). A universal bound in the base order could therefore feed back to the original graph without a cop-number loss. The conditional input in the upper theorem is the multistage base class, not a conjectural lower transfer. This distinction does not remove any of the capacity or retained-resource obstacles below.

The transfer separates three tasks: locating distinct cop resources, establishing local protection under a deadline, and capturing the robber inside the residual domain. Actual cloud ports solve the second task, and synchronized setup makes the third inexpensive when the residual domain contains at most two clouds. The present proof still assigns one cop to every target of a full remaining-ball union, so the capacity obstruction survives the removal of the cloud-order factor.

::: question
**Question 27**. *Is there a strategy that assigns guards to a smaller exit set and proves an affordable decrease in the residual domain? Such a lemma must count retained guards and the mobile reserve simultaneously, since finite setup alone does not provide a deadline.*
:::

It must also supply an internal pursuit bound for the remaining component, since a thin boundary does not make arbitrary interior pursuit inexpensive. Weakening [(H1)](#cloud-h1) would additionally remove the automatic estimate $\Delta(G)=O(\sqrt N)$ used to absorb the reserve here, and that resource would then need a new bound.

::: question
**Question 28**. *Can a frontier or boundary demand strictly weaker than the full remaining ball support a comparable timed strategy under shrinking expansion, including capture when the robber waits? [Corollary 26](#cor-slow-hall) rules out the uniform full-region certificate; it does not rule out every sampled matching.*
:::

The [late-handoff example](#prop-late-handoff) does not exclude earlier deployment or exterior prepositioning. Conversely the positive theorem does not simulate every base strategy.

::: question
**Question 29**. *[Theorem 11](#thm-adjacent-clouds) says exactly when one guard covers two adjacent clouds. Is there a corresponding criterion for larger unions — over a base subtree, say — that survives the triangle and girth-five obstructions and reduces the number of retained guards?*
:::

Even though its conclusion is on the square-root scale in the tower's order, the base hypotheses here remain substantially stronger than polynomially shrinking expansion. The theorem establishes the cloud mechanism under fixed multistage hypotheses and no universal progress in the exponent of Meyniel's conjecture, which remains open. The bounded source comparison does not establish priority for every component lemma.

# Verification and reproducibility

The September 9, 2026 follow-up makes the lower comparison self-contained, generalizes the short-walk count, records isometric geodesic lifts and the exact adjacent-cloud retraction criterion, and replaces the internal subdivided-clique citation with a direct strategy. The alleged three-move interception is checked in both turn orders; only the cop-first order captures, and that order does not satisfy the simulation's checkpoint. The lower comparison and the main timed upper theorem keep their conclusions.

The proofs use the pinned source versions in the bibliography and exact combinatorial arguments. Finite checks independently rebuild the HMGHM gadget, its stopped towers, retractions, and the 104-vertex handoff example. They exhaust lazy exterior shadow games on small clouds, check the first possible third-cloud visit, and verify both orders of anchor arrival and root observation in the synchronized clock. Separate checks validate the Hall-capacity inequality on finite graphs and the generic serial-setup arithmetic. These computations support identities and explicit examples; they do not certify the asymptotic theorem or replace its universal quantifiers.

The accompanying research source contains the checks `hmghm-cloud-retractions.py`, `hmghm-exterior-tree-setup.py`, `hmghm-timed-handoff.py`, `synchronized-cloud-schedule.py`, `timed-cloud-deadlines.py`, and `remaining-ball-hall-capacity.py`. The additional `hmghm-lower-transfer.py` checks every cop-reply distance certificate and prescribed-endpoint geodesic lift in its finite sample, and `hmghm-adjacent-cloud-retract.py` verifies the new retractions and their exterior tree games together with the triangle and girth-five neighborhood counterexamples. Neither is a cop-number census.
