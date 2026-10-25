"""Synthetic tests for the School registration-reference timetable-clash gate."""

from __future__ import annotations

import json
from pathlib import Path

from app.advisor.eligibility import StudentProfile, check_eligibility, load_clash_rules


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _profile(*repeating: str) -> StudentProfile:
    return StudentProfile(
        programme_code="EFA03",
        completed_modules=frozenset(),
        current_modules=frozenset(),
        planned_modules=frozenset(),
        repeating_modules=frozenset(repeating),
    )


def _module(course_code: str) -> dict[str, str]:
    return {
        "programme_code": "EFA03",
        "course_code": course_code,
        "year_of_study": "3",
        "source_id": "SRC_TEST",
    }


def _source() -> dict[str, str]:
    return {
        "source_id": "SRC_TEST",
        "title": "Synthetic eligibility source",
        "verification_status": "verified",
        "url": "https://example.test/source",
        "local_path": "",
    }


def _clash(
    repeating: str,
    target: str,
    clash_type: str,
    *,
    source_ids: str = "EIE_PLANNER_2026;EIE_REG_GRID_2026",
    sheet: str = "EIE_PLANNER_2026:EE YOS 2;EIE_REG_GRID_2026:EE YOS 2",
) -> dict[str, str]:
    return {
        "rule_id": f"CLASH_{repeating}_{target}",
        "scope": "EFA03",
        "rule_type": "timetable_clash",
        "repeating_course": repeating,
        "target_course_code": target,
        "clash_type": clash_type,
        "source_ids": source_ids,
        "sheet": sheet,
    }


def _check(
    target: str,
    profile: StudentProfile,
    *,
    clash_rules: tuple[dict[str, str], ...] = (),
    rules: tuple[dict[str, str], ...] = (),
    enabled: bool = True,
):
    return check_eligibility(
        target,
        profile,
        [_module(target)],
        rules,
        [_source()],
        clash_rules=clash_rules,
        enable_timetable_clashes=enabled,
    )


def test_lecture_clash_with_repeated_module_is_ineligible() -> None:
    result = _check(
        "ELEN3000A",
        _profile("ELEN2003A"),
        clash_rules=(_clash("ELEN2003A", "ELEN3000A", "LEC"),),
    )

    assert result.decision == "ineligible"
    assert result.reasons == (
        "CLASH_ELEN2003A_ELEN3000A: ELEN3000A has a lecture timetable clash "
        "with ELEN2003A, which the student is repeating, so it cannot be taken "
        "(EIE_PLANNER_2026, sheet 'EE YOS 2'; EIE_REG_GRID_2026).",
    )


def test_text_only_unspecified_clash_and_missing_suffix_are_supported() -> None:
    result = _check(
        "ELEN3003A",
        _profile("ELEN2017"),
        clash_rules=(
            _clash(
                "ELEN2017A",
                "ELEN3003A",
                "UNSPECIFIED",
                source_ids="EIE_REG_GRID_2026",
                sheet="EIE_REG_GRID_2026:EE YOS 2",
            ),
        ),
    )

    assert result.decision == "ineligible"
    assert "has a timetable clash with ELEN2017A" in result.reasons[0]


def test_non_clashing_repeat_reports_prerequisite_only() -> None:
    prerequisite = {
        "rule_id": "PRE_ELEN3002",
        "scope": "EFA03",
        "rule_type": "prerequisite",
        "target_course_code": "ELEN3002A",
        "condition_json": json.dumps({"all_of": ["ELEN2005A"]}),
        "source_id": "SRC_TEST",
    }
    result = _check(
        "ELEN3002A",
        _profile("ELEN2005A"),
        rules=(prerequisite,),
    )

    assert result.decision == "ineligible"
    assert result.reasons == ("Prerequisite rule PRE_ELEN3002 is not satisfied.",)
    assert all("CLASH_" not in reason for reason in result.reasons)


