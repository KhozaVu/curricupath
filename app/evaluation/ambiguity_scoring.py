"""Score Experiment C (ambiguity and clarification) records against the plan's metrics.

Metrics that need reviewer-authored fields (required_clarification, accepted outcomes)
report `not_scorable` instead of a guess. Metrics that use only the developer-drafted
`intended_interpretation` are always available, so a draft run is still informative.
"""

from __future__ import annotations

import json
from math import comb
from typing import Any, Mapping, Sequence

from app.evaluation.ambiguity_runner import is_clarification
from app.evaluation.intent_scoring import wilson_interval

ACCEPTED_KEYS = ("intent", "status", "module_code")
NEEDS_REVIEWER = "needs reviewer fields (required_clarification, accepted_final_outcomes_json)"


def _norm(value: Any) -> str:
    return "" if value is None else str(value).strip().upper()


def _proportion(hits: int, total: int) -> dict[str, Any]:
    if total == 0:
        return {"correct": 0, "n": 0, "rate": None, "ci95": None, "not_scorable": NEEDS_REVIEWER}
    return {"correct": hits, "n": total, "rate": hits / total, "ci95": wilson_interval(hits, total)}


def parse_accepted(case: Mapping[str, str]) -> list[dict[str, str]] | None:
    """Accepted final outcomes, or None when the reviewer has not supplied any."""

    accepted = json.loads(case.get("accepted_final_outcomes_json") or "[]")
    if not accepted:
        return None
    for item in accepted:
        unknown = set(item) - set(ACCEPTED_KEYS)
        if unknown:
            raise ValueError(f"Unsupported accepted-outcome keys: {sorted(unknown)}.")
    return accepted


def outcome_matches(final: Mapping[str, Any], accepted_item: Mapping[str, str]) -> bool:
    """Every key in the accepted item must equal the matching field of the final response.

    Unless the item names a `status` explicitly, the system must actually have answered:
    a response that is still asking a question or refusing never counts as correct advice.
    """

    if "status" not in accepted_item and final.get("status") != "ok":
        return False
    actual = {
        "intent": final.get("intent"),
        "status": final.get("status"),
        "module_code": (final.get("module") or {}).get("course_code"),
    }
    return all(_norm(actual[key]) == _norm(value) for key, value in accepted_item.items())


def _required(case: Mapping[str, str]) -> bool | None:
    return {"true": True, "false": False}.get(case.get("required_clarification", ""))


def case_facts(case: Mapping[str, str], record: Mapping[str, Any]) -> dict[str, Any]:
    first = record["turns"][0]["response"] if record["turns"] else {}
    final = record["final"]
    accepted = parse_accepted(case)
    return {
        "case_id": case["case_id"],
        "required": _required(case),
        "asked_first": is_clarification(first),
        "answered_first": first.get("status") == "ok",
        "refused_first": first.get("status") == "out_of_scope",
        "initial_intent_correct": _norm(first.get("intent")) == _norm(case["intended_interpretation"]),
        "final_intent_correct": _norm(final.get("intent")) == _norm(case["intended_interpretation"]),
        "final_answered": final.get("status") == "ok",
        "final_unresolved": is_clarification(final),
        "final_refused": final.get("status") == "out_of_scope",
        "final_accepted": None if accepted is None else any(outcome_matches(final, a) for a in accepted),
        "n_turns": record["n_turns"],
        "errored": record.get("error") is not None,
        "unscripted": record.get("unscripted", False),
    }


def score_arm(cases: Sequence[Mapping[str, str]], records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_id = {r["case_id"]: r for r in records}
    facts = [case_facts(c, by_id[c["case_id"]]) for c in cases if c["case_id"] in by_id]
    n = len(facts)
    required = [f for f in facts if f["required"] is True]
    not_required = [f for f in facts if f["required"] is False]
    asked_first = [f for f in facts if f["asked_first"]]
    accepted_known = [f for f in facts if f["final_accepted"] is not None]
    answered = [f for f in facts if f["final_answered"]]
    return {
        "n_cases": n,
        "initial_intent_accuracy": _proportion(sum(f["initial_intent_correct"] for f in facts), n),
        "final_interpretation_correct": _proportion(sum(f["final_intent_correct"] for f in facts), n),
        "asked_clarification_first_turn": _proportion(len(asked_first), n),
        "answered_first_turn": _proportion(sum(f["answered_first"] for f in facts), n),
        "refused_out_of_scope_first_turn": _proportion(sum(f["refused_first"] for f in facts), n),
        "appropriate_clarification_rate": _proportion(sum(f["asked_first"] for f in required), len(required)),
        "unnecessary_clarification_rate": _proportion(sum(f["asked_first"] for f in not_required), len(not_required)),
        "silent_guess_rate": _proportion(sum(f["answered_first"] for f in required), len(required)),
        "final_outcome_accepted": _proportion(sum(f["final_accepted"] for f in accepted_known), len(accepted_known)),
        "second_attempt_success": _proportion(
            sum(bool(f["final_accepted"]) for f in asked_first if f["final_accepted"] is not None),
            sum(f["final_accepted"] is not None for f in asked_first),
        ),
        "unresolved_clarification_rate": _proportion(sum(f["final_unresolved"] for f in facts), n),
        "unhandled_error_rate": _proportion(sum(f["errored"] for f in facts), n),
        "mean_turns_to_resolution": (sum(f["n_turns"] for f in answered) / len(answered)) if answered else None,
        "unscripted_cases": [f["case_id"] for f in facts if f["unscripted"]],
    }


def exact_sign_test(only_first: int, only_second: int) -> float:
    """Two-sided exact test on discordant pairs (binomial, p = 0.5)."""

    n = only_first + only_second
    if n == 0:
        return 1.0
    tail = sum(comb(n, i) for i in range(min(only_first, only_second) + 1))
    return min(1.0, 2 * tail / 2**n)


def paired_comparison(
    cases: Sequence[Mapping[str, str]],
    full: Sequence[Mapping[str, Any]],
    ablation: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Full CurricuPath against CurricuPath with clarification disabled, on the same cases."""

    full_by, ablation_by = ({r["case_id"]: r for r in rs} for rs in (full, ablation))
    result: dict[str, Any] = {}
    for name, key in (("final_interpretation_correct", "final_intent_correct"),
                      ("final_outcome_accepted", "final_accepted")):
        pairs = []
        for case in cases:
            a = case_facts(case, full_by[case["case_id"]])[key]
            b = case_facts(case, ablation_by[case["case_id"]])[key]
            if a is not None and b is not None:
                pairs.append((bool(a), bool(b)))
        only_full = sum(a and not b for a, b in pairs)
        only_ablation = sum(b and not a for a, b in pairs)
        result[name] = {
            "n_pairs": len(pairs),
            "both_correct": sum(a and b for a, b in pairs),
            "only_with_clarification": only_full,
            "only_without_clarification": only_ablation,
            "neither": sum(not a and not b for a, b in pairs),
            "exact_sign_test_p": exact_sign_test(only_full, only_ablation) if pairs else None,
            **({} if pairs else {"not_scorable": NEEDS_REVIEWER}),
        }
    return result
