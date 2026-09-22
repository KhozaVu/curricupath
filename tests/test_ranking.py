"""Tests for deterministic and learned public-course ranking."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.advisor.engine import AdvisorEngine
from app.advisor.intent import DeterministicIntentExtractor, ParsedAdvisorRequest
from app.advisor.ranker_training import (
    Judgement,
    RankedExample,
    TrainingProfile,
    evaluate_ranker,
    fit_pairwise_model,
    load_judgements,
    pairwise_training_data,
    validate_experiment_design,
)
from app.advisor.ranking import (
    ARTIFACT_VERSION,
    FEATURE_ORDER,
    MODEL_TYPE,
    DeterministicPublicCourseRanker,
    PairwiseLogisticRanker,
    artifact_checksum,
    public_course_features,
)
from app.backend import CurricuPathService
from app.data.repository import CsvCatalogueRepository
from app.data.sessions import ConversationContext


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DATA = PROJECT_ROOT / "data" / "processed"


class CompleteSemanticMatcher:
    def course_scores(self, query, course_ids):
        return {course_id: 0.8 for course_id in course_ids}

    def module_scores(self, query, module_codes):
        return {module_code: 0.8 for module_code in module_codes}


def _course(**overrides):
    course = {
        "course_id": "CRS001",
        "title": "Machine Learning Foundations",
        "description": "Learn supervised machine learning with Python.",
        "outcomes": ["Evaluate models"],
        "topic_tags": ["python", "machine_learning"],
        "interest_tags": ["machine_learning"],
        "career_tags": ["data_science"],
        "workload": "moderate",
        "format": "online",
        "provider": "Provider",
        "rating_mean": 5.0,
        "rating_count": 1000,
        "source_id": "SRC001",
    }
    course.update(overrides)
    return course


def _request():
    return ParsedAdvisorRequest(
        interests=["machine_learning"],
        career_preferences=["data_science"],
        workload_preference="moderate",
    )


def _artifact(**overrides):
    artifact = {
        "artifact_version": ARTIFACT_VERSION,
        "model_type": MODEL_TYPE,
        "feature_order": list(FEATURE_ORDER),
        "coefficients": [1.0] * len(FEATURE_ORDER),
        "catalogue_fingerprint": "catalogue-v1",
        "embedding_model": "embedding-v1",
        "deployment_eligible": True,
        "requires_semantic": True,
    }
    artifact.update(overrides)
    artifact["model_checksum"] = artifact_checksum(artifact)
    return artifact


def test_frozen_features_exclude_ratings_ids_sources_and_format() -> None:
    request = _request()
    first = public_course_features(
        "machine learning for data science",
        request,
        _course(),
        0.7,
    )
    second = public_course_features(
        "machine learning for data science",
        request,
        _course(
            course_id="DIFFERENT",
            rating_mean=0.0,
            rating_count=0,
            source_id="OTHER",
            format="in-person",
        ),
        0.7,
    )

    assert tuple(first) == FEATURE_ORDER
    assert first == second


def test_missing_preference_indicators_are_explicit() -> None:
    features = public_course_features(
        "python",
        ParsedAdvisorRequest(),
        _course(),
        0.4,
    )

    assert features["interest_missing"] == 1.0
    assert features["career_missing"] == 1.0
    assert features["workload_missing"] == 1.0
    assert features["interest_overlap"] == 0.0


def test_deterministic_ranker_remains_the_default_baseline() -> None:
    result = DeterministicPublicCourseRanker().score(
        "machine learning",
        _request(),
        _course(),
        0.8,
    )

    assert result["ranking_mode"] == "deterministic"
    assert 0 < result["score"] <= 1
    assert result["score_components"]["semantic"] == 0.8


def test_pairwise_data_adds_forward_and_reverse_weighted_pairs() -> None:
    better = RankedExample("P1", "train", "C1", 3, (1.0,) * len(FEATURE_ORDER))
    worse = RankedExample("P1", "train", "C2", 1, (0.0,) * len(FEATURE_ORDER))

    features, labels, weights = pairwise_training_data((better, worse), "train")

    assert features.shape == (2, len(FEATURE_ORDER))
    assert labels.tolist() == [1, 0]
    assert weights.tolist() == [2.0, 2.0]
    assert features[1].tolist() == (-features[0]).tolist()


def test_material_judge_disagreement_requires_notes(tmp_path: Path) -> None:
    path = tmp_path / "judgements.csv"
    path.write_text(
        "profile_id,course_id,judge_1_id,judge_1_grade,judge_2_id,"
        "judge_2_grade,final_grade,adjudication_notes\n"
        "P1,C1,J1,3,J2,1,2,\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="without adjudication notes"):
        load_judgements(path)


def test_profile_group_cannot_cross_splits() -> None:
    profiles = []
    for index in range(50):
        split = "train" if index < 30 else "validation" if index < 40 else "test"
        group = "LEAKED" if index in {0, 49} else f"G{index}"
        profiles.append(
            TrainingProfile(
                profile_id=f"P{index}",
                profile_group_id=group,
                split=split,
                query="circuits",
                interests=("electric_circuits",),
                career_preferences=(),
                workload_preference=None,
                profile_author="reviewer",
                review_status="approved",
            )
        )
    judgements = [
        Judgement(profile.profile_id, "C1", "J1", 2, "J2", 2, 2, "")
        for profile in profiles
    ]

    with pytest.raises(ValueError, match="Profile groups cross data splits"):
        validate_experiment_design(profiles, judgements, ["C1"])


def test_pairwise_model_can_fit_and_rank_separable_examples() -> None:
    examples = []
    for split in ("train", "validation", "test"):
        examples.extend(
            (
                RankedExample(
                    f"{split}-profile",
                    split,
                    "better",
                    3,
                    (1.0,) + (0.0,) * (len(FEATURE_ORDER) - 1),
                ),
                RankedExample(
                    f"{split}-profile",
                    split,
                    "worse",
                    0,
                    (0.0,) * len(FEATURE_ORDER),
                ),
            )
        )

    model, selected_c, tuning = fit_pairwise_model(examples)
    metrics = evaluate_ranker(examples, "test", model.coef_[0])

    assert selected_c in {0.01, 0.1, 1.0, 10.0}
    assert len(tuning["trials"]) == 4
    assert metrics["ndcg_at_3"] == 1.0


def test_ranker_artifact_detects_tampering(tmp_path: Path) -> None:
    artifact = _artifact()
    artifact["coefficients"][0] = 9.0
    path = tmp_path / "model.json"
    path.write_text(json.dumps(artifact), encoding="utf-8")

    with pytest.raises(ValueError, match="checksum"):
        PairwiseLogisticRanker.load(
            path,
            catalogue_fingerprint="catalogue-v1",
            embedding_model="embedding-v1",
        )


def test_ranker_artifact_rejects_stale_catalogue(tmp_path: Path) -> None:
    artifact = _artifact()
    path = tmp_path / "model.json"
    path.write_text(json.dumps(artifact), encoding="utf-8")

    with pytest.raises(ValueError, match="catalogue fingerprint"):
        PairwiseLogisticRanker.load(
            path,
            catalogue_fingerprint="catalogue-v2",
            embedding_model="embedding-v1",
        )


def test_advisor_uses_valid_learned_ranker_with_complete_semantics() -> None:
    repository = CsvCatalogueRepository(PROCESSED_DATA)
    service = CurricuPathService(repository, str(PROJECT_ROOT))
    ranker = PairwiseLogisticRanker(
        coefficients=(1.0,) * len(FEATURE_ORDER),
        catalogue_fingerprint="test",
        embedding_model="test",
        model_checksum="test",
        deployment_eligible=True,
    )
    engine = AdvisorEngine(
        service,
        DeterministicIntentExtractor(repository.data.aliases),
        CompleteSemanticMatcher(),
        ranker,
    )

    result = engine.advise("Find an electric circuits course")

    assert result["ranking_mode"] == "pairwise_logistic"
    assert all(
        item["ranking_mode"] == "pairwise_logistic"
        for item in result["recommendations"]
    )
    assert "model_contributions" in result["recommendations"][0]["score_components"]


def test_advisor_can_explicitly_select_deterministic_ranking() -> None:
    repository = CsvCatalogueRepository(PROCESSED_DATA)
    service = CurricuPathService(repository, str(PROJECT_ROOT))
    ranker = PairwiseLogisticRanker(
        coefficients=(1.0,) * len(FEATURE_ORDER),
        catalogue_fingerprint="test",
        embedding_model="test",
        model_checksum="test",
        deployment_eligible=False,
    )
    engine = AdvisorEngine(
        service,
        DeterministicIntentExtractor(repository.data.aliases),
        CompleteSemanticMatcher(),
        ranker,
    )

    result = engine.advise(
        "Find an electric circuits course",
        ranking_mode="deterministic",
    )

    assert result["ranking_mode"] == "deterministic"
    assert all(
        "model_contributions" not in item["score_components"]
        for item in result["recommendations"]
    )


def test_prototype_collects_and_applies_workload_and_difficulty() -> None:
    repository = CsvCatalogueRepository(PROCESSED_DATA)
    service = CurricuPathService(repository, str(PROJECT_ROOT))
    ranker = PairwiseLogisticRanker(
        coefficients=(1.0,) * len(FEATURE_ORDER),
        catalogue_fingerprint="test",
        embedding_model="test",
        model_checksum="test",
        deployment_eligible=False,
    )
    engine = AdvisorEngine(
        service,
        DeterministicIntentExtractor(repository.data.aliases),
        CompleteSemanticMatcher(),
        ranker,
    )

    workload = engine.advise(
        "Find a networking course",
        ranking_mode="prototype",
    )
    difficulty = engine.advise(
        "Light workload",
        context=ConversationContext.from_dict(workload["conversation_context"]),
        ranking_mode="prototype",
    )
    result = engine.advise(
        "Beginner",
        context=ConversationContext.from_dict(difficulty["conversation_context"]),
        ranking_mode="prototype",
    )

    assert workload["clarification_options"] == [
        "Light workload",
        "Moderate workload",
        "Heavy workload",
    ]
    assert difficulty["clarification_options"] == ["Beginner", "Intermediate"]
    assert result["status"] == "ok"
    assert result["preferences_applied"] == {
        "workload": "light",
        "difficulty": "beginner",
    }
    assert all(course["level"] == "beginner" for course in result["recommendations"])
    assert all(
        "networking" in course["interest_tags"]
        for course in result["recommendations"]
    )
    assert result["recommendations"][0]["workload"] == "light"
    assert "explicit_workload_match" in result["recommendations"][0]["score_components"]


def test_advisor_falls_back_for_whole_request_without_semantics() -> None:
    repository = CsvCatalogueRepository(PROCESSED_DATA)
    service = CurricuPathService(repository, str(PROJECT_ROOT))
    ranker = PairwiseLogisticRanker(
        coefficients=(1.0,) * len(FEATURE_ORDER),
        catalogue_fingerprint="test",
        embedding_model="test",
        model_checksum="test",
        deployment_eligible=True,
    )
    engine = AdvisorEngine(
        service,
        DeterministicIntentExtractor(repository.data.aliases),
        public_course_ranker=ranker,
    )

    result = engine.advise("Find an electric circuits course")

    assert result["ranking_mode"] == "deterministic"
    assert all(
        item["ranking_mode"] == "deterministic"
        for item in result["recommendations"]
    )
