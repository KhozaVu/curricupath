"""Score test set v1 raw outputs: Macro-F1, unsafe decision rate and confusion matrices.

Writes CSV tables that the MATLAB figure script reads. An arm/level whose raw file does not
cover every case is scored on the cases it has and marked incomplete; it is never presented as
a finished result. Labels are the School registration reference adopted with the set
(no named independent reviewer).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.evaluation.scoring import (
    INVALID,
    LABELS,
    OUTCOMES,
    arm_metrics,
    bootstrap_metrics,
    encode,
    read_observations,
)
from scripts.run_test_set_v1 import ARMS, CASES_PATH, LEVELS, RAW, TEST_SET, verify_frozen


RESULTS = TEST_SET / "results"
SPLITS = ("all", "held_out", "development", "subset60", "subset40")
N_BOOT = 5_000
SEED = 20261001


def _cases() -> list[dict[str, str]]:
    with CASES_PATH.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=RAW)
    parser.add_argument("--results-dir", type=Path, default=RESULTS)
    args = parser.parse_args()
    raw_dir = args.raw_dir if args.raw_dir.is_absolute() else PROJECT_ROOT / args.raw_dir
    results_dir = (
        args.results_dir if args.results_dir.is_absolute() else PROJECT_ROOT / args.results_dir
    )
    digest = verify_frozen()
    cases = _cases()
    rows, summary, confusion_rows = [], {"case_file_sha256": digest, "label_source": (
        "School of EIE registration reference (Admin Manager, 2026-09-30); adopted, "
        "no named independent reviewer"), "results": {}}, []
    for split in SPLITS:
        if split in {"subset60", "subset40"}:
            name = "subset_60.json" if split == "subset60" else "subset_40.json"
            members = set(json.loads((TEST_SET / name).read_text(encoding="utf-8"))["case_ids"])
            scoped = [c for c in cases if c["case_id"] in members]
        else:
            scoped = [c for c in cases if split == "all" or c["split"] == split]
        ids = [c["case_id"] for c in scoped]
        reference = encode([c["reference_label"] for c in scoped])
        for level in LEVELS:
            predictions, meta = {}, {}
            for arm in ARMS:
                path = raw_dir / f"{arm}__{level}.jsonl"
                observations = read_observations(path) if path.exists() else []
                by_case = {o.case_id: o for o in observations}
                missing = [i for i in ids if i not in by_case]
                if len(missing) == len(ids):
                    continue
                present = [i for i in ids if i in by_case]
                predictions[arm] = (present, encode([by_case[i].decision for i in present]))
                meta[arm] = {
                    "missing": len(missing),
                    "provider_failures": sum(by_case[i].provider_failure for i in present),
                }
            for arm, (present, predicted) in predictions.items():
                ref = encode([next(c["reference_label"] for c in scoped if c["case_id"] == i) for i in present])
                metrics = arm_metrics(ref, predicted)
                draws = bootstrap_metrics(ref, {arm: predicted}, n_boot=N_BOOT, seed=SEED)[arm]["macro_f1"]
                low, high = (float(v) for v in np.percentile(draws, [2.5, 97.5]))
                unsafe = metrics["safety"]["unsafe_false_positive_rate"]
                complete = meta[arm]["missing"] == 0
                rows.append({
                    "split": split, "level": level, "arm": arm,
                    "n_scored": metrics["n_cases"], "n_missing": meta[arm]["missing"],
                    "complete": int(complete),
                    "macro_f1": round(metrics["macro_f1"], 4),
                    "macro_f1_ci_low": round(low, 4), "macro_f1_ci_high": round(high, 4),
                    "unsafe_rate": unsafe["rate"] if unsafe["rate"] is not None else "",
                    "unsafe_numerator": unsafe["numerator"], "unsafe_denominator": unsafe["denominator"],
                    "invalid_rate": metrics["safety"]["invalid_output_rate"]["rate"],
                    "balanced_accuracy": round(metrics["balanced_accuracy"], 4),
                    "provider_failures": meta[arm]["provider_failures"],
                })
                summary["results"].setdefault(split, {}).setdefault(level, {})[arm] = {
                    **metrics, "macro_f1_ci95": [low, high], "complete": complete,
                    "missing_cases": meta[arm]["missing"],
                }
                counts = metrics["confusion_matrix"]["counts"]
                for r, ref_label in enumerate(LABELS):
                    for c, pred_label in enumerate(OUTCOMES):
                        confusion_rows.append({"split": split, "level": level, "arm": arm,
                                               "reference": ref_label, "predicted": pred_label,
                                               "count": counts[r][c]})
    results_dir.mkdir(parents=True, exist_ok=True)
    with (results_dir / "metrics_by_level.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with (results_dir / "confusion_long.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(confusion_rows[0]))
        writer.writeheader()
        writer.writerows(confusion_rows)
    (results_dir / "metrics_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )

    print("split=all  (Macro-F1 [95% CI] | unsafe rate | complete)")
    for row in rows:
        if row["split"] == "all":
            print(f"  {row['level']:6s} {row['arm']:30s} {row['macro_f1']:.3f} "
                  f"[{row['macro_f1_ci_low']:.3f}, {row['macro_f1_ci_high']:.3f}] | "
                  f"{row['unsafe_numerator']}/{row['unsafe_denominator']} | "
                  f"{'yes' if row['complete'] else 'NO, missing ' + str(row['n_missing'])}")


if __name__ == "__main__":
    main()
