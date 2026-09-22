"""Tests for blinded ranking-label collection and adjudication."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from app.advisor.ranking_labels import RankingLabelStore


PROFILE_FIELDS = (
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


def _store(tmp_path: Path, status: str = "approved") -> RankingLabelStore:
    path = tmp_path / "profiles.csv"
    with path.open("w", newline="", encoding="utf-8") as profile_file:
        writer = csv.DictWriter(profile_file, fieldnames=PROFILE_FIELDS)
        writer.writeheader()
        writer.writerow(
            {
                "profile_id": "P1",
                "profile_group_id": "G1",
                "split": "train",
                "query": "circuits",
                "interests": "electric_circuits",
                "career_preferences": "electrical_engineering",
                "workload_preference": "moderate",
                "profile_author": "author",
                "review_status": status,
            }
        )
    return RankingLabelStore(tmp_path, ("C1", "C2"))


def test_draft_profiles_block_judging_until_approved(tmp_path: Path) -> None:
    store = _store(tmp_path, "draft")

    with pytest.raises(ValueError, match="not approved"):
        store.save_grade(1, "Judge A", "P1", "C1", 2)

    store.approve_profiles("Profile Reviewer")
    store.save_grade(1, "Judge A", "P1", "C1", 2)

    assert store.judge_state(1, "Judge A")["completed"] == 1


def test_judge_slots_are_blinded_and_cannot_change_owner(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.save_grade(1, "Judge A", "P1", "C1", 3)

    with pytest.raises(ValueError, match="belongs to another judge"):
        store.judge_state(1, "Judge B")

    assert store.judge_state(2, "Judge B")["grades"] == {}

    with pytest.raises(ValueError, match="same person"):
        store.save_grade(2, "Judge A", "P1", "C1", 2)


def test_both_complete_judges_can_prepare_and_adjudicate(tmp_path: Path) -> None:
    store = _store(tmp_path)
    for course_id, first, second in (("C1", 3, 1), ("C2", 2, 2)):
        store.save_grade(1, "Judge A", "P1", course_id, first)
        store.save_grade(2, "Judge B", "P1", course_id, second)

    state = store.prepare_adjudication()
    disagreements = store.disagreements()

    assert state["unresolved_adjudications"] == 1
    assert len(disagreements) == 1
    with pytest.raises(ValueError, match="require adjudication notes"):
        store.save_adjudication("P1", "C1", 2, "")

    store.save_adjudication("P1", "C1", 2, "Balanced the two interpretations.")

    assert store.readiness()["training_ready"] is True


def test_adjudication_cannot_exceed_judges_range(tmp_path: Path) -> None:
    store = _store(tmp_path)
    for course_id in ("C1", "C2"):
        store.save_grade(1, "Judge A", "P1", course_id, 1)
        store.save_grade(2, "Judge B", "P1", course_id, 2)
    store.prepare_adjudication()

    with pytest.raises(ValueError, match="within the two judges"):
        store.save_adjudication("P1", "C1", 3, "Too high")
