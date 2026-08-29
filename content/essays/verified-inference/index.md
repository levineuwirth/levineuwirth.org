---
title: "Verified Inference Between Adversaries"
date: 2026-08-29
abstract: >
  A compute operator who claims to have run a particular model can be lying, and
  the logs that would settle it are written by the party under suspicion. VerInf
  produces zero-knowledge proofs of LLM inference, bounding the information in an
  output stream that a committed model does not account for. This is a working
  note on what the system certifies, what it does not, and what I contributed to
  it during the MARS V fellowship.
tags:
  - ai
  - tech
  - research
  - research/machine-learning
status: "Working model"
confidence: 85
importance: 4
evidence: 4
scope: broad
novelty: moderate
practicality: moderate
history:
  - date: "2026-08-29"
---

A datacenter tells you it ran a 400-billion-parameter model on your prompt. It
might have run a smaller one, an older checkpoint, or a quantized copy that
costs a fraction as much. Ordinary logging cannot settle this, because the logs
are produced by the party whose behavior is in question. Neither can a hash of
the weights: the operator can hold the right weights and still run something
else.

This is not a hypothetical failure mode so much as an unresolved gap in every
current deployment story. Evaluations measure a model under conditions you
control; they say nothing about the model served to somebody else afterward.
Attestation binds a binary to a machine; it does not bind an output to a
computation. What is missing is a way for a verifier to check a claim about a
computation without trusting the party that ran it.

