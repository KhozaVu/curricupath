from pathlib import Path

import pytest

from app.advisor.prototype_labels import (
    PROTOTYPE_LABEL_SOURCE,
    generate_prototype_labels,
    load_prototype_judgements,
    write_prototype_labels,
)
from app.advisor.ranker_training import TrainingProfile


def _profile(*, interests=("machine_learning",), careers=("data_science",)):
    return TrainingProfile(
        profile_id="P1",
        profile_group_id="G1",
        split="train",
        query="I want machine learning for data science",
        interests=interests,
        career_preferences=careers,
        workload_preference="moderate",
        profile_author="reviewer",
        review_status="approved",
    )


def _course(course_id: str, interests, careers):
    return {
        "course_id": course_id,
        "title": "Course title",
        "description": "Course description",
        "outcomes": [],
        "topic_tags": [],
        "interest_tags": list(interests),
        "career_tags": list(careers),
    }


def test_prototype_labels_cover_every_profile_course_pair() -> None:
    courses = (
        _course("C1", ("machine_learning",), ("data_science",)),
        _course("C2", ("electric_circuits",), ("electrical_engineering",)),
    )

    labels = generate_prototype_labels((_profile(),), courses)

    assert len(labels) == 2
    assert labels[0].final_grade == 3
    assert labels[1].final_grade == 0
    assert all(label.label_source == PROTOTYPE_LABEL_SOURCE for label in labels)
    assert all(label.rationale for label in labels)


def test_prototype_labels_round_trip_as_training_judgements(tmp_path: Path) -> None:
    labels = generate_prototype_labels(
        (_profile(),),
        (_course("C1", ("machine_learning",), ("data_science",)),),
    )
    path = tmp_path / "prototype.csv"
    write_prototype_labels(path, labels)

    loaded = load_prototype_judgements(path)

    assert loaded[0].final_grade == 3
    assert loaded[0].judge_1_id == PROTOTYPE_LABEL_SOURCE
    assert loaded[0].adjudication_notes.startswith("criteria_score=")


def test_prototype_loader_rejects_unmarked_provenance(tmp_path: Path) -> None:
    path = tmp_path / "prototype.csv"
    path.write_text(
        "profile_id,course_id,final_grade,label_source,rationale\n"
        "P1,C1,2,human,reason\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="invalid provenance"):
        load_prototype_judgements(path)
