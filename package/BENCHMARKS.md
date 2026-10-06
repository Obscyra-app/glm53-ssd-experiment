# Local measurement notes

Measurements were made on a physical MacBook Air M3, 16 GB RAM, with an external ADATA LEGEND 960 MAX in a UGREEN CM847 enclosure. Background applications were open. These are observations, not isolated-hardware performance guarantees.

See `benchmark-results.json` for the numeric results and `provenance.json` for the pinned model and runtime.

- Three coding tasks passed 24 functional checks, but two answers violated the requested output format. Native decode ranged from 0.653 to 0.681 tokens/s.
- The recorded UI request asked for a Python interval-merging function, including touching intervals, sorted output, empty input and no input mutation. Its 298-token input included UI system instructions; 106 generated tokens include reasoning/control tokens. Ten functional/non-mutation checks passed.
- UI first visible text: 514.48 seconds. Total UI request: 704.60 seconds. Native decode: 195.91 seconds, 0.541 tokens/s. Peak process RSS: 5.50 GiB, observed system swap growth: zero.
- A separate 1496-token input retrieval probe returned its marker in a short eight-token output in 2291.875 seconds. This establishes one context/retrieval smoke, not long-context reasoning quality.

Different prompts and background loads prevent causal comparison of the recorded UI run with the earlier coding series. No claim that screen recording caused the difference is made. Zero observed swap growth is not a guarantee on other workloads.

The standalone release helper uses the same engine profile but one direct user message and a fresh process. It intentionally omits the experiment UI harness and dialogue checkpoint cache. Its validation result is recorded separately in `standalone-validation.json`.