def test_no_repeating_modules_leaves_clash_gate_silent() -> None:
    result = _check(
        "ELEN3000A",
        _profile(),
        clash_rules=(_clash("ELEN2003A", "ELEN3000A", "LEC"),),
    )

    assert result.decision == "eligible"
    assert result.reasons == ()


def test_feature_flag_off_preserves_previous_eligibility_path() -> None:
    result = _check(
        "ELEN3000A",
        _profile("ELEN2003A"),
        clash_rules=(_clash("ELEN2003A", "ELEN3000A", "LEC"),),
        enabled=False,
    )

    assert result.decision == "eligible"


def test_clash_and_prerequisite_failures_are_both_reported() -> None:
    prerequisite = {
        "rule_id": "PRE_ELEN3000",
        "scope": "EFA03",
        "rule_type": "prerequisite",
        "target_course_code": "ELEN3000A",
        "condition_json": json.dumps({"all_of": ["MATH2014A"]}),
        "source_id": "SRC_TEST",
    }
    result = _check(
        "ELEN3000A",
        _profile("ELEN2003A"),
        clash_rules=(_clash("ELEN2003A", "ELEN3000A", "LEC"),),
        rules=(prerequisite,),
    )

    assert result.decision == "ineligible"
    assert len(result.reasons) == 2
    assert result.reasons[0] == "Prerequisite rule PRE_ELEN3000 is not satisfied."
    assert result.reasons[1].startswith("CLASH_ELEN2003A_ELEN3000A:")


def test_generated_rules_include_known_text_only_pair() -> None:
    rules = load_clash_rules(PROJECT_ROOT / "data" / "rules" / "grid_clash_rules.csv")

    assert len(rules) == 52
    known = next(
        rule
        for rule in rules
        if rule["repeating_course"] == "ELEN2017A"
        and rule["target_course_code"] == "ELEN3003A"
    )
    assert known["agreement"] == "text_only"
    assert known["clash_type"] == "UNSPECIFIED"


def _concurrent_profile(*, current=(), planned=(), confirmed=None, cleared=()) -> StudentProfile:
    return StudentProfile(
        programme_code="EFA03",
        completed_modules=frozenset(),
        current_modules=frozenset(current),
        planned_modules=frozenset(planned),
        clash_cleared_modules=frozenset(cleared),
        module_history_confirmed=confirmed,
    )


def test_current_module_clashes_with_the_target_in_either_direction() -> None:
    rule = (_clash("ELEN2003A", "ELEN3000A", "LEC"),)

    forward = _check("ELEN3000A", _concurrent_profile(current={"ELEN2003A"}), clash_rules=rule)
    backward = _check("ELEN2003A", _concurrent_profile(planned={"ELEN3000A"}), clash_rules=rule)

    assert forward.decision == backward.decision == "ineligible"
    assert "taking or planning in the same period" in forward.reasons[0]
    assert "has a lecture timetable clash with ELEN3000A" in backward.reasons[0]


def test_unknown_partner_is_asked_about_only_when_history_is_unconfirmed() -> None:
    rule = (_clash("ELEN2003A", "ELEN3000A", "LEC"),)

    unconfirmed = _check("ELEN3000A", _concurrent_profile(confirmed=False), clash_rules=rule)
    confirmed = _check("ELEN3000A", _concurrent_profile(confirmed=True), clash_rules=rule)
    legacy = _check("ELEN3000A", _concurrent_profile(confirmed=None), clash_rules=rule)

    assert unconfirmed.decision == "needs_clarification"
    assert unconfirmed.clarification["gate"] == "timetable_clash"
    assert unconfirmed.clarification["target_predicates"] == ["ELEN2003A"]
    assert unconfirmed.clarification["options"] == ["Repeating", "Current", "Planned", "None of these"]
    assert confirmed.decision == legacy.decision == "eligible"


def test_a_cleared_partner_is_not_asked_about_again() -> None:
    rule = (_clash("ELEN2003A", "ELEN3000A", "LEC"),)

    result = _check(
        "ELEN3000A",
        _concurrent_profile(confirmed=False, cleared={"ELEN2003A"}),
        clash_rules=rule,
    )

    assert result.decision == "eligible"


