"""Tests for auditable curriculum-elective relevance scoring."""

from app.advisor.module_matching import score_module_relevance


def _module(name: str, scope: str) -> dict:
    return {
        "course_name": name,
        "course_information": {
            "scope": scope,
            "prescribed_materials": None,
            "additional_materials": None,
        },
    }


def _module_with_materials(name: str, scope: str, materials: str) -> dict:
    module = _module(name, scope)
    module["course_information"]["additional_materials"] = materials
    return module


def test_controlled_interest_matches_verified_cbo_scope() -> None:
    result = score_module_relevance(
        ["networking"],
        _module("Network Fundamentals", "Protocol layers routing and local networks."),
    )

    assert result["score"] == 1.0
    assert result["matched_tags"] == ["networking"]


def test_semantic_and_controlled_scores_are_reported_separately() -> None:
    result = score_module_relevance(
        ["renewable_energy"],
        _module("Renewable Energy", "Solar and wind generation."),
        semantic_score=0.8,
    )

    assert result["score"] == 0.89
    assert result["score_components"] == {
        "controlled_interest": 1.0,
        "semantic": 0.8,
    }


def test_incidental_material_reference_is_weaker_than_taught_scope() -> None:
    result = score_module_relevance(
        ["machine_learning"],
        _module_with_materials(
            "Control II",
            "Advanced control-system analysis and design.",
            "Bishop - Pattern Recognition and Machine Learning.",
        ),
    )

    assert result["score"] == 0.35
    assert result["matched_tags"] == ["machine_learning"]
