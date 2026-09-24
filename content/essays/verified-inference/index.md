---
title: "Verified Inference Between Adversaries"
date: 2026-08-29
abstract: >
  An operator can fabricate execution logs and hold approved weights while running
  something else. VerInf investigates proofs of language-model inference that
  mutually distrustful parties can verify on their own hardware. This living
  document explains what the proof certifies, the system I started from, and my
  work on profiling, prover optimization, and scale-out during the MARS V fellowship.
tags:
  - research
  - research/machine-learning
  - ai
  - tech
status: "Working model"
confidence: 85
importance: 5
evidence: 4
scope: broad
novelty: moderate
practicality: moderate
history:
  - date: "2026-09-24"
    note: "Verification section updated for the enrollment-identity anchor and the index-bound Merkle opening in pull request 21."
  - date: "2026-09-22"
    note: "Rewritten to cover the proof guarantee, contribution history, and current profiling and scale-out work."
  - date: "2026-08-31"
  - date: "2026-08-30"
  - date: "2026-08-29"
revised:
  - date: "2026-09-22"
    note: "Comprehensive update on the proof guarantee and current research."
---

A datacenter asserts that it ran a particular model on your prompt. It might have run a smaller one, an older checkpoint, or a cheaper quantized copy. The operator can fabricate logs describing the agreed computation regardless of what it actually ran. A hash of the right weights does not settle the matter either: the operator can possess those weights and execute something else.

Consider an agreement between two mutually distrustful states concerning permitted AI models or workloads. Neither party can be expected to accept the other's execution logs as evidence that the agreement was followed. Nor can either be expected to trust the other's hardware or execution environment. Both may also require their weights, prompts, and outputs to remain confidential. Evaluating a model beforehand leaves the central question unanswered: what can either party establish about the computation the other subsequently performed?

VerInf takes this mutual distrust as a design requirement. Hardware attestation would introduce a hardware root of trust; the intended arrangement here requires no trust in the other party's hardware, including the hardware that generates the proof. Each party runs an independent verifier on its own cluster and checks the proof produced on the other's. The proving cluster is outside the verifier's trusted base. The aim is to make a computational claim checkable across that boundary without requiring either party to disclose its private data.

