"""Tests for the frozen v2.5 evaluation contracts and blocking gates."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from app.evaluation.models import EvaluationDecision
from app.evaluation.runner import EvaluationRunner
from scripts.check_evaluation_readiness import readiness_errors


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVALUATION = PROJECT_ROOT / "experiments" / "evaluation" / "v2_5"


class FakeSearch:
    def search(self, query: str, *, item_type: str, limit: int):
        assert query == "Can I take ELEN4006A?"
        assert item_type == "evaluation_handbook"
        assert limit == 3
        return [
            {
                "item_type": item_type,
                "item_id": "EBE_2026::pdf_page_58_printed_56::chunk_00",
                "chunk_kind": "raw_pdf_page",
                "content": "Progression evidence",
                "source_id": "EBE_2026",
                "similarity": 0.9,
            }
        ]


class FakeClient:
    model_name = "frozen-test-model"

    def decide(self, system_instruction, payload):
        assert "experimental Wits curriculum decision system" in system_instruction
        decision = EvaluationDecision.model_validate(
            {
                "decision": "manual_review_required",
                "answer": "The supplied evidence is insufficient.",
                "citations": [
                    {"source_id": "EBE_2026", "page": "printed page 56"}
                ],
            }
        )
        return decision.model_dump_json(), decision


def test_evaluation_runner_preserves_three_class_output() -> None:
    runner = EvaluationRunner(
        FakeSearch(),
        FakeClient(),
        EVALUATION,
        rules=[],
        source_states=[],
        top_k=3,
    )
    result = runner.run_case(
        {
            "case_id": "TEST001",
            "question": "Can I take ELEN4006A?",
            "student_profile": {"programme_code": "EFA04"},
        },
        "handbook_rag",
        1,
    )

    assert result.status == "valid"
    assert result.parsed_output["decision"] == "manual_review_required"
    assert result.run_number == 1
    assert result.retrieved_chunks[0]["source_id"] == "EBE_2026"


def test_v2_5_draft_package_has_required_case_volume_and_pending_labels() -> None:
    with (EVALUATION / "eligibility_cases.csv").open(
        newline="", encoding="utf-8"
    ) as csv_file:
        rows = list(csv.DictReader(csv_file))

    assert len(rows) == 60
    assert {row["developer_expected_label"] for row in rows} == {
        "eligible",
        "ineligible",
        "manual_review_required",
    }
    assert all(not row["reference_label"] for row in rows)
    assert all(row["approval_state"] == "pending_academic_review" for row in rows)


def test_retrieval_configuration_is_frozen_from_development_cases() -> None:
    config = json.loads(
        (EVALUATION / "rag_retrieval_config.json").read_text(encoding="utf-8")
    )

    assert config["status"] == "frozen_target_met"
    assert config["selected_top_k"] == 20
    assert config["development_results"]["20"]["multi_rule_mean_recall"] >= 0.9


def test_official_evaluation_is_blocked_until_human_review() -> None:
    errors = readiness_errors(require_clean_git=False)

    assert any("academic reviewer" in error for error in errors)
    assert any("three-class label" in error for error in errors)
    assert any("grounding judge" in error for error in errors)
