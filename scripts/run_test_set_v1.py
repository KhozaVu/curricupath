"""Run one arm of test set v1 at one ambiguity level and append raw outputs.

Plan: experiments/evaluation/test_set_v1/PLAN.md. The three ambiguity levels are the three
phrasings stored with every case (low = course code, medium = module name, high = informal).
The timetable-clash gate is on for every CurricuPath and rules-only run, because the set
contains clash cases. Output is append-only and resumable: cases already recorded are skipped,
and a run refused by the hosted model for quota or availability stops without writing that
case, so the next invocation picks up where this one stopped.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path
from time import perf_counter, sleep
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
TEST_SET = PROJECT_ROOT / "experiments" / "evaluation" / "test_set_v1"
CASES_PATH = TEST_SET / "curricupath_test_set_v1.csv"
RAW = TEST_SET / "results" / "raw"
PROMPTS = PROJECT_ROOT / "experiments" / "evaluation" / "v2_5"

LEVELS = {"low": "question", "medium": "question_by_name", "high": "question_informal"}
ARMS = (
    "curricupath",
    "curricupath_no_clarification",
    "rules_only",
    "structured_rules_llm",
    "handbook_rag",
)
LLM_ARMS = {"structured_rules_llm", "handbook_rag"}
DECISIONS = {"eligible", "ineligible", "manual_review_required"}
FACT_PREFIX = "Additional declared fact: "
LEDGER = TEST_SET / "results" / "spend_ledger.json"
# USD per million tokens (Google price page read 2026-10-01): gemini-3.5-flash-lite.
PRICE_PER_MILLION = {"input": 0.30, "output": 2.50}
WORST_CASE_CALL_USD = 0.03  # 40k input + 4k output tokens, a safe ceiling for one call


def spend_so_far(ledger: Path) -> float:
    if not ledger.exists():
        return 0.0
    return float(json.loads(ledger.read_text(encoding="utf-8"))["usd"])


def add_spend(usage, ledger: Path) -> float:
    """Add one call's cost to the persistent ledger (thinking tokens are billed as output)."""

    if usage is None:
        cost = WORST_CASE_CALL_USD  # unknown usage: charge the ceiling rather than undercount
        tokens = {"input": None, "output": None}
    else:
        tin = int(getattr(usage, "prompt_token_count", 0) or 0)
        tout = int(getattr(usage, "candidates_token_count", 0) or 0) + int(
            getattr(usage, "thoughts_token_count", 0) or 0)
        cost = tin * PRICE_PER_MILLION["input"] / 1e6 + tout * PRICE_PER_MILLION["output"] / 1e6
        tokens = {"input": tin, "output": tout}
    state = {"usd": 0.0, "calls": 0, "input_tokens": 0, "output_tokens": 0}
    if ledger.exists():
        state = json.loads(ledger.read_text(encoding="utf-8"))
    state["usd"] = round(state["usd"] + cost, 6)
    state["calls"] += 1
    state["input_tokens"] += tokens["input"] or 0
    state["output_tokens"] += tokens["output"] or 0
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return state["usd"]


def verify_frozen() -> str:
    freeze = json.loads((TEST_SET / "freeze.json").read_text(encoding="utf-8"))
    digest = hashlib.sha256(CASES_PATH.read_bytes()).hexdigest()
    if digest != freeze["sha256"]:
        raise SystemExit("curricupath_test_set_v1.csv changed after it was frozen; make a v2 instead.")
    return digest


def load_cases(level: str) -> list[dict[str, Any]]:
    """Cases with `question` set to the phrasing for this level."""

    with CASES_PATH.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    column = LEVELS[level]
    cases = []
    for row in rows:
        question = row[column].strip()
        reply = row["scripted_reply"].strip()
        cases.append({
            **row,
            "question": question,
            "student_profile": json.loads(row["student_profile_json"]),
            # Non-interactive arms receive the scripted fact up front (same as v2.5 protocol).
            "consolidated_noninteractive_input": (
                f"{question} {FACT_PREFIX}{reply}" if reply else question
            ),
        })
    return cases


