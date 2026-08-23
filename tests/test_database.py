"""Tests for curriculum dataset validation."""

from __future__ import annotations

import shutil
from pathlib import Path

from app.data.validators import validate_processed_data


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DATA = PROJECT_ROOT / "data" / "processed"


def test_initial_curriculum_data_has_no_errors() -> None:
    report = validate_processed_data(PROCESSED_DATA)

    assert report.is_valid
    assert any(
        issue.code == "EXTERNAL_COURSE_REFERENCE" for issue in report.warnings
    )


def test_duplicate_module_membership_is_an_error(tmp_path: Path) -> None:
    data_directory = tmp_path / "processed"
    shutil.copytree(PROCESSED_DATA, data_directory)
    modules_path = data_directory / "modules.csv"
    modules_path.write_text(
        modules_path.read_text(encoding="utf-8")
        + modules_path.read_text(encoding="utf-8").splitlines()[1]
        + "\n",
        encoding="utf-8",
    )

    report = validate_processed_data(data_directory)

    assert any(
        issue.code == "DUPLICATE_MODULE_MEMBERSHIP" for issue in report.errors
    )
