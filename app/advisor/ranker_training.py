"""Reproducible experiment utilities for the public-course pairwise ranker."""

from __future__ import annotations

import csv
import hashlib
import itertools
import math
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping, Sequence

if TYPE_CHECKING:
    import numpy as np
    from sklearn.linear_model import LogisticRegression

from app.advisor.ranking import FEATURE_ORDER, public_course_features


RANDOM_SEED = 26073
REGULARISATION_VALUES = (0.01, 0.1, 1.0, 10.0)
VALID_SPLITS = {"train", "validation", "test"}


@dataclass(frozen=True)
class TrainingProfile:
    profile_id: str
    profile_group_id: str
    split: str
    query: str
    interests: tuple[str, ...]
    career_preferences: tuple[str, ...]
    workload_preference: str | None
    profile_author: str
    review_status: str


@dataclass(frozen=True)
class Judgement:
    profile_id: str
    course_id: str
    judge_1_id: str
    judge_1_grade: int
    judge_2_id: str
    judge_2_grade: int
    final_grade: int
    adjudication_notes: str


@dataclass(frozen=True)
class RankedExample:
    profile_id: str
    split: str
    course_id: str
    grade: int
    features: tuple[float, ...]


def load_profiles(
    path: Path | str, *, require_approved: bool = True
) -> tuple[TrainingProfile, ...]:
    required = (
        "profile_id",
        "profile_group_id",
        "split",
        "query",
        "interests",
        "career_preferences",
        "workload_preference",
        "profile_author",
        "review_status",
    )
    rows = _read_csv(path, required)
    profiles: list[TrainingProfile] = []
    seen: set[str] = set()
    for row in rows:
        profile_id = row["profile_id"].strip()
        profile_group_id = row["profile_group_id"].strip()
        split = row["split"].strip().lower()
        query = row["query"].strip()
        workload = row["workload_preference"].strip().lower() or None
        author = row["profile_author"].strip()
        review_status = row["review_status"].strip().lower()
        if not profile_id or not profile_group_id or profile_id in seen:
            raise ValueError(f"Duplicate or empty profile_id {profile_id!r}.")
        if split not in VALID_SPLITS:
            raise ValueError(f"Profile {profile_id} has invalid split {split!r}.")
        if not query:
            raise ValueError(f"Profile {profile_id} has no query.")
        if workload not in {None, "light", "moderate", "heavy"}:
            raise ValueError(f"Profile {profile_id} has invalid workload {workload!r}.")
        if not author:
            raise ValueError(f"Profile {profile_id} has no profile author.")
        if review_status not in {"draft", "approved"}:
            raise ValueError(
                f"Profile {profile_id} has invalid review status {review_status!r}."
            )
        if require_approved and review_status != "approved":
            raise ValueError(
                f"Profile {profile_id} is not approved for independent judging."
            )
        seen.add(profile_id)
        profiles.append(
            TrainingProfile(
                profile_id=profile_id,
                profile_group_id=profile_group_id,
                split=split,
                query=query,
                interests=_split_tags(row["interests"]),
                career_preferences=_split_tags(row["career_preferences"]),
                workload_preference=workload,
                profile_author=author,
                review_status=review_status,
            )
        )
    return tuple(profiles)


def load_judgements(path: Path | str) -> tuple[Judgement, ...]:
    required = (
        "profile_id",
        "course_id",
        "judge_1_id",
        "judge_1_grade",
        "judge_2_id",
        "judge_2_grade",
        "final_grade",
        "adjudication_notes",
    )
    rows = _read_csv(path, required)
    judgements: list[Judgement] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        key = (row["profile_id"].strip(), row["course_id"].strip())
        if not all(key) or key in seen:
            raise ValueError(f"Duplicate or empty judgement key {key!r}.")
        judge_1 = row["judge_1_id"].strip()
        judge_2 = row["judge_2_id"].strip()
        if not judge_1 or not judge_2 or judge_1 == judge_2:
            raise ValueError(f"Judgement {key} requires two different named judges.")
        grades = tuple(
            _grade(row[field], key)
            for field in ("judge_1_grade", "judge_2_grade", "final_grade")
        )
        notes = row["adjudication_notes"].strip()
        if not min(grades[0], grades[1]) <= grades[2] <= max(grades[0], grades[1]):
            raise ValueError(
                f"Judgement {key} final grade must be within the judges' grades."
            )
        if abs(grades[0] - grades[1]) >= 2 and not notes:
            raise ValueError(
                f"Judgement {key} has a material disagreement without adjudication notes."
            )
        seen.add(key)
        judgements.append(
            Judgement(
                profile_id=key[0],
                course_id=key[1],
                judge_1_id=judge_1,
                judge_1_grade=grades[0],
                judge_2_id=judge_2,
                judge_2_grade=grades[1],
                final_grade=grades[2],
                adjudication_notes=notes,
            )
        )
    return tuple(judgements)