def declares_module_history(case: dict[str, Any]) -> bool:
    return "every module" in case.get("scripted_reply", "")


def _record(case, arm, level, result, started, *, status=None, error=None) -> dict[str, Any]:
    decision = (result or {}).get("decision")
    status = status or ("valid" if decision in DECISIONS else "no_decision")
    return {
        "case_id": case["case_id"],
        "arm": arm,
        "level": level,
        "run_number": 1,
        "status": status,
        "parsed_output": result,
        "raw_output": json.dumps(result, sort_keys=True, default=str),
        "latency_ms": max(0, round((perf_counter() - started) * 1000)),
        "error": error if error is not None else (
            None if status == "valid" else "No three-class decision was produced."
        ),
    }


# ---- deterministic and CurricuPath arms --------------------------------------------------------

def curricupath_components():
    from app.advisor.engine import AdvisorEngine
    from app.advisor.intent import build_intent_extractor
    from app.backend import CurricuPathService
    from app.config import get_settings
    from app.data.repository import CsvCatalogueRepository
    from app.main import create_app

    settings = get_settings()
    repository = CsvCatalogueRepository(settings.processed_data_directory)
    service = CurricuPathService(
        repository,
        str(PROJECT_ROOT),
        timetable_clash_gate_enabled=True,
        school_grid_requirements_enabled=True,
    )
    # Deterministic intent extraction for every message; Gemini is used only by the
    # interpretation fallback for messages the parser cannot resolve (server setting).
    extractor = build_intent_extractor(repository.get_aliases(), "", settings.gemini_model)
    app = create_app(service=service, advisor_engine=AdvisorEngine(service, extractor))
    return service, app


def rules_only(service, case, level) -> dict[str, Any]:
    profile = case["student_profile"]
    started = perf_counter()
    result = service.eligibility(
        case["target_course_code"],
        profile["programme_code"],
        set(profile.get("completed_modules", [])),
        set(profile.get("current_modules", [])),
        set(profile.get("planned_modules", [])),
        tuple(profile.get("manual_review_reasons", [])),
        module_history_confirmed=True if declares_module_history(case) else None,
        repeating_modules=set(profile.get("repeating_modules", [])),
    )
    return _record(case, "rules_only", level, result, started)


def curricupath(client, case, level, *, allow_clarification: bool) -> dict[str, Any]:
    profile = case["student_profile"]
    message = case["question"] if allow_clarification else case["consolidated_noninteractive_input"]
    payload = {
        "message": message,
        "programme_code": profile["programme_code"],
        "completed_modules": profile.get("completed_modules", []),
        "current_modules": profile.get("current_modules", []),
        "planned_modules": profile.get("planned_modules", []),
        "repeating_modules": profile.get("repeating_modules", []),
        "manual_review_reasons": profile.get("manual_review_reasons", []),
        "allow_clarification": allow_clarification,
    }
    started = perf_counter()
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
    arm = "curricupath" if allow_clarification else "curricupath_no_clarification"
    return _record(case, arm, level, result, started)


# ---- LLM arms ----------------------------------------------------------------------------------

