"""Bounded deterministic repairs for reviewer-identified presentation defects."""

from __future__ import annotations

from typing import Any


SUPPORTED_REPAIRS = frozenset(
    {
        "MISSING_SOURCE_QUALIFIER",
        "MISSING_REQUIREMENT_EXPLANATION",
    }
)


def repair_response(
    result: dict[str, Any], reason_codes: list[str]
) -> dict[str, Any] | None:
    """Apply one safe repair without changing structured decision fields."""

    applicable = set(reason_codes).intersection(SUPPORTED_REPAIRS)
    if not applicable:
        return None

    repaired = dict(result)
    answer = str(result.get("answer", "")).rstrip()
    additions: list[str] = []

    if "MISSING_REQUIREMENT_EXPLANATION" in applicable:
        requirements = result.get("requirements", {})
        for label, key in (
            ("Prerequisites", "prerequisites"),
            ("Corequisites", "corequisites"),
        ):
            entries = requirements.get(key, []) if isinstance(requirements, dict) else []
            if entries and label.lower() not in answer.lower():
                descriptions = "; ".join(
                    str(entry.get("description", "recorded requirement"))
                    for entry in entries
                )
                additions.append(f"{label}: {descriptions}.")

    if "MISSING_SOURCE_QUALIFIER" in applicable and "source" not in answer.lower():
        additions.append("This answer is based on the verified CurricuPath catalogue.")

    if not additions:
        return None
    repaired["answer"] = " ".join([answer, *additions])
    return repaired
