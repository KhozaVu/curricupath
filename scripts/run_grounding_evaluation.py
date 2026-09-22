"""Generate immutable Experiment B answers for blind atomic-claim review."""

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
from app.evaluation.models import GroundingAnswer
from app.main import AdvisorRequest, create_app
from scripts.check_evaluation_readiness import readiness_errors


ARMS = ("handbook_rag", "structured_rules_llm", "curricupath")


def _cases() -> list[dict[str, str]]:
    with (EVALUATION / "grounding_cases.csv").open(
        newline="", encoding="utf-8"
    ) as csv_file:
        return list(csv.DictReader(csv_file))


def _gemini_components():
    from google import genai
    from google.genai import types

    settings = get_settings()
    if not settings.gemini_api_key or not settings.hf_token:
        raise SystemExit("GEMINI_API_KEY and HF_TOKEN are required.")
    client = genai.Client(
        api_key=settings.gemini_api_key,
        http_options=types.HttpOptions(
            timeout=60_000,
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )
    provider = HuggingFaceHostedEmbeddings(
        settings.hf_token,
        settings.embedding_model,
        settings.embedding_dimension,
    )
    search = PostgresSemanticSearch(
        create_database_engine(settings.database_url), provider
    )
    config = json.loads(
        (EVALUATION / "rag_retrieval_config.json").read_text(encoding="utf-8")
    )
    prompt = (EVALUATION / "grounding_prompt.md").read_text(encoding="utf-8")
    with (PROJECT_ROOT / "data" / "processed" / "rules.csv").open(
        newline="", encoding="utf-8"
    ) as csv_file:
        rules = list(csv.DictReader(csv_file))
    return settings, client, types, search, config, prompt, rules


def _gemini_record(components, case, arm: str, run_number: int) -> dict[str, Any]:
    settings, client, types, search, config, prompt, rules = components
    item_type = str(config["grounding_corpus_item_type"])
    retrieved = []
    if case["category"] != "public_course_rating":
        retrieved = search.search(
            case["question"],
            item_type=item_type,
            limit=int(config["selected_top_k"]),
        )
    payload: dict[str, Any] = {
        "case_id": case["case_id"],
        "question": case["question"],
        "retrieved_evidence": retrieved,
    }
    if arm == "structured_rules_llm":
        payload["structured_rules"] = rules
    started = perf_counter()
    raw = ""
    try:
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=json.dumps(payload, sort_keys=True),
            config=types.GenerateContentConfig(
                system_instruction=prompt,
                response_mime_type="application/json",
                response_schema=GroundingAnswer,
                temperature=0,
            ),
        )
        raw = response.text or ""
        parsed = (
            response.parsed
            if isinstance(response.parsed, GroundingAnswer)
            else GroundingAnswer.model_validate(response.parsed)
        )
        status = "valid"
        output = parsed.model_dump()
        error = None
    except Exception as exc:
        status = "malformed_or_failed"
        output = None
        error = f"{type(exc).__name__}: {exc}"
    return {
        "case_id": case["case_id"],
        "arm": arm,
        "run_number": run_number,
        "model": settings.gemini_model,
        "status": status,
        "parsed_output": output,
        "raw_output": raw,
        "retrieved_chunks": retrieved,
        "latency_ms": max(0, round((perf_counter() - started) * 1000)),
        "error": error,
    }


def _curricupath_app():
    settings = get_settings()
    repository = CsvCatalogueRepository(settings.processed_data_directory)
    service = CurricuPathService(repository, str(PROJECT_ROOT))
    advisor = AdvisorEngine(
        service,
        build_intent_extractor(
            repository.get_aliases(), settings.gemini_api_key, settings.gemini_model
        ),
    )
    return create_app(service=service, advisor_engine=advisor)


def _curricupath_record(app, case, run_number: int) -> dict[str, Any]:
    from fastapi.testclient import TestClient

    started = perf_counter()
    with TestClient(app) as client:
        response = client.post(
            "/advisor",
            json=AdvisorRequest(message=case["question"]).model_dump(mode="json"),
        )
        response.raise_for_status()
        result = response.json()
    return {
        "case_id": case["case_id"],
        "arm": "curricupath",
        "run_number": run_number,
        "status": "valid" if result.get("answer") else "malformed_or_failed",
        "parsed_output": result,
        "raw_output": json.dumps(result, sort_keys=True, default=str),
        "retrieved_chunks": [],
        "latency_ms": max(0, round((perf_counter() - started) * 1000)),
        "error": None if result.get("answer") else "No answer was produced.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=ARMS, required=True)
    parser.add_argument("--allow-draft", action="store_true")
    args = parser.parse_args()
    if not args.allow_draft:
        errors = readiness_errors()
        if errors:
            raise SystemExit("Official run blocked:\n- " + "\n- ".join(errors))

    prefix = "draft_" if args.allow_draft else ""
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUTS / f"{prefix}grounding_{args.arm}.jsonl"
    if output_path.exists() and not args.allow_draft:
        raise SystemExit(f"Refusing to overwrite immutable output: {output_path}")
    components = _gemini_components() if args.arm != "curricupath" else None
    app = _curricupath_app() if args.arm == "curricupath" else None
    with output_path.open("w" if args.allow_draft else "x", encoding="utf-8") as output:
        for case in _cases():
            for run_number in range(1, 4):
                record = (
                    _curricupath_record(app, case, run_number)
                    if app is not None
                    else _gemini_record(components, case, args.arm, run_number)
                )
                output.write(json.dumps(record, sort_keys=True, default=str) + "\n")
                output.flush()
    print(f"Wrote immutable output: {output_path}")


if __name__ == "__main__":
    main()
