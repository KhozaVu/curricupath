"""Recounts of existing test-set-v1 outputs: evidence sufficiency, abstention and wording level.

No new model runs. Population: the frozen 40-case subset (the only cases all five systems ran).
Deterministic systems appear twice: before the School-grid rules were loaded (results/raw) and
after (results_post_grid_final, development-informed and partly circular because the labels and
the grid share a source). Per-level rows are single observations per case, so Wilson intervals
are valid; 'pooled' rows add the three wordings of the same cases and carry counts only.
Labels: School registration reference, adopted, no independent reviewer.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
T = PROJECT_ROOT / "experiments" / "evaluation" / "test_set_v1"
OUT = T / "results_uncertainty"
LEVELS = ("low", "medium", "high")
DECIDABLE = {"eligible", "ineligible"}

from app.evaluation.scoring import decision_from_record  # noqa: E402

SYSTEMS = [
    # (label, raw directory, arm file stem, group)
    ("handbook_rag", "results", "handbook_rag", "llm"),
    ("structured_rules_llm", "results", "structured_rules_llm", "llm"),
    ("curricupath_before_grid", "results", "curricupath", "deterministic"),
    ("rules_only_before_grid", "results", "rules_only", "deterministic"),
    ("curricupath_after_grid", "results_post_grid_final", "curricupath", "deterministic"),
    ("rules_only_after_grid", "results_post_grid_final", "rules_only", "deterministic"),
]


def wilson(k: int, n: int) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    z, p = 1.96, k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (max(0.0, c - h), min(1.0, c + h))


def load_decisions(directory: str, stem: str, level: str) -> dict[str, str]:
    path = T / directory / "raw" / f"{stem}__{level}.jsonl"
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            record = json.loads(line)
            out[str(record["case_id"])] = decision_from_record(record)
    return out


def fmt(value):
    return "" if value is None else round(value, 4)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cases = {r["case_id"]: r for r in csv.DictReader((T / "curricupath_test_set_v1.csv").open(encoding="utf-8-sig"))}
    ids = sorted(json.loads((T / "subset_40.json").read_text(encoding="utf-8"))["case_ids"])
    strata = {
        "source_sufficient": [i for i in ids if cases[i]["answerable_from_handbook"] == "true"],
        "source_insufficient": [i for i in ids if cases[i]["answerable_from_handbook"] == "false"],
        "needs_review_reference": [i for i in ids if cases[i]["reference_label"] == "manual_review_required"],
        "all_40": ids,
    }
    decisions = {(s[0], lv): load_decisions(s[1], s[2], lv) for s in SYSTEMS for lv in LEVELS}

    sufficiency, abstention, wording = [], [], []
    for label, _, _, group in SYSTEMS:
        for level in LEVELS + ("pooled",):
            levels = LEVELS if level == "pooled" else (level,)
            obs = [(i, decisions[(label, lv)].get(i, "invalid")) for lv in levels for i in ids]
            ref = {i: cases[i]["reference_label"] for i in ids}

            def count(sub, pred):
                s = set(sub)
                return sum(1 for i, d in obs if i in s and pred(ref[i], d))

            for name, members in strata.items():
                n = len(members) * len(levels)
                correct = count(members, lambda r, d: d == r)
                unsafe_n = count(members, lambda r, d: r != "eligible" and True)
                unsafe = count(members, lambda r, d: r != "eligible" and d == "eligible")
                undecided = count(members, lambda r, d: d == "invalid")
                row = {"system": label, "group": group, "level": level, "stratum": name, "n": n,
                       "correct": correct, "accuracy": fmt(correct / n if n else None),
                       "unsafe_eligible": unsafe, "not_eligible_reference": unsafe_n,
                       "no_decision": undecided}
                if level != "pooled":
                    lo, hi = wilson(correct, n)
                    row.update({"acc_ci_low": fmt(lo), "acc_ci_high": fmt(hi)})
                sufficiency.append(row)

            # Abstention: defer = manual_review_required. Positive class = reference needs review.
            all_ids = ids
            pred_defer = count(all_ids, lambda r, d: d == "manual_review_required")
            tp = count(all_ids, lambda r, d: r == "manual_review_required" and d == "manual_review_required")
            ref_defer = count(all_ids, lambda r, d: r == "manual_review_required")
            decidable_ref = count(all_ids, lambda r, d: r in DECIDABLE)
            over = count(all_ids, lambda r, d: r in DECIDABLE and d == "manual_review_required")
            under = count(all_ids, lambda r, d: r == "manual_review_required" and d in DECIDABLE)
            unsupported = count(all_ids, lambda r, d: r == "manual_review_required" and d == "eligible")
            abstention.append({
                "system": label, "group": group, "level": level,
                "reference_needs_review": ref_defer, "predicted_defer": pred_defer, "true_defer": tp,
                "defer_precision": fmt(tp / pred_defer if pred_defer else None),
                "defer_recall": fmt(tp / ref_defer if ref_defer else None),
                "over_referral_rate": fmt(over / decidable_ref if decidable_ref else None),
                "over_referrals": over, "decidable_reference": decidable_ref,
                "under_referral_rate": fmt(under / ref_defer if ref_defer else None),
                "unsupported_eligible_on_review": unsupported,
            })

            n = len(ids) * len(levels)
            correct = count(ids, lambda r, d: d == r)
            decided = count(ids, lambda r, d: d in {"eligible", "ineligible", "manual_review_required"})
            unsafe = count(ids, lambda r, d: r != "eligible" and d == "eligible")
            unsafe_den = count(ids, lambda r, d: r != "eligible")
            wording.append({"system": label, "group": group, "level": level, "n": n, "correct": correct,
                            "accuracy": fmt(correct / n), "decided": decided,
                            "unsafe_eligible": unsafe, "unsafe_denominator": unsafe_den,
                            "unsafe_rate": fmt(unsafe / unsafe_den if unsafe_den else None)})

    def write(name, rows):
        with (OUT / name).open("w", newline="", encoding="utf-8") as h:
            w = csv.DictWriter(h, fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
            w.writeheader(); w.writerows(rows)

    write("sufficiency_split.csv", sufficiency)
    write("abstention.csv", abstention)
    write("wording_levels.csv", wording)

    print("EVIDENCE SUFFICIENCY (pooled over 3 wordings; counts, 40 cases x 3):")
    for s in SYSTEMS:
        row = {r["stratum"]: r for r in sufficiency if r["system"] == s[0] and r["level"] == "pooled"}
        print(f"  {s[0]:26s} sufficient {row['source_sufficient']['correct']:3d}/{row['source_sufficient']['n']:3d}"
              f" (unsafe {row['source_sufficient']['unsafe_eligible']:2d}) | insufficient {row['source_insufficient']['correct']:3d}/{row['source_insufficient']['n']:3d}"
              f" (unsafe {row['source_insufficient']['unsafe_eligible']:2d}) | needs-review ref {row['needs_review_reference']['correct']:2d}/{row['needs_review_reference']['n']:2d}")
    print("ABSTENTION (level=low):")
    for r in abstention:
        if r["level"] == "low":
            print(f"  {r['system']:26s} defer-precision {r['defer_precision']!s:6s} defer-recall {r['defer_recall']!s:6s} "
                  f"over-referral {r['over_referral_rate']!s:6s} under-referral {r['under_referral_rate']!s:6s}")
    print("WORDING (accuracy | unsafe):")
    for s in SYSTEMS:
        cells = {r["level"]: r for r in wording if r["system"] == s[0]}
        print(f"  {s[0]:26s} " + "  ".join(f"{lv}: {cells[lv]['accuracy']:.2f}|{cells[lv]['unsafe_eligible']}" for lv in LEVELS))


if __name__ == "__main__":
    main()
