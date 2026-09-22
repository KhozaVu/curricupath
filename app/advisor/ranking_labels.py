"""Blinded local collection and adjudication of public-course relevance labels."""

from __future__ import annotations

import csv
from pathlib import Path
from threading import Lock
from typing import Any, Mapping, Sequence

from app.advisor.ranker_training import load_profiles


JUDGE_FIELDS = ("profile_id", "course_id", "judge_id", "grade")
COMBINED_FIELDS = (
    "profile_id",
    "course_id",
    "judge_1_id",
    "judge_1_grade",
    "judge_2_id",
    "judge_2_grade",
    "final_grade",
    "adjudication_notes",
)


class RankingLabelStore:
    """Write separate judge files and reveal grades only after both are complete."""

    def __init__(
        self,
        experiment_directory: Path | str,
        course_ids: Sequence[str],
    ) -> None:
        self.directory = Path(experiment_directory)
        self.profile_path = self.directory / "profiles.csv"
        self.judgement_path = self.directory / "judgements.csv"
        self.course_ids = tuple(course_ids)
        self._lock = Lock()

    def profiles(self, *, require_approved: bool = False):
        return load_profiles(self.profile_path, require_approved=require_approved)

    def approve_profiles(self, reviewer: str) -> None:
        reviewer = reviewer.strip()
        if not reviewer:
            raise ValueError("A profile reviewer name is required.")
        with self._lock:
            rows, fields = _read_rows(self.profile_path)
            for row in rows:
                author = row["profile_author"].strip()
                review_marker = f"reviewed_by:{reviewer}"
                row["profile_author"] = (
                    f"{author};{review_marker}" if author else review_marker
                )
                row["review_status"] = "approved"
            _write_rows(self.profile_path, fields, rows)

    def save_grade(
        self,
        slot: int,
        judge_id: str,
        profile_id: str,
        course_id: str,
        grade: int,
    ) -> None:
        self.profiles(require_approved=True)
        judge_id = judge_id.strip()
        if slot not in {1, 2}:
            raise ValueError("Judge slot must be 1 or 2.")
        if not judge_id:
            raise ValueError("A judge identifier is required.")
        if grade not in {0, 1, 2, 3}:
            raise ValueError("A relevance grade must be from 0 to 3.")
        expected = self._expected_keys()
        key = (profile_id, course_id)
        if key not in expected:
            raise ValueError(f"Unknown profile-course pair {key!r}.")
        path = self._judge_path(slot)
        with self._lock:
            records = self._judge_records(slot)
            other_records = self._judge_records(2 if slot == 1 else 1)
            other_ids = {row["judge_id"] for row in other_records.values()}
            if judge_id in other_ids:
                raise ValueError("The same person cannot occupy both judge slots.")
            existing_ids = {row["judge_id"] for row in records.values()}
            if existing_ids and existing_ids != {judge_id}:
                raise ValueError(
                    f"Judge slot {slot} is already assigned to "
                    f"{next(iter(existing_ids))!r}."
                )
            records[key] = {
                "profile_id": profile_id,
                "course_id": course_id,
                "judge_id": judge_id,
                "grade": str(grade),
            }
            _write_rows(path, JUDGE_FIELDS, [records[item] for item in sorted(records)])

    def judge_state(self, slot: int, judge_id: str) -> dict[str, Any]:
        if slot not in {1, 2}:
            raise ValueError("Judge slot must be 1 or 2.")
        records = self._judge_records(slot)
        existing_ids = {row["judge_id"] for row in records.values()}
        if existing_ids and existing_ids != {judge_id.strip()}:
            raise ValueError(f"Judge slot {slot} belongs to another judge.")
        expected_count = len(self._expected_keys())
        return {
            "slot": slot,
            "judge_id": judge_id.strip(),
            "grades": {
                f"{profile_id}|{course_id}": int(row["grade"])
                for (profile_id, course_id), row in records.items()
            },
            "completed": len(records),
            "total": expected_count,
            "is_complete": len(records) == expected_count,
        }

    def prepare_adjudication(self) -> dict[str, Any]:
        """Merge complete blinded files while preserving prior adjudications."""

        expected = self._expected_keys()
        with self._lock:
            first = self._judge_records(1)
            second = self._judge_records(2)
            if set(first) != expected or set(second) != expected:
                raise ValueError("Both judges must grade every profile-course pair first.")
            previous = self._combined_records()
            rows: list[dict[str, str]] = []
            for key in sorted(expected):
                first_row = first[key]
                second_row = second[key]
                first_grade = int(first_row["grade"])
                second_grade = int(second_row["grade"])
                old = previous.get(key, {})
                if first_grade == second_grade:
                    final_grade = str(first_grade)
                    notes = "Judges agreed."
                else:
                    final_grade = old.get("final_grade", "")
                    notes = old.get("adjudication_notes", "")
                rows.append(
                    {
                        "profile_id": key[0],
                        "course_id": key[1],
                        "judge_1_id": first_row["judge_id"],
                        "judge_1_grade": str(first_grade),
                        "judge_2_id": second_row["judge_id"],
                        "judge_2_grade": str(second_grade),
                        "final_grade": final_grade,
                        "adjudication_notes": notes,
                    }
                )
            _write_rows(self.judgement_path, COMBINED_FIELDS, rows)
        return self.readiness()

    def disagreements(self) -> list[dict[str, Any]]:
        records = self._combined_records()
        if not records:
            raise ValueError("Prepare adjudication after both judges finish.")
        return [
            {
                **row,
                "judge_1_grade": int(row["judge_1_grade"]),
                "judge_2_grade": int(row["judge_2_grade"]),
                "final_grade": int(row["final_grade"]) if row["final_grade"] else None,
            }
            for row in records.values()
            if row["judge_1_grade"] != row["judge_2_grade"]
        ]

    def save_adjudication(
        self,
        profile_id: str,
        course_id: str,
        final_grade: int,
        notes: str,
    ) -> None:
        if final_grade not in {0, 1, 2, 3}:
            raise ValueError("A final relevance grade must be from 0 to 3.")
        key = (profile_id, course_id)
        with self._lock:
            records = self._combined_records()
            if key not in records:
                raise ValueError(f"Unknown adjudication pair {key!r}.")
            row = records[key]
            lower = min(int(row["judge_1_grade"]), int(row["judge_2_grade"]))
            upper = max(int(row["judge_1_grade"]), int(row["judge_2_grade"]))
            if not lower <= final_grade <= upper:
                raise ValueError("Final grade must be within the two judges' grades.")
            if upper - lower >= 2 and not notes.strip():
                raise ValueError("Material disagreements require adjudication notes.")
            row["final_grade"] = str(final_grade)
            row["adjudication_notes"] = notes.strip() or "Adjudicated."
            _write_rows(
                self.judgement_path,
                COMBINED_FIELDS,
                [records[item] for item in sorted(records)],
            )

    def readiness(self) -> dict[str, Any]:
        profiles = self.profiles(require_approved=False)
        expected_count = len(profiles) * len(self.course_ids)
        first = self._judge_records(1)
        second = self._judge_records(2)
        combined = self._combined_records()
        unresolved = sum(
            not row.get("final_grade", "").strip() for row in combined.values()
        )
        approved = all(profile.review_status == "approved" for profile in profiles)
        ready = bool(
            approved
            and len(first) == expected_count
            and len(second) == expected_count
            and len(combined) == expected_count
            and unresolved == 0
        )
        return {
            "profiles": len(profiles),
            "courses": len(self.course_ids),
            "expected_judgements_per_judge": expected_count,
            "profiles_approved": approved,
            "judge_1_completed": len(first),
            "judge_2_completed": len(second),
            "combined_judgements": len(combined),
            "adjudication_prepared": len(combined) == expected_count,
            "unresolved_adjudications": unresolved,
            "training_ready": ready,
        }

    def _expected_keys(self) -> set[tuple[str, str]]:
        profiles = self.profiles(require_approved=False)
        return {
            (profile.profile_id, course_id)
            for profile in profiles
            for course_id in self.course_ids
        }

    def _judge_path(self, slot: int) -> Path:
        return self.directory / f"judge_{slot}.csv"

    def _judge_records(self, slot: int) -> dict[tuple[str, str], dict[str, str]]:
        path = self._judge_path(slot)
        if not path.exists():
            return {}
        rows, fields = _read_rows(path)
        if tuple(fields) != JUDGE_FIELDS:
            raise ValueError(f"{path.name} has invalid columns.")
        return _indexed_rows(rows, path.name)

    def _combined_records(self) -> dict[tuple[str, str], dict[str, str]]:
        if not self.judgement_path.exists():
            return {}
        rows, fields = _read_rows(self.judgement_path)
        if tuple(fields) != COMBINED_FIELDS:
            raise ValueError("judgements.csv has invalid columns.")
        return _indexed_rows(rows, self.judgement_path.name)


def _indexed_rows(
    rows: Sequence[dict[str, str]], filename: str
) -> dict[tuple[str, str], dict[str, str]]:
    indexed: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        key = (row["profile_id"], row["course_id"])
        if key in indexed:
            raise ValueError(f"{filename} contains duplicate pair {key!r}.")
        indexed[key] = row
    return indexed


def _read_rows(path: Path) -> tuple[list[dict[str, str]], tuple[str, ...]]:
    with path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        return list(reader), tuple(reader.fieldnames or ())


def _write_rows(
    path: Path,
    fields: Sequence[str],
    rows: Sequence[Mapping[str, Any]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)
