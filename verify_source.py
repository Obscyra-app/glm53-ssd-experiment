#!/usr/bin/env python3
"""Verify the source-release checksums. Does not download or load weights."""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    failures = []
    count = 0
    for line in (ROOT / "SOURCE_SHA256SUMS").read_text().splitlines():
        expected, name = line.split("  ", 1)
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT):
            failures.append(f"unsafe path: {name}")
            continue
        if not path.is_file():
            failures.append(f"missing: {name}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            failures.append(f"SHA256 mismatch: {name}")
        count += 1
    if not count:
        failures.append("empty source manifest")
    if failures:
        raise SystemExit("FAIL\n" + "\n".join(failures))
    print(f"PASS: {count} source files. Weight integrity is checked by package/verify.py.")


if __name__ == "__main__":
    main()
