"""Transparent weak labels for exercising the ranking pipeline during prototyping."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from app.advisor.normalisation import normalise_text
from app.advisor.ranker_training import Judgement, TrainingProfile


PROTOTYPE_LABEL_SOURCE = "prototype_criteria_v1_codex_assisted"
PROTOTYPE_FIELDS = (
    "profile_id",
    "course_id",
    "final_grade",
    "label_source",
    "rationale",
)

RELATED_TAGS: dict[str, frozenset[str]] = {
    "artificial_intelligence": frozenset({"machine_learning", "data_science", "software"}),
    "machine_learning": frozenset({"artificial_intelligence", "data_science", "software"}),
    "data_science": frozenset({"machine_learning", "artificial_intelligence", "software"}),
    "software": frozenset({"data_science", "machine_learning", "artificial_intelligence", "distributed_computing"}),
    "communications": frozenset({"networking", "high_frequency"}),
    "networking": frozenset({"communications", "cybersecurity", "distributed_computing"}),
    "cybersecurity": frozenset({"networking", "software"}),
    "control": frozenset({"electric_circuits", "embedded_systems", "measurement_systems", "electrical_machines", "power_systems"}),
    "electric_circuits": frozenset({"control", "embedded_systems", "measurement_systems", "electrical_machines", "power_systems"}),
    "embedded_systems": frozenset({"control", "electric_circuits", "measurement_systems", "software"}),
    "measurement_systems": frozenset({"control", "electric_circuits", "embedded_systems"}),
    "electrical_machines": frozenset({"control", "electric_circuits", "power_systems", "renewable_energy"}),
    "power_systems": frozenset({"electrical_machines", "high_voltage", "renewable_energy", "electric_circuits"}),
    "high_voltage": frozenset({"power_systems", "electrical_machines"}),
    "renewable_energy": frozenset({"power_systems", "electrical_machines"}),
    "high_frequency": frozenset({"communications", "networking", "electric_circuits"}),
    "distributed_computing": frozenset({"software", "networking", "data_science"}),
    "quantum_computing": frozenset({"artificial_intelligence", "software"}),
}

RELATED_CAREERS: dict[str, frozenset[str]] = {
    "data_science": frozenset({"ml_engineering", "software_development"}),
    "ml_engineering": frozenset({"data_science", "software_development"}),
    "software_development": frozenset({"data_science", "ml_engineering"}),
    "network_engineering": frozenset({"cybersecurity", "electronics_engineering"}),
    "cybersecurity": frozenset({"network_engineering", "software_development"}),
    "electrical_engineering": frozenset({"electronics_engineering", "control_engineering"}),
    "electronics_engineering": frozenset({"electrical_engineering", "control_engineering"}),
    "control_engineering": frozenset({"electrical_engineering", "electronics_engineering"}),
}

STOP_WORDS = frozenset(
    {
        "a", "an", "and", "for", "i", "in", "introduction", "me", "my",
        "of", "recommend", "study", "the", "to", "want", "with",
    }
)


@dataclass(frozen=True)
class PrototypeLabel:
    """One synthetic relevance label with explicit provenance and explanation."""

    profile_id: str
    course_id: str
    final_grade: int
    label_source: str
    rationale: str


def generate_prototype_labels(
    profiles: Sequence[TrainingProfile],
    courses: Sequence[Mapping[str, Any]],
) -> tuple[PrototypeLabel, ...]:
    """Generate complete weak labels without altering independent judge files."""

    return tuple(
        prototype_label(profile, course)
        for profile in profiles
        for course in courses
    )


def prototype_label(
    profile: TrainingProfile,
    course: Mapping[str, Any],
) -> PrototypeLabel:
    """Assign a 0-3 grade using the frozen criteria-v1 controlled-tag rubric."""

    requested_interests = set(profile.interests)
    requested_careers = set(profile.career_preferences)
    course_interests = set(course["interest_tags"])
    course_careers = set(course["career_tags"])

    direct_interests = requested_interests & course_interests
    direct_careers = requested_careers & course_careers
    related_interests = _related_matches(
        requested_interests - direct_interests,
        course_interests,
        RELATED_TAGS,
    )
    related_careers = _related_matches(
        requested_careers - direct_careers,
        course_careers,
        RELATED_CAREERS,
    )
    interest_signal = _signal(
        requested_interests,
        direct_interests,
        related_interests,
    )
    career_signal = _signal(requested_careers, direct_careers, related_careers)
    lexical_signal = _lexical_signal(profile.query, course)

    if requested_interests and requested_careers:
        score = 0.60 * interest_signal + 0.32 * career_signal + 0.08 * lexical_signal
    elif requested_interests:
        score = 0.90 * interest_signal + 0.10 * lexical_signal
    elif requested_careers:
        score = 0.90 * career_signal + 0.10 * lexical_signal
    else:
        score = lexical_signal

    if score >= 0.78:
        grade = 3
    elif score >= 0.45:
        grade = 2
    elif score >= 0.18:
        grade = 1
    else:
        grade = 0

    rationale_parts = [f"criteria_score={score:.3f}"]
    if direct_interests:
        rationale_parts.append("direct interests: " + ", ".join(sorted(direct_interests)))
    if related_interests:
        rationale_parts.append("related interests: " + ", ".join(sorted(related_interests)))
    if direct_careers:
        rationale_parts.append("direct careers: " + ", ".join(sorted(direct_careers)))
    if related_careers:
        rationale_parts.append("related careers: " + ", ".join(sorted(related_careers)))
    if len(rationale_parts) == 1:
        rationale_parts.append("no material controlled-vocabulary match")
    return PrototypeLabel(
        profile_id=profile.profile_id,
        course_id=str(course["course_id"]),
        final_grade=grade,
        label_source=PROTOTYPE_LABEL_SOURCE,
        rationale="; ".join(rationale_parts),
    )


def write_prototype_labels(path: Path | str, labels: Sequence[PrototypeLabel]) -> None:
    """Write prototype labels atomically using their intentionally distinct schema."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as label_file:
        writer = csv.DictWriter(label_file, fieldnames=PROTOTYPE_FIELDS)
        writer.writeheader()
        for label in labels:
            writer.writerow(label.__dict__)
    temporary.replace(destination)


