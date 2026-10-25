"""Run Experiment C (ambiguity and clarification): full CurricuPath against no clarification.

Official runs need reviewer-authored fields on every case and pass the readiness gate. Draft
runs (`--allow-draft`) use the cases as they stand: metrics that depend on reviewer fields are
reported as not scorable, and nothing in the case file is edited or guessed.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EVALUATION = PROJECT_ROOT / "experiments" / "evaluation" / "v2_5"
RAW = EVALUATION / "results" / "raw"

from app.evaluation import ambiguity_runner as runner
from app.evaluation import ambiguity_scoring as scoring
from scripts.check_evaluation_readiness import readiness_errors

ARMS = {"curricupath": True, "curricupath_no_clarification": False}
BANNER = "DRAFT: reviewer fields are pending; results describe behaviour only, not correctness"


def _cases() -> list[dict[str, str]]:
    with (EVALUATION / "ambiguity_cases.csv").open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _sender(client, case, allow_clarification=True):
    from app.main import AdvisorRequest

    profile = json.loads(case.get("student_profile_json") or "{}")

    def send(message: str, session_id: str | None):
        payload = AdvisorRequest(
            message=message,
            session_id=session_id,
            programme_code=profile.get("programme_code"),
            completed_modules=set(profile.get("completed_modules", [])),
            current_modules=set(profile.get("current_modules", [])),
            planned_modules=set(profile.get("planned_modules", [])),
            allow_clarification=allow_clarification,
        ).model_dump(mode="json")
        response = client.post("/advisor", json=payload)
        response.raise_for_status()
        return response.json()

    return send


def _fmt(metric) -> str:
    if metric["rate"] is None:
        return "not scorable"
    low, high = metric["ci95"]
    return f"{metric['correct']}/{metric['n']} ({metric['rate'] * 100:.0f}%, 95% CI {low:.2f} to {high:.2f})"


def _markdown(cases, metrics, paired, extraction, draft) -> str:
    rows = [("initial_intent_accuracy", "Initial intent matches intended interpretation"),
            ("asked_clarification_first_turn", "Asked for clarification on the first turn"),
            ("answered_first_turn", "Answered on the first turn"),
            ("refused_out_of_scope_first_turn", "Refused as out of scope on the first turn"),
            ("final_interpretation_correct", "Final intent matches intended interpretation"),
            ("unresolved_clarification_rate", "Ended with an unresolved clarification"),
            ("appropriate_clarification_rate", "Appropriate clarification (when required)"),
            ("unnecessary_clarification_rate", "Unnecessary clarification (when not required)"),
            ("silent_guess_rate", "Silent guess (answered when clarification was required)"),
            ("final_outcome_accepted", "Final outcome accepted by the reviewer"),
            ("second_attempt_success", "Success after a clarification")]
    names = list(metrics)
    lines = ["# Experiment C: ambiguity and clarification", ""]
    if draft:
        lines += [f"> **{BANNER}.**", ""]
    unscripted = metrics[names[0]]["unscripted_cases"]
    lines += [f"Cases: {len(cases)}. Intent extraction: {extraction}. One run per case.", ""]
    if unscripted:
        lines += [f"**No reply could be sent in {len(unscripted)} cases where a clarification was asked "
                  f"({', '.join(unscripted)}), because the fixed simulated reply is still pending.** Until "
                  "reviewer-authored replies exist, the two arms cannot differ, so an identical result here "
                  "says nothing about whether clarification helps.", ""]
    lines += [
              "| Measure | " + " | ".join(names) + " |", "| --- | " + " | ".join("---" for _ in names) + " |"]
    for key, label in rows:
        lines.append(f"| {label} | " + " | ".join(_fmt(metrics[a][key]) for a in names) + " |")
    lines += ["| Mean turns when answered | " + " | ".join(
        "n/a" if metrics[a]["mean_turns_to_resolution"] is None else f"{metrics[a]['mean_turns_to_resolution']:.2f}"
        for a in names) + " |", "", "## Paired comparison: with clarification against without", ""]
    for name, p in paired.items():
        if "not_scorable" in p:
            lines.append(f"- **{name.replace('_', ' ')}**: not scorable ({p['not_scorable']}).")
        else:
            lines.append(
                f"- **{name.replace('_', ' ')}**: {p['n_pairs']} pairs; correct only with clarification "
                f"{p['only_with_clarification']}, only without {p['only_without_clarification']}, both "
                f"{p['both_correct']}, neither {p['neither']}; exact sign test p = {p['exact_sign_test_p']:.3f}.")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-draft", action="store_true", help="Run before reviewer approval; output is DRAFT.")
    parser.add_argument("--extraction", choices=("deterministic", "gemini"), default="deterministic",
                        help="Deterministic blanks GEMINI_API_KEY so only one extraction path is measured. "
                             "Gemini can fall back silently when quota runs out, so check quota first.")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    cases = _cases()
    if not args.allow_draft:
        errors = readiness_errors(require_clean_git=False) + runner.case_errors(cases)
        if errors:
            raise SystemExit("Official run blocked:\n- " + "\n- ".join(errors))

    from scripts.run_evaluation import _curricupath_components

    if args.extraction == "deterministic":
        os.environ["GEMINI_API_KEY"] = ""
    _, app = _curricupath_components()

    prefix = "draft_" if args.allow_draft else ""
    RAW.mkdir(parents=True, exist_ok=True)
    from fastapi.testclient import TestClient

    records: dict[str, list[dict]] = {}
    with TestClient(app) as client:
        for arm, allow in ARMS.items():
            path = RAW / f"{prefix}ambiguity_{arm}.jsonl"
            if path.exists() and not args.allow_draft:
                raise SystemExit(f"Refusing to overwrite immutable output: {path}")
            records[arm] = []
            with path.open("w" if args.allow_draft else "x", encoding="utf-8") as output:
                for case in cases:
                    record = runner.run_case(_sender(client, case, allow), case, allow_clarification=allow)
                    record.update({"arm": arm, "run_number": 1, "extraction": args.extraction})
                    records[arm].append(record)
                    output.write(json.dumps(record, sort_keys=True, default=str) + "\n")

    metrics = {arm: scoring.score_arm(cases, rs) for arm, rs in records.items()}
    paired = scoring.paired_comparison(cases, records["curricupath"], records["curricupath_no_clarification"])
    out = args.output_dir or (EVALUATION / "results" / ("draft_analysis" if args.allow_draft else "analysis") / "ambiguity")
    out.mkdir(parents=True, exist_ok=True)
    (out / "ambiguity_metrics.json").write_text(json.dumps(
        {"draft": args.allow_draft, "extraction": args.extraction, "arms": metrics, "paired": paired},
        indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "ambiguity_report.md").write_text(
        _markdown(cases, metrics, paired, args.extraction, args.allow_draft), encoding="utf-8")

    by_arm = {arm: {r["case_id"]: r for r in rs} for arm, rs in records.items()}
    with (out / "ambiguity_cases.csv").open("w", newline="", encoding="utf-8") as handle:
        columns = ["case_id", "ambiguity_type", "query", "intended_interpretation"]
        for arm in ARMS:
            columns += [f"{arm}_first_status", f"{arm}_first_intent", f"{arm}_final_status",
                        f"{arm}_final_intent", f"{arm}_turns"]
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for case in cases:
            row = {k: case[k] for k in columns[:4]}
            for arm in ARMS:
                rec = by_arm[arm][case["case_id"]]
                first = rec["turns"][0]["response"] if rec["turns"] else {}
                row.update({f"{arm}_first_status": first.get("status"), f"{arm}_first_intent": first.get("intent"),
                            f"{arm}_final_status": rec["final"].get("status"),
                            f"{arm}_final_intent": rec["final"].get("intent"), f"{arm}_turns": rec["n_turns"]})
            writer.writerow(row)

    for arm, m in metrics.items():
        print(f"{arm}: initial intent {_fmt(m['initial_intent_accuracy'])}; asked first turn "
              f"{_fmt(m['asked_clarification_first_turn'])}; out of scope {_fmt(m['refused_out_of_scope_first_turn'])}")
    if args.allow_draft:
        print(f"\n{BANNER}.")
    print(f"Wrote outputs to {out}")


if __name__ == "__main__":
    main()
