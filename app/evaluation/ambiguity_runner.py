"""Drive one ambiguity case through the advisor under the frozen scripted-reply protocol.

Protocol (revised evaluation plan, section 9.2):
- the query is sent once;
- if the system asks for clarification, the case's fixed simulated reply is sent once;
- if it then asks something further, the case's neutral fallback reply is sent once;
- any further question leaves the case unresolved. No reply is ever improvised.
"""

from __future__ import annotations

from time import perf_counter
from typing import Any, Callable, Mapping

CLARIFICATION_STATUSES = frozenset({"clarification_required", "needs_clarification"})
PENDING = "pending_independent_review"
Send = Callable[[str, "str | None"], Mapping[str, Any]]


def is_clarification(response: Mapping[str, Any]) -> bool:
    return response.get("status") in CLARIFICATION_STATUSES


def _scripted(reply: str | None) -> bool:
    return bool(reply) and reply != PENDING


def run_case(
    send: Send,
    case: Mapping[str, str],
    *,
    allow_clarification: bool,
) -> dict[str, Any]:
    """Run one case. `send(message, session_id)` returns the advisor's response."""

    started = perf_counter()
    turns = []
    error: str | None = None
    unscripted = False
    response: Mapping[str, Any] = {}
    try:
        response = send(case["query"], None)
        turns.append({"message": case["query"], "response": response})
        if allow_clarification:
            for field in ("fixed_simulated_reply", "neutral_fallback_reply"):
                if not is_clarification(response):
                    break
                reply = case.get(field)
                if not _scripted(reply):
                    unscripted = True
                    break
                response = send(reply, response.get("session_id"))
                turns.append({"message": reply, "response": response})
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    return {
        "case_id": case["case_id"],
        "turns": turns,
        "final": dict(response),
        "n_turns": len(turns),
        "unscripted": unscripted,
        "latency_ms": max(0, round((perf_counter() - started) * 1000)),
        "error": error,
    }


def case_errors(cases: list[Mapping[str, str]]) -> list[str]:
    """What an official run still needs from the independent reviewer."""

    import json

    problems: list[str] = []
    for case in cases:
        cid = case["case_id"]
        if case["approval_state"] != "approved":
            problems.append(f"{cid}: approval_state is {case['approval_state']}, not approved.")
        if case["required_clarification"] not in {"true", "false"}:
            problems.append(f"{cid}: required_clarification is not set to true or false.")
        if case["required_clarification"] == "true" and not _scripted(case["fixed_simulated_reply"]):
            problems.append(f"{cid}: a fixed simulated reply is required when clarification is required.")
        try:
            accepted = json.loads(case["accepted_final_outcomes_json"] or "[]")
        except json.JSONDecodeError:
            accepted = None
        if not accepted:
            problems.append(f"{cid}: accepted_final_outcomes_json is empty or invalid.")
    return problems
