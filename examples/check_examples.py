#!/usr/bin/env python3
"""Recheck the saved model-generated functions without running a model."""
import copy
import hashlib
import json
from pathlib import Path

from first_unique import first_unique
from merge_intervals import merge_intervals

ROOT = Path(__file__).resolve().parent


def main():
    receipt = json.loads((ROOT.parent / "results" / "two-function-run.json").read_text())
    for name, metadata in receipt["tasks"].items():
        actual = hashlib.sha256((ROOT / f"{name}.py").read_bytes()).hexdigest()
        if actual != metadata["code_sha256"]:
            raise SystemExit(f"FAIL: {name} differs from the saved model output")
    cases = json.loads((ROOT / "cases.json").read_text())
    passed = 0
    failures = []
    for name, function in [("merge_intervals", merge_intervals), ("first_unique", first_unique)]:
        for i, case in enumerate(cases[name], 1):
            argument = copy.deepcopy(case["input"])
            result = function(argument)
            if result == case["expected"] and argument == case["input"]:
                passed += 1
            else:
                failures.append(f"{name} case {i}: wrong result or modified input")
    total = sum(len(items) for items in cases.values())
    if total != 22 or failures:
        raise SystemExit(f"FAIL: {passed}/{total}\n" + "\n".join(failures))
    print("PASS: 22/22 functional cases; original source hashes match; inputs unchanged.")


if __name__ == "__main__":
    main()
