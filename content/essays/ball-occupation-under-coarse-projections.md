---
title: "Ball-Occupation Certificates under Coarse Graph Projections"
subtitle: "Degree Reduction, Square-Root Hard Families, and Toroidal Barriers"
date: 2026-07-27
revised:
  - date: "2026-09-06"
    note: "Added the adaptive multistage transfer, early-accessibility derivation, and fixed-degree random-regular corollary, with full hypotheses, source attribution, and pinned Prałat–Wormald versions."
  - date: "2026-09-05"
    note: "Corrected the cloud-product estimate and expansion loss, completed the core and metric proofs, and clarified upper-bound tightness and traversal-time claims. The subsequent literature revision sharpens connected-cloud expansion and qualifies the HMGHM transfer exponent."
abstract: >
  We isolate an abstract strategy-transfer principle for Cops and Robber: a
  coarse graph projection with bounded fibers and bounded distance distortion
  lets cops occupy a lifted macro-ball before the robber escapes, giving a
  quantitative cop-number bound from uniform growth on the base. Applied to the
  Hosseini-Mohar-Gonzalez Hermosillo de la Maza degree-reduction
  construction, this gives the known hard family an upper bound within a
  polylogarithmic factor of the square-root scale. A counting argument then
  proves a sharp limit on the strategy
  class itself: Cartesian tori of cycles have bounded doubling and constant
  cop number but linear occupation cost at every radius, so weak expansion
  alone cannot certify a universal robustness theorem. The adaptive multistage
  strategy of Prałat and Wormald does transfer when the base has sphere growth
  and reservoirs accessible five layers early: for fixed degree, every
  $(\lambda,P)$-occupation projection satisfies $c(H)\le C_dP\sqrt N$,
  with no logarithm or scale dependence in the cop count. Fixed-degree random
  regular bases satisfy the strengthened hypothesis with high probability.
tags:
  - research
  - research/mathematics
  - research/graph-theory
authors:
  - "Levi Neuwirth | /me.html"
affiliation:
  - "Brown University | https://www.brown.edu"
bibliography: data/ball-occupation-paper.bib
preprint: /papers/ball-occupation-paper.pdf
no-collapse: true
status: "Durable"
confidence: proved
evidence: 5
peer-status: unreviewed
result-shape: mixed
history:
  - date: "2026-09-06"
    note: "Added the adaptive multistage transfer, early-accessibility derivation, and fixed-degree random-regular corollary, with full hypotheses, source attribution, and pinned Prałat–Wormald versions."
  - date: "2026-09-05"
    note: "Corrected the cloud-product estimate and expansion loss, completed the core and metric proofs, and clarified upper-bound tightness and traversal-time claims. The subsequent literature revision sharpens connected-cloud expansion and qualifies the HMGHM transfer exponent."
  - date: "2026-07-27"

---

# Introduction and main conclusions

The multi-cop version of Cops and Robber was developed by Aigner and Fromme, who proved that three cops suffice on every planar graph [@AignerFromme]. Meyniel's conjecture asks whether every connected $n$-vertex graph has cop number $O(\sqrt n)$. The current best universal upper bound remains $$\frac{n}{2^{(1-o(1))\sqrt{\log_2 n}}},$$ proved independently by Lu–Peng and Scott–Sudakov [@LuPeng; @ScottSudakov]. Bose–Esperet–Hodor–Joret–Micek–Rambaud recently extended the same scale of bound from graph order to vertex-cover number [@BoseEsperetHodorJoretMicekRambaud]. Expansion is one of the principal settings in which polynomial savings are known: Bradshaw–Hosseini–Mohar–Stacho obtain weak Meyniel bounds from bounded-degree expansion restricted to sublinear set scales [@BradshawHosseiniMoharStacho], while Clow's withdrawn preprint developed a closely related structural program connecting failure of weak Meyniel to high-cop expanding examples [@Clow].

The motivation here is the effect of bounded-degree replacement gadgets on pursuit. The degree-reduction construction of Hosseini–Mohar–Gonzalez Hermosillo de la Maza (HMGHM) preserves lower bounds on cop number and produces subcubic graphs with cop number $M^{1/2-o(1)}$ [@HMG]. A natural converse question is whether a useful upper strategy on the base graph survives the replacement tower.

An arbitrary winning strategy does not lift transparently. Moving one step in the quotient may require a squad dispersed through a cloud to reorganize while the robber continues moving. The successful object is narrower and more stable: an *occupation certificate* that assigns distinct cops to all vertices of a region before the robber can leave it. Distance stretching slows both deployment and escape, and a bounded normalized additive error leaves a strict timing margin.

The first result is therefore stated for an abstract projection, rather than for the HMGHM gadget. The gadget enters only later, through an exact metric calculation. The resulting upper bound is stronger quantitatively than the notation $M^{1/2+o(1)}$ suggests: it is $\sqrt M$ times a polylogarithmic factor. By contrast, the available lower bound approaches the square-root exponent at the triple-logarithmic rate displayed in the abstract. These two facts should not be conflated merely because both can be written $M^{1/2+o(1)}$.

The one-shot barrier marks the boundary of the occupation mechanism. A one-shot occupation certificate needs polynomial ball amplification between radii $R$ and $2R$. Polynomially weak expansion alone does not supply this. For every fixed $k$, the Cartesian tori $C_L^{\square k}$ have bounded metric doubling, exact cop number $k+1$, and linear one-shot occupation cost at every radius. Taking $k>1/\delta$ puts these examples inside every window $h(G)\ge |G|^{-\delta}$. A separate cubic replacement retains the barrier at $\delta=1/2$. The obstacle in the universal problem is therefore not degree reduction itself; it is the need for adaptive reuse over many weak-growth layers.