[VerInf](https://github.com/JamesPetrie/VerInf), led by James Petrie at the Future of Life Institute, investigates this question through proofs of language-model inference. I work on it through the [MARS V fellowship](https://caish.org/mars). My responsibility began with the profiler and the path to multi-GPU proving, and has grown to include hardware measurement, prover optimization, and the integration and hardening of new proof mechanisms.

Work on VerInf remains ongoing. Our current results have produced a weight-splitting decomposition and measured improvements on individual-GPU workflows, and work on a multi-device executor is well underway. The engineering questions at the heart of the system have evolved just as the system has.

## What the proof certifies

The output of a deployed language model is, generally, not a bit-for-bit reproduction of a fixed integer computation. Between floating-point kernels, hardware, and sampling, nondeterminism is introduced. VerInf represents the model with integer arithmetic and proves an upper bound on the output stream's total [surprisal](https://en.wikipedia.org/wiki/Information_content) under a predictor derived from that computation.

Surprisal measures how unexpected an output is: a token assigned a low probability costs more bits to explain. The predictor derives these probabilities from the integer model's logits, the scores it assigns to possible next tokens. The proof checks both the model computation that supplies those scores and the arithmetic that turns them into a bound. Rounding must push the bound upward, so approximation cannot make the output appear better explained than it is.

Writing $Q$ for the predictor and $o_t$ for the output token at position $t$, the proof certifies

$$
\sum_t -\log_2 Q(o_t \mid \text{model computation}, o_{<t}) \leq \widehat U.
$$

Here $o_{<t}$ denotes the preceding tokens, and $\widehat U$ is the reported upper bound in bits.

The predictor and the information it may use are part of the statement being proved. For a fixed predictor, averaging this score over possible output streams gives an upper bound on their [conditional entropy](https://en.wikipedia.org/wiki/Conditional_entropy): the uncertainty that remains given the information available to the predictor. This is the connection to unexplained information. An individual proof certifies the score of a particular transcript; it does not, on its own, measure the uncertainty of the deployment's entire output distribution.

A small score means the stream is well explained by the committed model and the specified predictor. It is important to keep in mind that it does not uniquely identify the implementation that produced it, as another computation could produce equally well-explained outputs. Nor does the score, by itself, establish a model's capabilities or whether a broader agreement was obeyed. Those claims require a policy and an observation process around the proof.

The intended end-to-end certificate has three parts:

- **An externally anchored transcript.** The committed inputs and outputs must be tied to a record made independently at generation time. Otherwise, the prover can choose a convenient transcript to explain. AES and SHA-256 circuits for this binding exist and have tests; the recorded-transcript construction has not yet been demonstrated end to end in the runs discussed here.
- **The integer forward pass.** Intermediate values upstream of the logits must be pinned by the constraints. Allowing the prover to choose among materially different intermediate values would give it control over the predictions being scored.
- **The reported bound.** Once the logits are fixed, the calculation of the bound may allow some freedom, but only in a direction that makes the reported value larger. Rounding upward is one such allowance. The prover may overstate how much the model leaves unexplained; the constraints must prevent it from understating it.

The model commitment and the public claim list also need to match what the verifier intended to approve. A valid proof of a statement the prover chose is not enough. The current full-proof path therefore checks externally supplied model-root and statement-digest policy. That anchors a particular statement; it does not automatically decide whether that statement constitutes an acceptable workload.

The claim list reveals the model's architecture. The intended [zero-knowledge](https://en.wikipedia.org/wiki/Zero-knowledge_proof) protection covers weights, activations, and tokens, subject to the masking and opening-budget requirements of the chosen protocol. The hash-based construction requires no trusted setup and is plausibly post-quantum. The system has not had a full security audit, and the experimental weight bridge described below does not yet provide the intended hiding of all its intermediate values.

## The system I started from

The core construction and the original large-model demonstration predate my contributions. The upstream already had a tensor-like claim language, a CUDA prover, an independently implemented Rust verifier, persistent-weight commitments and refresh/linking machinery, and an analytical performance model.

Its central implementation choice is streaming. A proof of the full Maverick model can involve terabytes of witness data. The prover generates an operation's witness, encodes rows, updates hashes or fold accumulators, and releases the data as it becomes unnecessary. Subsequent proof stages regenerate the witness instead of requiring the entire encoded computation to remain in memory.

That made a large demonstration possible on one DGX Spark. The archived 1,000-token Maverick run reports 14.26 hours to prove, 17.67 hours for independent Rust verification, a 93.6 GB proof, and a 78.13 GB GPU peak. Its reported score was 0.8801 bits per continuation token.[^original-run] These are results from the original system, not measurements of my optimizations.

The historical run establishes the scale of the computation and its checking, but its verifier acceptance does not establish all the confidentiality and adversarial-soundness properties described in the accompanying prose. The default path at that point used fixed public masking entropy and prederived challenges; later collaborator work changed both and required external policy.[^historical-security] Those conditions matter when moving from a computational demonstration to an adversarial deployment.

Streaming solves a memory problem by creating a regeneration problem. The model and its auxiliaries are revisited across proof stages. At small context lengths, loading and converting the weights can dominate even when little token computation is required. The upstream had already identified this effect. My initial task was to make the workload and its distribution measurable enough to decide what to do about it.

## Making the cost model executable

The existing model separated three kinds of work: witness slots, distinct linear constraint IDs, and quadratic products. Each claim contributes counts determined by its shape. Hardware constants translate those counts into an approximate cost:

$$
T_{\mathrm{kernel}} \approx A W + B L + C Q.
$$

I built a [dry-run profiler](https://github.com/JamesPetrie/VerInf/tree/3508ef1d63d004686e85373f6100689ae94b922a/profiler) around a common workload manifest. One producer walks a real lazy tape; another constructs synthetic workloads from model dimensions. Consumers calculate costs, expose the dependency graph, and compare ways of assigning claims to devices. The manifest preserves enough structure to distinguish model weights, ordinary inputs, produced variables, and their consumers.

The separation matters. Witness counts can be checked against the prover's layout without trusting the timing model. Hardware rates can be measured without running a full proof. A runtime estimate can then fail because a rate was wrong, a count was wrong, or the model omitted a class of work. Those failures call for different changes.

The first B200 session reproduced 109,273,513 rows from a real Maverick tape, agreeing with the archived run's approximately 109.27 million.[^first-calibration] It also measured the machine primitives and exposed limitations in the benchmarks. A small transform can measure launch overhead rather than the throughput of the prover's batched path. Later batched measurements on H200 and B200 did not follow the simple bandwidth extrapolation: measured NTT time per element was roughly three to four times the bandwidth-scaled expectation on those configurations.[^batched-transforms]

The profiler also corrected an error in my own distribution model. Its first scorecard attributed approximately 950 GB per sweep to cross-device traffic. Most of that was lookup-settlement data that could be reduced locally: the settlement needs each shard's contribution to a sum, not every element used to produce it. Correcting the accounting reduced the estimate to approximately 2.4–2.8 GB per sweep. This was a correction to a model, not a measured networking speedup. Message latency, synchronization, and the eventual interconnect topology still require measurement.

The profiler's scope has followed the implementation. It now distinguishes fresh witness from enrolled weights, physical row padding from logical lengths, and packed source bytes from expanded field tensors. The latest integration repair preserves bridge-held weights as source dependencies while excluding them from ordinary witness accounting. Reports explicitly say that the bridge's own costs are not yet modeled. Counting less witness is correct; treating the replacement mechanism as free would not be.

## What the experiments changed

The first cache targeted routed expert outputs that were being regenerated across sweeps. On an H200, caching them eliminated 7,020 shard loads and approximately 2.36 TB of decoded traffic in a 100-token proof. Prove time improved by only 1.2%.[^routed-cache]

The counters explained why. Those expert shards were inexpensive to fetch from the page-cached model and decode on the GPU. Dense weight loading was much more expensive, including repeated decoding of groups of tensors. I added group memoization and a decoded-weight cache, then measured those paths separately.

The first host-backed cache lost. On the session-3 B200 host, prove time rose from 2,492.8 to 2,966.6 seconds. The cache avoided repeated decoding, but pinned allocations competed with the model's page cache inside the container's memory limit. Initial stores became expensive and subsequent shard reads paid for reclaimed pages. Other host effects were not fully separable in that session, which led to additional resource sampling.[^host-cache]

A GPU tier avoided the host-memory pressure. On the next B200 host, it reduced prove time from 1,890.8 to 1,787.0 seconds, or 5.5%. The cache consumed approximately 64.7 GB of GPU memory, so the result is a time–memory tradeoff whose usefulness depends on the rest of the workload.[^gpu-cache]

These experiments narrowed the question. Saving a large number of bytes is useful only when moving or producing those bytes limits the run. Once dense loading became cheaper, the repeated encoding and folding of enrolled weights stood out more clearly.

## Splitting work while preserving the proof

Ordinary enrollment avoids rebuilding the weight commitment for every proof, but leaves two expensive passes over the enrolled rows: folding them into the test polynomials and reconstructing the challenged columns for opening.

I implemented a decomposition of those passes. Each worker owns a contiguous interval of weight variables. For the fold, it returns unfinalized field-sum partials, which the coordinator adds before finalizing the polynomials. For the opening, it writes column pieces at their original absolute row positions. Coverage checks reject missing or overlapping pieces. Padding retains the logical offsets used by the enrollment.

With the proof's secret randomness pinned for the comparison, the result must be byte-identical to the ordinary proof. The existing Rust verifier therefore checks the same object under the same rules. This decomposition introduces no new verifier-side aggregation argument.

The ownership plan can differ between the two stages, but their timings cannot be combined arbitrarily. The opening challenge depends on the completed test polynomials. Every fold contribution must arrive before the opening stage begins, giving a scheduling model of

$$
T = T_{\mathrm{commit}} + \max_i T_{\mathrm{fold},i}
    + \max_i T_{\mathrm{open},i}.
$$

A slow fold on one device cannot be canceled by a fast opening on that device. Memory must also accommodate the union of the device's fold and opening ownership. The implementation and model account for whole-variable cuts and per-variable row padding rather than assuming arbitrary fractions of the weights can be assigned.

The hardware gate checked proof-byte identity and Rust acceptance across different partitions and stage cuts.[^split-gate] The roles ran sequentially on one GPU. Actual multi-device execution still needs device-local state, transport, synchronization, and its own correctness and performance tests; the current worker deliberately refuses an unsupported second-device placement.

## Removing expert-weight work with a bridge

While I was developing the distribution and measurement work, collaborators were changing the protocol. Routed projection removed the need to commit every expert's activation for every token. A subsequent coefficient-RS weight enrollment and late bridge moved expert-weight authentication out of the ordinary Ligero witness.

The bridge is the collaborator's construction and implementation. I integrated it into my branch, added it to the research driver and measurement workflow, reviewed the verification boundaries, and worked on its remaining implementation costs.

This changed the scale-out problem. The original weight split distributes passes over a very large enrolled block. The bridge removes most expert rows from that block and authenticates the projections through a separate mechanism. Dense weights still use the ordinary commitment. The remaining work must be measured and modeled under this new division.

In the same-host B200 experiment, the bridge reduced 100-token prove time from 1,890.8 to 988.0 seconds. The comparison was:

| Mode | Prove-return time | Change from baseline |
|:---|---:|---:|
| Ordinary enrolled weights | 1,890.8 s | — |
| GPU-tier decoded-weight cache | 1,787.0 s | −5.5% |
| Weight bridge | 988.0 s | −47.7% |

All three arms used the same instrumentation and routed-output cache on one B200, with 50 prompt and 50 continuation tokens. Times exclude construction, enrollment, the separate reveal pass, and proof serialization.[^bridge-comparison] The full arms passed their internal leaf checks; independently accepted Rust proofs were the smaller two-layer gates. No full proof was dumped during that session.

The bridge result also has a confidentiality qualification: its interim implementation sends the projections, projected masks, and aggregate in the clear. The committed form needed for the intended zero-knowledge guarantee is unfinished. The table measures the cost reduction of the implemented mechanism, not a completed private deployment.

Instrumentation then showed where the bridge itself spent time. I moved mask generation onto the GPU using the prover's existing BLAKE3 row PRG. The following session measured a 198.5-second bridge pass, including 66.5 seconds of shard decoding and 46 seconds converting columns to Python integers.[^bridge-timing] The latest code removes duplicate shard decoding and keeps columns as tensors through compact serialization. Their combined effect has not yet been measured at full scale.

The whole prove in that following session became slower despite the shorter bridge pass. The host differed, and resource sampling showed heavy CPU throttling: thread pools were sized for visible cores rather than the container's quota. It would be misleading to present the cross-host difference as a controlled total-runtime improvement. This is why the archives retain the host configuration and separate stage times from the proof's wall time.

## Checking which model the bridge authenticates

Integration also exposed a verification issue that is easy to miss when concentrating on performance. A bridged proof has two model anchors: the ordinary root for dense weights and a separate enrollment root for expert weights. The verifier checked the first, but in that mixed configuration left the second without an external policy comparison.

Authenticating a projection against a root supplied by the prover does not establish that those are the approved expert weights. I added a separate required policy input for the enrollment root, keeping both comparisons explicit.[^bridge-policy] A proof must satisfy its algebraic checks and authenticate the model the verifier meant to approve.

The same review added bridge geometry and opening-count checks and refused bridge verification on the legacy file-seed path. In the imported sumcheck implementation, I also fixed missing checks on the number of rounds and the factor domains: the verifier must enforce the transcript length required by the statement, rather than merely iterating over whatever rounds it receives.[^sumcheck]

A later review, before the branch was proposed for merge, went further on two points. The enrollment root alone was not enough: it did not fix where the enrolled weights end and the masks begin. The trusted anchor is now the enrollment's identity, a versioned digest of the root, the manifest, the geometry, the claims' row layout, and the padding rule, encoded identically by the Python and Rust verifiers.[^enrollment-identity]

The second gap was in the main proof, not only the bridge. The verifier checked each opened column's Merkle path by walking the direction bits the proof supplied rather than deriving them from the challenged index, so a valid path for a different column could answer a query. The verifiers now derive the path from the queried index, require the tree's exact depth, and check that the index is in range. The fix applies to `main` as well.[^index-binding]

These changes are distinct from the verifier-transparent weight split. They modify verification boundaries and need their own review and negative tests. They illustrate why a system can have correct arithmetic checks and still authenticate the wrong statement or accept an inadequately formed argument.

## Current state and the next questions

The profiler, calibration tooling, and earlier accounting corrections are merged upstream. The weight-split decomposition, caches, bridge integration and hardening, and later measurement archives are on the public [weight-split-model branch](https://github.com/JamesPetrie/VerInf/tree/weight-split-model). The latest external-weight profiler corrections are published there too, and [pull request 21](https://github.com/JamesPetrie/VerInf/pull/21) proposes the branch for merge into `main`. Implementation throughout this project is agent-assisted; I own the direction, experiments, review, and validation of the work described here as mine.

The immediate questions follow the current implementation:

- **What does the bridged proof cost as a whole?** The profiler now excludes external weights from ordinary witness counts, but does not yet price their enrollment, the per-proof bridge pass, or the bridge proof section. The measured stage breakdown supplies starting points for that model. Completing the private bridge form is a separate protocol requirement.
- **Which remaining work should run on additional devices?** The weight-split decomposition is validated on one GPU. A multi-device implementation must establish correct device-local execution and measure transfer and synchronization costs. Its baseline must reflect the protocol actually being distributed.
- **How much regeneration should be replaced by storage?** Witness caching competes with weights and working memory. The useful tradeoff changes with context length, hardware capacity, and host storage; it cannot be settled by a single cache benchmark.
- **What changes for larger and differently routed models?** Top-k routing and a second level of enrollment commitments are design work aimed at broader model support and smaller opening traffic. Neither is a demonstrated trillion-parameter deployment.

The repository also contains a separate sampled-audit approach, with a different detection guarantee from a full proof. Its timings are not included in the comparisons here. Selecting a proof or audit mode requires specifying what a verifier needs to establish and what probability of missed violations is acceptable.

The larger assurance question remains open. A proof must be about an approved computation, tied to the inputs and outputs that were actually observed, and checked under an appropriate soundness and confidentiality policy. Even then, a policy about permitted models needs an argument connecting those models to the risks the policy is meant to reduce. VerInf supplies a candidate computational component of that arrangement. The work now is to make its guarantees explicit and its costs tractable enough to find out where that component is useful.

[^original-run]: The [original run archive](https://github.com/JamesPetrie/VerInf/blob/2bdf823b08ea012cf5d26eeaac1c65698bb51e20/analysis/full-model-hidden-run-archive.md#runtimes) records 500 prompt and 500 continuation tokens, all hidden, with 40 columns opened and 20 Rust verifier threads. The prove time excludes the separate reveal and dump stages; the proof size is in decimal GB.

[^historical-security]: At the [pre-contribution snapshot](https://github.com/JamesPetrie/VerInf/tree/2bdf823b08ea012cf5d26eeaac1c65698bb51e20), `prover/core.py` supplied a fixed `MASTER_SEED` to the streaming setup. The [later protocol record](https://github.com/JamesPetrie/VerInf/blob/3508ef1d63d004686e85373f6100689ae94b922a/analysis/routed-projected-status.md#stages) documents fresh secret masking entropy, sequential Fiat–Shamir challenges, and external policy requirements. This qualification comes from comparing implementations; it is not a claim to have reconstructed an attack on the archived proof.

[^first-calibration]: The [first B200 archive](https://github.com/JamesPetrie/VerInf/blob/3508ef1d63d004686e85373f6100689ae94b922a/analysis/blackwell-session-1-archive.md#results) includes the extracted manifests, layout crosschecks, measured machine profile, and calibration logs. Agreement on the row count validates that part of the accounting independently of the runtime prediction.

[^batched-transforms]: See the batched NTT measurements in [H200 session 2](https://github.com/JamesPetrie/VerInf/blob/3508ef1d63d004686e85373f6100689ae94b922a/analysis/h200-session-2-archive.md#results) and [B200 session 3](https://github.com/JamesPetrie/VerInf/blob/3508ef1d63d004686e85373f6100689ae94b922a/analysis/b200-session-3-archive.md#results). These are comparisons with a bandwidth-based prediction, not measured slowdowns of the full prover.

[^routed-cache]: [H200 session 2](https://github.com/JamesPetrie/VerInf/blob/3508ef1d63d004686e85373f6100689ae94b922a/analysis/h200-session-2-archive.md#results) records 3,833.3 seconds with the routed-output cache off and 3,788.9 seconds with it on. The decoded-traffic counter describes work avoided across repeated sweeps, not the size of the stored model.

[^host-cache]: The [session-3 archive](https://github.com/JamesPetrie/VerInf/blob/3508ef1d63d004686e85373f6100689ae94b922a/analysis/b200-session-3-archive.md#results) retains the paired logs and a [diagnosis of host-memory pressure](https://github.com/JamesPetrie/VerInf/blob/3508ef1d63d004686e85373f6100689ae94b922a/analysis/b200-session-3-archive.md#what-d3-means). The approximately 19% regression belongs to this host and cache configuration.

[^gpu-cache]: In [session 4](https://github.com/JamesPetrie/VerInf/blob/3508ef1d63d004686e85373f6100689ae94b922a/analysis/b200-session-4-archive.md#results), the 3,982 dense resolutions became 362 initial decodes and 3,620 cache hits. Each cache comparison here uses its own same-host baseline; the absolute runtimes across sessions are not a controlled comparison.

[^split-gate]: The [weight-split review gate](https://github.com/JamesPetrie/VerInf/blob/3508ef1d63d004686e85373f6100689ae94b922a/analysis/weight-split-review-gate.md) covers two- and three-way partitions, differing fold and opening cuts, chunk boundaries, and both fold representations. Pinned secret randomness makes proof-byte identity a reproducible test condition, not a prescription for deployment.

[^bridge-comparison]: The table comes from the three same-host arms in [B200 session 4](https://github.com/JamesPetrie/VerInf/blob/3508ef1d63d004686e85373f6100689ae94b922a/analysis/b200-session-4-archive.md#results). The archive includes configurations, raw logs, and the smaller Rust verification gates. Its timing boundary is the return from the prover, which is why enrollment and subsequent serialization are excluded.

[^bridge-timing]: [B200 session 5](https://github.com/JamesPetrie/VerInf/blob/3508ef1d63d004686e85373f6100689ae94b922a/analysis/b200-session-5-archive.md#results) records the 198.5-second bridge stage alongside a 1,271.2-second full prove. [Resource sampling](https://github.com/JamesPetrie/VerInf/blob/3508ef1d63d004686e85373f6100689ae94b922a/analysis/b200-session-5-archive.md#what-it-means) found 144 Torch threads against a quota of approximately 30.6 CPUs. These observations motivate another controlled run; they do not isolate every cause of the total-runtime change.

[^bridge-policy]: The [policy repair](https://github.com/JamesPetrie/VerInf/commit/3c47d54) requires separate external approval of the ordinary dense-weight root and the expert-weight enrollment root. Checking that the proof is consistent with its own declared roots is insufficient.

[^sumcheck]: The [sumcheck repair](https://github.com/JamesPetrie/VerInf/commit/f426f97) enforces the expected number of rounds and the factor domains, with negative tests for malformed arguments.

[^enrollment-identity]: The [identity anchor](https://github.com/JamesPetrie/VerInf/commit/fd92b5e) and [its exact encoding](https://github.com/JamesPetrie/VerInf/commit/830d6fd) are described in [pull request 21](https://github.com/JamesPetrie/VerInf/pull/21).

[^index-binding]: The [index-bound opening](https://github.com/JamesPetrie/VerInf/commit/84dcc67) and the bridge's [counterpart for enrollment openings](https://github.com/JamesPetrie/VerInf/commit/76ce501) are listed under the fixes that also apply to `main` in [pull request 21](https://github.com/JamesPetrie/VerInf/pull/21).