def load_prototype_judgements(path: Path | str) -> tuple[Judgement, ...]:
    """Load weak labels into training examples while retaining prototype provenance."""

    with Path(path).open(newline="", encoding="utf-8") as label_file:
        reader = csv.DictReader(label_file)
        if tuple(reader.fieldnames or ()) != PROTOTYPE_FIELDS:
            raise ValueError("Prototype labels have invalid columns.")
        rows = list(reader)

    judgements: list[Judgement] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        key = (row["profile_id"].strip(), row["course_id"].strip())
        if not all(key) or key in seen:
            raise ValueError(f"Duplicate or empty prototype label key {key!r}.")
        source = row["label_source"].strip()
        if not source.startswith("prototype_"):
            raise ValueError(f"Prototype label {key!r} has invalid provenance.")
        try:
            grade = int(row["final_grade"])
        except ValueError as error:
            raise ValueError(f"Prototype label {key!r} has a non-integer grade.") from error
        if grade not in {0, 1, 2, 3}:
            raise ValueError(f"Prototype label {key!r} has invalid grade {grade}.")
        rationale = row["rationale"].strip()
        if not rationale:
            raise ValueError(f"Prototype label {key!r} requires a rationale.")
        seen.add(key)
        judgements.append(
            Judgement(
                profile_id=key[0],
                course_id=key[1],
                judge_1_id=source,
                judge_1_grade=grade,
                judge_2_id="not_applicable_prototype",
                judge_2_grade=grade,
                final_grade=grade,
                adjudication_notes=rationale,
            )
        )
    return tuple(judgements)


def _related_matches(
    requested: set[str],
    available: set[str],
    relationships: Mapping[str, frozenset[str]],
) -> set[str]:
    return {
        requested_tag
        for requested_tag in requested
        if relationships.get(requested_tag, frozenset()) & available
    }


def _signal(requested: set[str], direct: set[str], related: set[str]) -> float:
    if not requested:
        return 0.0
    return (len(direct) + 0.45 * len(related)) / len(requested)


def _lexical_signal(query: str, course: Mapping[str, Any]) -> float:
    query_tokens = set(normalise_text(query).split()) - STOP_WORDS
    course_text = " ".join(
        (
            str(course["title"]),
            str(course["description"]),
            *course["outcomes"],
            *course["topic_tags"],
        )
    ).replace("_", " ")
    course_tokens = set(normalise_text(course_text).split()) - STOP_WORDS
    return len(query_tokens & course_tokens) / len(query_tokens) if query_tokens else 0.0
