"""Score the frozen typo/phrasing set against one interpretation-fallback configuration.

Diagnostic, developer-written cases (frozen before the fallback code existed). One turn per case.
A case is correct when the response's status, intent and module all fall within the accepted sets
given for that case.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path
from time import sleep


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
FOLDER = PROJECT_ROOT / "experiments" / "evaluation" / "v2_5" / "results" / "diagnostics" / "llm_fallback"

from app.evaluation.intent_scoring import wilson_interval


def _split(value: str) -> set[str]:
    return {v for v in (value or "").split(";") if v}


def is_correct(case: dict, response: dict) -> bool:
    intents, modules, status = _split(case["accepted_intents"]), _split(case["accepted_modules"]), case["accepted_status"]
    module = (response.get("module") or {}).get("course_code")
    return ((not status or response.get("status") == status)
            and (not intents or response.get("intent") in intents)
            and (not modules or module in modules))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("none", "off", "fuzzy", "llm"), default="none",
                        help="none: the system as it was before the fallback existed (same as off). "
                             "off / fuzzy / llm: the interpretation_fallback setting for the test app.")
    parser.add_argument("--label", required=True)
    parser.add_argument("--pace-seconds", type=float, default=0.0,
                        help="Pause after each request in llm mode to stay under a provider's per-minute limit.")
    args = parser.parse_args()
    if args.pace_seconds < 0:
        raise SystemExit("--pace-seconds must be zero or positive.")

    freeze = json.loads((FOLDER / "fresh_cases.freeze.json").read_text(encoding="utf-8"))
    digest = hashlib.sha256((FOLDER / "fresh_cases.csv").read_bytes()).hexdigest()
    if digest != freeze["sha256"]:
        raise SystemExit("fresh_cases.csv changed after it was frozen; add a new case file instead.")
    with (FOLDER / "fresh_cases.csv").open(newline="", encoding="utf-8") as handle:
        cases = list(csv.DictReader(handle))

    mode = "off" if args.mode == "none" else args.mode
    # Set the server-side mode explicitly: requests can only lower it, and .env may say otherwise.
    os.environ["INTERPRETATION_FALLBACK"] = mode
    if mode != "llm":
        os.environ["GEMINI_API_KEY"] = ""
    from fastapi.testclient import TestClient
    from scripts.run_evaluation import _curricupath_components

    _, app = _curricupath_components()
    rows = []
    with TestClient(app) as client:
        for case in cases:
            payload = {"message": case["message"], "programme_code": case["programme"],
                       "interpretation_fallback": mode}
            response = client.post("/advisor", json=payload).json()
            rows.append({
                "case_id": case["case_id"], "category": case["category"], "message": case["message"],
                "status": response.get("status"), "intent": response.get("intent"),
                "module": (response.get("module") or {}).get("course_code"),
                "fallback": json.dumps(response.get("interpretation_fallback")),
                "correct": is_correct(case, response),
            })
            if mode == "llm":
                sleep(args.pace_seconds)

    out = FOLDER / args.label
    out.mkdir(parents=True, exist_ok=True)
    with (out / "cases.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    by_category = {}
    for category in dict.fromkeys(r["category"] for r in rows):
        rs = [r for r in rows if r["category"] == category]
        k = sum(r["correct"] for r in rs)
        by_category[category] = {"correct": k, "n": len(rs), "rate": k / len(rs), "ci95": wilson_interval(k, len(rs))}
    total = sum(r["correct"] for r in rows)
    summary = {"mode": args.mode, "label": args.label, "case_file_sha256": digest,
               "overall": {"correct": total, "n": len(rows), "rate": total / len(rows),
                           "ci95": wilson_interval(total, len(rows))},
               "by_category": by_category,
               "fallback_used": sum(r["fallback"] not in ("null", '"null"') for r in rows)}
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"{args.label} ({args.mode}): {total}/{len(rows)} correct")
    for category, v in by_category.items():
        print(f"  {category:14s} {v['correct']}/{v['n']}")
    print("  first-response statuses:", dict(Counter(r["status"] for r in rows)))


if __name__ == "__main__":
    main()
