---
title: "Proof Broker: Separating Proof Search from Trust"
date: 2026-09-05
abstract: >
  Proof search is improving faster than the case for trusting it. Proof
  Broker puts a boundary between the two: Lean and Rocq send a goal out to
  external provers, take back a certificate with a graded trust tier,
  verify it at the boundary, and still require a proof term the home
  kernel checks. Nothing behind the boundary is trusted, so the search
  behind it can be as aggressive, heterogeneous, or unreliable as finding
  proofs requires. This essay sets out the architecture, what it makes
  possible, the evidence so far — 19 of 19 arithmetic obligations closed
  in a real verification project — and the research program that
  evidence opens.
tags:
  - research
  - tech
  - ai
status: "Working system"
confidence: 87
importance: 4
evidence: 4
scope: broad
novelty: idiosyncratic
practicality: moderate
history:
  - date: "2026-09-05"
---

The beauty of the proof assistant is the simplicity of the kernel.
The trusted surface is small and the kernel itself stable; therefore
we may, without too much worry, defer checking a proof to such an
apparatus. This yields an elegant setup where everything else in the
system — elaborator, tactics, automation —
can be wrong without a false theorem resulting, because the kernel is
the only judge.

That structure does not require proof search to happen inside the
assistant; in fact, the tools that are usually good at finding proofs
mostly live outside it. An SMT solver decides the bounded-arithmetic side conditions
that saturate real verification work in milliseconds. A saturation
prover handles first-order goals that the assistant's own automation
does not. Language models [have begun](https://www.anthropic.com/research/formalizing-fermats-last-theorem) 
to propose proofs for goals where neither applies. Each of these is a large, opaque, changing program,
and each keeps getting better, if not more complex.
If we take the example of Claude's formalization of Fermat's Last Theorem, then
we're on the scale of millions of lines of proof across many subtheorems.
The amount that a human needs to review is mind-boggling; a model's proof sketch,
at least given the current tendency of models towards verbosity, is a claim
made by something nobody can audit at all, in a way that is difficult to audit.
A solver's `unsat` is, in stark contrast, a claim made by a
few hundred thousand lines of C++. 

Using external search without trusting it is established practice.
Isabelle's `sledgehammer` has for years sent goals to external provers
and reconstructed what came back inside Isabelle; SMTCoq checks SMT
solvers' proof witnesses in Coq; F* marks the other end of the design
space, where the SMT encoding and the solver are trusted outright. I find
both extremes to be unattractive. Trust the external tool, and it
joins the implicity trusted base^[Even worse, one could argue that it *rejoins* the trusted base on every new release.]. 
Refuse it, and formalization stays where it is: in
[VerInf](/essays/verified-inference/)'s Lean formalization of a
floating-point bracket, a file this essay returns to below, the
project's own findings record that "100% of the iteration cost was
Lean plumbing", with `omega` unable to chain a variable bound into the
concrete `< P` fact the proof needed, so that each step waited on a
`norm_num` lemma fed in by hand.

There is a harder engineering problem sitting between the extremes, then:
using increasingly heterogeneous external search *without*
inheriting its trust assumptions, and *without* building a separate
integration for every prover and backend pair. Proof search is getting
better at a remarkably faster rate than trusting it is getting easier, 
and the bridges that exist are each one home system's answer for its own backends. 
**Proof Broker** is my ongoing attempt at a general architecture around untrusted
search: a shared intermediate representation, heterogeneous backends
behind one interface, explicit evidence tiers, certificate adaptation,
more than one home prover, and a uniform boundary whose logical
trusted base does not grow with the search machinery behind it.

## Separate search from acceptance

::: {.figure #fig-trust script="figures/trust_zones.py" caption="The three zones. The query path runs along the top, the answer path returns along the bottom. Certificate verification is the broker's *acceptance* boundary — a candidate that fails it never reaches a closer — but only the kernel-checked zone is the logical trusted base."}
:::

The architecture has three zones. The **untrusted zone** holds search: today cvc4, cvc5, z3, and the
Vampire saturation prover, with a language-model adapter I return to
below. The box is drawn loosely on purpose. Nothing in it is trusted,
so anything may sit there. The **broker machinery** — reifier,
intermediate representation, rewrite engine, dispatcher, and the OCaml
certificate verifier — is deliberately *unprivileged*: it earns
confidence, but no soundness claim rests on it. The **kernel-checked
zone** is where soundness lives, and it is exactly as large as it was
before the broker existed.

What crosses from search back into the broker is never a bare answer.
It is a **certificate**, carrying provenance and a trust tier that
says how much of the proof it contains. A Tier 3 certificate carries
the solver's replayable proof trace. A Tier 1 certificate carries a
Farkas witness — one nonnegative multiplier per hypothesis whose
weighted sum is a contradiction — and Tier 2 is its case-split
extension. A Tier 0 certificate carries only the solver's verdict
inside an integrity envelope, with no checkable content, and it is
labelled as such. The broker verifies what each tier claims, prefers
the strongest tier that verifies, and records the tier in the result,
so a consumer always knows which rung it is standing on. The tiers
grade the evidence that came back, not the backend that sent it: how
much of the proof the certificate contains and how it can be replayed.
Trust in the backend itself is zero at every tier.

Then the home prover closes the goal, and this is what makes the three
zones worth having. Every closer ends in an ordinary proof term that
the kernel checks. In term mode, the certificate's coefficients flow
directly into that term. In gated mode, the certificate licenses a run
of a tactic such as `omega`, and the tactic's output is the term. The
foreign-function interface returns data, never proofs, and an axiom
guard on every build refuses the escape hatches (`sorry`-bearing
axioms, `native_decide`). So a certificate can fail at the broker
boundary; a bug in the broker could admit a bad candidate past that
boundary; but neither can make Lean accept a false theorem without
producing a kernel-valid proof term from the sanctioned axioms. The
broker's checks buy confidence, provenance, and early failure.
Soundness, as expected, rests on the kernel alone.

## What does the boundary buy?

The immediate benefit is that arithmetic side conditions close from an
external solver's search, but this is *not* why the architecture is
interesting.

Once search is structurally untrusted, the prover behind the boundary
no longer has to be something you would put in a trusted base. It only
has to return something checkable, and that changes what you can
optimize for. A backend can be buggy, probabilistic, opaque, or
enormous; two backends can disagree; an ensemble can race. The
architectural response to unreliable search is not to trust it more
carefully. It is to make trust irrelevant by insisting on a
certificate, and to grade the certificate honestly when the backend
cannot supply a strong one. Three consequences follow, and each is
already visible in the system as built.

**Heterogeneity is cheap.** The broker speaks one intermediate
representation and one certificate format to every backend. SMT
solvers, a saturation prover, and a language model already sit behind
the same interface, and each home system needs one bridge rather than
one per backend. The specification's framing is *N* home systems and
*M* backends joined by *N* + *M* adapters instead of *N* × *M*
bridges.

**Certificates can be synthesized, not only relayed.** The obvious
pipeline is solver, then solver-native proof, then home prover; there
exist others. cvc4 answers `unsat` without producing any proof
object; the broker's own search then recovers a sparse Farkas witness
consistent with that verdict, checks it, and hands Lean the witness.
The certificate language is the stable interface. A backend need not
speak it natively, and need not know which home prover is asking.
Adapting arbitrary search into a checkable certificate is a research
area in its own right, and the arithmetic case is its first instance.

**Learned search gets no credit for proposing.** The language-model
adapter renders a goal as Lean syntax, asks a model for a tactic
script, and mints the script as a Tier 3 certificate — a proof trace,
in the ladder's terms, though one the verifier explicitly marks as
unverified until kernel replay. The home closer elaborates the script
against the goal, requires the goal actually closed, and accepts only
if the replayed term's axioms fall inside the same ceiling every other
closer uses. A hallucinated `sorry` or `native_decide` is a tactic
failure with the goal left open. The adapter and its replay closer
exist in both bridges and are tested in CI without a network; the
downstream demonstration below does not use them, and no live model
has yet been run against a real consumer's goals. The model may be
arbitrarily clever, but it receives no trust for being so.

## One proof, end to end

One obligation from the demonstration below, traced through the
figure. The goal is a bound of the form $2^{24} + 2\cdot Z_{\max} \le
P$ over the natural numbers, with eighteen hypotheses in scope. The
Lean bridge reifies the goal and its hypotheses into the broker's
intermediate representation, specializing ℕ to ℤ with a recorded
refinement witness so the proof can be lifted back, and dispatches to
the solvers. cvc4 answers `unsat` in about ten milliseconds — and
produces no proof. Rather than book that as an oracle verdict, the
SDK's sparse-support Farkas search looks for a witness among small
subsets of the hypotheses, and finds one using two facts: the bound
$Z_{\max} \le 2^{16}$ taken twice, and the negated goal once. The
OCaml verifier checks that this weighted sum is contradictory *before*
any certificate is minted. The Lean bridge then applies the same two
multipliers to the same two facts as an explicit proof term, and the
kernel checks that term like any other. Had the solver been wrong, the
error would have died at one of two independent gates: the arithmetic
check at the boundary, or the kernel.

That is a Tier 1 certificate in term mode: the certificate *is* the
proof's content. In gated mode the certificate is evidence instead. It
verifies, and then a tactic the certificate says will succeed produces
the term, which the kernel checks in turn. Both modes end in the same
place. The whole call is tens of milliseconds, and every number, per
obligation, is in the demo's generated tables.

## Contact with a real formalization

An architecture argument needs a consumer that was not written for it.
The one I used is the softmax-bracket uniqueness spike from [VerInf](/essays/verified-inference/) —
the consumer that project identified as its hardest — taken verbatim
at its upstream commit. Here is the region its findings called "100%
of the iteration cost", before:

```lean
  have hnum : (2:ℕ)^24 + 2 * 2^16 ≤ P := by norm_num [P]
  have hxz : (x + z).val = x.val + z.val := by
    apply val_add_lt
    have hzsum : x.val + z.val < 2^24 + 2 * Zmax := by omega
    have hle : (2:ℕ)^24 + 2 * Zmax ≤ P := by omega
    omega
```

and after:

```lean
  have hnum : (2:ℕ)^24 + 2 * 2^16 ≤ P := by proof_broker
  have hxz : (x + z).val = x.val + z.val := by
    apply val_add_lt
    have hzsum : x.val + z.val < 2^24 + 2 * Zmax := by proof_broker_term
    have hle : (2:ℕ)^24 + 2 * Zmax ≤ P := by proof_broker_term
    proof_broker_term
```

The second version isn't shorter. What changed is where the proof search
happens and what has to be believed about it; `hle` is the obligation
traced above. `diff` against the upstream file shows two added
imports, a header, and the marked tactic swaps.

The result, in the
[R4 release](https://github.com/levineuwirth/proof-broker/releases/tag/r4)
of September 2026, is 19 of 19 targeted obligations closed in the
unmodified spike, with probe logs, build logs, the axiom audit, and
timing tables generated by scripts in the
[demo repository](https://github.com/levineuwirth/proof-broker-demo)
rather than typed by anyone. The certificates span the ladder. Four
obligations close in term mode from Farkas witnesses. Five replay
cvc5's proof traces step by step through the Alethe walker. Nine close
through certificate-gated `omega`. One rides a Tier 0 verdict, where
the envelope is checked, the verdict is not, and `omega` carries the
whole proof.

If you are skeptical, and rightfully so, I encourage you to read the axiom audit. Everything
stays inside Lean's sanctioned ceiling (`propext`, `Classical.choice`,
`Quot.sound`). One headline theorem gets *narrower* than upstream: the
hand proof's `norm_num` calls pulled in `Classical.choice`, and the
Farkas terms and gated `omega` that replaced them do not. One theorem
gets *wider*: its trace-replay closer is classical where the hand
proof was not, term mode cannot express those goals' shapes, and the
widening is structural. The demo reports it as such, in a generated
table, next to the theorem it affects.

## The consumer broke the broker

The broker's own test suite passed throughout, and the downstream file
still found three defects. The Farkas search materialized its
candidate space before searching it — $4^{15}$ coefficient vectors at
this file's fifteen-hypothesis goals, a 57 GB process on my poor 58 GB
machine — and now streams under an explicit budget. The reifier's
accumulators raced Lean's parallel elaboration, failing about one
elaboration in three on this file, until they became per-call values
pinned by a regression test. And the tactic front-end was
context-sensitive: a goal inside a real proof carries metadata and
uninstantiated metavariables that a goal stated as a bare declaration
never exhibits, so eight obligations that closed in isolation failed
in the real file until the bridge normalized at entry. The demo repository carries the full
account.

## From arithmetic to richer theories

Arithmetic demonstrates the architecture, but it doesn't test the full
generality of the claim, namely that the boundary holds as the
theories behind it get richer.

The first target is named by the consumer itself. VerInf's uniqueness
queries — whether each claim in a proof's forward pass admits exactly
one satisfying assignment — are prime-field problems, and the
project's plan names cvc5's finite-field mode as the engine. The same
plan flags the objection that solver timeouts make gate verdicts
nondeterministic. The broker's answer to that objection is the stored
certificate: once a certificate is independently checkable, future
acceptance no longer depends on reproducing the original search. Reaching those queries needs three things
the broker does not yet have: a theory tag for prime fields in the
intermediate representation, an adapter for cvc5's finite-field mode
that mints a certificate a checker can re-verify, and a corpus of
uniqueness queries to measure against. That is the first real test of
whether theory-specific certificate interfaces can be built around
much richer search than linear arithmetic. After finite fields the
same question recurs for bit-vectors, where the roadmap's open
question is whether the term-mode idiom generalizes or the theory
needs its own closer, then for nonlinear arithmetic, and eventually
for probabilistic claims. The interesting answers will not all be yes.

Two further directions push certificates toward the top of the
ladder. The Alethe walker replays cvc5's proof skeleton step by step
but re-decides its arithmetic leaves with `omega`; making those leaves
flow from the trace's own coefficients would make Tier 3 as faithful
as Tier 1 term mode. Vampire's derivations are checked today for
provenance and structure rather than re-derived; closing a first-order
goal from the derivation alone is the gate for the same claim about
saturation provers.

The last direction is portability. Both bridges share the SDK, so what
a certificate means is already independent of which prover asked.
Keeping that true as the Lean bridge runs ahead — the Rocq ports of
the recent lifting and reifier work are recorded deferrals — is what
makes "common infrastructure between proof assistants and automated
reasoning" a claim rather than a slogan.

## What remains

The evidence is one file, from one project, on one machine on one
day, and nothing has run in anyone's CI but mine. Each limit is also a
question.

- **Breadth.** Does the abstraction hold across unrelated
  developments, or is the bracket spike's arithmetic unusually
  well-shaped for it?
- **Tier strength.** One of the nineteen obligations rides a Tier 0
  oracle certificate, and nine more verify a proof trace but let
  `omega` produce the term. How much of the ladder can be pushed to
  certificates that are the proof?
- **Rocq parity.** Can the same broker semantics stay genuinely
  prover-independent while one bridge leads?
- **Finite fields.** What does the certificate boundary look like for
  the first theory whose native proof object is not a
  linear-arithmetic witness?
- **Learned search.** The adapter has not yet met a real consumer.
  What becomes useful when a model may propose arbitrarily clever
  proofs and receives no trust for proposing them?

## The prover does not have to be trustworthy

What Proof Broker is trying to make separable is *who or what found a
proof* from *why anyone should believe it*. Nineteen arithmetic goals
in one file do not establish that separation in general. They
establish that it survived contact with a real formalization that was
not written for it, on the weakest and strongest rungs of the ladder
at once, with the trust footprint reported per theorem. That is enough
to make the larger claim worth pursuing, and not enough to make it.

The same question — checking a claim without trusting its author — is
the one [VerInf](/essays/verified-inference/) asks about model
inference, where the claim is that this model produced that output and
the author is a datacenter. Proof Broker asks it about automated
reasoning, where the claim is a proof and the author is a solver or a
model. These are two attacks on one problem: building trustworthy
interfaces around computation that is increasingly powerful and
increasingly hard to trust. That problem is where my work is heading,
and R4 is the point at which the proof-search half of it stopped being
a specification.

**On agent assistance.** Implementation was agent-assisted
throughout, under my direction of the program and its architecture.
Every phase shipped only after adversarial review rounds, and each
finding — the three defects above included — was closed with its own
commit and regression pin. The records are public in the repository.
The specific methodology used is derived from the methodology of our
MARS V stream working on VerInf.

::: {.work-entry-links}
[Demo: 19/19 downstream obligations, full evidence](https://github.com/levineuwirth/proof-broker-demo) ·
[Code](https://github.com/levineuwirth/proof-broker) ·
[Release: R4](https://github.com/levineuwirth/proof-broker/releases/tag/r4)
:::
