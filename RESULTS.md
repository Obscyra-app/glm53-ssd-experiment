# GLM-5.3-Flash on a 16 GB Mac: measured results

These October 5–6, 2026 experiments demonstrate local execution of a roughly
120 GB quantized model from an external SSD, with process memory around 5.5 GiB.
They also show a substantial latency cost: coding decode was below one token
per second, and fresh inputs could take minutes to process. This is a feasibility
experiment on one machine, not a general coding benchmark or a maximum-speed claim.

## Setup and timing conventions

The machine was a physical MacBook Air M3 with 16 GB RAM. Storage was an ADATA
LEGEND 960 MAX in a UGREEN CM847 enclosure; background applications remained
open. WARP 0.8.1 used CPU/NEON, VQ3R experts and a mixed Q4G/Q8G trunk. The profile
used a 6 GiB engine budget, 1536-token context allocation, Low reasoning effort,
greedy decoding, four compute threads and two I/O readers. Metal was disabled.
Pinned versions and weight provenance are in [provenance.json](package/provenance.json).

Decode rates count generated reasoning and control tokens as well as answer
tokens. Native decode time, first callback, first visible answer and full request
time are different measurements. An allocated 1536-token window does not imply
that a particular test filled it.

## Code generation

Two simple Python functions completed in the successful Low-effort retry:

| Function | Input / generated tokens | Request wall | Native decode |
|---|---:|---:|---:|
| `merge_intervals` | 67 / 103 | 264.49 s | 0.573 tokens/s |
| `first_unique` | 50 / 60 | 155.54 s | 0.704 tokens/s |

The unmodified generated functions passed **22 distinct functional and input
non-mutation checks**. Both ran serially in one resident engine; the complete run
took 421.88 seconds, with peak RSS about 5.50 GiB and zero observed system swap
growth. This was not first-attempt success: an earlier default-reasoning attempt
reached its 384-token limit without final code. The retry is recorded explicitly
in the [run receipt](results/two-function-run.json); generated functions and cases
are in [examples](examples/).

A separate three-task development series passed **24 functional checks**, but
two answers violated the requested output format. Native decode was
**0.653–0.681 tokens/s**. Those task materials are not included; only aggregate
outcomes are reported. Functional success did not imply reliable formatting.

The UI interval-merging request used 298 input tokens and generated 106 tokens.
It passed ten checks, with first visible answer at **514.48 seconds**, total
request time **704.60 seconds**, and native decode **0.541 tokens/s**. Different
inputs and background load prevent attributing its slower timing to the UI or
screen recording. See [measurement notes](package/BENCHMARKS.md).

## Context, repeated turns and memory

Fresh-input retrieval probes with **237, 486, 1019 and 1496 input tokens** each
returned the requested marker. Their elapsed times were 367.440, 745.592,
1556.818 and 2291.875 seconds. The last returned just eight output tokens after
**38 minutes 12 seconds**. These are marker-retrieval checks, not evidence of
long-context reasoning quality. Peak RSS across this series was approximately
5.52 GiB, with zero observed swap growth.

A local exact-prefix cache prototype produced identical output tokens and
**54.48–65.79% earlier first visible text** on short related turns with
26/43/60-token inputs. It reduced repeated input processing, not decode time.
Long, diverse histories were not measured. **This dialogue cache is not included
in the public standalone helper.**

A repeated arithmetic session completed 36/36 answers across twelve three-turn
cycles in 20 minutes 7 seconds, with repeatable tokens, zero observed swap growth
and a clean exit. This supports limited session stability, not arbitrary long
conversations. Zero swap growth in these runs is not a guarantee for other loads.

## Optimization attempts

The four-expert parallel candidate preserved exact output tokens but made the
two-function pair **3.26% and 4.17% slower** in the two request orders. It was
rejected; the baseline remained the default.

Two-request batching also preserved all 163 generated tokens. All 88 repeated
checks passed—**22 distinct cases repeated across four runs**, not 88 independent
cases. Pair wall time fell by **2.28% and 4.79%**, while the first visible answer
arrived later than for the first serial request. This was a small observed
throughput benefit with an individual-request latency tradeoff.

Joint prefill retained correctness but produced **2.30% and 10.24% earlier first
visible text** in the two orders. It missed the predeclared requirement of at
least 5% in both orders. Control timings drifted, so these measurements do not
establish a stable causal speedup. Batching and joint prefill remain experiments;
neither is part of the public helper.

No representative coding benchmark, perplexity study, original-precision quality
comparison or exhaustive optimization search was performed. The public helper
provides the tested baseline profile; the experimental outcomes above are not
claims that every prototype is shipped here.