The last section supplies an adaptive transfer for one base class.  The
deterministic multistage theorem of Prałat and Wormald
[@PralatWormald, Theorem 4.1] wins with $O(\sqrt N)$ cops on bases with sphere
growth, accessible reservoirs, and a small exceptional set.  Its phase
argument lifts unchanged through a coarse projection once randomly placed
cops become squads that fill whole fibers and the reservoirs are required
five base layers closer to their targets, which pays for the additive
metric error.  The result is $c(H)\le C_dP\sqrt N$ for fixed $d$
([Theorem 25](#thm-multistage)), without the logarithm of
[Theorem 3](#thm-abstract-transfer); random regular bases of fixed degree satisfy
the strengthened hypothesis ([Corollary 30](#cor-regular)).  This does not improve
the growing-degree hard-family estimates, which are retained as stated.

# Scale-adaptive cores and the robustness window

For a connected graph $J$, write $$h(J)=\min_{\varnothing\ne A\subseteq V(J),\ |A|\le |J|/2}
\frac{|\partial_J A|}{|A|},\qquad h(K_1)=+\infty.$$ The following elementary reduction explains why polynomially weak expansion is the relevant robustness window for the universal problem.

::: {#prop-adaptive-core .exhibit .exhibit--proposition data-exhibit-type="proposition" data-exhibit-name="Proposition 1 (Scale-adaptive induced core)"}
**Proposition 1** (Scale-adaptive induced core). *Let $J$ be a connected graph of order $n$, and let $\eta(1)\ge\cdots\ge\eta(n)\ge0$. Then $J$ contains a connected induced subgraph $K$, of order $m$, such that $$\boxed{h(K)\ge\eta(m)}
\qquad\text{and}\qquad
\boxed{c(J)\le c(K)+\sum_{j=m+1}^{n}\eta(j).}$$*
:::

::: proof
*Proof.* Induct on $n$. If $h(J)\ge\eta(n)$, take $K=J$; this also covers $n=1$ by the singleton convention. Otherwise choose $A\subseteq V(J)$ with $0<|A|\le n/2$ and $|S|<\eta(n)|A|$, where $S=\partial_J A$. Placing $|S|$ stationary cops on $S$ confines the robber to a component of $J-S$. The remaining cops can then move to a winning initial placement in that component while $S$ stays guarded. Hence $$c(J)\le |S|+\max_{C\text{ a component of }J-S}c(C).$$ Choose a component $C$ attaining this maximum, and write $t=|C|$. If $C\subseteq A$, then $t\le |A|\le n/2$; otherwise $C$ is disjoint from $A$. In both cases $|A|\le n-t$, so monotonicity of $\eta$ gives $$|S|<\eta(n)|A|\le\eta(n)(n-t)
\le
\sum_{j=t+1}^{n}\eta(j).$$ Apply the induction hypothesis to $C$ and the restricted sequence $\eta(1),\ldots,\eta(t)$. It supplies a fixed connected induced subgraph $K\subseteq C$, of order $m$, with $h(K)\ge\eta(m)$ and $c(C)\le c(K)+\sum_{j=m+1}^{t}\eta(j)$. Combining the two estimates proves the claim. Since $C$ is induced in $J$, so is $K$. ◻
:::

Taking $\eta(j)=j^{-a}$ shows that a polynomial cop-number saving on subcubic graphs with $h(K)\ge |K|^{-a}$ would imply a weak form of Meyniel for arbitrary graphs after the bounded-degree transfer of Hosseini–Mohar–Gonzalez Hermosillo de la Maza [@HMG, arXiv v2, Corollary 8]. Bradshaw–Hosseini–Mohar–Stacho already treat constant expansion restricted to sublinear set scales [@BradshawHosseiniMoharStacho]; the unresolved axis in this reduction is expansion that itself shrinks polynomially.

# Coarse occupation projections

::: {#def-projection .exhibit .exhibit--definition data-exhibit-type="definition" data-exhibit-name="Definition 2 (Coarse occupation projection)"}
**Definition 2** (Coarse occupation projection). Let $G$ and $H$ be connected graphs. A surjection $\pi:V(H)\to V(G)$ is a $(\lambda,P)$-occupation projection if, writing $F_v=\pi^{-1}(v)$,

1. $|F_v|\le P$ for every $v\in V(G)$;

2. for distinct $u,v\in V(G)$ and arbitrary $x\in F_u$, $y\in F_v$, $$\lambda(\operatorname{dist}_G(u,v)-1)+1
   \le
   \operatorname{dist}_H(x,y)
   \le
   \lambda(\operatorname{dist}_G(u,v)+2)-2;$$

3. $\operatorname{diam}_H(F_v)\le2(\lambda-1)$ for every $v\in V(G)$.
:::

The particular constants in [Definition 2](#def-projection) are chosen because they are exact for the HMGHM tower. The proof below only needs a bounded additive slack after division by $\lambda$ and a strict gap between deployment and escape deadlines.

For $U\subseteq V(G)$, let $B_G(U,r)$ be its closed radius-$r$ neighborhood.

::: {#thm-abstract-transfer .exhibit .exhibit--theorem data-exhibit-type="theorem" data-exhibit-name="Theorem 3 (Abstract macro-ball occupation transfer)"}
**Theorem 3** (Abstract macro-ball occupation transfer). *Let $G$ have $N$ vertices. Fix $d\ge2$, $R\ge2$, and constants $a,A_0>0$. Assume $$\sqrt N\le d^{R-2}<d\sqrt N,
\qquad
d^3\le\sqrt N,$$ and $$\begin{aligned}
|B_G(U,R-2)|
&\ge a\min\{|U|d^{R-2},N\}
&&\text{for every }U\subseteq V(G),\\
|B_G(v,R)|
&\le A_0d^R
&&\text{for every }v\in V(G).
\end{aligned}$$ If $H$ admits a $(\lambda,P)$-occupation projection onto $G$, then $$\boxed{
c(H)
\le
C(a,A_0)P\bigl(d^3+\log(ePN)\bigr)\sqrt N.
}$$ The displayed number of cops captures the robber within at most $\lambda R$ cop moves. In particular, the cop-number bound is independent of the scale factor $\lambda$; tower depth affects capture time but not the required bank size.*
:::

::: proof
*Proof.* Put $$\Theta=d^3+\log(ePN),
\qquad
\mu=\frac{AP\Theta}{\sqrt N},$$ where $A$ is a sufficiently large constant depending only on $a,A_0$. Choose one canonical vertex $z^*\in F_z$ in every fiber. At $z^*$ place an independent Poisson number of cop tokens of mean $\mu$.

For a possible robber fiber $F_v$, set $$X_v=\pi^{-1}(B_G(v,R)).$$ By the upper-growth hypothesis and the displayed scale conditions above, $$Q_v:=|X_v|
\le PA_0d^R
<A_0Pd^3\sqrt N
\le A_0P\Theta\sqrt N.$$ We prove simultaneously for every $v$ that the sampled tokens can be matched distinctly to all vertices of $X_v$, with every assigned token based over a base vertex within distance $R-2$ of its target fiber.

Let $S\subseteq X_v$, $|S|=s$, and put $U=\pi(S)$. Since every fiber has at most $P$ targets, $|U|\ge s/P$. Every token based over $Z=B_G(U,R-2)$ is adjacent in the assignment graph to at least one target in $S$.

If $|U|d^{R-2}<N$, then the number of available tokens is Poisson with mean at least $$\mu a|U|d^{R-2}\ge Aa\Theta s.$$ For a Poisson variable $Y$ of mean $\Lambda\ge Aa\Theta s$, $$\Pr(Y<s)\le e^{-\Lambda}\left(\frac{e\Lambda}{s}\right)^s.$$ After increasing $A$, this is at most $(ePN)^{-4s}$. There are at most $N\binom{PN}{s}$ choices of a root and a target subset of size $s$, so summing over $s\ge1$ gives $o(1)$.

If $|U|d^{R-2}\ge N$, then the available-token mean is at least $$\mu aN=AaP\Theta\sqrt N
\ge\frac{Aa}{A_0}Q_v$$ using the bound on $Q_v$ above. Taking $A$ large and applying the same Poisson bound shows, after a union bound over at most $N2^{Q_v}$ target subsets, that no saturated Hall condition fails with probability $1-o(1)$. Here every saturated target set has $$s\ge |U|\ge\frac{N}{d^{R-2}}>\frac{\sqrt N}{d}\ge N^{1/3},$$ so the polynomial prefactors are negligible.

Hall's condition therefore holds simultaneously for all macro-balls with probability $1-o(1)$. The total number of sampled tokens is at most $2AP\Theta\sqrt N$ with probability $1-o(1)$, so a deterministic placement of the claimed size exists.

It remains to compare deadlines. A target $y\in X_v$ lies over some $u\in B_G(v,R)$. Its assigned cop begins over $z$ with $\operatorname{dist}_G(z,u)\le R-2$. If $z\ne u$, the upper distortion bound gives travel time at most $$\lambda((R-2)+2)-2=\lambda R-2.$$ If $z=u$, the fiber-diameter bound gives at most $2(\lambda-1)\le\lambda R-2$, since $R\ge2$.

To leave $X_v$, the robber must enter a fiber over a base vertex at distance at least $R+1$ from $v$. The lower distortion bound makes this require at least $$\lambda((R+1)-1)+1=\lambda R+1$$ steps. Every vertex of $X_v$ is occupied first, and the cop assigned to the robber's current vertex captures her. ◻
:::

::: {#rem-pw-uniform .exhibit .exhibit--remark data-exhibit-type="remark" data-exhibit-name="Remark 4 (The quantifier needed from the random base)"}
*Remark 4* (The quantifier needed from the random base). The use of the lower-growth hypothesis above is graph-uniform, not a per-source-set probability statement. In the dense theorem of Prałat and Wormald, condition (i) of their deterministic Theorem 3.1 is explicitly quantified over *every* source set and radius. Their Theorem 3.4 proves that a single $G(N,p)$ satisfies those hypotheses asymptotically almost surely; its proof unions over the bad source sets and concludes that the growth estimate holds simultaneously for all sets and radii [@PralatWormald]. Thus the external input has the quantifier order required by [Theorem 3](#thm-abstract-transfer).
:::

# The HMGHM replacement tower

For a vertex of degree $r$, the HMGHM replacement has one external port for every incident edge. The ports are partitioned into nearly equal classes, and for each pair of classes there is an internal vertex adjacent to every port in the two classes [@HMG].

For degree zero or one, use a singleton cloud, serving as the external port in the degree-one case. Each round replaces every vertex according to its current degree, including vertices of degree two or three. For degree reduction, stop when the entire graph is subcubic.

::: {#lem-portgeometry .exhibit .exhibit--lemma data-exhibit-type="lemma" data-exhibit-name="Lemma 5 (One-round port geometry)"}
**Lemma 5** (One-round port geometry). *For every HMGHM replacement cloud of degree at least two:*

1. *distinct ports are nonadjacent and have distance exactly two;*

2. *every cloud vertex is within distance at most three of every specified port;*

3. *the cloud diameter is at most four.*
:::

::: proof
*Proof.* Two ports in different classes share the internal vertex associated with their class pair. Two ports in the same class share any internal vertex associated with that class and another nonempty class. Since ports are mutually nonadjacent, their distance is exactly two.

An internal vertex is adjacent to every port in either of two classes. If a specified port lies in neither class, travel to a port in one of the two classes, then through the internal vertex corresponding to that class and the specified port's class, and finally to the specified port. This takes three steps. For the diameter bound, two internal vertices whose class pairs intersect share a port. If their pairs are disjoint, choose one class from each pair and route through the internal vertex associated with those two classes, using four edges. The port–port and port–internal cases have already been bounded by two and three edges, respectively. ◻
:::

Let $$G=G_0,G_1,\ldots,G_k=H$$ be an iterated HMGHM tower, and let $\pi:V(H)\to V(G)$ map every final vertex to its original ancestor. Put $$F_v=\pi^{-1}(v),
\qquad
P=\max_v|F_v|,
\qquad
\lambda=3^k.$$

::: {#thm-metric .exhibit .exhibit--theorem data-exhibit-type="theorem" data-exhibit-name="Theorem 6 (Exact normalized distortion)"}
**Theorem 6** (Exact normalized distortion). *The ancestry projection is a $(3^k,P)$-occupation projection. Explicitly, for distinct base vertices $u,v$, $r=\operatorname{dist}_G(u,v)$, and arbitrary $x\in F_u$, $y\in F_v$, $$\boxed{
3^k(r-1)+1
\le
\operatorname{dist}_H(x,y)
\le
3^k(r+2)-2,
}$$ and $$\boxed{\operatorname{diam}_H(F_v)\le2(3^k-1).}$$*
:::

::: proof
*Proof.* For one round, a shortest path between distinct clouds uses $e\ge r$ external edges. Between consecutive external edges it enters and leaves an intermediate cloud through distinct ports: otherwise it immediately traverses one external edge back. By [Lemma 5](#lem-portgeometry), each intermediate port change costs at least two internal edges, and hence $$\operatorname{dist}_{G_1}(x,y)\ge e+2(e-1)\ge3r-2.$$ For the upper bound, follow a base geodesic. Reaching the first prescribed port costs at most three, each intermediate port change costs two, the external edges cost $r$, and reaching the final endpoint costs at most three. Thus $$\operatorname{dist}_{G_1}(x,y)\le3+r+2(r-1)+3=3r+4.$$ The one-round fiber diameter is at most four. A singleton cloud contributes zero endpoint cost and cannot be an intermediate cloud on a shortest path, so the degree-zero and degree-one conventions preserve these bounds.

The lower and upper affine recurrences are $$L_j(r)=3L_{j-1}(r)-2,
\qquad
U_j(r)=3U_{j-1}(r)+4,$$ with $L_0(r)=U_0(r)=r$. Solving gives $$L_k(r)=3^k(r-1)+1,
\qquad
U_k(r)=3^k(r+2)-2.$$ The diameter recurrence $D_j\le3D_{j-1}+4$, $D_0=0$, gives $D_k\le2(3^k-1)$. ◻
:::

The feature that matters is not the number of rounds but the normalized additive error: after division by $3^k$, it remains two quotient layers. By [Theorem 3](#thm-abstract-transfer), any other graph projection with the same three properties inherits the same occupation-certificate transfer.

# Expansion retention under connected-cloud replacement

For a nontrivial graph $J$, write
$$
 \iota(J)=\min_{\varnothing\ne A\subseteq V(J),\ |A|\le |J|/2}
 \frac{e_J(A,V(J)\setminus A)}{|A|}.
$$

::: {#prop-port-exp .exhibit .exhibit--proposition data-exhibit-type="proposition" data-exhibit-name="Proposition 7 (Expansion under connected-cloud replacement)"}
**Proposition 7** (Expansion under connected-cloud replacement).
Let $G$ be a connected nontrivial graph of maximum degree $D$, and put
$\alpha=\iota(G)$.  Replace each vertex by a connected nonempty cloud of
order at most $P$, retaining exactly one inter-cloud edge for each base edge
and no other inter-cloud edges.  The resulting graph $H$ satisfies
$$
 \boxed{
 \iota(H)
 \ge
 \frac{\alpha}{P(D+\alpha)}
 \ge \frac{\alpha}{2DP}.
 }
$$
No distinct-port or equal-cloud-size assumption is needed.  If $H$ is
subcubic, then $h(H)\ge\alpha/[3P(D+\alpha)]$.
:::

::: proof
*Proof.*
Fix $S\subseteq V(H)$ with $0<s=|S|\le|H|/2$.  Partition the base vertices
into $U$, whose clouds lie wholly in $S$; $W$, whose clouds lie wholly
outside $S$; and $T$, whose clouds meet both sides.  Put $q=|T|$.
Since both sides of the cut contain at least $s$ vertices and every cloud
has order at most $P$,
$$
 |U|\ge s/P-q,\qquad |W|\ge s/P-q.
$$
In particular, $\min\{|U|,|G|-|U|\}\ge s/P-q$.  Apply base expansion to
the smaller side of the cut from $U$; if that side is empty, the resulting
inequality is trivial.  At most $Dq$ of its edges end in
$T$, so
$$
 e_G(U,W)\ge\alpha s/P-(D+\alpha)q.
$$
Every partially cut cloud contributes at least one internal cut edge by
connectivity.  These $q$ edges are distinct from the retained edges
corresponding to $E_G(U,W)$, all of which cross the lifted cut.  Thus, with
$A=\alpha s/P$ and $B=D+\alpha\ge1$,
$$
 e_H(S,V(H)\setminus S)\ge q+\max\{0,A-Bq\}\ge A/B.
$$
For the last inequality, $q\ge A/B$ suffices by itself; otherwise
$q+A-Bq=A-(B-1)q\ge A/B$.  Divide by $s$, and use $\alpha\le D$.
If $H$ is subcubic, each exterior boundary vertex accounts for at most
three cut edges, giving the asserted vertex-expansion bound.
◻
:::

The following estimate derives the cloud product directly from the one-round HMGHM gadget, retaining the factors introduced at every step.

::: {#lem-cloud-product .exhibit .exhibit--lemma data-exhibit-type="lemma" data-exhibit-name="Lemma (Cloud-product bound)"}
**Lemma** (Cloud-product bound). *Let $D\ge4$ be the initial maximum degree, let $k$ be the first round at which the replacement tower is subcubic, and let $L_i$ be the largest cloud order in round $i$, for $0\le i<k$. Then $$\prod_{i=0}^{k-1}L_i\le C D^2(\log D)^2,
\qquad
2^k=O(\log D).$$ The power two of $\log D$ is attained by a sequence of regular bases.*
:::

::: proof
*Proof.* For degree $d\ge5$, HMGHM use $m=\lceil\sqrt{2d}\rceil$ classes, so the cloud order is $$d+\binom m2\le2d+\sqrt{d/2}.$$ Together with the small-degree gadgets, this bounds the largest cloud order at maximum degree $x\ge4$ by $L(x)\le2x+\sqrt{x/2}$. Writing $D_i=\Delta(G_i)$, the one-round degree bound is $D_{i+1}\le2\lceil\sqrt{D_i/2}\rceil$ until the final special round at maximum degree four [@HMG, Theorem 3].

Put $q=D/2$, $t_i=q^{2^{-i}}$, and $r=\lceil\log_2(\log_2 q)\rceil$. The identity $\lceil\sqrt{\lceil y\rceil}\rceil=\lceil\sqrt y\rceil$ gives $D_i\le2\lceil t_i\rceil$ by induction for every round reached. Since $t_r\le2$, we have $k\le r+1$, and hence $2^k=O(\log D)$. For each such round, $$L_i\le4(t_i+1)+\sqrt{t_i+1}
\le4t_i(1+C_0t_i^{-1/2}).$$ If $r\ge1$, then $\sqrt2<t_r\le2$ and $t_{r-j}=t_r^{2^j}$, so $$\sum_{i=0}^r t_i^{-1/2}
\le\sum_{j=0}^{\infty}2^{-2^j/4}<\infty.$$ Thus the product of the factors $1+C_0t_i^{-1/2}$ is bounded by an absolute constant. Extending the upper product to $r+1$ terms if the tower stops earlier gives $$\prod_{i=0}^{k-1}L_i
\le C4^{r+1}\prod_{i=0}^r t_i
=C4^{r+1}q^{2-2^{-r}}
\le CD^2(\log D)^2.$$ The case $D=4$, for which $r=0$, follows directly from the seven-vertex degree-four gadget.

For sharpness, let $a_j=2^{2^j+1}$, so $a_0=4$, and start from any connected $a_j$-regular graph. At degree $a_i$ the gadget has $m=\sqrt{2a_i}=a_{i-1}$ equal classes, each of size $m/2$. Both its ports, after attaching external edges, and its internal vertices have degree $m$. Thus the next graph is $a_{i-1}$-regular and every cloud has order $2a_i-a_{i-1}/2$. After the final degree-four round, every ancestry fiber therefore has order $$7\prod_{i=1}^j(2a_i-a_{i-1}/2)
=7a_j^2 4^{j-2}\prod_{i=1}^j\left(1-\frac1{2a_{i-1}}\right)
=\Theta\bigl(a_j^2(\log a_j)^2\bigr).$$ The last product converges to a positive constant. In particular, the smaller logarithmic exponent stated in the iteration estimate of HMGHM [@HMG, arXiv v2, Section 3] does not bound the cloud product of this tower. This comparison concerns the inspected preprint; the full published proof was not available for comparison. ◻
:::

Apply [Proposition 7](#prop-port-exp) once to the final ancestry clouds,
using the [cloud-product bound](#lem-cloud-product) for their maximum order.

::: {#cor-exp-retention .exhibit .exhibit--corollary data-exhibit-type="corollary" data-exhibit-name="Corollary 8 (Expansion retained by HMGHM reduction)"}
**Corollary 8** (Expansion retained by HMGHM reduction).
Let $H$ be the final subcubic graph obtained from a connected graph $G$ of
maximum degree $D\ge4$.  Then
$$
 \boxed{
 h(H)
 \ge
 \frac{\iota(G)}{C D^3(\log D)^2}.
 }
$$
In particular, if $D=|G|^{o(1)}$ and $\iota(G)=|G|^{-o(1)}$, then
$|H|=|G|^{1+o(1)}$ and $h(H)=|H|^{-o(1)}$.
:::

::: proof
*Proof.*
Every final ancestry cloud is connected: inductively, each vertex of a
connected earlier cloud is replaced by a connected cloud, and every earlier
internal edge is retained between its two replacement clouds.  Likewise,
each original base edge remains the unique edge between its two final
ancestry clouds, and no new inter-ancestry edges appear.  Thus the proposition
applies with $P\le\prod_iL_i\le CD^2(\log D)^2$, giving
$$
 h(H)
 \ge
 \frac{\iota(G)}{3P(D+\iota(G))}
 \ge
 \frac{\iota(G)}{C D^3(\log D)^2}.
$$
The order statement follows from $|G|\le|H|\le P|G|$ and the same
cloud-product bound.
◻
:::

::: {#rem-replacement-products .exhibit .exhibit--remark data-exhibit-type="remark" data-exhibit-name="Remark 9 (Relation to replacement products)"}
*Remark 9* (Relation to replacement products).
The regular replacement-product literature proves stronger spectral
conclusions under much stronger hypotheses on the clouds; see, for example,
Reingold–Vadhan–Wigderson [@ReingoldVadhanWigderson].  [Proposition 7](#prop-port-exp) allows arbitrary
connected, nonuniform clouds, including coincident external ports.  It gives
an elementary isoperimetric estimate; no priority claim is made for this
inequality.
:::

## Quantitative scope of the general degree reduction

The qualitative transfer cited in the [core reduction](#prop-adaptive-core) holds, but its exponent requires
care.  The discrepancy below already follows from HMGHM's own arXiv v2
Corollary 4 order bound: the logarithmic correction does not affect the
polynomial exponent balance.  Suppose connected subcubic graphs
of order $m$ satisfy $c\le m^{1-\varepsilon+o(1)}$, for fixed
$0<\varepsilon\le1/2$.  For a connected graph $G$ of order $n$, follow the threshold
argument in [@HMG, arXiv v2, Section 5]: place a stationary cop at a vertex of
residual degree at least $D$ and remove its closed neighborhood, repeating
until the residual maximum degree is below $D$.  There are $O(n/D)$ guards.
A robber entering a removed neighborhood is captured on the next cop move;
otherwise it remains in one residual component.  With the guards retained,
the other cops can move to a winning initial placement in that component.
Its subcubic reduction has order at most $CnD^2(\log D)^2$ and cop number
at least that of the component.  Therefore
$$
 c(G)\le O(n/D)
       +\bigl(CnD^2(\log D)^2\bigr)^{1-\varepsilon+o(1)}.
$$
Writing $D=n^a$ and balancing
$1-a=(1-\varepsilon)(1+2a)$ gives $a=\varepsilon/(3-2\varepsilon)$, hence
$$
 c(G)\le n^{1-\varepsilon/(3-2\varepsilon)+o(1)}.
$$
For $0<\varepsilon<1/2$, this is weaker than the exponent $1-\varepsilon/2$ printed in
[@HMG, arXiv v2, Corollary 8]; both give $3/4$ at $\varepsilon=1/2$.
This identifies what the displayed threshold proof establishes, not a
counterexample to the stronger implication or a claim about the inaccessible
published proof.  Every fixed polynomial saving still transfers.

# A square-root-exponent family with a polylogarithmic upper bound

Take $$d=(\log N)^4,
\qquad
p=\frac{d}{N-1},
\qquad
G\sim G(N,p).$$ Iterate the HMGHM replacement until the graph $H$ is subcubic, and write $M=|H|$.

With high probability, $\Delta(G)\le2d$. By [Remark 4](#rem-pw-uniform), the dense Prałat–Wormald theorem supplies the uniform lower growth needed above; in the volume range used here it also supplies the matching upper growth [@PralatWormald]. Choose $R$ minimally so that $d^{R-2}\ge\sqrt N$. Since $d$ is polylogarithmic, the scale conditions of [Theorem 3](#thm-abstract-transfer) hold.

The [cloud-product bound](#lem-cloud-product) gives, both globally and along one ancestry fiber, $$P\le C d^2(\log d)^2,
\qquad
N\le M\le PN.$$ The HMGHM shadow strategy gives $c(H)\ge c(G)$, and the random-graph lower bound of Bollobás–Kun–Leader used in their argument [@BollobasKunLeader] yields $$c(G)
\ge
d^{-2}N^{\frac12-\frac{9}{2\log\log d}}.$$ The abstract transfer theorem gives $$c(H)
\le
CP\bigl(d^3+\log(ePN)\bigr)\sqrt N
\le
\sqrt M\,(\log M)^{20+o(1)}.$$ Using $d=(\log N)^4$ and $M=N(\log N)^{O(1)}$ in the lower bound gives the following more informative formulation.

::: {#thm-hardfamily .exhibit .exhibit--theorem data-exhibit-type="theorem" data-exhibit-name="Theorem 10 (Quantitative HMGHM hard family)"}
**Theorem 10** (Quantitative HMGHM hard family). *There is a sequence of connected subcubic graphs $H$, of order $M\to\infty$, for which $$\boxed{
M^{\frac12-\frac{9+o(1)}{2\log\log\log M}}
\le
c(H)
\le
\sqrt M\,(\log M)^{20+o(1)}.
}$$ The upper bound is $\sqrt M$ times a polylogarithmic factor. The lower exponent tends to $1/2$ only at a triple-logarithmic rate.*
:::

The base edge expansion is $\Omega(d)$ with high probability, and its
maximum degree is at most $2d$.  [Corollary 8](#cor-exp-retention) gives
$$
 h(H)=\Omega\!\left(d^{-2}(\log d)^{-2}\right),
 \qquad h(H)\ge(\log M)^{-8-o(1)}=M^{-o(1)},
$$
where $d=(\log N)^4$ and $M=N(\log N)^{O(1)}$.  More generally, a base
with $\iota(G)=\Omega(D)$ retains
$h(H)=\Omega(D^{-2}(\log D)^{-2})$.  At polynomial initial degree this
estimate supplies only polynomially small expansion, rather than the
subpolynomial loss obtained here.

::: {#cor-weakexpander .exhibit .exhibit--corollary data-exhibit-type="corollary" data-exhibit-name="Corollary 11 (Square-root weak-expander family)"}
**Corollary 11** (Square-root weak-expander family). *There are connected subcubic graphs satisfying $$h(H)\ge (\log M)^{-8-o(1)}
\qquad\text{and}\qquad
c(H)=M^{1/2+o(1)}.$$ More precisely, they obey the two-sided bounds of [Theorem 10](#thm-hardfamily).*
:::

::: {#rem-robustness-endpoint .exhibit .exhibit--remark data-exhibit-type="remark" data-exhibit-name="Remark 12 (What is forced, and what is achieved)"}
*Remark 12* (What is forced, and what is achieved). By [Proposition 1](#prop-adaptive-core), polynomially weak expansion is a natural robustness window for weak Meyniel. The HMGHM lower bound alone already forces every proposed estimate $$c(J)\le C\phi^{-p}|J|^{1-\varepsilon+o(1)}
\qquad(h(J)\ge\phi=|J|^{-o(1)})$$ to have $\varepsilon\le1/2$. That restriction predates the upper transfer proved here. The new conclusion is an upper bound within a polylogarithmic factor of $\sqrt M$ for the known stressing family. The available lower bound does not locate its cop number within polylogarithmic factors of $\sqrt M$; the displayed estimates leave that stronger conclusion open.
:::

# Why chase strategies need not transfer

The abstract theorem deliberately transfers a strategy class, not arbitrary cop number. The smallest example explains the distinction. For a degree-two vertex, one HMGHM cloud is a three-vertex path. Replacing every vertex of $C_3$ therefore produces $C_9$. But $$c(C_3)=1,
\qquad
c(C_9)=2.$$ The one-cop win on $C_3$ is a direct chase/dismantling phenomenon. The subdivision-like stretching destroys it. By contrast, an occupation certificate is synchronized to a deadline: the replacement tower stretches the cops' travel and the robber's escape by the same factor, and the bounded normalized additive slack preserves a strict margin. The examples $K_4$ and the diamond graph exhibit the same one-round increase, so the issue is structural rather than peculiar to one cycle.

# A one-shot occupation barrier

::: {#def-occ .exhibit .exhibit--definition data-exhibit-type="definition" data-exhibit-name="Definition 13 (Universal one-shot occupation number)"}
**Definition 13** (Universal one-shot occupation number). For a connected graph $G$ and integer $R\ge0$, let $\operatorname{Occ}_R(G)$ be the minimum size of a finite set $X$ of distinct cop tokens, equipped with a position map $p:X\to V(G)$, such that for every $v\in V(G)$ there is an injection $$f_v:B_G(v,R)\longrightarrow X$$ with $$\operatorname{dist}_G(u,p(f_v(u)))\le R
\qquad\text{for every }u\in B_G(v,R).$$ Different tokens may have the same initial position. After learning the robber's starting vertex, the common prepositioned bank can occupy her entire radius-$R$ ball within $R$ moves.
:::

::: {#rem-target-deadline .exhibit .exhibit--remark data-exhibit-type="remark" data-exhibit-name="Remark 14 (Why the target and deadline are natural)"}
*Remark 14* (Why the target and deadline are natural). If the robber starts at $v$, she needs at least $R+1$ robber moves to leave $B_G(v,R)$. Occupying that whole ball within $R$ cop moves is therefore the canonical one-shot certificate: every vertex she could still occupy is filled before her first possible escape. The parameter $\operatorname{Occ}_R$ measures this specific strategy class, not ordinary cop number.
:::

::: {#thm-occ-lower .exhibit .exhibit--theorem data-exhibit-type="theorem" data-exhibit-name="Theorem 15 (Counting barrier)"}
**Theorem 15** (Counting barrier). *Every connected graph satisfies $$\boxed{
\operatorname{Occ}_R(G)
\ge
\frac{\sum_{v\in V(G)}|B_G(v,R)|}
{\max_{x\in V(G)}|B_G(x,2R)|}.
}$$ In particular, if $G$ is vertex-transitive, then $$\boxed{
\operatorname{Occ}_R(G)
\ge
|V(G)|\frac{|B_G(o,R)|}{|B_G(o,2R)|}.
}$$*
:::

::: proof
*Proof.* Fix a feasible multiset $X$. For each possible robber start $v$, every cop token used by the injection $f_v$ lies in $B_G(v,2R)$, by the triangle inequality. Hence at least $|B_G(v,R)|$ tokens of $X$ lie in $B_G(v,2R)$. Summing over $v$, the number of incident pairs $(v,x)$ with $x\in X\cap B_G(v,2R)$ is at least $\sum_v|B_G(v,R)|$.

A fixed token based at $x$ is counted only for starts $v\in B_G(x,2R)$, at most $\max_y|B_G(y,2R)|$ times. Therefore $$|X|\max_y|B_G(y,2R)|
\ge
\sum_v|B_G(v,R)|,$$ which proves the claim. ◻
:::

The theorem identifies the exact growth ratio demanded by one-shot occupation. A polynomial saving from the trivial $|V(G)|$ bound requires polynomial amplification from radius $R$ to radius $2R$.

We now give subcubic witnesses showing that polynomially weak expansion does not imply such amplification.

::: {#def-qt .exhibit .exhibit--definition data-exhibit-type="definition" data-exhibit-name="Definition 16 (The cubic truncated torus)"}
**Definition 16** (The cubic truncated torus). For $L\ge5$, let $Q_L$ have vertex set $$(\mathbb Z/L\mathbb Z)^2\times\mathbb Z/4\mathbb Z.$$ Inside each fiber $(x,y)\times\mathbb Z/4\mathbb Z$, join the four vertices in a cycle. Add the external edges $$(x,y,0)(x,y+1,2)
\qquad\text{and}\qquad
(x,y,1)(x+1,y,3)$$ for every $(x,y)$. Equivalently, $(x,y,2)$ receives its external edge from $(x,y-1,0)$, and $(x,y,3)$ receives its external edge from $(x-1,y,1)$. Thus every vertex has two internal cycle neighbors and one external neighbor, and $Q_L$ is the four-cycle port replacement of the square torus $C_L\square C_L$.
:::

Every vertex of $Q_L$ has degree three, and the construction embeds on the torus by replacing each base vertex inside a small disk. Its order is $4L^2$.

::: {#lem-doubling .exhibit .exhibit--lemma data-exhibit-type="lemma" data-exhibit-name="Lemma 17 (Vertex transitivity and explicit doubling of Q_L)"}
**Lemma 17** (Vertex transitivity and explicit doubling of $Q_L$). *The graph $Q_L$ is vertex-transitive and, for every vertex $x$ and radius $R\ge0$, $$|B_{Q_L}(x,2R)|\le 5500\,|B_{Q_L}(x,R)|.$$*
:::

::: proof
*Proof.* Translations in the first two coordinates are automorphisms. The map $$\rho(x,y,i)=(y,-x,i+1)$$ (with coordinates interpreted cyclically) preserves internal cycle edges and interchanges the two external edge directions. Translations together with $\rho$ act transitively.

Let $T_L=C_L\square C_L$ and project $(x,y,i)$ to $(x,y)$. Projection does not increase distance, so $$|B_{Q_L}(x,2R)|\le4|B_{T_L}(\pi x,2R)|
\le4\min\{L,4R+1\}^2.$$ Conversely, from an arbitrary cloud vertex one can enter the required port in at most two internal moves and then lift each base step using at most three moves. Hence, with $r=\lfloor(R-2)/3\rfloor$ for $R\ge2$, $$|B_{Q_L}(x,R)|\ge |B_{T_L}(\pi x,r)|.$$ The coordinate box of cyclic radius $\lfloor r/2\rfloor$ lies inside the $\ell_1$ ball, so $$|B_{T_L}(\pi x,r)|
\ge \min\{L,2\lfloor r/2\rfloor+1\}^2.$$ For $R<10$, the upper bound is at most $4\cdot37^2<5500$ and the denominator is at least one. For $R\ge10$, one has $r\ge R/6$ and $2\lfloor r/2\rfloor+1\ge r$, whence the ratio is at most $4\cdot30^2<5500$. This proves the displayed constant. ◻
:::

::: {#thm-cubic-barrier .exhibit .exhibit--theorem data-exhibit-type="theorem" data-exhibit-name="Theorem 18 (Cubic one-shot barrier)"}
**Theorem 18** (Cubic one-shot barrier). *For $L\ge5$, the connected cubic graphs $Q_L$, with $M=|Q_L|=4L^2$, satisfy $$\boxed{
h(Q_L)=\Theta(M^{-1/2}),
\qquad
c(Q_L)\le3,
\qquad
\operatorname{Occ}_R(Q_L)\ge \frac{M}{5500}
\quad\text{for every }R\ge0.
}$$*
:::

::: proof
*Proof.* The square torus has edge and vertex expansion $\Theta(1/L)$ by the discrete torus isoperimetric inequality [@BollobasLeader]. Applying [Proposition 7](#prop-port-exp) with cloud size four gives the matching lower bound for $Q_L$; lifting a coordinate slab of width $\lfloor L/2\rfloor$ gives the upper bound for every $L$. Since $Q_L$ is cubic, edge and vertex expansion differ by at most a constant factor. Thus $h(Q_L)=\Theta(1/L)=\Theta(M^{-1/2})$.

The graph $Q_L$ is toroidal, and every toroidal graph has cop number at most three [@Lehner]. Vertex transitivity, [Theorem 15](#thm-occ-lower), and [Lemma 17](#lem-doubling) give $$\operatorname{Occ}_R(Q_L)
\ge
M\frac{|B_{Q_L}(x,R)|}{|B_{Q_L}(x,2R)|}
\ge \frac{M}{5500}.$$ The finite audit suggests that the optimal asymptotic constant is $1/4$, but that sharpening is not needed here. ◻
:::

## The barrier throughout every polynomial expansion window

For integers $k\ge2$ and $L\ge4$, write $$T_{L,k}=\underbrace{C_L\square\cdots\square C_L}_{k\text{ factors}}.$$ Its order is $m=L^k$, its degree is $2k$, and its metric is the cyclic $\ell_1$ metric.

::: {#lem-ktorus-doubling .exhibit .exhibit--lemma data-exhibit-type="lemma" data-exhibit-name="Lemma 19 (Uniform doubling of Cartesian tori)"}
**Lemma 19** (Uniform doubling of Cartesian tori). *For every fixed $k\ge2$, every $L\ge4$, every vertex $x$, and every radius $R\ge0$, $$|B_{T_{L,k}}(x,2R)|\le (5k)^k|B_{T_{L,k}}(x,R)|.$$*
:::

::: proof
*Proof.* Every coordinate of a point in $B(x,2R)$ has cyclic distance at most $2R$, so $$|B(x,2R)|\le \min\{L,4R+1\}^k.$$ The coordinate box in which every coordinate has cyclic distance at most $\lfloor R/k\rfloor$ lies in $B(x,R)$, and therefore $$|B(x,R)|\ge\min\{L,2\lfloor R/k\rfloor+1\}^k.$$ If $R<k$, the ratio is at most $(4k+1)^k$. If $R\ge k$, then $2\lfloor R/k\rfloor+1\ge R/k$ and $4R+1\le5R$; taking the minima with $L$ does not increase their ratio beyond $5k$. The claim follows. ◻
:::

::: {#thm-full-window .exhibit .exhibit--theorem data-exhibit-type="theorem" data-exhibit-name="Theorem 20 (Full-window toroidal barrier)"}
**Theorem 20** (Full-window toroidal barrier). *For every fixed $k\ge2$, the graphs $T_{L,k}$ satisfy $$\boxed{
h(T_{L,k})=\Theta_k(m^{-1/k}),
\qquad
c(T_{L,k})=k+1,
\qquad
\operatorname{Occ}_R(T_{L,k})\ge (5k)^{-k}m
\quad\text{for every }R\ge0.
}$$ Consequently, for every $\delta>0$ there is a constant-degree graph family with $$h(G)\ge |G|^{-\delta},
\qquad
c(G)=O_\delta(1),
\qquad
\operatorname{Occ}_R(G)=\Omega_\delta(|G|)
\quad\text{for every radius }R.$$*
:::

::: proof
*Proof.* The discrete-torus edge-isoperimetric inequality gives order $1/L$ [@BollobasLeader]. Since $T_{L,k}$ has degree $2k$, edge boundary and external vertex boundary differ by at most the fixed factor $2k$; a coordinate slab of width $\lfloor L/2\rfloor$ supplies the matching upper bound. Hence $h(T_{L,k})=\Theta_k(1/L)=\Theta_k(m^{-1/k})$. Neufeld and Nowakowski proved that a Cartesian product of $k$ cycles, each of length at least four, has cop number exactly $k+1$ [@NeufeldNowakowski]. Since the torus is vertex-transitive, [Theorem 15](#thm-occ-lower) and [Lemma 19](#lem-ktorus-doubling) give the occupation lower bound.

Given $\delta>0$, choose $k=\max\{2,\lfloor1/\delta\rfloor+1\}$. Then $1/k<\delta$, so for sufficiently large $m$ the expansion lower bound $h(T_{L,k})\ge m^{-\delta}$ holds after absorbing the fixed $k$-dependent constant. ◻
:::

::: {#rem-sharp-metric-constant .exhibit .exhibit--remark data-exhibit-type="remark" data-exhibit-name="Remark 21 (The sharp metric constant)"}
*Remark 21* (The sharp metric constant). For fixed $k$, choose radii $1\ll R\ll L$. Lattice-point asymptotics for the $\ell_1$ ball give $$\frac{|B_{T_{L,k}}(x,2R)|}{|B_{T_{L,k}}(x,R)|}=2^k+o(1).$$ Thus no uniform doubling constant below $2^k$ is possible, and the counting bound of [Theorem 15](#thm-occ-lower) approaches the natural fraction $2^{-k}m$ on these local radii. The explicit constant $(5k)^{-k}$ is chosen only for a short all-radii proof.
:::

::: {#cor-no-exp-occ .exhibit .exhibit--corollary data-exhibit-type="corollary" data-exhibit-name="Corollary 22 (No expansion-only one-shot theorem)"}
**Corollary 22** (No expansion-only one-shot theorem). *For every $\delta>0$, there is no implication of the form $$h(G)\ge |G|^{-\delta}
\quad\Longrightarrow\quad
\operatorname{Occ}_R(G)\le |G|^{1-\varepsilon}
\text{ for some radius $R$}$$ with any fixed $\varepsilon>0$, even when the maximum degree is bounded by a constant depending only on $\delta$.*
:::

::: proof
*Proof.* Take the family from [Theorem 20](#thm-full-window). It lies in the prescribed expansion window, while $\operatorname{Occ}_R(G)=\Omega_\delta(|G|)$ for every $R$. ◻
:::

::: {#rem-architectural-meaning .exhibit .exhibit--remark data-exhibit-type="remark" data-exhibit-name="Remark 23 (Architectural meaning)"}
*Remark 23* (Architectural meaning). The logical obstruction is not that tori are difficult pursuit instances; they are not. Rather, [Theorem 15](#thm-occ-lower) makes every vertex-transitive bounded-doubling graph expensive for one-shot occupation, and bounded doubling is compatible with every polynomial weak-expansion window by [Theorem 20](#thm-full-window). The tori certify that the hypothesis class contains such graphs while coordinate-wise shadowing still uses exactly $k+1$ cops. Therefore ball amplification is the wrong invariant for adaptive pursuit, not merely a poor description of one particular easy family. The cubic family $Q_L$ records that the same separation already occurs in maximum degree three at exponent $1/2$.
:::

# Adaptive multistage transfer for fixed-degree bases {#adaptive-multistage}

The barrier of the previous section rules out one-shot occupation as a
universal mechanism, and [Theorem 3](#thm-abstract-transfer) carries a factor
$\log(ePN)$ even where it applies.  This section transfers an adaptive
strategy instead.  Prałat and Wormald proved Meyniel's conjecture for
random graphs through a deterministic multistage theorem
[@PralatWormald, Theorem 4.1]: successive fresh teams of cops, with geometrically
decreasing budgets, cover most of each sphere the robber must cross, and a
final team finishes by a Hall matching.  Their phase argument is used here
without change and is theirs throughout; the contribution of this section
is the lifting.  Randomly placed cops become squads that fill whole fibers,
deadlines are recomputed from the distortion bounds, and the accessibility
hypothesis is read five base layers early, which pays for the additive
metric error.  The result is a bound $C_dP\sqrt N$ with no logarithm and no
dependence on the scale $\lambda$ in the cop count.  Random
$(d+1)$-regular bases of fixed degree satisfy the strengthened hypothesis
with high probability, by reading intermediate levels of the reservoir
trees constructed in the companion paper [@PralatWormaldRegular].

## Multistage bases

For $V'\subseteq V(G)$ and $r\ge0$, let $S_G(V',r)$ be the set of vertices
at distance exactly $r$ from $V'$; $B_G(V',r)$ is the closed
$r$-neighborhood, as before.  Following [@PralatWormald, Section 4], a set
$U\subseteq V(G)$ is *$(t,c_1,c_2)$-accessible* if there are pairwise
disjoint sets $W(w)\subseteq B_G(w,t)$, one for each $w\in U$, with
$$
 |W(w)|\ge c_1\min\Bigl(d^{t},\frac{c_2N}{|U|}\Bigr).
$$
A cop starting anywhere in $W(w)$ reaches $w$ within $t$ moves, and
disjointness lets distinct targets draw on distinct cops.

::: {#def-multistage-base .exhibit .exhibit--definition data-exhibit-type="definition" data-exhibit-name="Definition 24 (Multistage base)"}
**Definition 24** (Multistage base).
Let $d\ge2$ and $s\ge0$ be integers, let $a_0\ge0$, and let
$\delta,J,a_1,\ldots,a_5>0$.
A connected graph $G$ on $N$ vertices is an
$(s;d,\delta,J,a_0,\ldots,a_5)$-*multistage base* if there is a set
$X\subseteq V(G)$ with $|X|\le a_0\sqrt N$ such that:

- [**(H1)**]{#multistage-h1} for all $v\in V(G)\setminus X$, all $r,r'\ge1$ with
  $d^{r}<N^{1/2+\delta}$ and $d^{r'}<N^{1/2+\delta}$, and all
  $V'\subseteq B_G(v,r)\setminus X$ with $|V'|=k$ and $kd^{r'}\le N/(\log N)^J$,
  $$
   a_1kd^{r'}\le|S_G(V',r')|\le a_2kd^{r'};
  $$

- [**(H2)**]{#multistage-h2} for all $r,r'$ with
  $N^{1/4-\delta}<(d+1)d^{r}<N^{1/4+\delta}$ and
  $N^{1/4-\delta}<(d+1)d^{r'}<N^{1/4+\delta}$, all $v\in V(G)\setminus X$,
  all $A\subseteq S_G(v,r)\setminus X$ with $|A|>N^{1/4-\delta}$, and
  $U=\bigcup_{a\in A}S_G(a,r')$ with $d^{r+r'}<a_3N/|U|$, there is
  $Q\subseteq V(G)$ with $|S_G(a,r')\cap Q|<N^{1/4-2\delta}$ for every
  $a\in A$ such that $U\setminus Q$ is
  $(r+r'+1-s,\,a_4,\,a_5)$-accessible;

- [**(H3)**]{#multistage-h3} $G-X$ is contained in one component of $G$.

:::

For $s=0$ these are exactly the hypotheses of [@PralatWormald, Theorem 4.1], whose
conclusion is $c(G)=O(\sqrt N)$ when $d<(\log N)^J$.  Increasing $s$
strengthens [(H2)](#multistage-h2): the reservoirs must sit $s$ layers closer to their
targets.  The case $s=5$ is what a projection consumes.

::: {#thm-multistage .exhibit .exhibit--theorem data-exhibit-type="theorem" data-exhibit-name="Theorem 25 (Fibered multistage transfer)"}
**Theorem 25** (Fibered multistage transfer).
Fix an integer $d\ge2$ and constants $a_0\ge0$ and
$\delta,J,a_1,\ldots,a_5>0$.  There are $C$ and $N_0$ such that the following holds
for every $N\ge N_0$.  Let $G$ be a $(5;d,\delta,J,a_0,\ldots,a_5)$-multistage base
on $N$ vertices, and let $H$ admit a $(\lambda,P)$-occupation projection
onto $G$ for some $\lambda\ge1$ and $P\ge1$.  Then
$$
 \boxed{c(H)\le CP\sqrt N,}
$$
and the displayed cops capture the robber within
$(\lceil(J+2)\log\log N\rceil+2)\,PN$ robber moves.  The constant $C$
depends only on $d$ and the listed constants; it depends neither on
$\lambda$ nor on $P$.

:::

The identity projection $\lambda=P=1$ returns the source's theorem under a
stronger hypothesis than it needs.  The scale $\lambda$ enters the deployment
and escape deadlines, while the stated cop-count and capture-time bounds
are independent of it.  The factor $\log(ePN)$ of
[Theorem 3](#thm-abstract-transfer) is gone.

::: {#rem-attribution .exhibit .exhibit--remark data-exhibit-type="remark" data-exhibit-name="Remark 26 (Attribution)"}
*Remark 26* (Attribution).
The proof below is the proof of [@PralatWormald, Theorem 4.1] with a fixed list of
substitutions, and every probabilistic estimate in it is theirs: the radius
schedule (4.1), the vulnerability threshold (4.3), the union bound over
robber strategies, the claim that each team restores vulnerability, and
the finishing Hall argument are used unchanged.  New are
[Lemma 27](#lem-shadow) and [Lemma 28](#lem-squad), the deadline comparison that fixes $s=5$, the
scaling of the exceptional guards and the clean-up team by $P$, and the
ball-shaped finishing set.  [Proposition 29](#prop-early) is likewise a reading of
intermediate levels of the tree family in [@PralatWormaldRegular]; its
contribution is the level shift, disjointness at the shifted level, and a
repaired exceptional set.

:::

## Two lifting lemmas

::: {#lem-shadow .exhibit .exhibit--lemma data-exhibit-type="lemma" data-exhibit-name="Lemma 27 (Lazy shadows and exit times)"}
**Lemma 27** (Lazy shadows and exit times).
Let $\pi:V(H)\to V(G)$ be a $(\lambda,P)$-occupation projection.

- **(i)** Every edge of $H$ lies inside one fiber or joins fibers over adjacent
  base vertices.  Consequently the shadow $\pi(\rho_0),\pi(\rho_1),\ldots$ of
  any walk in $H$ is a lazy walk in $G$.

- **(ii)** If a walk starts in $F_u$ and its shadow first lies in $S_G(u,r)$
  after the $m$-th step, then $m\ge\lambda(r-1)+1$, and all earlier shadows
  lie in $B_G(u,r-1)$.

:::

::: proof
*Proof.*

If $x\in F_u$ and $y\in F_v$ are adjacent with $u\ne v$, the lower
distortion bound gives $\lambda(\operatorname{dist}_G(u,v)-1)+1\le1$, so
$\operatorname{dist}_G(u,v)=1$.  This proves (i).  For (ii), the shadow moves by at most
one base step per move, so it passes through every smaller distance before
reaching distance $r$, and the lower distortion bound applied to the
endpoints gives $m\ge\operatorname{dist}_H(\rho_0,\rho_m)\ge\lambda(r-1)+1$.

◻
:::

::: {#lem-squad .exhibit .exhibit--lemma data-exhibit-type="lemma" data-exhibit-name="Lemma 28 (Squad deployment)"}
**Lemma 28** (Squad deployment).
Let $\pi$ be a $(\lambda,P)$-occupation projection, let $t\ge0$, and let
$\{W(w):w\in U'\}$ be pairwise disjoint subsets of $V(G)$ with
$W(w)\subseteq B_G(w,t)$.  Fix a representative $z^*\in F_z$ for every
$z\in V(G)$.  Let $Z\subseteq V(G)$ contain each base vertex independently
with probability $p$, and place a *squad* of $P$ cops on $z^*$ for
each $z\in Z$.  Then:

- **(i)** assigning to each $w\in U'$ with $W(w)\cap Z\ne\varnothing$ the squad
  at the first element of $W(w)\cap Z$, in a fixed order of $V(G)$, is
  injective;

- **(ii)** if a squad based at $z$ is assigned to $w$, and $|F_w|$ of its
  members are sent to the distinct vertices of $F_w$ while the remaining
  $P-|F_w|$ stay idle, then after at most $\lambda(t+2)-2$ cop moves every
  vertex of $F_w$ is occupied, and the squad can hold $F_w$ for as long as
  required;

- **(iii)** the events $E_w=\{W(w)\cap Z=\varnothing\}$, $w\in U'$, are mutually
  independent, and $\Pr(E_w)=(1-p)^{|W(w)|}\le e^{-p|W(w)|}$.

:::

::: proof
*Proof.*

Part (i) is disjointness of the reservoirs.  For (ii), if $z\ne w$ then
each dispatched member travels along a shortest path of length at most
$\lambda(\operatorname{dist}_G(z,w)+2)-2\le\lambda(t+2)-2$ by the upper distortion bound;
if $z=w$, the fiber-diameter bound gives at most
$2(\lambda-1)\le\lambda(t+2)-2$.  Cops may share vertices, so the members
do not obstruct one another, and once in place they stay.  Part (iii) holds
because the reservoirs are disjoint sets of independent coordinates.

◻
:::

The lemma is the reason the transfer costs no logarithm: a squad is one
Bernoulli trial at the source's base density, so the probability that a
reservoir delivers a squad equals the probability that it delivered a
single cop in [@PralatWormald].  Filling a fiber of order up to $P$ multiplies the
number of cops by $P$ and leaves every failure probability unchanged.

## Proof of [Theorem 25](#thm-multistage)

::: proof
*Proof.*

Throughout, $d$, $\delta$, $J$ and $a_0,\ldots,a_5$ are fixed, $N$ is
large, and the game is played on $H$ with the cops moving first.  We
follow the proof of [@PralatWormald, Theorem 4.1] step by step, citing its
displayed equations by their numbers there.

*Placement.*
The cops first occupy every vertex of $\pi^{-1}(X)$ permanently, using at
most $P|X|\le a_0P\sqrt N$ cops; the robber never enters $\pi^{-1}(X)$, and
every set of base vertices below excludes $X$.  Let $F=J+2$ and
$i_f=\lceil F\log\log N\rceil$.  For $1\le i\le i_f$ let $Z_i\subseteq V(G)$
be independent random sets in which each base vertex appears independently
with probability $c_i/N$, where $c_i=Ce^{-i}\sqrt N$ for $i<i_f$ and
$c_{i_f}=\sqrt N$; here $C\ge1$ is a constant fixed below.  Team $i$
consists of one squad of $P$ cops at $z^*$ for each $z\in Z_i$, as in
[Lemma 28](#lem-squad).  A clean-up team of $PN^{1/3}$ further cops is placed
anywhere.  All cops are placed before the robber chooses her start
$\rho_1\in V(H)\setminus\pi^{-1}(X)$; she sees every cop and knows the
strategy.  By the Chernoff bound, with probability $1-o(1)$ every team $i$
has at most $2c_i$ squads, so the total number of cops is at most
$$
 a_0P\sqrt N+2P\sqrt N\Bigl(C\sum_{i\ge1}e^{-i}+1\Bigr)+PN^{1/3}
 \le(a_0+2C+3)P\sqrt N.
$$
It remains to show that, with probability $1-o(1)$ over the placement, the
cops have a winning strategy against every robber strategy; a placement of
the displayed size then exists.

*Radii and rounds.*
Let $r_1,\ldots,r_{i_f+1}$ be the radii of [@PralatWormald, (4.1)], defined from
$N$, $d$ and a small constant $\varepsilon_0$ chosen below.  They satisfy
[@PralatWormald, (4.2)], namely $d^{r_i}=\Omega(N^{1/4}/d)$ and
$d^{r_i}=O(e^{2i}N^{1/4})$, and $d^{r_{i}+r_{i+1}}$ lies between
$\varepsilon_0e^{2i}\sqrt N/d$ and $\varepsilon_0e^{2i}\sqrt N$.  Since $d$ is fixed and
$e^{2i}\le(\log N)^{2F}$, every pair $r_i,r_{i+1}$ with $i\le i_f$ lies in
the window of [(H2)](#multistage-h2) for large $N$.

Let $v_i$ be the robber's shadow at the start of round $i$; then
$v_i\notin X$.  Round $i$ ends at the robber's first move whose shadow lies
in $S_G(v_i,r_i)$, and $v_{i+1}$ is that shadow.  By [Lemma 27](#lem-shadow), the
round lasts at least $\lambda(r_i-1)+1$ robber moves, during which the
shadow stays in $B_G(v_i,r_i-1)$.

*Waiting and reversal.*
At the start of each round the clean-up team assigns one cop to each vertex
of $\pi^{-1}(B_G(v_i,r_i)\setminus X)$ and walks there.  By [(H1)](#multistage-h1) with
$k=1$ and by (4.2), this set has at most
$P(1+2a_2d^{r_i})\le PN^{1/4}(\log N)^{2F+1}\le PN^{1/3}$ vertices, and each
cop arrives within $PN$ moves because $H$ is connected on at most $PN$
vertices.  A robber whose shadow is still in $B_G(v_i,r_i-1)$ after $PN$
moves stands on an occupied vertex, so every round lasts at most $PN$
robber moves.  Reversal inside the current ball is waiting, and reversal
after a round has ended is movement within the next round; the round
structure is insensitive to it.

*Vulnerable positions.*
Team $i$ is dispatched at the start of round $i$, with destinations chosen
from $v_i$ and the uncovered set $S_{i-1}$ defined next, and it has rounds
$i$ and $i+1$ to arrive.  Let $S_0=S_G(v_1,r_1)\setminus X$, and for
$i\ge1$ let
$$
 S_i=\bigl\{\,w\in S_G(v_{i+1},r_{i+1})\setminus X:\ \text{no squad of
 team $i$ is assigned to }F_w\,\bigr\}.
$$
Call $v_i$ *vulnerable* if $|S_{i-1}|\le e^{-5(i-1)}|S_G(v_i,r_i)|$,
which is [@PralatWormald, (4.3)]; $v_1$ is vulnerable.  The robber sees the cops,
so $S_{i-1}$ depends on her earlier choices as well as on the samples.  As
in [@PralatWormald, p. 13], a robber strategy to round $i$ is a sequence
$(u_1,\ldots,u_i)$ of base vertices that she can feasibly realize as
$(v_1,\ldots,v_i)$; there are at most $N^{i}$ of them, the strategy of team
$i$ is defined for each, and it depends on the robber only through
$(v_1,\ldots,v_i)$, because squads are placed at base vertices.

*The squad form of Claim 4.2.*
Fix $i<i_f$, a vulnerable $v_i$, and a possible $S_{i-1}$ with
$|S_{i-1}|>e^{-5(i_f-1)}|S_G(v_i,r_i)|$.  We claim that, with probability
$1-O(N^{-\log N})$ over $Z_i$, team $i$ can be assigned so that $v_{i+1}$
is vulnerable whatever the robber does.

Put $A=S_{i-1}$, $r=r_i$, $r'=r_{i+1}$ and $U=\bigcup_{a\in A}S_G(a,r')$.
The hypotheses of [(H2)](#multistage-h2) hold by the source's verification, which uses
base quantities only: $v_i\notin X$ and $A\subseteq S_G(v_i,r_i)\setminus X$
by construction; $|A|>N^{1/4-\delta}$ from
$|S_{i-1}|>e^{-5i_f}a_1d^{r_i}$ and (4.2); and, by [(H1)](#multistage-h1) with $k=1$,

::: {#eq-u-bound}
$$
|U|\le|S_{i-1}|\,a_2d^{r'}\le e^{-5(i-1)}a_2^2d^{r+r'},
 \qquad
 |U|\,d^{r+r'}\le a_2^2\varepsilon_0^2e^{5-i}N<a_3N\tag{7}
$$
:::

once $\varepsilon_0$ is small, using $d^{r+r'}\le\varepsilon_0e^{2i}\sqrt N$; this is
[@PralatWormald, (4.4)].  Hence [(H2)](#multistage-h2) supplies $Q$ and pairwise disjoint
reservoirs $W(w)\subseteq B_G(w,r+r'-4)$, $w\in U\setminus Q$, with

::: {#eq-reservoir}
$$
|W(w)|
 \ge a_4\min\Bigl(d^{r+r'-4},\frac{a_5N}{|U|}\Bigr)
 \ge\kappa\,e^{2i}\sqrt N,
 \qquad
 \kappa=a_4\min\Bigl(\varepsilon_0d^{-5},\ \frac{a_5}{a_2^2\varepsilon_0e^{5}}\Bigr),\tag{8}
$$
:::

by the lower part of (4.1) and by [(7)](#eq-u-bound).  The source's
estimate at radius $r+r'+1$ is the same with $d^{-5}$ removed; this factor
is the entire cost of the early radius.

Apply [Lemma 28](#lem-squad) with $t=r+r'-4$, $Z=Z_i$ and $p=c_i/N$.  Each
$w\in U\setminus Q$ with $W(w)\cap Z_i\ne\varnothing$ receives its own
squad, and
$$
 \Pr(E_w)\le\exp\bigl(-Ce^{-i}\sqrt N\cdot\kappa e^{2i}\sqrt N/N\bigr)
 =\exp(-C\kappa e^{i})\le\tfrac12e^{-5i}
$$
for all $i\ge1$ once $C\ge6/(e\kappa)$.  We fix
$C=\lceil6/(e\kappa)\rceil$, which has the form $C_0d^{5}$ with
$C_0=C_0(a_2,a_4,a_5,\varepsilon_0)$.  Fix $u\in A$ and let
$H_u=S_G(u,r')\setminus Q$.  By [(H1)](#multistage-h1) with $k=1$ and by [(H2)](#multistage-h2),
$|S_G(u,r')|\ge a_1d^{r'}>a_1N^{1/4-\delta}/(d+1)$ and
$|S_G(u,r')\cap Q|<N^{1/4-2\delta}$, so $|H_u|\ge\tfrac12a_1d^{r'}$.  The
events $E_w$, $w\in H_u$, are independent, each of probability at most
$\tfrac12e^{-5i}$, so the number that occur is dominated by a binomial
variable of mean
$\mu=\tfrac12e^{-5i}|H_u|=\Omega(N^{1/4-\delta}(\log N)^{-5F})$, and the
Chernoff bound gives at most $\tfrac23e^{-5i}|H_u|$ of them with
probability $1-\exp(-\mu/27)=1-\exp(-\Omega(N^{1/4-2\delta}))$.  Since
$N^{1/4-2\delta}\le\tfrac13e^{-5i}|S_G(u,r')|$ for large $N$, all but an
$e^{-5i}$ fraction of $S_G(u,r')$ then receives a squad.  A union bound
over the at most $N$ choices of $u\in A$ gives the assignment with
probability $1-O(N^{-\log N})$.

Now let the robber end round $i+1$ at a vertex of $F_w$ with
$w\in S_G(v_{i+1},r_{i+1})\setminus X$, where $v_{i+1}=u\in A$.  By
[Lemma 27](#lem-shadow) this happens at her $m$-th move after the dispatch of
team $i$ with
$m\ge\lambda(r_i-1)+1+\lambda(r_{i+1}-1)+1=\lambda(r+r'-2)+2$, and the cops
then make their $(m+1)$-st move.  By [Lemma 28](#lem-squad)(ii) with
$t=r+r'-4$, a squad assigned to $F_w$ has occupied every vertex of $F_w$
after $\lambda(r+r'-2)-2\le m+1$ cop moves and has held it since; so the
robber is captured, on her own move if the squad arrived earlier and on the
next cop move otherwise.  Hence she can end round $i+1$ only at a vertex of
$S_i$, and $|S_i|\le e^{-5i}|S_G(v_{i+1},r_{i+1})|$: $v_{i+1}$ is
vulnerable.  The margin in the deadline is five cop moves for every
$\lambda$; for reservoirs at radius $r+r'+1-s$ the same comparison reads
$\lambda(5-s)\le5$, which is why the hypothesis takes $s=5$.

A union bound over the at most $N^{i}$ robber strategies to round $i$, and
then over $i<i_f$, as in [@PralatWormald, p. 13], shows that with probability
$1-o(1)$ all teams have such assignments, so every $v_i$ with $i\le i_f$ is
vulnerable.

*The finishing team.*
Team $i_f$ is dispatched at the start of the first round $i^*$ with
$|S_{i^*-1}|\le e^{-5(i_f-1)}|S_G(v_{i^*},r_{i^*})|$; by the above,
$i^*\le i_f$ with probability $1-o(1)$, and teams $i^*,\ldots,i_f-1$ are
not needed.  Put
$$
 r''=r_{i_f}+r_{i_f+1}-r_{i^*},
 \qquad
 \hat r=r_{i_f}+r_{i_f+1}+1,
 \qquad
 \hat t=\hat r-5,
 \qquad
 U_{\mathrm{fin}}=\bigcup_{u\in S_{i^*-1}}B_G(u,r'')\setminus X.
$$
Balls replace the spheres of [@PralatWormald, p. 14] because the robber may stay
still.  Since $r''\ge\min(r_{i_f},r_{i_f+1})\ge1$ and, by [(H1)](#multistage-h1),
$|B_G(u,r'')|\le1+2a_2d^{r''}$, the source's bound persists:

::: {#eq-ufin}
$$
|U_{\mathrm{fin}}|
 \le e^{-5(i_f-1)}a_2d^{r_{i^*}}\cdot3a_2d^{r''}
 \le3a_2^2e^{5}\varepsilon_0\,e^{-3i_f}\sqrt N .\tag{9}
$$
:::

Team $i_f$ must occupy all of $\pi^{-1}(U_{\mathrm{fin}})$.  By Hall's
theorem it suffices that every $V''\subseteq U_{\mathrm{fin}}$ with
$|V''|=k$ has at least $k$ squads of team $i_f$ based in
$B_G(V'',\hat t)$.  Apply [(H1)](#multistage-h1) with $v=v_{i^*}$, $r=\hat r-1$,
$r'=\hat t$ and $V'=V''$: indeed
$V''\subseteq B_G(v_{i^*},r_{i^*}+r'')\setminus X=B_G(v_{i^*},\hat r-1)\setminus X$,
the radii satisfy $d^{\hat r-1}\le\varepsilon_0e^{2i_f}\sqrt N<N^{1/2+\delta}$,
and
$kd^{\hat t}\le|U_{\mathrm{fin}}|d^{\hat r}=O(dNe^{-i_f})=O(N(\log N)^{-F})\le N/(\log N)^J$
by [(9)](#eq-ufin), (4.1) and $F=J+2$.  Hence
$$
 |S_G(V'',\hat t)|\ge a_1kd^{\hat t}
 \ge a_1\varepsilon_0d^{-5}\,k\sqrt N\,(\log N)^{2F},
$$
using $d^{\hat t}=d^{-4}d^{r_{i_f}+r_{i_f+1}}\ge\varepsilon_0d^{-5}e^{2i_f}\sqrt N$.
The number of squads of team $i_f$ based in $S_G(V'',\hat t)$ is binomial
with mean at least $a_1\varepsilon_0d^{-5}k(\log N)^{2F}\ge k(\log N)^2$ for
large $N$, so it is smaller than $k$ with probability at most
$\exp(-k(\log N)^2/8)$.  Summing over $k$ and over the at most $N^{k}$
sets $V''$ of order $k$ gives failure probability $O(e^{-(\log N)^2/9})$,
and a union bound over the $N^{O(i_f)}$ feasible pairs
$(v_{i^*},S_{i^*-1})$ leaves probability $1-o(1)$.  A system of distinct
representatives therefore gives every $w\in U_{\mathrm{fin}}$ its own squad
based within base distance $\hat t$ of $w$, and by [Lemma 28](#lem-squad)(ii)
that squad occupies all of $F_w$ within
$\lambda(\hat t+2)-2=\lambda(r_{i^*}+r''-2)-2$ cop moves after dispatch.

Let $T=\lambda(r_{i^*}+r''-2)+2$.  If the robber ends round $i^*$ at her
$m$-th move after dispatch with $m\le T$, then $m\ge\lambda(r_{i^*}-1)+1$
by [Lemma 27](#lem-shadow), so $T-m\le\lambda(r''-1)+1$, and by the same lemma
her shadow at move $T$ lies in $B_G(v_{i^*+1},r'')\setminus X\subseteq U_{\mathrm{fin}}$;
at the following cop move every vertex of $\pi^{-1}(U_{\mathrm{fin}})$ is
occupied and she is captured.  If she has not ended round $i^*$ by move
$T$, the finishing squads are already in place and hold their fibers, so
she is captured on entering $F_{v_{i^*+1}}\subseteq\pi^{-1}(U_{\mathrm{fin}})$;
and if she never ends the round, the clean-up team captures her.  This
completes the proof, with $C=C_0d^{5}$ and at most $(i_f+2)PN$ robber
moves.

◻
:::

## Early accessibility for random regular bases

Write $\mathcal G_{N,d+1}$ for the uniform random $(d+1)$-regular graph on
$N$ vertices; the branching parameter is $d$, matching [@PralatWormaldRegular].
Prałat and Wormald verify the hypotheses of their Theorem 4.1 for
$\mathcal G_{N,d+1}$ with $X=\varnothing$ [@PralatWormaldRegular, Lemma 3.2], and
their proof of accessibility constructs a family of disjoint trees rooted
at the targets whose every level is bounded from below, not only the top
level.  Reading the level $s$ layers below the top gives accessibility $s$
layers early.

::: {#prop-early .exhibit .exhibit--proposition data-exhibit-type="proposition" data-exhibit-name="Proposition 29 (Early accessibility)"}
**Proposition 29** (Early accessibility).
Fix an integer $d\ge2$, a constant $0<\delta<1/32$, an integer $s\ge1$, and
$0<c_1<2/5$.  With probability $1-o(1)$, $G\in\mathcal G_{N,d+1}$ is
disconnected or has the following property.  For all $r,r'$ with
$N^{1/4-\delta}<(d+1)d^{r}<N^{1/4+\delta}$ and
$N^{1/4-\delta}<(d+1)d^{r'}<N^{1/4+\delta}$, every $v\in V(G)$, every
$A\subseteq S_G(v,r)$ with $|A|>N^{1/4-\delta}$, and
$U=\bigcup_{a\in A}S_G(a,r')$ with $d^{r+r'}<N/(9|U|)$, there is a set
$Q''\subseteq V(G)$, determined by $(G,v,r,r',s)$ and not by $A$, with
$|Q''|\le N^{5\delta}$, such that $U\setminus Q''$ is
$(r+r'+1-s,\,c_1,\,1/9)$-accessible.

:::

For $s=0$ and $c_1=2/5$ this is [@PralatWormaldRegular, Lemma 3.2(iii)], with the
exceptional set $Q$ of that proof.  The proof below reads intermediate
levels of the same tree family on the same probability event, so the
statement holds for all fixed $s$ simultaneously; the shallow exclusion
$B_G(v,s-1)$ is the only place where $s$ enters the exceptional set.

::: proof
*Proof.*

We use the objects constructed in the proof of
[@PralatWormaldRegular, Lemma 3.2(iii)], arXiv v2, pp. 16–24, with their
probability estimates, citing by page.  Fix $v$, $r$, $r'$.  Write
$L_i=S_G(v,i)$ and $t_{\mathrm s}=\lfloor\log_d\log^{12}N\rfloor$, and let
$U_0=\bigcup_{u\in S_G(v,r)}S_G(u,r')$, so that $U\subseteq U_0$ for every
$A$.

*Inherited objects.*
The graph is exposed from $v$ in the pairing model, and a pair is
*bad* when its second point lands in an already exposed vertex
(p. 11).  Phase 2 (p. 17) places $w\in U_0$ into $Q$ exactly when the tree
$T_{t_{\mathrm s}}(w)$ of descendants of $w$ to depth $t_{\mathrm s}$ meets
a bad pair; for $w\notin Q$ that tree is a perfect $d$-ary tree, and two
such trees rooted in the same $L_i$ are disjoint (p. 18).  Phase 3
(pp. 18–20) grows, for each $w\in\hat U_0=L_{r+r'}\setminus Q$, a tree
$\tilde T(w)$ of height $i_0=t_0-r-r'$ whose level $i$ has at least
$(1-\varepsilon_i)d^{i}$ vertices with $\varepsilon_i=o(1)$, and Property 3.3 (p. 20)
makes these trees pairwise disjoint.  Sub-lemma 3.4 (pp. 20–21) extends
them, for any $U^*\subseteq\hat U_0$ with $|U^*|<N/(9d^{r+r'})$, keeping
them disjoint, so that for every $1\le i\le r+r'+1$ the level $i$ of
$\tilde T(w)$ has at least $\tfrac25\min(d^{i},N/(9|U^*|))$ vertices; the
bound is stated for every level.  Finally, for $j\ge0$ let
$R_j=L_{r+r'-j}\cap U_0\setminus Q$.  The mixed-depth argument
(pp. 23–24) grows from each $w\in R_j$ a bad-pair-free tree $T(w)$ up to
$L_{r+r'}$, disjoint for distinct $w$ of the same level, with root set
$F(w)=V(T(w))\cap L_{r+r'}$ of order $(1-o(1))d^{j}$; with
$\tilde U=\bigcup_wF(w)$ and $\tilde U_j$ the roots whose least such $j$
equals $j$, it asserts its (3.19): pairwise disjoint extensions
$\tilde T(v')$, $v'\in\tilde U$, such that for $v'\in\tilde U_j$ the height
is $r+r'+1-j$ and every level $1\le i\le r+r'+1-j$ has at least
$\tfrac25\min(d^{i},Nd^{-j}/(9|U|))$ vertices.  The source obtains its
reservoirs from the top levels of these trees.  The source grows the trees
$T(w)$ only for $w\in U\setminus Q$; growing them from every vertex of
$L_{r+r'-j}\cap U_0\setminus Q$ changes nothing, since they are subtrees of
the exposure pruned at bad pairs, and all of them are determined by
$(G,v,r,r')$.

*The exceptional set.*
The source asserts $F(w)\cap Q=\varnothing$ without proof.  Let
$Q^{\mathrm{anc}}$ be the set of $w\in U_0\setminus Q$ with
$F(w)\cap Q\ne\varnothing$, and put
$$
 Q''=Q\cup Q^{\mathrm{anc}}\cup B_G(v,s-1).
$$
Phase 2 records more than its displayed conclusion $|Q|=o(N^{5\delta})$
(p. 17): after $r+r'+t_{\mathrm s}$ rounds at most
$O(d^{r+r'+t_{\mathrm s}})=O(N^{1/2+2\delta}\log^{12}N)$ vertices carry
exposed points, at most $d$ times as many pairs are exposed, each is bad
with probability $O(N^{-1/2+2\delta}\log^{12}N)$, so by its (3.11) the
number of bad pairs is $O(dN^{4\delta}\log^{24}N)$ with probability
$1-o(N^{-3})$, and each bad pair eliminates at most
$|T_{t_{\mathrm s}}(w)|=O(d\log^{12}N)$ vertices $w$.  Hence
$|Q|=O(d^{2}N^{4\delta}\log^{36}N)$.  Since the trees $T(w)$ from one level
are disjoint, each $q\in Q\cap L_{r+r'}$ lies in $F(w)$ for at most one $w$
per level, so $|Q^{\mathrm{anc}}|\le(r+r'+1)|Q|=O(d^{2}N^{4\delta}\log^{37}N)$.
With $|B_G(v,s-1)|\le3d^{s-1}$ and $d$ fixed, $|Q''|\le N^{5\delta}$ for
large $N$, and $Q''$ depends on $(G,v,r,r',s)$ only.

*Reservoirs.*
Put $t=r+r'+1-s$.  Let $w\in U\setminus Q''$, let $\ell=\operatorname{dist}_G(v,w)$ and
$j=r+r'-\ell$, so that $w\in R_j$ and, since $w\notin B_G(v,s-1)$,
$h:=t-j=\ell+1-s\ge1$.  Define
$$
 W(w)=\bigcup_{v'\in F(w)}L_h\bigl(\tilde T(v')\bigr),
$$
the union of the level-$h$ sets of the trees rooted at $F(w)$; these trees
exist because $w\notin Q^{\mathrm{anc}}$.  Each $v'\in F(w)$ is at depth
$j$ in $T(w)$, and each vertex of $L_h(\tilde T(v'))$ is at tree distance
$h$ from $v'$, so $W(w)\subseteq B_G(w,j+h)=B_G(w,t)$.  For disjointness,
the trees $\tilde T(v')$, $v'\in\tilde U$, are pairwise disjoint and each
vertex has one height in its tree, so the global level sets
$\mathcal L_h=\bigcup_{v'}L_h(\tilde T(v'))$ are disjoint for distinct
$h$.  If $w_1,w_2\in U\setminus Q''$ have
$\operatorname{dist}_G(v,w_1)\ne\operatorname{dist}_G(v,w_2)$ then $h_1\ne h_2$ and
$W(w_1)\cap W(w_2)=\varnothing$; if the distances agree, then
$F(w_1)\cap F(w_2)=\varnothing$ and distinct roots have disjoint trees.
This is the source's disjointness argument (p. 24) with the height
$r+r'+1-j$ replaced by $t-j$; it uses no alignment of tree height with
distance from $v$.  For the size, a root $v'\in F(w)$ lies in
$\tilde U_{j'}$ with $j'\le j$, its tree has height $r+r'+1-j'\ge h$, and
(3.19) at level $h$ gives
$$
 |L_h(\tilde T(v'))|
 \ge\tfrac25\min\Bigl(d^{h},\frac{Nd^{-j'}}{9|U|}\Bigr)
 \ge\tfrac25\,d^{-j}\min\Bigl(d^{t},\frac{N}{9|U|}\Bigr).
$$
Summing over the $(1-o(1))d^{j}$ roots,
$|W(w)|\ge\tfrac25(1-o(1))\min(d^{t},N/(9|U|))\ge c_1\min(d^{t},N/(9|U|))$
for large $N$.

*Probability.*
Nothing new is random.  The sets $W(w)$ are sub-level-sets of the family
whose existence the source establishes with probability
$1-o(2^{-N^{1/4+\delta}}/N^{4})$ for each $(v,A)$ given the exposed
subgraph, and with probability $1-o(N^{-3})$ for the exposed subgraph,
before its union bound over $v$, $r$, $r'$ and the $2^{N^{1/4+\delta}}$
sets $A$ (p. 20).  The proposition therefore holds on the same event as the
source's lemma.

◻
:::

::: {#cor-regular .exhibit .exhibit--corollary data-exhibit-type="corollary" data-exhibit-name="Corollary 30 (Random regular bases)"}
**Corollary 30** (Random regular bases).
Fix an integer $d\ge2$.  There is a constant $C_d$ such that, with
probability $1-o(1)$, $G\in\mathcal G_{N,d+1}$ has the following property:
for every $\lambda\ge1$, every $P\ge1$, and every graph $H$ admitting a
$(\lambda,P)$-occupation projection onto $G$,
$$
 \boxed{c(H)\le C_dP\sqrt N.}
$$

:::

::: proof
*Proof.*

Take $\delta=1/40$, $J=2$ and $X=\varnothing$.  Random $(d+1)$-regular
graphs are connected with probability $1-o(1)$ for $d+1\ge3$
[@PralatWormaldRegular, Section 3], which gives [(H3)](#multistage-h3) and removes the
disconnected alternative in [Proposition 29](#prop-early).  Regularity gives
$|S_G(V',r')|\le k(d+1)d^{r'-1}\le2kd^{r'}$, so $a_2=2$.  The lower bound
of [(H1)](#multistage-h1) with $a_1=1/10$ is [@PralatWormaldRegular, Lemma 3.2(ii)], which
holds with probability $1-o(1)$ for all $k=O(N^{1/2+\delta})$, all $V'$ of
order $k$, and all $r'$ with $k(d+1)d^{r'-1}\le N/\log N$; the constraint
$kd^{r'}\le N/(\log N)^2$ in [(H1)](#multistage-h1) implies this, and
$k\le|B_G(v,r)|<3d^{r}=O(N^{1/2+\delta})$.  [Proposition 29](#prop-early) with $s=5$
and $c_1=1/3$ gives [(H2)](#multistage-h2) with $a_3=a_5=1/9$ and $a_4=1/3$, since
$|S_G(a,r')\cap Q''|\le N^{5\delta}<N^{1/4-2\delta}$.  Hence, with
probability $1-o(1)$, $G$ is a
$(5;d,\tfrac1{40},2,0,\tfrac1{10},2,\tfrac19,\tfrac13,\tfrac19)$-multistage
base, and [Theorem 25](#thm-multistage) applies to every $H$ projecting onto it.

◻
:::

::: {#rem-multistage-scope .exhibit .exhibit--remark data-exhibit-type="remark" data-exhibit-name="Remark 31 (Scope of the adaptive transfer)"}
*Remark 31* (Scope of the adaptive transfer).
[Theorem 25](#thm-multistage) does not supersede [Theorem 3](#thm-abstract-transfer), and
it does not change the estimates of [Theorem 10](#thm-hardfamily).  The hard family
has base degree $d=(\log N)^4$ growing with $N$ and base $G(N,p)$, whereas
[Corollary 30](#cor-regular) concerns fixed $d$ and random regular bases; early
accessibility is derived here only for the latter, and for growing $d$ the
team constant $C_0d^{5}$ and the finishing estimate would require a larger
$F$, which we do not pursue.  What the theorem removes is the factor
$\log(ePN)$, for fixed-degree bases and under the stronger hypothesis
[(H2)](#multistage-h2).  Neither route approaches $\sqrt{|V(H)|}$ when $P$ grows, since
$P\sqrt N$ exceeds $\sqrt{PN}$ by $\sqrt P$.  Random regular graphs already
satisfy Meyniel; the content of [Corollary 30](#cor-regular) is robustness of the
square-root bound under every coarse projection of the base, including the
HMGHM tower of [Theorem 6](#thm-metric).

:::

# Outlook

For vertex expansion $h(G)\ge\phi$, iterating the elementary growth factor
$1+\phi$ reaches global scale after $O(\phi^{-1}\log |G|)$ layers.  The same
iteration gives the standard diameter bound of that order; these are two
forms of the same calculation, not independent evidence.  When
$\phi=|G|^{-a}$, this supplies an $O(|G|^a\log|G|)$ upper bound on the
number of layers needed to reach global scale.  It does not establish a
necessary pursuit timescale: for example, the fixed-dimensional tori above
have $h(G)=\Theta(|G|^{-1/k})$ and diameter $\Theta(|G|^{1/k})$, without
the extra logarithm.

The present paper separates four phenomena:

- **(1)** bounded normalized metric distortion preserves a strong occupation
  certificate through degree reduction;

- **(2)** the HMGHM stressing family has an upper bound within a polylogarithmic
  factor of the square-root scale;

- **(3)** one-shot occupation is nevertheless incapable of proving a universal
  robustness theorem throughout any polynomial weak-expansion window, even on
  bounded-degree graphs with constant cop number; a cubic instance already
  appears at exponent $1/2$;

- **(4)** the adaptive multistage strategy of Prałat and Wormald transfers
  through every coarse projection of a fixed-degree base with sphere growth
  and early accessibility, without the logarithm or scale dependence in the
  cop count.

The multistage transfer consumes four quantitative inputs: reservoir sizes,
exceptional fractions, frontier contraction, and the final Hall expansion.
Extracting the weakest such conditions the proof actually uses, and asking
which weaker geometric assumptions supply them, is the concrete route from
[the adaptive multistage transfer section](#adaptive-multistage) toward shrinking expansion; expansion alone is not
known to suffice.  The remaining universal question is therefore an adaptive one.  On the tori,
ball growth carries essentially no information about pursuit cost; product
structure instead supports coordinate-wise shadowing.  What geometric or
combinatorial quantity replaces product coordinates on a general
polynomially weak expander?  Equivalently, can a capacitated, correlated, or
deferred witness system reuse the same cop resources over polynomially many
weak-growth layers, or must every such one-traversal certificate incur
polynomial congestion?

# Acknowledgments

The author is grateful to Anthony Clow, Peter Bradshaw, Bojan Mohar, and Florian Lehner for work and perspectives that helped shape the questions addressed here. Additional acknowledgments will be added in a later version. The author welcomes corrections concerning priority, related graph-substitution inequalities, and the scope of the occupation framework.

# Audit and reproducibility

The September 5, 2026 audit revision gave a direct cloud-product proof of
$O(D^2(\log D)^2)$ and completed the core and metric proofs.  It also
distinguished the upper bound from two-sided polylogarithmic tightness and
removed an unsupported traversal-time necessity claim.  The subsequent
literature revision applies the connected-cloud cut estimate once to the
final ancestry fibers, improving the expansion denominator from
$CD^4(\log D)^5$ to $CD^3(\log D)^2$.  It also records the quantitative
scope of the threshold proof in the inspected HMGHM preprint.

The September 6, 2026 revision adds [the adaptive multistage transfer section](#adaptive-multistage).  Its phase
argument is inherited from Prałat–Wormald's Theorem 4.1, and its
early-accessibility proposition reads intermediate levels of the tree
family in their random-regular proof on the same probability event; the
new steps are the squad lemma, the deadline comparison, the ball-shaped
finishing set, and the repaired exceptional set with its explicit size.
The original occupation theorem and the growing-degree hard-family
estimates are retained unchanged.  No computation accompanies the new
section.

The metric inequalities were independently tested on HMGHM towers rebuilt from the published gadget description, including structured base graphs not used in the original audit. The Hall inequalities and timing margins were checked numerically, and exact small replacement games were solved by retrograde analysis. The toroidal barrier audit computes exact ball profiles of $C_L^{\square k}$ by convolving cyclic distance distributions, verifies the $(5k)^k$ doubling bound for $k=2,3,4,5$, constructs $Q_L$, checks cubicity, connectivity, and the displayed rotation automorphism, and evaluates the counting lower bound at every radius. No theorem depends on the computations.
