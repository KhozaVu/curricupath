"""Score the clarification set: final decisions after any scripted reply, and the questions asked.

Primary population: 'ask' cases (a needed fact is unknown). Controls (fact already known) and
irrelevant-unknown cases check that the system does not ask when it does not need to.
Labels are developer-proposed (pending academic review), not independent evidence.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
from scripts.run_clarification_set_v2 import ARMS, RAW, SET, load_cases, verify_frozen


RESULTS = SET / "results"


def wilson(k: int, n: int) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    z, p = 1.96, k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def main() -> None:
    digest = verify_frozen()
    cases = {c["case_id"]: c for c in load_cases()}
    rows, per_type, paired_rows = [], [], []
    finals: dict[str, dict[str, dict]] = {}
    for arm in ARMS:
        path = RAW / f"{arm}.jsonl"
        if not path.exists():
            continue
        records = {r["case_id"]: r for r in (json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip())}
        finals[arm] = records
        for population in ("ask", "control", "irrelevant"):
            subset = [r for r in records.values() if r["kind"] == population]
            n = len(subset)
            correct = sum(r["final_decision"] == cases[r["case_id"]]["reference_label"] for r in subset)
            unresolved = sum(r["final_decision"] == "none" for r in subset)
            wrong = n - correct - unresolved
            unsafe_n = sum(cases[r["case_id"]]["reference_label"] == "ineligible" for r in subset)
            unsafe = sum(r["final_decision"] == "eligible" and cases[r["case_id"]]["reference_label"] == "ineligible" for r in subset)
            asked = sum(bool(r["asked"]) for r in subset)
            lo, hi = wilson(correct, n)
            rows.append({
                "arm": arm, "population": population, "n": n, "correct": correct,
                "accuracy": round(correct / n, 4) if n else "", "acc_ci_low": round(lo, 4),
                "acc_ci_high": round(hi, 4), "unresolved": unresolved, "wrong_decision": wrong,
                "unsafe_eligible_on_ineligible": unsafe, "unsafe_denominator": unsafe_n,
                "questions_asked": asked,
                "question_rate": round(asked / n, 4) if n else "",
            })
        for fact_type in sorted({r["fact_type"] for r in records.values() if r["kind"] == "ask"}):
            subset = [r for r in records.values() if r["kind"] == "ask" and r["fact_type"] == fact_type]
            correct = sum(r["final_decision"] == cases[r["case_id"]]["reference_label"] for r in subset)
            per_type.append({"arm": arm, "fact_type": fact_type, "n": len(subset), "correct": correct,
                             "accuracy": round(correct / len(subset), 4),
                             "unresolved": sum(r["final_decision"] == "none" for r in subset)})
    # Paired comparisons on ask cases: how many cases one arm gets right and the other wrong.
    ask_ids = [cid for cid, c in cases.items() if c["kind"] == "ask"]
    def ok(arm, cid):
        return finals[arm][cid]["final_decision"] == cases[cid]["reference_label"]
    for a, b in (("clarify", "no_clarification"), ("clarify", "assume_absent"), ("clarify", "oracle")):
        if a in finals and b in finals:
            only_a = sum(ok(a, i) and not ok(b, i) for i in ask_ids)
            only_b = sum(ok(b, i) and not ok(a, i) for i in ask_ids)
            paired_rows.append({"arm_a": a, "arm_b": b, "n": len(ask_ids),
                                "a_right_b_wrong": only_a, "b_right_a_wrong": only_b,
                                "both_right": sum(ok(a, i) and ok(b, i) for i in ask_ids),
                                "both_wrong": sum((not ok(a, i)) and (not ok(b, i)) for i in ask_ids)})
    # Cases where clarify fails: list for inspection
    misses = []
    if "clarify" in finals:
        for cid in ask_ids:
            r = finals["clarify"][cid]
            if r["final_decision"] != cases[cid]["reference_label"]:
                misses.append({"case_id": cid, "fact_type": cases[cid]["fact_type"],
                               "reply": cases[cid]["scripted_reply"], "reference": cases[cid]["reference_label"],
                               "got": r["final_decision"], "status": r["final_status"],
                               "answer": r["final_answer"][:140]})

    RESULTS.mkdir(parents=True, exist_ok=True)
    def write(name, data):
        if data:
            with (RESULTS / name).open("w", newline="", encoding="utf-8") as h:
                w = csv.DictWriter(h, fieldnames=list(data[0])); w.writeheader(); w.writerows(data)
    write("metrics_by_arm.csv", rows)
    write("metrics_by_fact_type.csv", per_type)
    write("paired_comparison.csv", paired_rows)
    write("clarify_misses.csv", misses)
    (RESULTS / "summary.json").write_text(json.dumps({"case_file_sha256": digest, "arms": rows,
        "by_fact_type": per_type, "paired": paired_rows, "clarify_misses": misses}, indent=2) + "\n", encoding="utf-8")

    print("ASK cases (a needed fact is unknown)")
    for r in rows:
        if r["population"] == "ask":
            print(f"  {r['arm']:18s} correct {r['correct']:2d}/{r['n']} ({r['accuracy']:.2f}) "
                  f"unresolved {r['unresolved']:2d} wrong {r['wrong_decision']:2d} "
                  f"unsafe {r['unsafe_eligible_on_ineligible']}/{r['unsafe_denominator']} questions {r['questions_asked']}")
    print("CONTROLS / IRRELEVANT (no question needed): questions asked, accuracy")
    for r in rows:
        if r["population"] in {"control", "irrelevant"}:
            print(f"  {r['arm']:18s} {r['population']:10s} asked {r['questions_asked']:2d}/{r['n']} correct {r['correct']}/{r['n']}")
    print("Paired (ask cases):", *[f"{p['arm_a']} vs {p['arm_b']}: {p['a_right_b_wrong']} vs {p['b_right_a_wrong']}" for p in paired_rows], sep="\n  ")
    print(f"clarify misses: {len(misses)}")
    for m in misses[:10]:
        print("  ", m)


if __name__ == "__main__":
    main()
