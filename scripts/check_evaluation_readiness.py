"""Fail loudly unless every non-human and human v2.5 prerequisite is frozen."""

from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVALUATION = PROJECT_ROOT / "experiments" / "evaluation" / "v2_5"
VALID_LABELS = {"eligible", "ineligible", "manual_review_required"}


def _json(name: str):
    return json.loads((EVALUATION / name).read_text(encoding="utf-8"))


def _csv(name: str) -> list[dict[str, str]]:
    with (EVALUATION / name).open(newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def readiness_errors(*, require_clean_git: bool = True) -> list[str]:
    errors: list[str] = []
    required = (
        "manifest.json",
        "personnel.json",
        "rag_prompt.md",
        "structured_rules_prompt.md",
        "rag_retrieval_config.json",
        "retrieval_development_cases.csv",
        "eligibility_cases.csv",
        "grounding_cases.csv",
        "corpus_manifest.json",
    )
    for name in required:
        if not (EVALUATION / name).exists():
            errors.append(f"Missing required evaluation artefact: {name}")
    if errors:
        return errors

    personnel = _json("personnel.json")
    for role in (
        "evaluation_lead",
        "baseline_owner",
        "curricupath_run_owner",
        "analyst",
        "supervisor",
    ):
        if not personnel.get(role):
            errors.append(f"Personnel assignment is missing: {role}")
    if not personnel.get("academic_reviewers"):
        errors.append("At least one named academic reviewer is required.")
    judges = personnel.get("grounding_judges") or []
    if not judges:
        errors.append("At least one named grounding judge is required.")
    elif not any(
        isinstance(judge, dict) and judge.get("is_developer") is False
        for judge in judges
    ):
        errors.append("At least one grounding judge must be a non-developer.")
    for commitment, hours in personnel.get("commitments", {}).items():
        if not isinstance(hours, (int, float)) or hours <= 0:
            errors.append(f"Positive committed hours are missing: {commitment}")

    eligibility = _csv("eligibility_cases.csv")
    if not 60 <= len(eligibility) <= 90:
        errors.append("Eligibility set must contain 60-90 cases.")
    missing_labels = [
        row["case_id"]
        for row in eligibility
        if row["reference_label"] not in VALID_LABELS
    ]
    if missing_labels:
        errors.append(
            f"{len(missing_labels)} eligibility cases have no approved three-class label "
            f"(first: {', '.join(missing_labels[:5])})."
        )
    unapproved = [
        row["case_id"]
        for row in eligibility
        if row["approval_state"] != "approved" or not row["reviewer_ids"].strip()
    ]
    if unapproved:
        errors.append(
            f"{len(unapproved)} eligibility cases lack recorded independent approval "
            f"(first: {', '.join(unapproved[:5])})."
        )
    for label in VALID_LABELS:
        count = sum(row["reference_label"] == label for row in eligibility)
        if count < 15:
            errors.append(f"Reference class {label} has only {count} cases; 15 required.")

    config = _json("rag_retrieval_config.json")
    if not isinstance(config.get("selected_top_k"), int):
        errors.append("top_k has not been selected and frozen.")
    if not str(config.get("status", "")).startswith("frozen_"):
        errors.append("Retrieval configuration is not frozen.")

    corpus = _json("corpus_manifest.json")
    if not corpus.get("database_updated") or not corpus.get("corpus_sha256"):
        errors.append("Evaluation corpus is not installed and fingerprinted.")

    if require_clean_git:
        dirty = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        if dirty:
            errors.append("Git working tree is not clean; official runs are blocked.")
    return errors


def main() -> None:
    errors = readiness_errors()
    if errors:
        print("EVALUATION NOT READY")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("EVALUATION READY")


if __name__ == "__main__":
    main()