def validate_experiment_design(
    profiles: Sequence[TrainingProfile],
    judgements: Sequence[Judgement],
    course_ids: Sequence[str],
    *,
    minimum_profiles: int = 50,
    allowed_interests: frozenset[str] | None = None,
    allowed_careers: frozenset[str] | None = None,
) -> None:
    """Require profile-level splits and complete independent course judgements."""

    if len(profiles) < minimum_profiles:
        raise ValueError(
            f"At least {minimum_profiles} independently defined profiles are required."
        )
    counts = {
        split: sum(profile.split == split for profile in profiles)
        for split in VALID_SPLITS
    }
    required_counts = {"train": 30, "validation": 10, "test": 10}
    for split, minimum in required_counts.items():
        if counts[split] < minimum:
            raise ValueError(f"The {split} split requires at least {minimum} profiles.")
    group_splits: dict[str, set[str]] = {}
    for profile in profiles:
        group_splits.setdefault(profile.profile_group_id, set()).add(profile.split)
    leaked_groups = sorted(
        group_id for group_id, splits in group_splits.items() if len(splits) > 1
    )
    if leaked_groups:
        raise ValueError(
            "Profile groups cross data splits: " + ", ".join(leaked_groups) + "."
        )
    for profile in profiles:
        interest_vocabulary = (
            set(profile.interests)
            if allowed_interests is None
            else set(allowed_interests)
        )
        career_vocabulary = (
            set(profile.career_preferences)
            if allowed_careers is None
            else set(allowed_careers)
        )
        unknown_interests = set(profile.interests) - interest_vocabulary
        unknown_careers = set(profile.career_preferences) - career_vocabulary
        if unknown_interests:
            raise ValueError(
                f"Profile {profile.profile_id} has unknown interests: "
                f"{', '.join(sorted(unknown_interests))}."
            )
        if unknown_careers:
            raise ValueError(
                f"Profile {profile.profile_id} has unknown careers: "
                f"{', '.join(sorted(unknown_careers))}."
            )

    expected = {
        (profile.profile_id, course_id)
        for profile in profiles
        for course_id in course_ids
    }
    actual = {(row.profile_id, row.course_id) for row in judgements}
    missing = expected - actual
    extra = actual - expected
    if missing:
        raise ValueError(f"Missing {len(missing)} profile-course judgements.")
    if extra:
        raise ValueError(f"Found {len(extra)} judgements outside the experiment design.")


def build_examples(
    profiles: Sequence[TrainingProfile],
    judgements: Sequence[Judgement],
    courses: Sequence[Mapping[str, Any]],
    semantic_scores: Mapping[tuple[str, str], float],
) -> tuple[RankedExample, ...]:
    profile_index = {profile.profile_id: profile for profile in profiles}
    course_index = {str(course["course_id"]): course for course in courses}
    examples: list[RankedExample] = []
    for judgement in judgements:
        profile = profile_index[judgement.profile_id]
        course = course_index[judgement.course_id]
        semantic_key = (judgement.profile_id, judgement.course_id)
        if semantic_key not in semantic_scores:
            raise ValueError(f"Missing semantic score for {semantic_key!r}.")
        feature_map = public_course_features(
            profile.query,
            profile,
            course,
            semantic_scores[semantic_key],
        )
        examples.append(
            RankedExample(
                profile_id=profile.profile_id,
                split=profile.split,
                course_id=judgement.course_id,
                grade=judgement.final_grade,
                features=tuple(feature_map[name] for name in FEATURE_ORDER),
            )
        )
    return tuple(examples)


