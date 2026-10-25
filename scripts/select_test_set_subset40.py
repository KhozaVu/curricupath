"""Freeze a 40-case subset nested inside the frozen 60-case subset of test set v1.

Same method as `select_test_set_subset.py` (proportional by reference label, round-robin over
scenario type, fixed seed) and chosen without reading any baseline result.
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_SET = PROJECT_ROOT / "experiments" / "evaluation" / "test_set_v1"
SIZE = 40
SEED = 20261002
OUTPUT = TEST_SET / "subset_40.json"


def main() -> None:
    if OUTPUT.exists():
        raise SystemExit(f"{OUTPUT.name} already exists; it is frozen.")
    freeze = json.loads((TEST_SET / "freeze.json").read_text(encoding="utf-8"))
    path = TEST_SET / "curricupath_test_set_v1.csv"
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != freeze["sha256"]:
        raise SystemExit("Test set changed after it was frozen.")
    pool_file = TEST_SET / "subset_60.json"
    pool_ids = set(json.loads(pool_file.read_text(encoding="utf-8"))["case_ids"])
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = [r for r in csv.DictReader(handle) if r["case_id"] in pool_ids]

    by_label = defaultdict(list)
    for row in rows:
        by_label[row["reference_label"]].append(row)
    exact = {label: SIZE * len(items) / len(rows) for label, items in by_label.items()}
    quota = {label: int(value) for label, value in exact.items()}
    for label in sorted(exact, key=lambda l: exact[l] - quota[l], reverse=True):
        if sum(quota.values()) < SIZE:
            quota[label] += 1

    rng = random.Random(SEED)
    chosen = []
    for label in sorted(by_label):
        groups = defaultdict(list)
        for row in sorted(by_label[label], key=lambda r: r["case_id"]):
            groups[row["scenario_type"]].append(row)
        for items in groups.values():
            rng.shuffle(items)
        order = sorted(groups)
        rng.shuffle(order)
        picked = []
        while len(picked) < quota[label]:
            progressed = False
            for scenario in order:
                if groups[scenario] and len(picked) < quota[label]:
                    picked.append(groups[scenario].pop())
                    progressed = True
            if not progressed:
                break
        chosen += picked

    record = {
        "size": len(chosen),
        "seed": SEED,
        "drawn_from": "subset_60.json",
        "drawn_from_sha256": digest,
        "method": "proportional by reference_label (largest remainder); round-robin over scenario_type",
        "chosen_before_any_baseline_result_was_read": True,
        "label_mix": dict(Counter(r["reference_label"] for r in chosen)),
        "split_mix": dict(Counter(r["split"] for r in chosen)),
        "scenario_types": len({r["scenario_type"] for r in chosen}),
        "case_ids": sorted(r["case_id"] for r in chosen),
    }
    OUTPUT.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in record.items() if k != "case_ids"}, indent=2))


if __name__ == "__main__":
    main()
