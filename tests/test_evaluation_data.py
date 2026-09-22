"""Integrity checks for the frozen draft evaluation datasets."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from app.advisor.eligibility import StudentProfile, check_eligibility
from app.data.loaders import load_curriculum_data


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVALUATION = PROJECT_ROOT / "experiments" / "evaluation"
PROCESSED = PROJECT_ROOT / "data" / "processed"


def read_csv(name: str) -> list[dict[str, str]]:
    with (EVALUATION / name).open(newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def test_rule_case_volume_ids_and_anchor_review_state() -> None:
    rows = read_csv("rule_cases.csv")
    assert len(rows) == 150
    assert len({row["case_id"] for row in rows}) == 150
    anchors = [row for row in rows if row["anchor_case"] == "true"]
    assert len(anchors) == 15
    assert {row["review_status"] for row in anchors} == {
        "pending_academic_review"
    }
    assert all(not row["academic_reviewer"] for row in anchors)


def test_rule_cases_cover_required_gate_and_structural_categories() -> None:
    rows = read_csv("rule_cases.csv")
    categories = {row["category"] for row in rows}
    assert {
        "prerequisite_satisfied",
        "prerequisite_missing",
        "corequisite_planned",
        "corequisite_unknown",
        "programme_mismatch",
        "progression_satisfied",
        "progression_missing_prior_course",
        "selection_count_satisfied",
        "selection_count_too_few",
        "programme_selection_valid",
        "programme_selection_missing",
        "unknown_module",
    }.issubset(categories)


def test_intent_case_volume_ids_and_coverage() -> None:
    rows = read_csv("intent_cases.csv")
    assert len(rows) == 100
    assert len({row["prompt_id"] for row in rows}) == 100
    assert all(row["prompt"].strip() for row in rows)
    assert {
        "module_information",
        "eligibility",
        "curriculum_list",
        "public_course_search",
        "career_path",
        "greeting",
        "help",
        "unknown",
    }.issubset({row["expected_intent"] for row in rows})
    assert any(row["clarification_expected"] == "true" for row in rows)
    assert any(row["context_required"] == "true" for row in rows)


def test_grounding_cases_have_parseable_facts_and_evidence_boundaries() -> None:
    rows = read_csv("grounding_cases.csv")
    assert len(rows) >= 50
    assert len({row["case_id"] for row in rows}) == len(rows)
    assert {"verified", "missing", "partial", "verified_snapshot"}.issubset(
        {row["evidence_state"] for row in rows}
    )
    for row in rows:
        facts = json.loads(row["expected_facts_json"])
        assert isinstance(facts, dict) and facts
        assert row["allowed_source_ids"].strip()
        assert row["prohibited_claims"].strip()


def test_manifest_records_the_case_generation_boundary() -> None:
    manifest = json.loads((EVALUATION / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["freeze_status"] == (
        "data_and_draft_cases_frozen_pending_review_and_git_commit"
    )
    assert manifest["catalogue"]["fingerprint"]
    assert manifest["accepted_evidence_gaps"]["missing_cbo_codes"]
    assert manifest["evaluation_datasets"] == {
        "rule_cases": 150,
        "anchor_cases_pending_academic_review": 15,
        "intent_cases": 100,
        "grounding_cases": 56,
        "review_state": "draft",
        "review_note": "Software checks establish structure and regression consistency only. Academic anchors, expected intents, and expected facts remain pending independent review.",
    }


def test_evaluation_references_use_frozen_catalogue_vocabularies() -> None:
    with (PROCESSED / "sources.csv").open(newline="", encoding="utf-8") as csv_file:
        source_ids = {row["source_id"] for row in csv.DictReader(csv_file)}
    with (PROCESSED / "rules.csv").open(newline="", encoding="utf-8") as csv_file:
        rule_ids = {row["rule_id"] for row in csv.DictReader(csv_file)}
    with (PROCESSED / "aliases.csv").open(newline="", encoding="utf-8") as csv_file:
        aliases = list(csv.DictReader(csv_file))
    interests = {
        row["canonical_tag"] for row in aliases if row["tag_type"] == "interest"
    }
    careers = {
        row["canonical_tag"] for row in aliases if row["tag_type"] == "career"
    }

    for row in read_csv("rule_cases.csv"):
        if row["expected_rule_id"]:
            assert row["expected_rule_id"] in rule_ids, row["case_id"]
        assert row["source_basis"] in source_ids, row["case_id"]

    for row in read_csv("intent_cases.csv"):
        assert set(filter(None, row["expected_interests"].split(";"))) <= interests
        assert set(filter(None, row["expected_career_preferences"].split(";"))) <= careers

    for row in read_csv("grounding_cases.csv"):
        assert set(row["allowed_source_ids"].split(";")) <= source_ids, row["case_id"]


def test_draft_eligibility_expectations_match_the_current_engine() -> None:
    """Regression consistency only; this does not replace academic review."""

    data = load_curriculum_data(PROCESSED)
    for row in read_csv("rule_cases.csv"):
        if row["operation"] != "eligibility":
            continue
        profile = StudentProfile(
            programme_code=row["programme_code"],
            completed_modules=frozenset(filter(None, row["completed_modules"].split(";"))),
            current_modules=frozenset(filter(None, row["current_modules"].split(";"))),
            planned_modules=frozenset(filter(None, row["planned_modules"].split(";"))),
        )
        result = check_eligibility(
            row["target"],
            profile,
            data.modules,
            data.rules,
            data.sources,
            source_root=PROJECT_ROOT,
        )
        assert result.eligible is (row["expected_eligible"] == "true"), row["case_id"]
        assert result.needs_clarification is (
            row["expected_needs_clarification"] == "true"
        ), row["case_id"]
