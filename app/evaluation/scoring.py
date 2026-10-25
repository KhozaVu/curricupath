"""Score frozen v2.5 evaluation outputs against reference labels.

Metric definitions follow docs/revised_evaluation_plan_2026-09-18.md section 7.4.
A run with no valid three-class decision is scored as an error and stays in every
denominator; it is never dropped.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


LABELS = ("eligible", "ineligible", "manual_review_required")
INVALID = "invalid"
OUTCOMES = LABELS + (INVALID,)
_CODES = {name: index for index, name in enumerate(OUTCOMES)}
STRATA = ("author_source", "scenario_type", "clarification_permitted", "reference_label")
DEFAULT_BOOTSTRAP = 10_000
DEFAULT_SEED = 20260918


@dataclass(frozen=True)
class Observation:
    """One case/arm/run record read from an immutable raw output file."""

    case_id: str
    arm: str
    run_number: int
    decision: str
    latency_ms: int | None
    status: str
    error: str | None
    provider_failure: bool = False


PROVIDER_FAILURE_MARKERS = ("429", "503", "resource_exhausted", "unavailable", "high demand")


def is_provider_failure(record: Mapping[str, Any]) -> bool:
    """True when a run failed because the hosted service refused it, not because the model erred."""

    if record.get("status") == "valid":
        return False
    error = str(record.get("error") or "").lower()
    return any(marker in error for marker in PROVIDER_FAILURE_MARKERS)


def decision_from_record(record: Mapping[str, Any]) -> str:
    """Return a valid three-class label, or INVALID for anything else."""

    if record.get("status") != "valid":
        return INVALID
    parsed = record.get("parsed_output")
    decision = parsed.get("decision") if isinstance(parsed, Mapping) else None
    return decision if decision in LABELS else INVALID


def read_observations(path: Path) -> list[Observation]:
    observations: list[Observation] = []
    seen: set[tuple[str, int]] = set()
    with path.open(encoding="utf-8") as raw_file:
        for line_number, line in enumerate(raw_file, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            key = (str(record["case_id"]), int(record["run_number"]))
            if key in seen:
                raise ValueError(f"{path.name}:{line_number} repeats case/run {key}.")
            seen.add(key)
            latency = record.get("latency_ms")
            observations.append(
                Observation(
                    case_id=key[0],
                    arm=str(record["arm"]),
                    run_number=key[1],
                    decision=decision_from_record(record),
                    latency_ms=int(latency) if latency is not None else None,
                    status=str(record.get("status", "")),
                    error=record.get("error"),
                    provider_failure=is_provider_failure(record),
                )
            )
    return observations


def load_reference_cases(path: Path, *, draft: bool) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Load scored cases and describe where their reference labels came from."""

    with path.open(newline="", encoding="utf-8") as csv_file:
        rows = list(csv.DictReader(csv_file))
    if draft:
        cases = [{**row, "reference_label": row["developer_expected_label"]} for row in rows]
        for row in cases:
            if row["reference_label"] not in LABELS:
                raise ValueError(f"{row['case_id']} has no developer_expected_label.")
        return cases, {
            "mode": "draft",
            "reference_source": "developer_expected_label (NOT independent evidence)",
            "rejected_cases": [],
        }

    cases, rejected, problems = [], [], []
    for row in rows:
        state = row["approval_state"]
        if state == "rejected_with_reason":
            rejected.append(row["case_id"])
        elif state != "approved" or row["reference_label"] not in LABELS:
            problems.append(row["case_id"])
        elif not row["reviewer_ids"].strip():
            problems.append(row["case_id"])
        else:
            cases.append(row)
    if problems:
        raise ValueError(
            f"{len(problems)} cases lack an approved label and reviewer "
            f"(first: {', '.join(problems[:5])})."
        )
    return cases, {
        "mode": "official",
        "reference_source": "reference_label (approved, reviewer-attributed)",
        "rejected_cases": rejected,
    }


def load_label_set(path: Path, column: str) -> dict[str, str]:
    """Read an alternate developer-side label set keyed by case_id."""

    with path.open(newline="", encoding="utf-8") as csv_file:
        labels = {row["case_id"]: row[column] for row in csv.DictReader(csv_file)}
    invalid = sorted(case for case, label in labels.items() if label not in LABELS)
    if invalid:
        raise ValueError(f"{path.name} has invalid labels for: {', '.join(invalid[:5])}.")
    return labels


