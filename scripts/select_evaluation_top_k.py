"""Select and freeze evaluation top_k on the separate development set."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EVALUATION = PROJECT_ROOT / "experiments" / "evaluation" / "v2_5"

from app.config import get_settings
from app.data.database import create_database_engine
from app.data.embeddings import HuggingFaceHostedEmbeddings, PostgresSemanticSearch


def main() -> None:
    settings = get_settings()
    if not settings.hf_token:
        raise SystemExit("HF_TOKEN is required to select top_k.")
    config_path = EVALUATION / "rag_retrieval_config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    with (EVALUATION / "retrieval_development_cases.csv").open(
        newline="", encoding="utf-8"
    ) as csv_file:
        cases = list(csv.DictReader(csv_file))
    if not cases or any(not row["gold_chunk_ids"].strip() for row in cases):
        raise SystemExit("Development cases and gold chunk IDs must be complete.")

    provider = HuggingFaceHostedEmbeddings(
        settings.hf_token,
        settings.embedding_model,
        settings.embedding_dimension,
    )
    search = PostgresSemanticSearch(
        create_database_engine(settings.database_url), provider
    )
    results: dict[str, dict[str, float]] = {}
    selected: int | None = None
    target = float(config["multi_rule_gold_chunk_recall_target"])
    for candidate in config["candidate_top_k"]:
        recalls: dict[str, float] = {}
        for case in cases:
            returned = {
                row["item_id"]
                for row in search.search(
                    case["question"],
                    item_type=str(
                        config.get("eligibility_corpus_item_type", "evaluation_handbook")
                    ),
                    limit=int(candidate),
                )
            }
            gold = set(case["gold_chunk_ids"].split(";"))
            recalls[case["case_id"]] = len(gold & returned) / len(gold)
        multi = [
            recalls[case["case_id"]]
            for case in cases
            if case["query_class"] == "multi_rule"
        ]
        mean_multi = sum(multi) / len(multi)
        overall = sum(recalls.values()) / len(recalls)
        results[str(candidate)] = {
            "multi_rule_mean_recall": round(mean_multi, 6),
            "overall_mean_recall": round(overall, 6),
            **{key: round(value, 6) for key, value in recalls.items()},
        }
        if selected is None and mean_multi >= target:
            selected = int(candidate)

    if selected is None:
        selected = max(int(value) for value in config["candidate_top_k"])
        status = "frozen_best_feasible_below_target"
    else:
        status = "frozen_target_met"
    config.update(
        {
            "status": status,
            "selected_top_k": selected,
            "development_results": results,
            "selection_note": (
                "Selected the smallest candidate meeting the multi-rule mean recall "
                "target; otherwise selected the largest tested value as the documented "
                "best feasible setting."
            ),
        }
    )
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print(f"Selected top_k: {selected}")
    print(f"Status: {status}")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
