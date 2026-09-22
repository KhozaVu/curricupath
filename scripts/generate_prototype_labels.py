"""Generate clearly marked weak labels for prototype ranker development."""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.advisor.prototype_labels import generate_prototype_labels, write_prototype_labels
from app.advisor.ranker_training import load_profiles
from app.data.repository import CsvCatalogueRepository


DEFAULT_DIRECTORY = PROJECT_ROOT / "experiments" / "ranking"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profiles", type=Path, default=DEFAULT_DIRECTORY / "profiles.csv")
    parser.add_argument("--output", type=Path, default=DEFAULT_DIRECTORY / "prototype_judgements.csv")
    parser.add_argument("--human-labels", type=Path, default=DEFAULT_DIRECTORY / "judge_1.csv")
    args = parser.parse_args()

    profiles = load_profiles(args.profiles)
    courses = CsvCatalogueRepository(PROJECT_ROOT / "data" / "processed").list_courses(limit=100)
    labels = generate_prototype_labels(profiles, courses)
    write_prototype_labels(args.output, labels)

    distribution = Counter(label.final_grade for label in labels)
    print(f"Prototype labels: {len(labels)}")
    print("Distribution: " + ", ".join(f"grade {grade}={distribution[grade]}" for grade in range(4)))
    print(f"Output: {args.output}")
    _report_human_comparison(args.human_labels, labels)
    print("WARNING: These are weak prototype labels, not independent human judgements.")


def _report_human_comparison(path: Path, labels) -> None:
    if not path.exists():
        return
    with path.open(newline="", encoding="utf-8") as human_file:
        human = {
            (row["profile_id"], row["course_id"]): int(row["grade"])
            for row in csv.DictReader(human_file)
        }
    generated = {(label.profile_id, label.course_id): label.final_grade for label in labels}
    overlap = sorted(human.keys() & generated.keys())
    if not overlap:
        return
    exact = sum(human[key] == generated[key] for key in overlap) / len(overlap)
    within_one = sum(abs(human[key] - generated[key]) <= 1 for key in overlap) / len(overlap)
    mean_error = sum(abs(human[key] - generated[key]) for key in overlap) / len(overlap)
    print(f"Human comparison: n={len(overlap)}, exact={exact:.1%}, within_one={within_one:.1%}, MAE={mean_error:.3f}")


if __name__ == "__main__":
    main()
