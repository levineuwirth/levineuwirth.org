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

A datacenter asserts that it ran a 400-billion-parameter model on your prompt. It
might have run a smaller one, an older checkpoint, or a quantized copy that
costs a fraction as much. Ordinary logging cannot settle this, because the logs
are produced by the party whose behavior is in question. Neither can a hash of
the weights: the operator can hold the right weights and still run something
else.

Similarly, assume that a treaty between two governments is reached regarding
AI research and development. Both governments claim that they are using particular
models that meet certain thresholds, have been approved by regulatory boards, etc.
The same problem applies; there is not any obvious way for one party to such an
agreement to verify the claims of the other.

This is not a hypothetical failure mode so much as an unresolved gap in every
current deployment. Evaluations measure a model under conditions you
control, saying nothing about the model served to somebody else afterward.
Attestation binds a binary to a machine, rather than binding an output to a
computation. What is missing is a way for an independent verifier, run on independent hardware,
to check a claim about a computation without trusting the party that ran it, or the hardware it ran on.

[VerInf](https://github.com/JamesPetrie/VerInf) is a research prototype
addressing that gap, led by James Petrie at the Future of Life Institute. I
work on it as a [MARS V](https://caish.org/mars) fellow. This living document
details what the system does and does not currently prove, where we think it is heading,
and my future ambitions for this line of work.

## What the proof certifies

The naive framing — chiefly, "prove the model produced this output" — is the wrong one.
Frontier inference runs in floating point, on nondeterministic kernels, across hardware that does not
reproduce bit-for-bit. Demanding exact reproduction would make the problem intractable, and even worse,
it isn't really even addressing the right problem. 

VerInf instead bounds the **unexplained information** in an output stream: the
number of bits in the output that the committed model does not account for. If
the operator swapped in a different model, the outputs it produced would be
poorly predicted by the model it committed to, and the bound rises. A cheap
substitution is therefore expensive to hide.

Our certified statement is a conjunction of three parts held to different standards:

- a **transcript anchor**, which binds the committed token streams to digests
  recorded independently at generation time. This ensures proof is about the run that
  actually happened, rather than a convenient reconstruction;
- the **forward pass**, where every claim must admit exactly one satisfying
  assignment. Slack in an intermediate value would propagate through the
  remaining layers in directions nobody can analyze;
- the **surprisal bound** itself, where freedom *is* permitted, provided every
  free direction pushes the reported number up rather than down.

Upstream of the logits the prover must have no room at all; 
downstream, in the short arithmetic from logits to the reported
bound, the prover may have room, so long as every rounding is forced upward.
In an elegant twist, cheating can only make your own number worse.

A related move governs our predictor. The bound is computed against a predictor
of the deployment's outputs that the *prover* supplies.
By [Gibbs' inequality](https://en.wikipedia.org/wiki/Gibbs%27_inequality) the resulting sum 
is a valid upper bound for *any* predictor, so the choice can indeed be left to the prover
entirely. 

Underneath, matrix products are checked with Freivalds projections over [Ligero](https://link.springer.com/content/pdf/10.1007/s10623-023-01222-8.pdf)
commitments, which are hash-based — so there is no trusted setup, and the construction is plausibly post-quantum^[Future research intends to make this statement of "plausible" post-quantum security into one of "definitive" post-quantum security.].

## Where trust is required

The **prover** wants confidentiality: weights, activations, and both token
streams must not leak. The **verifier** wants soundness: the reported bound must
be genuine. Their interface is a public claim list stating what kind of
computation was performed — which reveals the model architecture, though not the
weights.

Each side trusts only its own code, and only its own hardware. 
The verifier's trusted base is deliberately small, and it shares no code with the prover. A fault anywhere on the prover's
side can cause a proof to fail; it cannot cause one to falsely verify. Similarly, we envision that in a setup between 
Governments, each government would be able to use their own hardware for their verifier of the other party's proofs, and no
trust of the datacenter in which this takes place would be required.

## Results on record

These are the published single-chip results, and they predate my involvement.
My own measurements — validation of the cost model, and the first figures from
Blackwell hardware — are in [What I contributed](#what-i-contributed) below,
separated there by what has merged upstream and what has not.

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

 At 0.880 bits per token against a 202,048-token vocabulary, the proof accounts for about 95% of the information a
token could carry. That is not "the model produced this"; it is "very little
here is unexplained by the model that was committed."

## What I contributed

Parallelizing the prover across GPUs is named future work in the paper, and it
is the direction I am working in. It runs into an immediate problem: you cannot
measure a cluster you do not yet have access to, and partitioning decisions have
to be made before the hardware arrives.

My first deliverable was the measurement scaffolding that parallelism needs. 
I built a **dry-run profiler** that predicts a
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

A profiler is only as good as its predictions, so validation came in two
rounds. The first was retrodictive: predict the archived Maverick run from a
synthetic manifest plus the development box's measured constants, then compare
against what that run actually recorded.

| quantity | predicted | measured |
|:---|:---|:---|
| witness rows | 108.7 M | 109.27 M |
| proof size | 93.1 GB | 93.6 GB |
| opened-column GPU payload | 34.8 GB | ~35 GB |
| verifier peak RSS | 76.1 GB | 75.7 GB |
| proof dump time | 751 s | 756 s |
| prove wall-clock | 3.0 h floor / 9.9 h aggregate | 14.26 h |

Prove time is deliberately a *bracket*, not a point estimate. The floor is the
bandwidth-bound target the design should reach after planned reorganization;
the aggregate is calibrated on today's code. The gap between bracket and
measurement is not error — it is the itemized implementation overhead, which
is to say the work-list.

The second round I ran end to end myself, on hardware the tooling had never
seen: a single rented B200, the class of machine the multi-GPU effort actually
targets. One morning and about eleven dollars of GPU time later:

- the calibration suite filled a complete machine profile from scratch, every
  constant measured on the box with its provenance recorded (headline: 29×
  the development box's memory bandwidth);
- the exact tape-walker ran against real tapes for the first time and
  **cross-checked clean against the closed-form builders — zero flags**: every
  claim count, witness slot, linear constraint, and quadratic product matched
  within the documented expected set, and the per-row witness layout agreed
  with the prover's own accounting row for row;
- the extracted Maverick manifest reported **109,273,513 witness rows,
  against the production run's measured 109.27 M** — the profiler reproducing
  reality, not merely its own model of it;
- the first cost bracket priced on measured Blackwell constants put the full
  Maverick proof at a **376-second floor** on one B200 — roughly 28× the
  development box, tracking the measured bandwidth ratio almost exactly,
  which is what the cost model's scaling story says should happen when the
  dominant terms ride memory bandwidth.

I also corrected the cost model's RMSNorm row to the wrap-free bracket
constants, bringing it into line with the paper's own analysis.

### A retraction

The same B200 session produced a finding I later had to withdraw: an apparent
interconnect bottleneck that turned out to be almost entirely an artifact of my
own traffic model. Nothing was wrong with the machine; something was wrong with
what I had assumed about it.

I record it because it is the discipline the whole exercise exists to enforce.
A profiler that only ever confirms its author is not a measurement instrument.
Predictions go out before the measurement, and get corrected in public when the
measurement disagrees — otherwise the numbers above would be worth very little.

### What is upstream, and what is not

**Merged** — the dry-run profiler (manifest contract, cost model, execution DAG,
partition scorecard) and the RMSNorm cost-model correction.

**Not yet merged, landing shortly** — the calibration suite, the tape-walker's
first run against real tapes, the measured Blackwell machine profile, and the
B200 figures reported above. Treat those as reported-by-me until they appear in
the pull request list.

::: {.work-entry-links}
[Merged pull requests](https://github.com/JamesPetrie/VerInf/pulls?q=is%3Apr+author%3Alevineuwirth) ·
[Upstream repository](https://github.com/JamesPetrie/VerInf)
:::

## Where this goes next

The immediate step is a port to 2–8 GPUs, and the reason is not that more GPUs
sound better. Multi-device proving is what lifts the ceiling on model scale,
context length, and mixture-of-experts breadth — the dimensions along which a
single box runs out first.

The honest projection carries the same bracket as everything else here. The
anchor is a **376-second floor for the full Maverick proof on one B200**: a
floor, not today's code, and it assumes the reorganization the cost model
already itemizes. Distributing that across 2–8 devices puts a 400B proof in the
low minutes if the partition scales cleanly, and under a minute at the
optimistic end. Both numbers are projections from a model validated against one
archived run and one live machine — good enough to plan against, not yet a
measurement.

Beyond that, fleets of 64–128 GPUs are what an order-of-magnitude larger model
would require. That figure comes from the same cost model and has not been
validated at that scale.

## Current Limitations
While VerInf looks promising, there are currently limitations:

- **No security audit.** It is a research prototype.
- **Proof Size** — 93.6 GB at full scale. This is a real deployment
  obstacle, not a rounding error.
- **0.880 bits per token is not zero.** For some applications that residue is
  fine; for others it is not, and the paper is explicit that tightening it is
  open work.
- **Soundness is a per-challenge bound** (about 2⁻¹⁶·⁶ in the demonstrated
  configuration), raised by opening more columns at a measured cost in
  verification time. It is a deployment choice, not a fixed property.
- **The claim list reveals the architecture.** 
- **The transcript anchor is not yet demonstrated end to end.** The AES and
  SHA-256 circuits are implemented and tested; binding them against
  independently recorded digests is not yet shown.

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