[VerInf](https://github.com/JamesPetrie/VerInf) is a research prototype
addressing that gap, built by James Petrie at the Future of Life Institute. I
worked on it as a [MARS V](https://caish.org/mars) fellow. This note describes
what the system proves, what it does not, and which parts of it are mine.

## What the proof certifies

The naive framing — "prove the model produced this output" — is the wrong one,
and understanding why is most of the insight. Frontier inference runs in
floating point, on nondeterministic kernels, across hardware that does not
reproduce bit-for-bit. Demanding exact reproduction would make the problem
intractable and would not even be the property you want.

VerInf instead bounds the **unexplained information** in an output stream: the
number of bits in the output that the committed model does not account for. If
the operator swapped in a different model, the outputs it produced would be
poorly predicted by the model it committed to, and the bound rises. A cheap
substitution is expensive to hide.

The certified statement is a conjunction of three parts, and they are held to
different standards:

- a **transcript anchor**, binding the committed token streams to digests
  recorded independently at generation time, so the proof is about the run that
  actually happened rather than a convenient reconstruction;
- the **forward pass**, where every claim must admit exactly one satisfying
  assignment, because slack in an intermediate value propagates through the
  remaining layers in directions nobody can analyze;
- the **surprisal bound** itself, where freedom *is* permitted — provided every
  free direction pushes the reported number up rather than down.

That asymmetry is the elegant part. Upstream of the logits the prover must have
no room at all; downstream, in the short arithmetic from logits to the reported
bound, the prover may have room so long as every rounding is forced upward.
Cheating can only make your own number worse.

A related move governs the predictor. The bound is computed against a predictor
of the deployment's outputs that the *prover* supplies — which sounds like
handing the adversary the pen. By Gibbs' inequality the resulting sum is a valid
upper bound for *any* predictor, so the choice can be left to the prover
entirely. The scheme is sound whatever they pick; a bad choice only inflates
their own reported bound.

Underneath, matrix products are checked with Freivalds projections over Ligero
commitments, which are hash-based — so there is no trusted setup, and the
construction is plausibly post-quantum.

## Who trusts whom

The two parties want different things, and the design is legible once you see
that.

The **prover** wants confidentiality: weights, activations, and both token
streams must not leak. The **verifier** wants soundness: the reported bound must
be genuine. Their interface is a public claim list stating what kind of
computation was performed — which reveals the model architecture, though not the
weights.

Each side trusts only its own code. The verifier's trusted base is deliberately
small, and it shares no code with the prover. A fault anywhere on the prover's
side can cause a proof to fail; it cannot cause one to falsely verify.

## Results on record

These are the published single-chip numbers, and they predate my involvement.

| | Llama-4-Maverick | Llama-2-7B |
|:---|:---|:---|
| Parameters | 400B MoE, 48 layers, 128 experts committed per layer | 7B, 32 layers |
| Transcript | 1000 tokens, **all hidden** | 1000 tokens |
| Prove | 14.3 h, 78.1 GB GPU peak | ~44 min, 11.2 GB peak |
| Verify | 17.7 h, 20 CPU cores, 40 columns opened | ~23 min, 10 columns |
| Proof size | 93.6 GB | 1.44 GB |
| Bound | 0.880 bits/token | — |

All on a single NVIDIA DGX Spark. The committed witness for the Maverick run is
roughly 7.2 TB, streamed at the working set rather than held.

The bound is the number to read. At 0.880 bits per token against a
202,048-token vocabulary, the proof accounts for about 95% of the information a
token could carry. That is not "the model produced this"; it is "very little
here is unexplained by the model that was committed."

## What I contributed

Parallelizing the prover across GPUs is named future work in the paper, and it
is the direction I am working in. It runs into an immediate problem: you cannot
measure a cluster you do not yet have access to, and partitioning decisions have
to be made before the hardware arrives.

So the first deliverable was not parallelism — it was the measurement
scaffolding parallelism needs. I built a **dry-run profiler** that predicts a
proving run's time, memory, bandwidth, and proof size *before* running it, from
a workload manifest plus measured hardware constants, and exposes the dependency
structure a future scheduler will consume:

- a **manifest contract** — one record per tape operation, with two independent
  producers (an exact tape-walker that runs where the prover runs, and
  closed-form builders in pure Python that cross-check it);
- a **cost model** in per-claim accounting form, carrying the production
  expressions from the paper's cost appendix;
- a **claim-level dependency DAG** with critical path and width profile, which
  is what tells you how much parallelism actually exists;
- a **partition scorecard** that maps claims onto *N* shards under competing
  strategies — contiguous tape ranges, pipelined layers, expert-sharded — and
  scores them.

One deliberate constraint: none of it touches the soundness-critical prover
path. A profiler that could perturb the proof would be a liability in a system
whose entire value is that a fault cannot cause false acceptance.

I also corrected the cost model's RMSNorm row to the wrap-free bracket
constants, bringing it into line with the paper's own analysis.

Both are merged upstream:

::: {.work-entry-links}
[Merged pull requests](https://github.com/JamesPetrie/VerInf/pulls?q=is%3Apr+author%3Alevineuwirth) ·
[Upstream repository](https://github.com/JamesPetrie/VerInf)
:::

**In progress:** the multi-GPU port itself. The aim is not parallelism for its
own sake — multi-device proving is what lifts the ceiling on model scale,
context length, and mixture-of-experts breadth. Results are preliminary and
unmerged; I will report them here when they are not.

## What this does not do

The honest list, mostly from the paper's own limitations section:

- **No security review.** It is a research prototype.
- **The proofs are enormous** — 93.6 GB at full scale. This is a real deployment
  obstacle, not a rounding error.
- **0.880 bits per token is not zero.** For some applications that residue is
  fine; for others it is not, and the paper is explicit that tightening it is
  open work.
- **Soundness is a per-challenge bound** (about 2⁻¹⁶·⁶ in the demonstrated
  configuration), raised by opening more columns at a measured cost in
  verification time. It is a deployment choice, not a fixed property.
- **The claim list reveals the architecture.** Hiding that too is future work.
- **The transcript anchor is not yet demonstrated end to end.** The AES and
  SHA-256 circuits are implemented and tested; binding them against
  independently recorded digests is not yet shown.

That last one is the gap I would press on hardest if I were reviewing this. The
anchor is what makes the bound a statement about a *particular real run* rather
than about some internally consistent transcript. Everything else is
cryptographic machinery; that is the part that connects it to the world.

## Why this matters for assurance

The reason to care is not that datacenters are presumed dishonest. It is that
"trust us, we ran the model we said" is the current state of the art, and it
does not scale to a world where the stakes of that claim keep rising —
third-party evaluation, regulatory audit, compute governance, any arrangement
where an inference claim carries weight and the parties are not aligned.

Verified inference is one approach to a general question: how do you establish
trustworthy claims about an AI system when the system, the operator, and the
evaluator may each be untrusted? Cryptography attacks it from below. Evaluations
attack it from above. Neither is sufficient alone.
