"""Deterministic relevance scoring for curriculum elective modules."""

from __future__ import annotations

import re
from typing import Any, Iterable

from app.advisor.normalisation import normalise_text


# Controlled criteria bridge user vocabulary to wording found in verified CBOs.
MODULE_MATCH_TERMS: dict[str, tuple[str, ...]] = {
    "artificial_intelligence": ("artificial intelligence", "machine learning"),
    "communications": ("antenna", "propagation", "communication", "high frequency"),
    "control": ("control", "feedback"),
    "control_engineering": ("control", "feedback"),
    "cybersecurity": ("security", "cryptography", "penetration testing", "threat"),
    "data_science": ("data science", "data systems", "data management", "mapreduce", "spark"),
    "distributed_computing": ("distributed", "parallel processing", "high performance computing"),
    "electrical_engineering": ("electrical", "power", "voltage", "antenna", "renewable energy"),
    "electrical_machines": ("electrical machine", "motor", "electromechanical"),
    "electronics_engineering": ("electronic", "instrumentation", "measurement", "circuit"),
    "high_frequency": ("high frequency", "antenna", "propagation", "electromagnetic"),
    "high_voltage": ("high voltage", "high electric field", "insulation", "dielectric"),
    "machine_learning": ("machine learning", "neural network", "classification", "regression"),
    "measurement_systems": ("measurement", "instrumentation", "calibration"),
    "ml_engineering": ("machine learning", "neural network", "classification", "regression"),
    "network_engineering": ("network", "routing", "protocol"),
    "networking": ("network", "routing", "protocol"),
    "power_systems": ("power system", "load flow", "hvdc", "fault analysis"),
    "quantum_computing": ("quantum computing", "quantum algorithm", "qiskit"),
    "renewable_energy": ("renewable energy", "solar", "wind", "sustainability"),
    "software": ("software", "javascript", "devops", "client server", "sql"),
    "software_development": ("software", "javascript", "devops", "client server", "sql"),
}

# Related terms receive partial credit; they are supporting rather than exact matches.
MODULE_RELATED_TERMS: dict[str, tuple[str, ...]] = {
    "data_science": ("machine learning", "distributed", "parallel processing"),
    "machine_learning": (
        "data systems",
        "data management",
        "distributed",
        "software development",
        "javascript",
        "devops",
    ),
    "ml_engineering": (
        "data systems",
        "data management",
        "distributed",
        "software development",
        "javascript",
        "devops",
    ),
    "renewable_energy": ("power system", "energy conversion"),
}


def score_module_relevance(
    requested_tags: Iterable[str],
    module: dict[str, Any],
    semantic_score: float | None = None,
) -> dict[str, Any]:
    """Score one module using published matching criteria and optional similarity."""

    tags = tuple(dict.fromkeys(requested_tags))
    information = module["course_information"]
    primary_text = normalise_text(
        " ".join(
            (
                module["course_name"],
                information.get("scope") or "",
            )
        )
    )
    supporting_text = normalise_text(
        " ".join(
            (
                information.get("prescribed_materials") or "",
                information.get("additional_materials") or "",
            )
        )
    )
    tag_strengths = {
        tag: _tag_match_strength(primary_text, supporting_text, tag)
        for tag in tags
    }
    matched_tags = tuple(tag for tag in tags if tag_strengths[tag] > 0)
    controlled_score = (
        sum(tag_strengths.values()) / len(tags) if tags else 0.0
    )

    components: list[tuple[float, float]] = [(0.45, controlled_score)]
    bounded_semantic: float | None = None
    if semantic_score is not None:
        bounded_semantic = max(0.0, min(1.0, semantic_score))
        components.append((0.55, bounded_semantic))
    score = sum(weight * value for weight, value in components) / sum(
        weight for weight, _ in components
    )

    return {
        "score": round(score, 4),
        "score_components": {
            "controlled_interest": round(controlled_score, 4),
            "semantic": round(bounded_semantic, 4) if bounded_semantic is not None else None,
        },
        "matched_tags": list(matched_tags),
    }


def _terms_for(tag: str) -> tuple[str, ...]:
    canonical_phrase = tag.replace("_", " ")
    return tuple(dict.fromkeys((canonical_phrase, *MODULE_MATCH_TERMS.get(tag, ()))))


def _tag_match_strength(primary_text: str, supporting_text: str, tag: str) -> float:
    if any(_contains_phrase(primary_text, term) for term in _terms_for(tag)):
        return 1.0
    if any(
        _contains_phrase(primary_text, term)
        for term in MODULE_RELATED_TERMS.get(tag, ())
    ):
        return 0.6
    # A book title or supporting tool is useful evidence but should never outrank
    # a module whose title or taught scope directly addresses the requested topic.
    if any(_contains_phrase(supporting_text, term) for term in _terms_for(tag)):
        return 0.35
    if any(
        _contains_phrase(supporting_text, term)
        for term in MODULE_RELATED_TERMS.get(tag, ())
    ):
        return 0.2
    return 0.0


def _contains_phrase(text: str, phrase: str) -> bool:
    normalized_phrase = normalise_text(phrase)
    return bool(
        normalized_phrase
        and re.search(
            rf"(?<![a-z0-9]){re.escape(normalized_phrase)}(?![a-z0-9])",
            text,
        )
    )
