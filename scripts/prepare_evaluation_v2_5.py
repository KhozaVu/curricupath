"""Create the draft v2.5 evaluation package without claiming human approval."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LEGACY = PROJECT_ROOT / "experiments" / "evaluation"
OUTPUT = LEGACY / "v2_5"
PROCESSED = PROJECT_ROOT / "data" / "processed"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _profile(row: dict[str, str]) -> str:
    return json.dumps(
        {
            "programme_code": row["programme_code"],
            "completed_modules": list(filter(None, row["completed_modules"].split(";"))),
            "current_modules": list(filter(None, row["current_modules"].split(";"))),
            "planned_modules": list(filter(None, row["planned_modules"].split(";"))),
        },
        sort_keys=True,
    )


def eligibility_cases() -> list[dict[str, Any]]:
    legacy = [
        row
        for row in read_csv(LEGACY / "rule_cases.csv")
        if row["operation"] == "eligibility"
    ]
    eligible = [row for row in legacy if row["expected_eligible"] == "true"][:20]
    deterministic_ineligible = [
        row
        for row in legacy
        if row["expected_eligible"] == "false"
        and row["expected_needs_clarification"] == "false"
    ][:10]
    clarification_cases = [
        row
        for row in legacy
        if row["expected_eligible"] == "false"
        and row["expected_needs_clarification"] == "true"
    ][:10]
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(
        [*eligible, *deterministic_ineligible, *clarification_cases], start=1
    ):
        clarification = row["expected_needs_clarification"] == "true"
        question = (
            f"Can I take {row['target']} in programme {row['programme_code']}?"
        )
        reply = (
            "I have listed every module I am currently taking or planning."
            if clarification
            else ""
        )
        rows.append(
            {
                "case_id": f"ELIG{index:03d}",
                "author_source": "developer_drafted",
                "question": question,
                "target_course_code": row["target"],
                "student_profile_json": _profile(row),
                "scenario_type": row["category"],
                "developer_expected_label": (
                    "eligible" if row["expected_eligible"] == "true" else "ineligible"
                ),
                "reference_label": "",
                "expected_material_reasons_json": "[]",
                "clarification_permitted": str(clarification).lower(),
                "scripted_reply": reply,
                "consolidated_noninteractive_input": (
                    f"{question} Additional declared fact: {reply}" if reply else question
                ),
                "reviewer_ids": "",
                "approval_state": "pending_academic_review",
                "notes": f"Migrated from draft case {row['case_id']}; {row['notes']}",
            }
        )

    manual_templates = (
        "I may receive a prerequisite concession for {module}. Can I register?",
        "My transfer credits may count toward the prerequisites for {module}. Can I take it?",
        "Two official records disagree about whether I completed a prerequisite for {module}. Am I eligible?",
        "I repeated a prerequisite for {module}, but the final result is not yet confirmed. Can I register?",
    )
    modules = ["ELEN4006A", "ELEN4010A", "ELEN4016A", "ELEN4017A", "ELEN4025A"]
    for offset in range(20):
        module = modules[offset % len(modules)]
        question = manual_templates[offset % len(manual_templates)].format(module=module)
        programme = "EFA04" if module in {"ELEN4010A", "ELEN4017A", "ELEN4025A"} else "EFA03"
        rows.append(
            {
                "case_id": f"ELIG{len(rows) + 1:03d}",
                "author_source": "developer_drafted",
                "question": question,
                "target_course_code": module,
                "student_profile_json": json.dumps(
                    {
                        "programme_code": programme,
                        "completed_modules": [],
                        "current_modules": [],
                        "planned_modules": [],
                        "manual_review_reasons": [
                            "The declared concession, transfer-credit, contradictory-record, or unconfirmed-result circumstance requires academic review."
                        ],
                    },
                    sort_keys=True,
                ),
                "scenario_type": "academic_discretion_or_unresolved_record",
                "developer_expected_label": "manual_review_required",
                "reference_label": "",
                "expected_material_reasons_json": "[]",
                "clarification_permitted": "false",
                "scripted_reply": "",
                "consolidated_noninteractive_input": question,
                "reviewer_ids": "",
                "approval_state": "pending_academic_review",
                "notes": "Developer-drafted manual-review vignette; independent approval required.",
            }
        )
    return rows


def ambiguity_cases() -> list[dict[str, Any]]:
    source = [
        row
        for row in read_csv(LEGACY / "intent_cases.csv")
        if row["clarification_expected"] == "true"
    ][:30]
    return [
        {
            "case_id": f"AMB{index:03d}",
            "query": row["prompt"],
            "student_profile_json": "{}",
            "intended_interpretation": row["expected_intent"],
            "ambiguity_type": row["category"],
            "required_clarification": "pending_independent_review",
            "fixed_simulated_reply": "pending_independent_review",
            "neutral_fallback_reply": "I do not know; please use only the information I already provided.",
            "accepted_final_outcomes_json": "[]",
            "approval_state": "pending_academic_review",
            "notes": row["notes"],
        }
        for index, row in enumerate(source, start=1)
    ]


def grounding_cases() -> list[dict[str, Any]]:
    source = read_csv(LEGACY / "grounding_cases.csv")
    return [
        {
            **row,
            "reviewer_ids": "",
            "approval_state": "pending_grounding_review",
        }
        for row in source
    ]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(args: list[str]) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    ).stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    protected = [
        OUTPUT / "eligibility_cases.csv",
        OUTPUT / "ambiguity_cases.csv",
        OUTPUT / "grounding_cases.csv",
    ]
    if not args.force and any(path.exists() for path in protected):
        raise SystemExit(
            "Draft case files already exist. Use --force only before human review begins."
        )

    eligibility = eligibility_cases()
    ambiguity = ambiguity_cases()
    grounding = grounding_cases()
    write_csv(OUTPUT / "eligibility_cases.csv", eligibility, list(eligibility[0]))
    write_csv(OUTPUT / "ambiguity_cases.csv", ambiguity, list(ambiguity[0]))
    write_csv(OUTPUT / "grounding_cases.csv", grounding, list(grounding[0]))

    files = [*protected, OUTPUT / "rag_prompt.md", OUTPUT / "structured_rules_prompt.md"]
    manifest = {
        "protocol_version": "2.5",
        "created_date": date.today().isoformat(),
        "status": "blocked_pending_people_review_top_k_and_clean_commit",
        "git": {
            "head": _git(["rev-parse", "HEAD"]),
            "working_tree_clean": not bool(_git(["status", "--porcelain"])),
        },
        "python": platform.python_version(),
        "case_counts": {
            "eligibility": len(eligibility),
            "ambiguity": len(ambiguity),
            "grounding": len(grounding),
        },
        "human_approval": {
            "eligibility": "pending",
            "grounding": "pending",
            "personnel": "pending",
        },
        "file_sha256": {path.name: _sha256(path) for path in files},
        "note": "Developer expectations are construction aids, not reference labels.",
    }
    (OUTPUT / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Eligibility cases: {len(eligibility)}")
    print(f"Ambiguity cases: {len(ambiguity)}")
    print(f"Grounding cases: {len(grounding)}")
    print("All human approval states remain pending.")


if __name__ == "__main__":
    main()
