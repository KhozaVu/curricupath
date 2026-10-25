"""Run the clarification test set (v2) under four conditions and record every turn.

Conditions (same cases, same engine, no language model involved):
  clarify          CurricuPath asks when a needed fact is unknown; the scripted reply is sent as
                   the next message; the FINAL decision is scored.
  no_clarification CurricuPath may not ask. Per the v2.5 protocol it receives the question plus
                   the scripted fact as text ("Additional declared fact: ...") up front.
  assume_absent    Legacy behaviour with no history flag: a module not listed is treated as not
                   completed, so nothing is ever asked (a naive guess).
  oracle           The facts are given as structured data (the matched control profile). This is a
                   ceiling, not a competitor.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path
from time import perf_counter


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
import os
SET = PROJECT_ROOT / "experiments" / "evaluation" / os.environ.get("CLARIFICATION_SET", "clarification_set_v2")
RAW = SET / "results" / "raw"
ARMS = ("clarify", "no_clarification", "assume_absent", "oracle")
FACT_PREFIX = "Additional declared fact: "
DECISIONS = {"eligible", "ineligible", "manual_review_required"}

from scripts.run_test_set_v1 import curricupath_components


def verify_frozen() -> str:
    freeze = json.loads((SET / "freeze.json").read_text(encoding="utf-8"))
    digest = hashlib.sha256((SET / freeze["file"]).read_bytes()).hexdigest()
    if digest != freeze["sha256"]:
        raise SystemExit("clarification_set_v2.csv changed after it was frozen; make a v3 instead.")
    return digest


def load_cases() -> list[dict]:
    with (SET / json.loads((SET / "freeze.json").read_text(encoding="utf-8"))["file"]).open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["profile"] = json.loads(row["student_profile_json"])
    return rows


def payload(case, *, message, history, states=True, allow=True) -> dict:
    p = case["profile"]
    body = {
        "message": message,
        "programme_code": case["programme_code"],
        "completed_modules": p["completed_modules"],
        "current_modules": p["current_modules"],
        "planned_modules": p["planned_modules"],
        "repeating_modules": p["repeating_modules"],
        "module_history_confirmed": history,
        "allow_clarification": allow,
    }
    if states:
        body["module_states"] = p.get("module_states", {})
    return body


def decision_of(result) -> str:
    return result.get("decision") if result.get("decision") in DECISIONS else "none"


def run_clarify(client, case) -> dict:
    started = perf_counter()
    body = payload(case, message=case["question"], history=False)
    first = client.post("/advisor", json=body).json()
    asked = first.get("status") in {"clarification_required", "needs_clarification"}
    question = first.get("clarification_question")
    final, replies = first, 0
    if asked and case["scripted_reply"]:
        body["message"] = case["scripted_reply"]
        body["session_id"] = first.get("session_id")
        final = client.post("/advisor", json=body).json()
        replies = 1
    return {"asked": asked, "question": question, "replies_sent": replies, "final": final,
            "latency_ms": round((perf_counter() - started) * 1000)}


def run_no_clarification(client, case) -> dict:
    started = perf_counter()
    message = case["question"]
    if case["scripted_reply"]:
        message = f"{case['question']} {FACT_PREFIX}{case['scripted_reply']}"
    final = client.post("/advisor", json=payload(case, message=message, history=False, allow=False)).json()
    return {"asked": False, "question": None, "replies_sent": 0, "final": final,
            "latency_ms": round((perf_counter() - started) * 1000)}


def run_assume_absent(client, case) -> dict:
    started = perf_counter()
    body = payload(case, message=case["question"], history=None, states=False, allow=False)
    final = client.post("/advisor", json=body).json()
    return {"asked": False, "question": None, "replies_sent": 0, "final": final,
            "latency_ms": round((perf_counter() - started) * 1000)}


def run_oracle(service, case, control) -> dict:
    started = perf_counter()
    p = control["profile"]
    result = service.eligibility(
        case["target_course_code"], case["programme_code"],
        set(p["completed_modules"]), set(p["current_modules"]), set(p["planned_modules"]), (),
        dict(p.get("module_states", {})), True, repeating_modules=set(p["repeating_modules"]),
    )
    return {"asked": False, "question": None, "replies_sent": 0, "final": result,
            "latency_ms": round((perf_counter() - started) * 1000)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=ARMS + ("all",), default="all")
    args = parser.parse_args()
    digest = verify_frozen()
    cases = load_cases()
    controls = {c["pair_id"]: c for c in cases if c["kind"] == "control"}
    service, app = curricupath_components()
    RAW.mkdir(parents=True, exist_ok=True)
    from fastapi.testclient import TestClient

    arms = ARMS if args.arm == "all" else (args.arm,)
    with TestClient(app) as client:
        for arm in arms:
            out = RAW / f"{arm}.jsonl"
            if out.exists():
                raise SystemExit(f"{out.name} exists; raw outputs are immutable. Move it aside to re-run.")
            with out.open("x", encoding="utf-8") as handle:
                for case in cases:
                    if arm == "clarify":
                        run = run_clarify(client, case)
                    elif arm == "no_clarification":
                        run = run_no_clarification(client, case)
                    elif arm == "assume_absent":
                        run = run_assume_absent(client, case)
                    else:
                        control = controls.get(case["pair_id"], case)
                        run = run_oracle(service, case, control)
                    final = run["final"]
                    record = {
                        "case_id": case["case_id"], "arm": arm, "kind": case["kind"],
                        "fact_type": case["fact_type"], "pair_id": case["pair_id"],
                        "asked": run["asked"], "question": run["question"],
                        "replies_sent": run["replies_sent"],
                        "final_decision": decision_of(final), "final_status": final.get("status"),
                        "latency_ms": run["latency_ms"],
                        "final_answer": (final.get("answer") or "")[:300],
                        "case_file_sha256": digest,
                    }
                    handle.write(json.dumps(record, sort_keys=True) + "\n")
            print(f"{arm}: wrote {len(cases)} records")


if __name__ == "__main__":
    main()