def apply_label_set(
    cases: Sequence[Mapping[str, str]],
    labels: Mapping[str, str],
    *,
    name: str,
    description: str,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Return the cases relabelled with an alternate set, plus its provenance."""

    missing = [case["case_id"] for case in cases if case["case_id"] not in labels]
    if missing:
        raise ValueError(f"Label set {name} lacks {len(missing)} cases (first: {missing[0]}).")
    relabelled = [{**case, "reference_label": labels[case["case_id"]]} for case in cases]
    return relabelled, {"mode": "draft", "label_set": name, "reference_source": description,
                        "rejected_cases": []}


def label_set_agreement(first: Sequence[str], second: Sequence[str]) -> dict[str, Any]:
    """Raw agreement, Cohen's kappa and the cross-tabulation of two label sets."""

    a, b = encode(first), encode(second)
    counts = np.bincount(a * 3 + b, minlength=9).reshape(3, 3)
    total = counts.sum()
    observed = np.trace(counts) / total
    expected = float((counts.sum(axis=1) / total) @ (counts.sum(axis=0) / total))
    return {
        "n_cases": int(total),
        "raw_agreement": float(observed),
        "cohens_kappa": None if expected == 1 else float((observed - expected) / (1 - expected)),
        "rows_first_set": list(LABELS),
        "columns_second_set": list(LABELS),
        "counts": counts.tolist(),
    }


def encode(labels: Sequence[str]) -> np.ndarray:
    return np.array([_CODES[label] for label in labels], dtype=np.int64)


def primary_decisions(
    observations: Sequence[Observation], case_ids: Sequence[str], run_number: int
) -> tuple[list[str], list[str]]:
    """Decisions for one run in case order; absent cases count as INVALID."""

    by_case = {o.case_id: o.decision for o in observations if o.run_number == run_number}
    missing = [case_id for case_id in case_ids if case_id not in by_case]
    return [by_case.get(case_id, INVALID) for case_id in case_ids], missing


def confusion_from_codes(reference: np.ndarray, predicted: np.ndarray) -> np.ndarray:
    """3x4 matrix: rows are reference labels; columns are labels plus INVALID."""

    return np.bincount(reference * 4 + predicted, minlength=12).reshape(3, 4)


def class_statistics(matrix: np.ndarray) -> dict[str, np.ndarray]:
    true_positive = np.diag(matrix[:, :3]).astype(float)
    support = matrix.sum(axis=1).astype(float)
    predicted = matrix[:, :3].sum(axis=0).astype(float)
    precision = np.divide(true_positive, predicted, out=np.zeros(3), where=predicted > 0)
    recall = np.divide(true_positive, support, out=np.zeros(3), where=support > 0)
    total = precision + recall
    f1 = np.divide(2 * precision * recall, total, out=np.zeros(3), where=total > 0)
    return {"precision": precision, "recall": recall, "f1": f1, "support": support}


def macro_f1(matrix: np.ndarray) -> float:
    return float(class_statistics(matrix)["f1"].mean())


def balanced_accuracy(matrix: np.ndarray) -> float:
    stats = class_statistics(matrix)
    present = stats["support"] > 0
    return float(stats["recall"][present].mean()) if present.any() else 0.0


def accuracy(matrix: np.ndarray) -> float:
    total = matrix.sum()
    return float(np.diag(matrix[:, :3]).sum() / total) if total else 0.0


def _rate(numerator: int, denominator: int) -> dict[str, Any]:
    return {
        "numerator": int(numerator),
        "denominator": int(denominator),
        "rate": float(numerator / denominator) if denominator else None,
    }


def safety_rates(matrix: np.ndarray) -> dict[str, dict[str, Any]]:
    """Error-type rates. Rows: eligible=0, ineligible=1, manual_review_required=2."""

    m = matrix
    return {
        "unsafe_false_positive_rate": _rate(m[1, 0] + m[2, 0], m[1].sum() + m[2].sum()),
        "overly_conservative_false_negative_rate": _rate(m[0, 1] + m[0, 2], m[0].sum()),
        "correct_escalation_rate": _rate(m[2, 2], m[2].sum()),
        "unsafe_overconfidence_rate_on_manual_review": _rate(m[2, 0] + m[2, 1], m[2].sum()),
        "unnecessary_escalation_rate": _rate(m[0, 2] + m[1, 2], m[0].sum() + m[1].sum()),
        "invalid_output_rate": _rate(m[:, 3].sum(), m.sum()),
    }


def arm_metrics(reference: np.ndarray, predicted: np.ndarray) -> dict[str, Any]:
    matrix = confusion_from_codes(reference, predicted)
    stats = class_statistics(matrix)
    return {
        "n_cases": int(matrix.sum()),
        "macro_f1": macro_f1(matrix),
        "balanced_accuracy": balanced_accuracy(matrix),
        "accuracy": accuracy(matrix),
        "per_class": {
            label: {
                "precision": float(stats["precision"][i]),
                "recall": float(stats["recall"][i]),
                "f1": float(stats["f1"][i]),
                "support": int(stats["support"][i]),
            }
            for i, label in enumerate(LABELS)
        },
        "confusion_matrix": {
            "rows_reference": list(LABELS),
            "columns_predicted": list(OUTCOMES),
            "counts": matrix.tolist(),
        },
        "safety": safety_rates(matrix),
    }


def bootstrap_metrics(
    reference: np.ndarray,
    predictions: Mapping[str, np.ndarray],
    *,
    n_boot: int = DEFAULT_BOOTSTRAP,
    seed: int = DEFAULT_SEED,
) -> dict[str, dict[str, np.ndarray]]:
    """Case-level bootstrap. Every arm shares each resample so differences are paired."""

    rng = np.random.default_rng(seed)
    rows = rng.integers(0, len(reference), size=(n_boot, len(reference)))
    draws = {
        arm: {"macro_f1": np.empty(n_boot), "balanced_accuracy": np.empty(n_boot)}
        for arm in predictions
    }
    for b in range(n_boot):
        resampled = reference[rows[b]]
        for arm, predicted in predictions.items():
            matrix = confusion_from_codes(resampled, predicted[rows[b]])
            draws[arm]["macro_f1"][b] = macro_f1(matrix)
            draws[arm]["balanced_accuracy"][b] = balanced_accuracy(matrix)
    return draws


def _interval(values: np.ndarray) -> list[float]:
    low, high = np.percentile(values, [2.5, 97.5])
    return [float(low), float(high)]


def paired_verdict(interval: Sequence[float]) -> str:
    """Directional only when the 95% interval excludes zero (plan section 7.4)."""

    if abs(interval[0]) < 1e-12 and abs(interval[1]) < 1e-12:
        return "identical (no difference in any resample)"
    if interval[0] > 0:
        return "first arm higher (interval excludes 0)"
    if interval[1] < 0:
        return "first arm lower (interval excludes 0)"
    return "inconclusive (interval includes 0)"


def paired_differences(
    draws: Mapping[str, Mapping[str, np.ndarray]],
    point: Mapping[str, Mapping[str, Any]],
    pairs: Sequence[tuple[str, str]],
) -> list[dict[str, Any]]:
    rows = []
    for first, second in pairs:
        for metric in ("macro_f1", "balanced_accuracy"):
            interval = _interval(draws[first][metric] - draws[second][metric])
            rows.append(
                {
                    "first_arm": first,
                    "second_arm": second,
                    "metric": metric,
                    "difference": float(point[first][metric] - point[second][metric]),
                    "ci95_low": interval[0],
                    "ci95_high": interval[1],
                    "verdict": paired_verdict(interval),
                }
            )
    return rows


def stability(
    observations: Sequence[Observation],
    case_ids: Sequence[str],
    runs: Sequence[int] = (1, 2, 3),
) -> dict[str, Any]:
    """Three-run agreement, decision-change rate, and per-case majority decisions."""

    by_case: dict[str, dict[int, str]] = {}
    for o in observations:
        by_case.setdefault(o.case_id, {})[o.run_number] = o.decision
    complete = [c for c in case_ids if all(r in by_case.get(c, {}) for r in runs)]
    if not complete:
        return {"n_complete_cases": 0, "exact_agreement_rate": None,
                "decision_change_rate": None, "majority": {}}
    agree = changed = 0
    majority: dict[str, str] = {}
    for case_id in complete:
        decisions = [by_case[case_id][r] for r in runs]
        agree += len(set(decisions)) == 1
        changed += any(d != decisions[0] for d in decisions[1:])
        top, count = Counter(decisions).most_common(1)[0]
        majority[case_id] = top if count > len(runs) / 2 else INVALID
    return {
        "n_complete_cases": len(complete),
        "exact_agreement_rate": agree / len(complete),
        "decision_change_rate": changed / len(complete),
        "majority": majority,
    }


def latency_summary(observations: Sequence[Observation]) -> dict[str, Any]:
    values = np.array([o.latency_ms for o in observations if o.latency_ms is not None], float)
    if not len(values):
        return {"n": 0}
    return {
        "n": int(len(values)),
        "median_ms": float(np.median(values)),
        "mean_ms": float(values.mean()),
        "p95_ms": float(np.percentile(values, 95)),
        "min_ms": float(values.min()),
        "max_ms": float(values.max()),
    }


def stratified_accuracy(
    cases: Sequence[Mapping[str, str]],
    decisions: Mapping[str, Sequence[str]],
) -> list[dict[str, Any]]:
    rows = []
    for column in STRATA:
        for value in sorted({case[column] for case in cases}):
            index = [i for i, case in enumerate(cases) if case[column] == value]
            for arm, predicted in decisions.items():
                correct = sum(predicted[i] == cases[i]["reference_label"] for i in index)
                rows.append(
                    {"stratum": column, "value": value, "arm": arm, "n": len(index),
                     "correct": correct, "accuracy": correct / len(index)}
                )
    return rows


def score(
    cases: Sequence[Mapping[str, str]],
    observations_by_arm: Mapping[str, Sequence[Observation]],
    *,
    primary_run: int = 1,
    n_boot: int = DEFAULT_BOOTSTRAP,
    seed: int = DEFAULT_SEED,
    focus_arm: str = "curricupath",
) -> dict[str, Any]:
    """Score every supplied arm on the primary run and compare against the focus arm."""

    case_ids = [case["case_id"] for case in cases]
    reference = encode([case["reference_label"] for case in cases])
    decisions: dict[str, list[str]] = {}
    arms: dict[str, Any] = {}
    for arm, observations in observations_by_arm.items():
        decisions[arm], missing = primary_decisions(observations, case_ids, primary_run)
        result = arm_metrics(reference, encode(decisions[arm]))
        result["missing_cases"] = missing
        result["provider_failure_cases"] = sorted(
            o.case_id for o in observations if o.run_number == primary_run and o.provider_failure
        )
        result["latency"] = latency_summary(observations)
        run_numbers = tuple(sorted({o.run_number for o in observations}))
        # A single pass has nothing to compare; asking for three runs yields "not available".
        runs = stability(observations, case_ids, run_numbers if len(run_numbers) > 1 else (1, 2, 3))
        majority = runs.pop("majority")
        result["stability"] = runs
        if majority:
            voted = [majority.get(c, INVALID) for c in case_ids]
            result["majority_vote_sensitivity"] = {
                "macro_f1": arm_metrics(reference, encode(voted))["macro_f1"],
                "balanced_accuracy": arm_metrics(reference, encode(voted))["balanced_accuracy"],
            }
        arms[arm] = result

    codes = {arm: encode(values) for arm, values in decisions.items()}
    draws = bootstrap_metrics(reference, codes, n_boot=n_boot, seed=seed)
    for arm in arms:
        arms[arm]["macro_f1_ci95"] = _interval(draws[arm]["macro_f1"])
        arms[arm]["balanced_accuracy_ci95"] = _interval(draws[arm]["balanced_accuracy"])
    pairs = [(focus_arm, arm) for arm in arms if arm != focus_arm] if focus_arm in arms else []
    return {
        "n_cases": len(cases),
        "primary_run": primary_run,
        "bootstrap": {"resamples": n_boot, "seed": seed, "unit": "case"},
        "arms": arms,
        "paired_differences": paired_differences(draws, arms, pairs),
        "stratified_accuracy": stratified_accuracy(cases, decisions),
        "decisions_by_case": {arm: dict(zip(case_ids, values)) for arm, values in decisions.items()},
    }
