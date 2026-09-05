---
title: "Ball-Occupation Certificates under Coarse Graph Projections"
subtitle: "Degree Reduction, Square-Root Hard Families, and Toroidal Barriers"
date: 2026-07-27
revised:
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
  alone cannot certify a universal robustness theorem.
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
  - date: "2026-09-05"
    note: "Corrected the cloud-product estimate and expansion loss, completed the core and metric proofs, and clarified upper-bound tightness and traversal-time claims. The subsequent literature revision sharpens connected-cloud expansion and qualifies the HMGHM transfer exponent."
  - date: "2026-07-27"

---

# Introduction and main conclusions

The multi-cop version of Cops and Robber was developed by Aigner and Fromme, who proved that three cops suffice on every planar graph [@AignerFromme]. Meyniel's conjecture asks whether every connected $n$-vertex graph has cop number $O(\sqrt n)$. The current best universal upper bound remains $$\frac{n}{2^{(1-o(1))\sqrt{\log_2 n}}},$$ proved independently by Lu–Peng and Scott–Sudakov [@LuPeng; @ScottSudakov]. Bose–Esperet–Hodor–Joret–Micek–Rambaud recently extended the same scale of bound from graph order to vertex-cover number [@BoseEsperetHodorJoretMicekRambaud]. Expansion is one of the principal settings in which polynomial savings are known: Bradshaw–Hosseini–Mohar–Stacho obtain weak Meyniel bounds from bounded-degree expansion restricted to sublinear set scales [@BradshawHosseiniMoharStacho], while Clow's withdrawn preprint developed a closely related structural program connecting failure of weak Meyniel to high-cop expanding examples [@Clow].

The motivation here is the effect of bounded-degree replacement gadgets on pursuit. The degree-reduction construction of Hosseini–Mohar–Gonzalez Hermosillo de la Maza (HMGHM) preserves lower bounds on cop number and produces subcubic graphs with cop number $M^{1/2-o(1)}$ [@HMG]. A natural converse question is whether a useful upper strategy on the base graph survives the replacement tower.

An arbitrary winning strategy does not lift transparently. Moving one step in the quotient may require a squad dispersed through a cloud to reorganize while the robber continues moving. The successful object is narrower and more stable: an *occupation certificate* that assigns distinct cops to all vertices of a region before the robber can leave it. Distance stretching slows both deployment and escape, and a bounded normalized additive error leaves a strict timing margin.

The first result is therefore stated for an abstract projection, rather than for the HMGHM gadget. The gadget enters only later, through an exact metric calculation. The resulting upper bound is stronger quantitatively than the notation $M^{1/2+o(1)}$ suggests: it is $\sqrt M$ times a polylogarithmic factor. By contrast, the available lower bound approaches the square-root exponent at the triple-logarithmic rate displayed in the abstract. These two facts should not be conflated merely because both can be written $M^{1/2+o(1)}$.

The final result marks the boundary of the mechanism. A one-shot occupation certificate needs polynomial ball amplification between radii $R$ and $2R$. Polynomially weak expansion alone does not supply this. For every fixed $k$, the Cartesian tori $C_L^{\square k}$ have bounded metric doubling, exact cop number $k+1$, and linear one-shot occupation cost at every radius. Taking $k>1/\delta$ puts these examples inside every window $h(G)\ge |G|^{-\delta}$. A separate cubic replacement retains the barrier at $\delta=1/2$. The obstacle in the universal problem is therefore not degree reduction itself; it is the need for adaptive reuse over many weak-growth layers.

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

# Outlook

For vertex expansion $h(G)\ge\phi$, iterating the elementary growth factor $1+\phi$ reaches global scale after $O(\phi^{-1}\log |G|)$ layers. The same iteration gives the standard diameter bound of that order; these are two forms of the same calculation, not independent evidence. When $\phi=|G|^{-a}$, this supplies an $O(|G|^a\log|G|)$ upper bound on the number of layers needed to reach global scale. It does not establish a necessary pursuit timescale: for example, the fixed-dimensional tori above have $h(G)=\Theta(|G|^{-1/k})$ and diameter $\Theta(|G|^{1/k})$, without the extra logarithm.

The present paper separates three phenomena:

1. bounded normalized metric distortion preserves a strong occupation certificate through degree reduction;

2. the HMGHM stressing family has an upper bound within a polylogarithmic factor of the square-root scale;

3. one-shot occupation is nevertheless incapable of proving a universal robustness theorem throughout any polynomial weak-expansion window, even on bounded-degree graphs with constant cop number; a cubic instance already appears at exponent $1/2$.

The remaining universal question is therefore an adaptive one. On the tori, ball growth carries essentially no information about pursuit cost; product structure instead supports coordinate-wise shadowing. What geometric or combinatorial quantity replaces product coordinates on a general polynomially weak expander? Equivalently, can a capacitated, correlated, or deferred witness system reuse the same cop resources over polynomially many weak-growth layers, or must every such one-traversal certificate incur polynomial congestion?

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

The metric inequalities were independently tested on HMGHM towers rebuilt from the published gadget description, including structured base graphs not used in the original audit. The Hall inequalities and timing margins were checked numerically, and exact small replacement games were solved by retrograde analysis. The toroidal barrier audit computes exact ball profiles of $C_L^{\square k}$ by convolving cyclic distance distributions, verifies the $(5k)^k$ doubling bound for $k=2,3,4,5$, constructs $Q_L$, checks cubicity, connectivity, and the displayed rotation automorphism, and evaluates the counting lower bound at every radius. No theorem depends on the computations.