def llm_runner():
    from app.evaluation.runner import EvaluationRunner, GeminiDecisionClient
    from app.config import get_settings
    from app.data.database import create_database_engine
    from app.data.embeddings import HuggingFaceHostedEmbeddings, PostgresSemanticSearch
    from app.advisor.eligibility import load_grid_requirement_rules

    settings = get_settings()
    if not settings.hf_token or not settings.gemini_api_key:
        raise SystemExit("HF_TOKEN and GEMINI_API_KEY are required for LLM arms.")
    historical_configs = [
        json.loads((RAW / f"{arm}__{level}.config.json").read_text(encoding="utf-8"))
        for arm in LLM_ARMS
        for level in LEVELS
    ]
    historical_models = {config.get("gemini_model") for config in historical_configs}
    if len(historical_models) != 1 or None in historical_models:
        raise SystemExit("Historical LLM configs do not identify one common model; refusing a mixed-model rerun.")
    historical_model = historical_models.pop()
    config = json.loads((PROMPTS / "rag_retrieval_config.json").read_text(encoding="utf-8"))
    provider = HuggingFaceHostedEmbeddings(
        settings.hf_token, settings.embedding_model, settings.embedding_dimension
    )
    search = PostgresSemanticSearch(create_database_engine(settings.database_url), provider)
    with (PROJECT_ROOT / "data" / "processed" / "rules.csv").open(newline="", encoding="utf-8") as h:
        rules = list(csv.DictReader(h))
    # The structured-rules model gets the same clash rules CurricuPath uses, so the comparison
    # measures reasoning over identical rules rather than access to them.
    with (PROJECT_ROOT / "data" / "rules" / "grid_clash_rules.csv").open(newline="", encoding="utf-8") as h:
        rules += list(csv.DictReader(h))
    grid_requirement_rules = list(
        load_grid_requirement_rules(PROJECT_ROOT / "data" / "rules" / "grid_rules.json")
    )
    # The structured arm receives the full School-grid rules as well as the shared, relevant
    # evidence passage supplied to both LLM arms.
    rules += grid_requirement_rules
    with (PROJECT_ROOT / "data" / "processed" / "sources.csv").open(newline="", encoding="utf-8") as h:
        sources = [
            {k: row[k] for k in ("source_id", "verification_status", "authority", "locator")}
            for row in csv.DictReader(h)
        ]
    retrieval_cache: dict[str, list[dict[str, Any]]] = {}
    cache_hashes: dict[str, str] = {}
    required_ids = set(json.loads((TEST_SET / "subset_40.json").read_text(encoding="utf-8"))["case_ids"])
    for level in LEVELS:
        cache_path = RAW / f"handbook_rag__{level}.jsonl"
        if not cache_path.exists():
            raise SystemExit(f"Frozen handbook retrieval cache is missing: {cache_path}")
        cache_hashes[str(cache_path.relative_to(PROJECT_ROOT))] = hashlib.sha256(cache_path.read_bytes()).hexdigest()
        for line in cache_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("retrieved_chunks"):
                retrieval_cache[f"{level}:{record['case_id']}"] = record["retrieved_chunks"]
        missing = sorted(f"{level}:{case_id}" for case_id in required_ids
                         if f"{level}:{case_id}" not in retrieval_cache)
        if missing:
            raise SystemExit("Frozen handbook retrieval cache is incomplete: " + ", ".join(missing[:5]))
    runner = EvaluationRunner(
        search,
        GeminiDecisionClient(settings.gemini_api_key, historical_model),
        PROMPTS,
        rules,
        sources,
        int(config["selected_top_k"]),
        str(config.get("eligibility_corpus_item_type", "evaluation_handbook")),
        grid_requirement_rules,
        retrieval_cache,
    )
    return runner, historical_model, int(config["selected_top_k"]), cache_hashes


# ---- main --------------------------------------------------------------------------------------

