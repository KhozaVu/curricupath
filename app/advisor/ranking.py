"""Transparent public-course ranking with an optional learned linear model."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol

from app.advisor.normalisation import normalise_text


FEATURE_ORDER = (
    "interest_overlap",
    "career_overlap",
    "lexical_relevance",
    "semantic_similarity",
    "workload_match",
    "interest_missing",
    "career_missing",
    "workload_missing",
)
MODEL_TYPE = "l2_pairwise_logistic"
ARTIFACT_VERSION = 1


class PreferenceRequest(Protocol):
    interests: list[str]
    career_preferences: list[str]
    workload_preference: str | None
    format_preference: str | None


class RankingUnavailableError(RuntimeError):
    """Raised when a learned ranker cannot safely score the current request."""


class PublicCourseRanker(Protocol):
    mode: str

    def score(
        self,
        message: str,
        request: PreferenceRequest,
        course: Mapping[str, Any],
        semantic_score: float | None,
    ) -> dict[str, Any]: ...


@dataclass(frozen=True)
class PairwiseLogisticRanker:
    """Versioned linear pairwise ranker deployed from a validated JSON artifact."""

    coefficients: tuple[float, ...]
    catalogue_fingerprint: str
    embedding_model: str
    model_checksum: str
    deployment_eligible: bool
    requires_semantic: bool = True
    mode: str = "pairwise_logistic"

    @classmethod
    def load(
        cls,
        path: Path | str,
        *,
        catalogue_fingerprint: str,
        embedding_model: str,
        require_deployment_eligible: bool = True,
    ) -> PairwiseLogisticRanker:
        """Load an artifact only when its provenance matches the live catalogue."""

        artifact_path = Path(path)
        with artifact_path.open(encoding="utf-8") as model_file:
            artifact = json.load(model_file)
        if not isinstance(artifact, dict):
            raise ValueError("Ranker artifact must contain a JSON object.")
        if artifact.get("artifact_version") != ARTIFACT_VERSION:
            raise ValueError("Unsupported ranker artifact version.")
        if artifact.get("model_type") != MODEL_TYPE:
            raise ValueError("Unsupported ranker model type.")
        if tuple(artifact.get("feature_order", ())) != FEATURE_ORDER:
            raise ValueError("Ranker feature order does not match the application.")

        checksum = artifact.get("model_checksum")
        if not isinstance(checksum, str) or checksum != artifact_checksum(artifact):
            raise ValueError("Ranker artifact checksum is invalid.")
        if artifact.get("catalogue_fingerprint") != catalogue_fingerprint:
            raise ValueError("Ranker catalogue fingerprint does not match the live data.")
        if artifact.get("embedding_model") != embedding_model:
            raise ValueError("Ranker embedding model does not match the live model.")
        if require_deployment_eligible and not artifact.get("deployment_eligible", False):
            raise ValueError("Ranker artifact has not passed the deployment criteria.")

        coefficients = tuple(float(value) for value in artifact.get("coefficients", ()))
        if len(coefficients) != len(FEATURE_ORDER) or not all(
            math.isfinite(value) for value in coefficients
        ):
            raise ValueError("Ranker artifact has invalid coefficients.")
        return cls(
            coefficients=coefficients,
            catalogue_fingerprint=catalogue_fingerprint,
            embedding_model=embedding_model,
            model_checksum=checksum,
            deployment_eligible=bool(artifact.get("deployment_eligible")),
            requires_semantic=bool(artifact.get("requires_semantic", True)),
        )

    def score(
        self,
        message: str,
        request: PreferenceRequest,
        course: Mapping[str, Any],
        semantic_score: float | None,
    ) -> dict[str, Any]:
        if self.requires_semantic and semantic_score is None:
            raise RankingUnavailableError(
                "The learned ranker requires a semantic similarity value."
            )
        features = public_course_features(message, request, course, semantic_score)
        exact_contributions = {
            name: features[name] * coefficient
            for name, coefficient in zip(FEATURE_ORDER, self.coefficients, strict=True)
        }
        raw_score = sum(exact_contributions.values())
        contributions = {
            name: round(value, 6) for name, value in exact_contributions.items()
        }
        probability = 1.0 / (1.0 + math.exp(-max(-700.0, min(700.0, raw_score))))
        return _ranked_course(
            course,
            probability,
            features,
            ranking_mode=self.mode,
            contributions=contributions,
            raw_score=raw_score,
            semantic_available=semantic_score is not None,
        )


class DeterministicPublicCourseRanker:
    """Frozen criteria-based production baseline and model fallback."""

    mode = "deterministic"

    def score(
        self,
        message: str,
        request: PreferenceRequest,
        course: Mapping[str, Any],
        semantic_score: float | None,
    ) -> dict[str, Any]:
        features = public_course_features(message, request, course, semantic_score)
        preference_parts: list[float] = []
        if request.workload_preference:
            preference_parts.append(features["workload_match"])
        if request.format_preference:
            preference_parts.append(
                1.0 if request.format_preference == course["format"] else 0.0
            )
        preference_score = (
            sum(preference_parts) / len(preference_parts) if preference_parts else None
        )
        weighted: list[tuple[float, float]] = [
            (0.22, features["lexical_relevance"])
        ]
        if semantic_score is not None:
            weighted.append((0.35, features["semantic_similarity"]))
        if not features["interest_missing"]:
            weighted.append((0.33, features["interest_overlap"]))
        if not features["career_missing"]:
            weighted.append((0.28, features["career_overlap"]))
        if preference_score is not None:
            weighted.append((0.17, preference_score))
        score = sum(weight * value for weight, value in weighted) / sum(
            weight for weight, _ in weighted
        )
        return _ranked_course(
            course,
            score,
            features,
            ranking_mode=self.mode,
            semantic_available=semantic_score is not None,
            preference_score=preference_score,
        )


def public_course_features(
    message: str,
    request: PreferenceRequest,
    course: Mapping[str, Any],
    semantic_score: float | None,
) -> dict[str, float]:
    """Create the frozen feature vector used by baseline and learned rankers."""

    interests = set(request.interests)
    careers = set(request.career_preferences)
    course_interests = set(course["interest_tags"])
    course_careers = set(course["career_tags"])
    query_tokens = set(normalise_text(message).split())
    item_text = " ".join(
        [
            str(course["title"]),
            str(course["description"]),
            *course["outcomes"],
            *course["topic_tags"],
        ]
    )
    item_tokens = set(normalise_text(item_text.replace("_", " ")).split())
    workload = request.workload_preference
    return {
        "interest_overlap": (
            len(interests & course_interests) / len(interests) if interests else 0.0
        ),
        "career_overlap": (
            len(careers & course_careers) / len(careers) if careers else 0.0
        ),
        "lexical_relevance": (
            len(query_tokens & item_tokens) / len(query_tokens) if query_tokens else 0.0
        ),
        "semantic_similarity": _bounded(semantic_score or 0.0),
        "workload_match": (
            _workload_score(workload, str(course["workload"])) if workload else 0.0
        ),
        "interest_missing": float(not interests),
        "career_missing": float(not careers),
        "workload_missing": float(workload is None),
    }


def artifact_checksum(artifact: Mapping[str, Any]) -> str:
    """Hash the canonical artifact payload while excluding its checksum field."""

    payload = {key: value for key, value in artifact.items() if key != "model_checksum"}
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _ranked_course(
    course: Mapping[str, Any],
    score: float,
    features: Mapping[str, float],
    *,
    ranking_mode: str,
    contributions: Mapping[str, float] | None = None,
    raw_score: float | None = None,
    semantic_available: bool = False,
    preference_score: float | None = None,
) -> dict[str, Any]:
    result = dict(course)
    result["score"] = round(_bounded(score), 4)
    result["ranking_mode"] = ranking_mode
    result["score_components"] = {
        "interest": None if features["interest_missing"] else features["interest_overlap"],
        "career": None if features["career_missing"] else features["career_overlap"],
        "text": round(features["lexical_relevance"], 4),
        "semantic": (
            round(features["semantic_similarity"], 4) if semantic_available else None
        ),
        "workload_format": preference_score,
        "feature_vector": {name: round(features[name], 6) for name in FEATURE_ORDER},
    }
    if contributions is not None:
        result["score_components"]["model_contributions"] = dict(contributions)
        result["score_components"]["model_raw_score"] = round(raw_score or 0.0, 6)
    return result


def _workload_score(preferred: str, actual: str) -> float:
    levels = {"light": 0, "moderate": 1, "heavy": 2}
    if preferred not in levels or actual not in levels:
        return 0.0
    return 1.0 - (abs(levels[preferred] - levels[actual]) / 2.0)


def _bounded(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
