"""Train and evaluate the versioned public-course pairwise logistic ranker."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.advisor.ranker_training import (
    FEATURE_ORDER,
    RANDOM_SEED,
    bootstrap_ndcg_difference,
    build_examples,
    dependency_versions,
    evaluate_baselines,
    evaluate_ranker,
    fit_pairwise_model,
    judge_agreement,
    label_file_hash,
    load_judgements,
    load_profiles,
    validate_experiment_design,
)
from app.advisor.prototype_labels import load_prototype_judgements
from app.advisor.ranking import (
    ARTIFACT_VERSION,
    MODEL_TYPE,
    artifact_checksum,
)
from app.config import get_settings
from app.data.database import create_database_engine
from app.data.embeddings import HuggingFaceHostedEmbeddings, PostgresSemanticSearch
from app.data.postgres_repository import PostgresCatalogueRepository
from app.data.recommendation_log import catalogue_version


DEFAULT_EXPERIMENT = PROJECT_ROOT / "experiments" / "ranking"
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "experiments"
    / "models"
    / "public_course_pairwise_logistic_v1.json"
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profiles",
        type=Path,
        default=DEFAULT_EXPERIMENT / "profiles.csv",
    )
    parser.add_argument(
        "--judgements",
        type=Path,
        default=DEFAULT_EXPERIMENT / "judgements.csv",
    )
    parser.add_argument(
        "--prototype-labels",
        type=Path,
        help=(
            "Use a clearly marked weak-label CSV instead of the two-judge dataset. "
            "Artifacts trained this way are never deployment eligible."
        ),
    )
    parser.add_argument(
        "--semantic-cache",
        type=Path,
        default=DEFAULT_EXPERIMENT / "semantic_scores.csv",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--bootstrap-samples", type=int, default=1000)
    parser.add_argument(
        "--approve-coefficients",
        action="store_true",
        help="Record that a human reviewed coefficient signs and contributions.",
    )
    args = parser.parse_args()

    try:
        profiles = load_profiles(args.profiles)
        judgements = (
            load_prototype_judgements(args.prototype_labels)
            if args.prototype_labels
            else load_judgements(args.judgements)
        )
    except (OSError, ValueError) as error:
        raise SystemExit(f"Training data is not ready: {error}") from error
    settings = get_settings()
    if not settings.hf_token:
        raise SystemExit("HF_TOKEN is required to build the frozen semantic feature.")
    engine = create_database_engine(settings.database_url)
    repository = PostgresCatalogueRepository(engine)
    if not repository.is_healthy():
        raise SystemExit("The imported PostgreSQL catalogue is not available.")
    courses = repository.list_courses(limit=100)
    course_ids = [course["course_id"] for course in courses]
    aliases = repository.get_aliases()
    validate_experiment_design(
        profiles,
        judgements,
        course_ids,
        allowed_interests=frozenset(
            alias.canonical_tag for alias in aliases if alias.tag_type == "interest"
        ),
        allowed_careers=frozenset(
            alias.canonical_tag for alias in aliases if alias.tag_type == "career"
        ),
    )

    fingerprint = catalogue_version(engine)
    semantic_scores = _semantic_scores(
        profiles,
        course_ids,
        fingerprint,
        settings.embedding_model,
        args.semantic_cache,
        PostgresSemanticSearch(
            engine,
            HuggingFaceHostedEmbeddings(
                settings.hf_token,
                settings.embedding_model,
                settings.embedding_dimension,
            ),
        ),
    )
    examples = build_examples(profiles, judgements, courses, semantic_scores)
    model, selected_c, tuning = fit_pairwise_model(examples)
    coefficients = [float(value) for value in model.coef_[0]]
    validation_metrics = next(
        trial["metrics"]
        for trial in tuning["trials"]
        if trial["C"] == selected_c
    )
    test_metrics = evaluate_ranker(examples, "test", coefficients)
    baselines = {
        "validation": evaluate_baselines(examples, "validation"),
        "test": evaluate_baselines(examples, "test"),
    }
    uncertainty = bootstrap_ndcg_difference(
        examples,
        coefficients,
        samples=args.bootstrap_samples,
    )
    coefficient_signs_acceptable = all(value >= 0 for value in coefficients[:5])
    deployment_checks = {
        "beats_test_deterministic_ndcg_at_3": (
            test_metrics["ndcg_at_3"]
            > baselines["test"]["deterministic"]["ndcg_at_3"]
        ),
        "bootstrap_lower_95_above_zero": uncertainty["lower_95"] > 0,
        "positive_test_profile_fraction_at_least_0_6": (
            uncertainty["positive_profile_fraction"] >= 0.6
        ),
        "relevance_coefficients_nonnegative": coefficient_signs_acceptable,
        "human_coefficient_review": args.approve_coefficients,
        "source_or_eligibility_violations": 0,
    }
    deployment_eligible = not args.prototype_labels and all(
        value is True
        for key, value in deployment_checks.items()
        if key != "source_or_eligibility_violations"
    ) and deployment_checks["source_or_eligibility_violations"] == 0

    artifact: dict[str, Any] = {
        "artifact_version": ARTIFACT_VERSION,
        "model_type": MODEL_TYPE,
        "feature_order": list(FEATURE_ORDER),
        "coefficients": coefficients,
        "regularization_C": selected_c,
        "fit_intercept": False,
        "requires_semantic": True,
        "catalogue_fingerprint": fingerprint,
        "training_label_hash": label_file_hash(
            args.prototype_labels or args.judgements
        ),
        "label_provenance": (
            "prototype_criteria_v1_codex_assisted"
            if args.prototype_labels
            else "two_independent_human_judges"
        ),
        "profile_definition_hash": label_file_hash(args.profiles),
        "embedding_model": settings.embedding_model,
        "embedding_dimension": settings.embedding_dimension,
        "random_seed": RANDOM_SEED,
        "dependency_versions": dependency_versions(),
        "judge_agreement": (
            {
                "status": "not_applicable",
                "reason": "Prototype weak labels have no independent second judge.",
                "judgement_count": len(judgements),
            }
            if args.prototype_labels
            else judge_agreement(judgements)
        ),
        "tuning": tuning,
        "validation_metrics": validation_metrics,
        "test_metrics": test_metrics,
        "baselines": baselines,
        "test_bootstrap_ndcg_at_3_difference": uncertainty,
        "deployment_checks": deployment_checks,
        "deployment_eligible": deployment_eligible,
    }
    artifact["model_checksum"] = artifact_checksum(artifact)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(f"Profiles: {len(profiles)}")
    print(f"Courses per profile: {len(courses)}")
    print(f"Judgements: {len(judgements)}")
    agreement = artifact["judge_agreement"]
    if "weighted_cohens_kappa" in agreement:
        print(f"Weighted Cohen's kappa: {agreement['weighted_cohens_kappa']}")
    else:
        print("Weighted Cohen's kappa: not applicable (prototype labels)")
    print(f"Selected C: {selected_c}")
    print(f"Test NDCG@3: {test_metrics['ndcg_at_3']}")
    print(
        "Deterministic test NDCG@3: "
        f"{baselines['test']['deterministic']['ndcg_at_3']}"
    )
    print(f"Deployment eligible: {deployment_eligible}")
    print(f"Artifact: {args.output}")


def _semantic_scores(
    profiles,
    course_ids: list[str],
    fingerprint: str,
    embedding_model: str,
    cache_path: Path,
    search: PostgresSemanticSearch,
) -> dict[tuple[str, str], float]:
    expected = {
        (profile.profile_id, course_id)
        for profile in profiles
        for course_id in course_ids
    }
    cached = _read_semantic_cache(cache_path, fingerprint, embedding_model)
    for profile in profiles:
        missing_ids = [
            course_id
            for course_id in course_ids
            if (profile.profile_id, course_id) not in cached
        ]
        if not missing_ids:
            continue
        values = search.course_scores(profile.query, missing_ids)
        if set(values) != set(missing_ids):
            missing = sorted(set(missing_ids) - set(values))
            raise ValueError(
                "Semantic retrieval did not return every course: " + ", ".join(missing)
            )
        cached.update(
            {
                (profile.profile_id, course_id): score
                for course_id, score in values.items()
            }
        )
        _write_semantic_cache(cache_path, fingerprint, embedding_model, cached)
    return {key: cached[key] for key in expected}


def _read_semantic_cache(
    path: Path, fingerprint: str, embedding_model: str
) -> dict[tuple[str, str], float]:
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as cache_file:
        rows = list(csv.DictReader(cache_file))
    return {
        (row["profile_id"], row["course_id"]): float(row["semantic_similarity"])
        for row in rows
        if row["catalogue_fingerprint"] == fingerprint
        and row["embedding_model"] == embedding_model
    }


def _write_semantic_cache(
    path: Path,
    fingerprint: str,
    embedding_model: str,
    values: dict[tuple[str, str], float],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as cache_file:
        writer = csv.DictWriter(
            cache_file,
            fieldnames=(
                "catalogue_fingerprint",
                "embedding_model",
                "profile_id",
                "course_id",
                "semantic_similarity",
            ),
        )
        writer.writeheader()
        for (profile_id, course_id), score in sorted(values.items()):
            writer.writerow(
                {
                    "catalogue_fingerprint": fingerprint,
                    "embedding_model": embedding_model,
                    "profile_id": profile_id,
                    "course_id": course_id,
                    "semantic_similarity": score,
                }
            )
    _replace_cache_file(temporary, path)


def _replace_cache_file(temporary: Path, destination: Path) -> None:
    """Retry atomic cache replacement when Windows briefly locks the old file."""

    for attempt in range(6):
        try:
            os.replace(temporary, destination)
            return
        except PermissionError:
            if attempt == 5:
                raise
            time.sleep(0.1 * (attempt + 1))


if __name__ == "__main__":
    main()
