#!/usr/bin/env python3
"""Download the pinned public container; never load the model or replace helpers."""
import argparse
import json
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent
REPO = "Nurymanau/GLM-5.3-Flash-WARP-VQ3R"
REVISION = "81fc33cff865a63e1a77946d0b7ff8c8feb5b73b"


def container_files():
    files = []
    for line in (ROOT / "package" / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split("  ", 1)
        path = PurePosixPath(name)
        if path.parts[0] != "glm53-vq3r.waste":
            continue
        if path.is_absolute() or ".." in path.parts or len(path.parts) != 2:
            raise ValueError(f"Invalid container path: {name}")
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError(f"Invalid SHA256 for {name}")
        files.append(name)
    if len(files) != 50 or len(set(files)) != 50:
        raise ValueError("Expected exactly 50 unique container files")
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", action="store_true", help="Print scope without network or downloads")
    args = parser.parse_args()
    files = container_files()
    if args.plan:
        print(json.dumps({"repo": REPO, "revision": REVISION, "destination": "package/",
                          "container_bytes": 119962584020, "files": files}, indent=2))
        return
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        parser.exit(2, "Install huggingface_hub in your download environment first.\n")
    snapshot_download(repo_id=REPO, revision=REVISION, repo_type="model", token=False,
                      local_dir=ROOT / "package", allow_patterns=files)
    print("Download finished. Run: python3 package/verify.py")


if __name__ == "__main__":
    main()