def pairwise_training_data(
    examples: Sequence[RankedExample],
    split: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Build balanced forward/reverse pairs weighted by relevance difference."""

    import numpy as np

    features: list[tuple[float, ...]] = []
    labels: list[int] = []
    weights: list[float] = []
    for group in _profile_groups(examples, split).values():
        for left, right in itertools.combinations(group, 2):
            if left.grade == right.grade:
                continue
            better, worse = (left, right) if left.grade > right.grade else (right, left)
            difference = tuple(
                high - low for high, low in zip(better.features, worse.features, strict=True)
            )
            relevance_difference = float(better.grade - worse.grade)
            features.extend((difference, tuple(-value for value in difference)))
            labels.extend((1, 0))
            weights.extend((relevance_difference, relevance_difference))
    if not features:
        raise ValueError(f"The {split} split does not contain any graded preference pairs.")
    return (
        np.asarray(features, dtype=np.float64),
        np.asarray(labels, dtype=np.int8),
        np.asarray(weights, dtype=np.float64),
    )


def fit_pairwise_model(
    examples: Sequence[RankedExample],
    regularisation_values: Sequence[float] = REGULARISATION_VALUES,
) -> tuple[LogisticRegression, float, dict[str, Any]]:
    """Tune only C on validation NDCG@3, then refit on train and validation."""

    train_x, train_y, train_weight = pairwise_training_data(examples, "train")
    trials: list[dict[str, Any]] = []
    best_c: float | None = None
    best_ndcg = -1.0
    for value in regularisation_values:
        model = _new_model(value)
        model.fit(train_x, train_y, sample_weight=train_weight)
        metrics = evaluate_ranker(examples, "validation", model.coef_[0])
        trials.append({"C": value, "metrics": metrics})
        if metrics["ndcg_at_3"] > best_ndcg:
            best_c = value
            best_ndcg = metrics["ndcg_at_3"]
    if best_c is None:
        raise ValueError("No regularisation candidate could be evaluated.")

    train_validation = tuple(
        example for example in examples if example.split in {"train", "validation"}
    )
    combined_x, combined_y, combined_weight = _pairwise_data_for_examples(
        train_validation
    )
    final_model = _new_model(best_c)
    final_model.fit(combined_x, combined_y, sample_weight=combined_weight)
    return final_model, best_c, {"trials": trials, "selected_C": best_c}


def evaluate_ranker(
    examples: Sequence[RankedExample],
    split: str,
    coefficients: Sequence[float],
) -> dict[str, float]:
    groups = _profile_groups(examples, split)
    if not groups:
        raise ValueError(f"No examples are available for split {split!r}.")
    per_profile = [
        _profile_metrics(group, coefficients) for group in groups.values()
    ]
    return _mean_metrics(per_profile)


def evaluate_baselines(
    examples: Sequence[RankedExample], split: str
) -> dict[str, dict[str, float]]:
    groups = _profile_groups(examples, split)
    deterministic = [
        _profile_metrics(group, None, baseline="deterministic")
        for group in groups.values()
    ]
    semantic = [
        _profile_metrics(group, None, baseline="semantic") for group in groups.values()
    ]
    return {
        "deterministic": _mean_metrics(deterministic),
        "semantic_only": _mean_metrics(semantic),
    }


def bootstrap_ndcg_difference(
    examples: Sequence[RankedExample],
    coefficients: Sequence[float],
    *,
    samples: int = 1000,
    seed: int = RANDOM_SEED,
) -> dict[str, float]:
    """Profile-cluster bootstrap interval for ML minus deterministic NDCG@3."""

    import numpy as np

    groups = list(_profile_groups(examples, "test").values())
    if not groups or samples <= 0:
        raise ValueError("Bootstrap evaluation requires test profiles and samples.")
    differences = np.asarray(
        [
            _profile_metrics(group, coefficients)["ndcg_at_3"]
            - _profile_metrics(group, None, baseline="deterministic")["ndcg_at_3"]
            for group in groups
        ],
        dtype=np.float64,
    )
    rng = np.random.default_rng(seed)
    means = np.asarray(
        [rng.choice(differences, size=len(differences), replace=True).mean() for _ in range(samples)]
    )
    return {
        "mean": round(float(differences.mean()), 6),
        "lower_95": round(float(np.quantile(means, 0.025)), 6),
        "upper_95": round(float(np.quantile(means, 0.975)), 6),
        "positive_profile_fraction": round(float((differences > 0).mean()), 6),
    }


def judge_agreement(judgements: Sequence[Judgement]) -> dict[str, float | int]:
    from sklearn.metrics import cohen_kappa_score

    if not judgements:
        raise ValueError("Judge agreement requires completed judgements.")
    score = cohen_kappa_score(
        [row.judge_1_grade for row in judgements],
        [row.judge_2_grade for row in judgements],
        weights="quadratic",
    )
    if not math.isfinite(float(score)):
        score = float(
            all(
                row.judge_1_grade == row.judge_2_grade
                for row in judgements
            )
        )
    return {
        "weighted_cohens_kappa": round(float(score), 6),
        "material_disagreements": sum(
            abs(row.judge_1_grade - row.judge_2_grade) >= 2 for row in judgements
        ),
        "judgement_count": len(judgements),
    }


def label_file_hash(path: Path | str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dependency_versions() -> dict[str, str]:
    import numpy as np
    from sklearn import __version__ as sklearn_version

    return {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scikit_learn": sklearn_version,
    }


def _new_model(regularisation: float) -> LogisticRegression:
    from sklearn.linear_model import LogisticRegression

    return LogisticRegression(
        solver="liblinear",
        fit_intercept=False,
        random_state=RANDOM_SEED,
        max_iter=2000,
        C=regularisation,
    )


def _pairwise_data_for_examples(
    examples: Sequence[RankedExample],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    remapped = tuple(
        RankedExample(
            profile_id=row.profile_id,
            split="combined",
            course_id=row.course_id,
            grade=row.grade,
            features=row.features,
        )
        for row in examples
    )
    return pairwise_training_data(remapped, "combined")


def _profile_groups(
    examples: Sequence[RankedExample], split: str
) -> dict[str, list[RankedExample]]:
    groups: dict[str, list[RankedExample]] = {}
    for example in examples:
        if example.split == split:
            groups.setdefault(example.profile_id, []).append(example)
    return groups


def _profile_metrics(
    examples: Sequence[RankedExample],
    coefficients: Sequence[float] | None,
    *,
    baseline: str | None = None,
) -> dict[str, float]:
    import numpy as np

    scored: list[tuple[float, int, str]] = []
    for example in examples:
        if baseline == "semantic":
            score = example.features[FEATURE_ORDER.index("semantic_similarity")]
        elif baseline == "deterministic":
            score = _deterministic_feature_score(example.features)
        elif coefficients is not None:
            score = float(np.dot(example.features, coefficients))
        else:
            raise ValueError("A model or named baseline is required.")
        scored.append((score, example.grade, example.course_id))
    ranked = sorted(scored, key=lambda row: (-row[0], row[2]))
    grades = [row[1] for row in ranked]
    return {
        "ndcg_at_3": _ndcg(grades, 3),
        "ndcg_at_5": _ndcg(grades, 5),
        "precision_at_3": sum(grade >= 2 for grade in grades[:3]) / min(3, len(grades)),
        "pairwise_accuracy": _pairwise_accuracy(scored),
    }


def _deterministic_feature_score(features: Sequence[float]) -> float:
    values = dict(zip(FEATURE_ORDER, features, strict=True))
    weighted: list[tuple[float, float]] = [
        (0.22, values["lexical_relevance"]),
        (0.35, values["semantic_similarity"]),
    ]
    if not values["interest_missing"]:
        weighted.append((0.33, values["interest_overlap"]))
    if not values["career_missing"]:
        weighted.append((0.28, values["career_overlap"]))
    if not values["workload_missing"]:
        weighted.append((0.17, values["workload_match"]))
    return sum(weight * value for weight, value in weighted) / sum(
        weight for weight, _ in weighted
    )


def _ndcg(ranked_grades: Sequence[int], limit: int) -> float:
    def dcg(values: Sequence[int]) -> float:
        return sum(
            ((2**grade) - 1) / math.log2(index + 2)
            for index, grade in enumerate(values[:limit])
        )

    ideal = dcg(sorted(ranked_grades, reverse=True))
    return dcg(ranked_grades) / ideal if ideal else 0.0


def _pairwise_accuracy(scored: Sequence[tuple[float, int, str]]) -> float:
    correct = 0
    total = 0
    for left, right in itertools.combinations(scored, 2):
        if left[1] == right[1]:
            continue
        total += 1
        correct += (left[0] - right[0]) * (left[1] - right[1]) > 0
    return correct / total if total else 0.0


def _mean_metrics(rows: Sequence[Mapping[str, float]]) -> dict[str, float]:
    if not rows:
        raise ValueError("At least one metric row is required.")
    return {
        key: round(sum(row[key] for row in rows) / len(rows), 6)
        for key in rows[0]
    }


def _read_csv(path: Path | str, required: Sequence[str]) -> list[dict[str, str]]:
    with Path(path).open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        missing = set(required) - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"{Path(path).name} is missing columns: {', '.join(sorted(missing))}.")
        rows = list(reader)
    if not rows:
        raise ValueError(f"{Path(path).name} contains no records.")
    return rows


def _grade(value: str, key: tuple[str, str]) -> int:
    try:
        grade = int(value)
    except ValueError as error:
        raise ValueError(f"Judgement {key} contains a non-integer grade.") from error
    if grade not in {0, 1, 2, 3}:
        raise ValueError(f"Judgement {key} contains grade {grade}; expected 0-3.")
    return grade


def _split_tags(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(";") if part.strip())
