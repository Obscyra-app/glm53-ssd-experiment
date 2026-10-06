---
license: mit
base_model: zai-org/GLM-5.3-Flash
base_model_relation: quantized
pipeline_tag: text-generation
tags:
- warp
- vq3r
- quantized
- moe
- apple-silicon
- ssd-offload
- custom-runtime
---

# GLM-5.3-Flash — WARP VQ3R

Community conversion of [Z.ai GLM-5.3-Flash](https://huggingface.co/zai-org/GLM-5.3-Flash) for [WARP](https://github.com/sqliteai/warp), tested on a **physical MacBook Air M3 with 16 GB unified memory and an external SSD**. The complete custom `.waste` container is **119,962,584,020 bytes (~120 GB / 111.72 GiB), 50 files**.

This package saves the original-weight download and local conversion step. Z.ai created the base model; SQLite Cloud created WARP and its VQ3R algorithm; Nurymanau prepared and tested this conversion and its packaging helpers. No new model architecture or quantization algorithm is claimed.

**Requires WARP.** This is not a GGUF or MLX checkpoint and cannot be loaded directly by Transformers, Ollama, llama.cpp or stock MLX. The tested engine uses CPU/NEON and streams selected experts from SSD; it is not an MLX/GPU run. No hosted inference widget is provided.

## What is included

- Complete `glm53-vq3r.waste/`: VQ3R expert weights, mixed Q4G/Q8G trunk, tokenizer, chat metadata, codebooks and manifest.
- A single-request `quickstart.py`, using Low reasoning, greedy generation and the tested 6 GiB engine budget.
- `verify.py`, `SHA256SUMS`, `weights-manifest.json`, provenance and limited benchmark results.
- The bounded-memory conversion helper and recorded conversion dependency versions for reproducibility.

Text generation is the validated use case. Vision metadata exists in the container, but image input, tool use and broad model-quality parity have not been validated in this release. The helper accepts text only. It does not implement the private experiment's persistent dialogue cache or DIMUL integration.

## Download

Use Python 3.11+ and the Hugging Face Python library. Avoid a bare `hf` command if another application on your computer already uses that name.

```sh
python3 -m venv .venv-download
.venv-download/bin/pip install huggingface_hub
.venv-download/bin/python -c "from huggingface_hub import snapshot_download; snapshot_download('Nurymanau/GLM-5.3-Flash-WARP-VQ3R', local_dir='GLM-5.3-Flash-WARP-VQ3R')"
cd GLM-5.3-Flash-WARP-VQ3R
python3 verify.py
```

Allow at least the 120 GB download size plus operational free space on your SSD. Full SHA verification reads all files and takes several minutes depending on storage. Downloads can be resumed by repeating the command.

## Build the pinned runtime and run

Tested on Apple Silicon macOS with Xcode Command Line Tools (`clang`, `make`, `git`) and Python 3.11. Build the exact WARP revision below; its CLI/library still use the historical `waste` name.

```sh
git clone https://github.com/sqliteai/warp.git warp
git -C warp checkout --detach 09fcff352ca55223b08ee222d15054b90546c6a9
make -C warp -j2
python3 quickstart.py --check
python3 quickstart.py 'Reply exactly: OK' --max-tokens 32
python3 quickstart.py 'Write a Python function that merges overlapping or touching intervals without mutating its input. Return only the function.' --max-tokens 256
```

The helper itself uses only Python's standard library and WARP's source bindings. It verifies binding-source hashes and container file sizes before execution; `verify.py` verifies all published file hashes. Build output is platform-dependent and is not expected to match the original Mac's binary SHA256.

The total context is **1536 tokens including the output reserve**. Longer requests are rejected rather than truncated. Default output limit is 128 tokens, including reasoning/control tokens; default total timeout is 1800 seconds. `--max-tokens` accepts 1–768 and `--timeout` accepts 60–3600. An output limit reached before completion exits with code 2 and reports `complete: false`. Ctrl+C stops the worker and unloads the weights.

The launcher samples process-group RSS and system swap once per second, stopping above 9 GiB RSS or 512 MiB additional system swap. These are sampled limits, not allocator guarantees; other applications can increase system swap and trigger a stop. Its lock prevents a second instance of this helper in the same release folder; keep other model runtimes stopped yourself.

The Low-reasoning system marker is set explicitly in the helper because the converted `chat.json` does not contain an effort field. The original container remains byte-for-byte unchanged. Selected settings: 4 compute threads, 2 readers, depth 2, lookahead 6, LFRU cache, CRC verification, temperature 0, seed 42.

## Measured performance and limits

See [BENCHMARKS.md](BENCHMARKS.md) and [benchmark-results.json](benchmark-results.json). The measurements below were collected in the local experiment before standalone packaging, using the same container and engine revision. They are not broad accuracy benchmarks or predictions for a different Mac/SSD.

| Observation | Measured result |
|---|---:|
| Three small coding requests | 0.653–0.681 generated tokens/s |
| Recorded DIMUL coding request | 0.541 generated tokens/s |
| Recorded request input/output | 298 / 106 tokens |
| Recorded first visible answer | 514.48 s (8 min 34 s) |
| Recorded total request time | 704.60 s (11 min 45 s) |
| Recorded peak process RSS | ~5.50 GiB |
| Recorded system swap growth | 0 |

Decode throughput includes reasoning and control tokens and excludes prompt processing. Visible characters per second are a different metric. The DIMUL prompt includes its compact system instructions, so the standalone example does not reproduce its exact input or timing.

Prefill is slow: one 1496-input-token retrieval request with a short output took approximately 38 minutes. An external SSD and physical 16 GB machine behave differently from a large-memory machine with an artificial engine budget. This release is useful for experimentation, not a claim of fast interactive coding.

Three small local coding tasks passed 24 functional checks, with formatting violations in two answers; the recorded interval-merging function passed ten input/non-mutation checks. No BF16/FP8 baseline comparison, perplexity evaluation or general coding benchmark was performed. Quantization can reduce quality.

## Conversion provenance

Base revision: `eb9eb208eb0d988989d07a6a12d0fdeb5f52574a`.
WARP revision: `09fcff352ca55223b08ee222d15054b90546c6a9` (engine 0.8.1).

The 62 source weight shards totaled 328,337,455,672 bytes and were SHA256-verified before conversion. A single CPU conversion worker used WARP's default VQ3R expert quantization and 4-bit trunk settings, with sensitive tensors retaining the upstream Q8 format. `convert_bounded.py` streams the large embedding/output-head Q8 matrices in 256-row chunks. Local synthetic checks matched the original Q8 and trunk bytes/index; they do not establish whole-model quality parity.

For a fresh conversion, separately download the pinned original model to `source/`, build WARP above, create a Python 3.11 environment with `conversion-requirements.txt`, then run from this release folder:

```sh
OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 VECLIB_MAXIMUM_THREADS=4 python convert_bounded.py --self-test
OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 VECLIB_MAXIMUM_THREADS=4 python convert_bounded.py --src source --out rebuilt.waste --jobs 1 --device cpu --reclaim dry
```

`--reclaim dry` retains source files. Conversion needs much more disk space than using this ready-made container and is not necessary for inference. Dependency versions are the recorded environment, not a guarantee on every platform. Monitor memory and disk during conversion; the helper alone does not include the local experiment's conversion supervisor.

## License

The base weights are MIT, Copyright (c) 2026 Z.AI Co., Ltd; see [LICENSE](LICENSE). Packaging helpers are MIT, Copyright (c) 2026 Nurymanau. WARP is a separately obtained Apache-2.0 dependency. See [NOTICE](NOTICE). Retain the respective licenses and attribution when redistributing.
