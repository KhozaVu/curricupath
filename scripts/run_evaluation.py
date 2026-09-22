"""Run one frozen CurricuPath v2.5 evaluation arm and preserve raw outputs."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from time import perf_counter
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EVALUATION = PROJECT_ROOT / "experiments" / "evaluation" / "v2_5"
OUTPUTS = EVALUATION / "results" / "raw"

from app.advisor.engine import AdvisorEngine
from app.advisor.intent import build_intent_extractor
from app.backend import CurricuPathService
from app.config import get_settings
from app.data.database import create_database_engine
from app.data.embeddings import HuggingFaceHostedEmbeddings, PostgresSemanticSearch
from app.data.repository import CsvCatalogueRepository
from app.evaluation.runner import EvaluationRunner, GeminiDecisionClient
from app.main import AdvisorRequest, create_app
from scripts.check_evaluation_readiness import readiness_errors


ARMS = (
    "handbook_rag",
    "structured_rules_llm",
    "rules_only",
    "curricupath",
    "curricupath_no_clarification",
)


def _cases() -> list[dict[str, Any]]:
    with (EVALUATION / "eligibility_cases.csv").open(
        newline="", encoding="utf-8"
    ) as csv_file:
        rows = list(csv.DictReader(csv_file))
    for row in rows:
        row["student_profile"] = json.loads(row.pop("student_profile_json"))
    return rows


def _llm_runner() -> EvaluationRunner:
    settings = get_settings()
    if not settings.hf_token or not settings.gemini_api_key:
        raise SystemExit("HF_TOKEN and GEMINI_API_KEY are required for LLM arms.")
    config = json.loads(
        (EVALUATION / "rag_retrieval_config.json").read_text(encoding="utf-8")
    )
    top_k = config.get("selected_top_k")
    if not isinstance(top_k, int):
        raise SystemExit("Select and freeze top_k before running LLM arms.")
    provider = HuggingFaceHostedEmbeddings(
        settings.hf_token,
        settings.embedding_model,
        settings.embedding_dimension,
    )
    search = PostgresSemanticSearch(
        create_database_engine(settings.database_url), provider
    )
    with (PROJECT_ROOT / "data" / "processed" / "rules.csv").open(
        newline="", encoding="utf-8"
    ) as csv_file:
        rules = list(csv.DictReader(csv_file))
    with (PROJECT_ROOT / "data" / "processed" / "sources.csv").open(
        newline="", encoding="utf-8"
    ) as csv_file:
        source_states = [
            {
                "source_id": row["source_id"],
                "verification_status": row["verification_status"],
                "authority": row["authority"],
                "locator": row["locator"],
            }
            for row in csv.DictReader(csv_file)
        ]
    return EvaluationRunner(
        search,
        GeminiDecisionClient(settings.gemini_api_key, settings.gemini_model),
        EVALUATION,
        rules,
        source_states,
        top_k,
        str(config.get("eligibility_corpus_item_type", "evaluation_handbook")),
    )


def _curricupath_components():
    settings = get_settings()
    repository = CsvCatalogueRepository(settings.processed_data_directory)
    service = CurricuPathService(repository, str(PROJECT_ROOT))
    extractor = build_intent_extractor(
        repository.get_aliases(), settings.gemini_api_key, settings.gemini_model
    )
    advisor = AdvisorEngine(service, extractor)
    app = create_app(service=service, advisor_engine=advisor)
    return service, app


def _rules_only(service: CurricuPathService, case: dict[str, Any]) -> dict[str, Any]:
    profile = case["student_profile"]
    started = perf_counter()
    result = service.eligibility(
        case["target_course_code"],
        profile["programme_code"],
        set(profile["completed_modules"]),
        set(profile["current_modules"]),
        set(profile["planned_modules"]),
        tuple(profile.get("manual_review_reasons", [])),
    )
    return {
        "case_id": case["case_id"],
        "arm": "rules_only",
        "run_number": 1,
        "status": "valid" if result.get("decision") else "no_decision",
        "parsed_output": result,
        "raw_output": json.dumps(result, sort_keys=True),
        "latency_ms": max(0, round((perf_counter() - started) * 1000)),
        "error": None,
    }


def _curricupath(
    app,
    case: dict[str, Any],
    run_number: int,
    *,
    allow_clarification: bool,
) -> dict[str, Any]:
    from fastapi.testclient import TestClient

    profile = case["student_profile"]
    started = perf_counter()
    with TestClient(app) as client:
        payload = AdvisorRequest(
            message=case["question"],
            programme_code=profile["programme_code"],
            completed_modules=set(profile["completed_modules"]),
            current_modules=set(profile["current_modules"]),
            planned_modules=set(profile["planned_modules"]),
        ).model_dump(mode="json")
        response = client.post("/advisor", json=payload)
        response.raise_for_status()
        result = response.json()
        if (
            allow_clarification
            and case["clarification_permitted"] == "true"
            and result.get("status") in {"clarification_required", "needs_clarification"}
        ):
            payload["message"] = case["scripted_reply"]
            payload["session_id"] = result.get("session_id")
            response = client.post("/advisor", json=payload)
            response.raise_for_status()
            result = response.json()

    decision = result.get("decision")
    status = "valid" if decision in {
        "eligible",
        "ineligible",
        "manual_review_required",
    } else "no_decision"
    return {
        "case_id": case["case_id"],
        "arm": (
            "curricupath" if allow_clarification else "curricupath_no_clarification"
        ),
        "run_number": run_number,
        "status": status,
        "parsed_output": result,
        "raw_output": json.dumps(result, sort_keys=True, default=str),
        "latency_ms": max(0, round((perf_counter() - started) * 1000)),
        "error": None if status == "valid" else "No three-class decision was produced.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=ARMS, required=True)
    parser.add_argument(
        "--allow-draft",
        action="store_true",
        help="Exercise the harness before approval; output is marked draft.",
    )
    args = parser.parse_args()
    if not args.allow_draft:
        errors = readiness_errors()
        if errors:
            raise SystemExit("Official run blocked:\n- " + "\n- ".join(errors))

    cases = _cases()
    prefix = "draft_" if args.allow_draft else ""
    output_path = OUTPUTS / f"{prefix}{args.arm}.jsonl"
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    if output_path.exists() and not args.allow_draft:
        raise SystemExit(f"Refusing to overwrite immutable output: {output_path}")

    llm = _llm_runner() if args.arm in {"handbook_rag", "structured_rules_llm"} else None
    service = app = None
    if args.arm in {"rules_only", "curricupath", "curricupath_no_clarification"}:
        service, app = _curricupath_components()

    with output_path.open("w" if args.allow_draft else "x", encoding="utf-8") as output:
        for case in cases:
            if llm is not None:
                for run_number in range(1, 4):
                    record = llm.run_case(case, args.arm, run_number).as_dict()
                    output.write(json.dumps(record, sort_keys=True, default=str) + "\n")
            elif args.arm == "rules_only":
                output.write(json.dumps(_rules_only(service, case), sort_keys=True) + "\n")
            else:
                for run_number in range(1, 4):
                    record = _curricupath(
                        app,
                        case,
                        run_number,
                        allow_clarification=args.arm == "curricupath",
                    )
                    output.write(json.dumps(record, sort_keys=True, default=str) + "\n")
            output.flush()
    print(f"Wrote immutable output: {output_path}")


if __name__ == "__main__":
    main()