def test_completed_partner_does_not_clash() -> None:
    profile = StudentProfile(
        programme_code="EFA03",
        completed_modules=frozenset({"ELEN2003A"}),
        current_modules=frozenset(),
        planned_modules=frozenset(),
        module_history_confirmed=False,
    )

    result = _check("ELEN3000A", profile, clash_rules=(_clash("ELEN2003A", "ELEN3000A", "LEC"),))

    assert result.decision == "eligible"


# ---- Conversation: the advisor asks about clash partners (developer-written fixtures) -------

def _clash_engine():
    from app.advisor.engine import AdvisorEngine
    from app.advisor.intent import DeterministicIntentExtractor
    from app.backend import CurricuPathService
    from app.data.repository import CsvCatalogueRepository

    repository = CsvCatalogueRepository(PROJECT_ROOT / "data" / "processed")
    service = CurricuPathService(
        repository, str(PROJECT_ROOT), timetable_clash_gate_enabled=True
    )
    return AdvisorEngine(service, DeterministicIntentExtractor(repository.data.aliases))


def _first_turn(engine):
    from app.data.sessions import ConversationContext

    # ELEN3000A in EFA03 lists a lecture clash with ELEN2003A (School reference rule).
    first = engine.advise(
        "Can I take ELEN3000A in EFA03?",
        completed_modules=_EVERYTHING_BUT_PAIR,
        module_history_confirmed=False,
    )
    return first, ConversationContext.from_dict(first["conversation_context"])


def _efa03_modules_except(*codes):
    from app.data.repository import CsvCatalogueRepository

    repository = CsvCatalogueRepository(PROJECT_ROOT / "data" / "processed")
    return {m["course_code"] for m in repository.list_modules("EFA03")} - set(codes)


_EVERYTHING_BUT_PAIR = _efa03_modules_except("ELEN3000A", "ELEN2003A")


def test_advisor_asks_whether_a_clashing_module_is_being_repeated() -> None:
    first, _ = _first_turn(_clash_engine())

    assert first["status"] == "clarification_required"
    assert first["conversation_context"]["pending_fact_gate"] == "timetable_clash"
    assert first["conversation_context"]["pending_fact_course_codes"] == ["ELEN2003A"]
    assert first["clarification_options"] == ["Repeating", "Current", "Planned", "None of these"]


def test_repeating_reply_makes_the_target_ineligible() -> None:
    engine = _clash_engine()
    _, context = _first_turn(engine)
    second = engine.advise(
        "Repeating", context=context, completed_modules=_EVERYTHING_BUT_PAIR,
        module_history_confirmed=False,
    )

    assert second["decision"] == "ineligible"
    assert any("CLASH_ELEN2003A_ELEN3000A" in reason for reason in second["reasons"])


def test_none_of_these_clears_the_clash_without_marking_the_module_not_completed() -> None:
    engine = _clash_engine()
    _, context = _first_turn(engine)
    second = engine.advise(
        "None of these", context=context, completed_modules=_EVERYTHING_BUT_PAIR,
        module_history_confirmed=False,
    )

    assert second["clarification_applied_all"] == [
        {"course_code": "ELEN2003A", "state": "not_taking", "gate": "timetable_clash"}
    ]
    assert second.get("clarification_exhausted") is not True
    assert second["conversation_context"].get("pending_fact_gate") != "timetable_clash"


def test_a_prerequisite_reply_is_still_read_against_the_prerequisite_gate_with_clashes_on() -> None:
    from app.data.sessions import ConversationContext

    engine = _clash_engine()
    first = engine.advise("Can I take ELEN3013A in EFA03?", module_history_confirmed=False)
    second = engine.advise(
        "ELEN2020A planned",
        context=ConversationContext.from_dict(first["conversation_context"]),
        module_history_confirmed=False,
    )

    assert first["conversation_context"]["pending_fact_gate"] == "prerequisite"
    assert second["status"] == "clarification_unresolved"