def _done(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {json.loads(line)["case_id"] for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=ARMS, required=True)
    parser.add_argument("--level", choices=tuple(LEVELS), required=True)
    parser.add_argument("--split", choices=("all", "development", "held_out", "subset60", "subset40"), default="all")
    parser.add_argument("--pace-seconds", type=float, default=0.0)
    parser.add_argument("--limit", type=int, default=0, help="Stop after this many new cases (0 = no limit).")
    parser.add_argument("--max-usd", type=float, default=0.0,
                        help="Hard spend cap in USD for LLM arms, across all runs (0 = no cap).")
    parser.add_argument("--spend-ledger", type=Path, default=LEDGER,
                        help="Spend ledger to use (defaults to the historical shared ledger).")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=RAW,
        help="Raw-output directory (default: the existing results/raw folder).",
    )
    args = parser.parse_args()
    if args.pace_seconds < 0:
        raise SystemExit("--pace-seconds must be zero or positive.")

    digest = verify_frozen()
    from app.evaluation.scoring import is_provider_failure

    subset = None
    if args.split in {"subset60", "subset40"}:
        name = "subset_60.json" if args.split == "subset60" else "subset_40.json"
        subset = set(json.loads((TEST_SET / name).read_text(encoding="utf-8"))["case_ids"])
    cases = [
        c for c in load_cases(args.level)
        if args.split == "all"
        or (subset is not None and c["case_id"] in subset)
        or (subset is None and c["split"] == args.split)
    ]
    for case in cases:
        case["phrasing_level"] = args.level
    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    spend_ledger = args.spend_ledger
    if not spend_ledger.is_absolute():
        spend_ledger = PROJECT_ROOT / spend_ledger
    out = output_dir / f"{args.arm}__{args.level}.jsonl"
    done = _done(out)
    todo = [c for c in cases if c["case_id"] not in done]
    config: dict[str, Any] = {"arm": args.arm, "level": args.level, "case_file_sha256": digest,
                              "timetable_clash_gate": True,
                              "school_grid_requirements": True,
                              "school_grid_facts_shared_with_both_llm_arms": True,
                              "structured_arm_receives_full_grid_rules": args.arm == "structured_rules_llm",
                              "runs_per_case": 1}

    llm = service = app = None
    if args.arm in LLM_ARMS:
        llm, model, top_k, cache_hashes = llm_runner()
        grid_input_files = (
            PROJECT_ROOT / "data" / "rules" / "grid_rules.json",
            PROJECT_ROOT / "data" / "rules" / "grid_clash_rules.csv",
            PROJECT_ROOT / "data" / "processed" / "rules.csv",
            PROMPTS / "rag_prompt.md",
            PROMPTS / "structured_rules_prompt.md",
        )
        config.update({"gemini_model": model, "top_k": top_k, "pace_seconds": args.pace_seconds,
                       "structured_rules_include_clash_rules": args.arm == "structured_rules_llm",
                       "frozen_handbook_retrieval_cache_sha256": cache_hashes,
                       "new_hosted_embedding_calls": 0,
                       "input_sha256": {
                           str(path.relative_to(PROJECT_ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                           for path in grid_input_files
                       }})
    else:
        from app.config import get_settings
        service, app = curricupath_components()
        config.update({"intent_extraction": "deterministic",
                       "interpretation_fallback": get_settings().interpretation_fallback})
    (output_dir / f"{args.arm}__{args.level}.config.json").write_text(
        json.dumps(config, indent=2) + "\n", encoding="utf-8")

    written = 0
    stopped = None
    from fastapi.testclient import TestClient
    client_context = TestClient(app) if app is not None else None
    client = client_context.__enter__() if client_context is not None else None
    try:
        with out.open("a", encoding="utf-8") as handle:
            for case in todo:
                if args.limit and written >= args.limit:
                    break
                if llm is not None:
                    if args.max_usd and spend_so_far(spend_ledger) + WORST_CASE_CALL_USD > args.max_usd:
                        stopped = f"BUDGET: ${spend_so_far(spend_ledger):.3f} spent; next call could exceed the ${args.max_usd:.2f} cap"
                        break
                    record = llm.run_case(case, args.arm, 1).as_dict()
                    if args.max_usd or spend_ledger.exists():
                        add_spend(llm.client.last_usage, spend_ledger)
                    record["level"] = args.level
                    if is_provider_failure(record):
                        stopped = record.get("error")
                        break
                    sleep(args.pace_seconds)
                elif args.arm == "rules_only":
                    record = rules_only(service, case, args.level)
                else:
                    record = curricupath(client, case, args.level,
                                         allow_clarification=args.arm == "curricupath")
                handle.write(json.dumps(record, sort_keys=True, default=str) + "\n")
                handle.flush()
                written += 1
                if llm is not None and written % 10 == 0:
                    print(
                        f"{args.arm} / {args.level}: {written}/{len(todo)} new cases; "
                        f"Gemini ledger ${spend_so_far(spend_ledger):.4f}",
                        flush=True,
                    )
    finally:
        if client_context is not None:
            client_context.__exit__(None, None, None)
    total = len(_done(out))
    print(f"{args.arm} / {args.level}: wrote {written}, {total}/{len(cases)} cases recorded in {out.name}")
    if stopped:
        print(f"Stopped on provider refusal (quota or outage); rerun later to resume: {stopped[:160]}")


if __name__ == "__main__":
    main()
