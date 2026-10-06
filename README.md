# GLM-5.3-Flash on a 16 GB MacBook Air + external SSD

A local experiment with a community VQ3R conversion of **GLM-5.3-Flash**, running through **WARP 0.8.1 on CPU/NEON**. Tested on a physical **MacBook Air M3, 16 GB unified memory**, with weights streamed from an external SSD.

The model ran within a 6 GiB engine budget. Three small coding requests generated **0.653–0.681 tokens/s**; a recorded DIMUL request generated **0.541 tokens/s**, with **8 min 34 s to first visible text** and approximately **5.50 GiB peak process RSS**. This is a feasibility experiment: prompt processing and generation remain slow.

| Artifact | Location |
|---|---|
| Ready-made weights (~120 GB) | [Hugging Face, pinned release](https://huggingface.co/Nurymanau/GLM-5.3-Flash-WARP-VQ3R/tree/81fc33cff865a63e1a77946d0b7ff8c8feb5b73b) |
| Experiment outcomes and limitations | [RESULTS.md](RESULTS.md) |
| Two generated Python functions, 22 functional cases | [examples/](examples/) |
| Launcher, bounded-memory converter, original model card | [package/](package/) |
| Measured coding and UI results | [package/benchmark-results.json](package/benchmark-results.json) |
| Published file-integrity receipt | [results/hf-integrity.json](results/hf-integrity.json) |

The Git repository contains source, examples and measurements. The 50-file weight container is **119,962,584,020 bytes (111.72 GiB)** and is downloaded separately. `package/` preserves all 14 helper/document files byte-for-byte from the pinned HF release.

## Check the source and saved examples

Python 3.11+; these commands use the standard library and do not load the model:

```sh
git clone https://github.com/Obscyra-app/glm53-ssd-experiment.git
cd glm53-ssd-experiment
python3 verify_source.py
python3 examples/check_examples.py
python3 download_weights.py --plan
```

The two saved functions passed 22 cases without manual edits in a **successful Low-reasoning retry**. An earlier default-reasoning attempt exhausted its output limit without final code. These examples are small functional checks, not a general coding benchmark.

## Download, verify and run

Requirements: Apple Silicon macOS, Python 3.11+, Xcode Command Line Tools (`clang`, `make`, `git`), and at least the 120 GB weight size plus operational free space on an SSD. The measured drive was an ADATA LEGEND 960 MAX in a UGREEN CM847 enclosure. Background applications were open during the experiment.

```sh
python3 -m venv .venv-download
.venv-download/bin/pip install huggingface_hub
.venv-download/bin/python download_weights.py
python3 package/verify.py

git clone https://github.com/sqliteai/warp.git package/warp
git -C package/warp checkout --detach 09fcff352ca55223b08ee222d15054b90546c6a9
make -C package/warp -j2
python3 package/quickstart.py --check
python3 package/quickstart.py 'Reply exactly: OK' --max-tokens 32
```

The downloader requests exactly the 50 container files from HF revision `81fc33cff865a63e1a77946d0b7ff8c8feb5b73b`; repeat it to resume. It never replaces the included helper files. `package/verify.py` reads all downloaded files to check SHA256, so verification itself takes time. To use an existing copy instead of downloading, verify that copy and supply `--model /path/to/glm53-vq3r.waste` to the launcher.

Try a coding request:

```sh
python3 package/quickstart.py 'Python only: implement first_unique(s): return the first character occurring exactly once, or None. Case sensitive; Unicode allowed. O(n) time. No imports. Return only the function.' --max-tokens 256
```

The single-request launcher uses Low reasoning, greedy decoding, a **1536-token total context including output reserve**, four compute threads and two SSD readers. It samples RSS and system swap, with stop thresholds of 9 GiB RSS and 512 MiB additional swap; see [the original model card](package/README.md) for limits, timeouts and conversion instructions. It does not include the experimental persistent prefix cache or a DIMUL server.

This is a custom WARP `.waste` container, not a GGUF or MLX checkpoint. Only text was validated. Speed figures count generated reasoning/control tokens and exclude prefill; first visible text is reported separately. No BF16/FP8 quality comparison, perplexity test or broad coding benchmark was performed.

## Attribution and license

Z.AI created [GLM-5.3-Flash](https://huggingface.co/zai-org/GLM-5.3-Flash); SQLite Cloud created [WARP and VQ3R](https://github.com/sqliteai/warp). Nurymanau prepared this conversion, packaging and local experiments. No new architecture or quantization algorithm is claimed.

Repository helpers and documentation are MIT ([LICENSE](LICENSE)). The original base-model license and attribution remain in [package/LICENSE](package/LICENSE) and [package/NOTICE](package/NOTICE). WARP is a separately obtained Apache-2.0 dependency. No affiliation or endorsement is implied.
