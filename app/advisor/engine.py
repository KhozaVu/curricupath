"""End-to-end deterministic advisor orchestration over the CSV catalogue."""

from __future__ import annotations

import re
from contextvars import ContextVar
from typing import Any, Literal, Protocol, Sequence

from app.advisor.eligibility import ModuleFactState
from app.advisor.intent import IntentExtractor, ParsedAdvisorRequest
from app.advisor.elective_careers import ELECTIVE_CAREER_DIRECTIONS
from app.advisor.module_matching import score_module_relevance
from app.advisor.module_resolution import _normalise_name
from app.advisor.normalisation import normalise_text
from app.advisor.ranking import (
    DeterministicPublicCourseRanker,
    PublicCourseRanker,
    RankingUnavailableError,
)
from app.backend import CurricuPathService
from app.data.sessions import ConversationContext


class SemanticCourseMatcher(Protocol):
    """Optional semantic candidate matcher used before deterministic ranking."""

    def course_scores(
        self, query: str, course_ids: Sequence[str]
    ) -> dict[str, float]: ...

    def module_scores(
        self, query: str, module_codes: Sequence[str]
    ) -> dict[str, float]: ...


class AdvisorEngine:
    """Apply extracted facts to fixed catalogue, eligibility and ranking operations."""

    def __init__(
        self,
        service: CurricuPathService,
        extractor: IntentExtractor,
        semantic_matcher: SemanticCourseMatcher | None = None,
        public_course_ranker: PublicCourseRanker | None = None,
    ) -> None:
        self.service = service
        self.extractor = extractor
        self.semantic_matcher = semantic_matcher
        self.public_course_ranker = public_course_ranker
        self._fallback_course_ranker = DeterministicPublicCourseRanker()

    def advise(
        self,
        message: str,
        programme_code: str | None = None,
        completed_modules: set[str] | None = None,
        current_modules: set[str] | None = None,
        planned_modules: set[str] | None = None,
        context: ConversationContext | None = None,
        ranking_mode: Literal["auto", "deterministic", "prototype"] = "auto",
        *,
        module_states: dict[str, ModuleFactState] | None = None,
        module_history_confirmed: bool | None = None,
        repeating_modules: set[str] | None = None,
        allow_clarification: bool = True,
    ) -> dict[str, Any]:
        """Answer one message. With clarification disabled the engine never asks a question:
        an ambiguous module name is resolved to its best-scoring candidate, and anything
        else it cannot determine becomes a final unresolved answer."""

        token = _ALLOW_CLARIFICATION.set(allow_clarification)
        try:
            result = self._advise(
                message, programme_code, completed_modules, current_modules, planned_modules,
                context, ranking_mode, module_states=module_states,
                module_history_confirmed=module_history_confirmed,
                repeating_modules=repeating_modules,
            )
        finally:
            _ALLOW_CLARIFICATION.reset(token)
        if not allow_clarification and result.get("status") in CLARIFICATION_STATUSES:
            return unresolved_without_clarification(result.get("intent", "unknown"))
        return result

    def _advise(
        self,
        message: str,
        programme_code: str | None = None,
        completed_modules: set[str] | None = None,
        current_modules: set[str] | None = None,
        planned_modules: set[str] | None = None,
        context: ConversationContext | None = None,
        ranking_mode: Literal["auto", "deterministic", "prototype"] = "auto",
        *,
        module_states: dict[str, ModuleFactState] | None = None,
        module_history_confirmed: bool | None = None,
        repeating_modules: set[str] | None = None,
    ) -> dict[str, Any]:
        current_request = self.extractor.extract(message)
        pending_fact_reply = _is_pending_fact_reply(current_request, context, message)
        parsed = _merge_context(current_request, context)
        if pending_fact_reply and context is not None and current_request.module_code:
            # A reply that names the pending modules answers the open check; it does not
            # start a new one about the first module it mentions.
            parsed = parsed.model_copy(
                update={"module_code": context.module_code, "intent": "eligibility"}
            )
        programme = (
            current_request.programme_code
            or programme_code
            or parsed.programme_code
            or ""
        ).upper() or None
        parsed = self._prefer_exact_module_name(message, parsed, programme)
        completed = _merge_modules(completed_modules, parsed.completed_modules)
        current = _merge_modules(current_modules, parsed.current_modules)
        planned = _merge_modules(planned_modules, parsed.planned_modules)
        effective_module_states = {
            code.upper(): state for code, state in (module_states or {}).items()
        }
        clarification_applied: dict[str, str] | None = None
        clarification_applied_all: list[dict[str, str]] = []
        answered_facts: dict[str, str] = {}
        if context is not None and context.pending_intent == "eligibility":
            # Statuses given earlier in this check stay applied while it continues.
            for known_code, known_state in context.answered_facts:
                answered_facts[known_code] = known_state
                _apply_module_fact(
                    known_code,
                    known_state,  # type: ignore[arg-type]
                    completed,
                    current,
                    planned,
                    effective_module_states,
                )
        if pending_fact_reply and context is not None:
            pending_codes = tuple(
                code.upper()
                for code in (
                    context.pending_fact_course_codes
                    or (context.pending_fact_course_code,)
                )
                if code
            )
            new_facts = _parse_module_fact_replies(
                message, pending_codes, context.pending_fact_gate
            )
            if not new_facts:
                return _unresolved_fact_reply(context)
            for fact_code, fact_state in new_facts.items():
                _apply_module_fact(
                    fact_code,
                    fact_state,
                    completed,
                    current,
                    planned,
                    effective_module_states,
                )
                answered_facts[fact_code] = fact_state
                clarification_applied_all.append(
                    {
                        "course_code": fact_code,
                        "state": fact_state,
                        "gate": context.pending_fact_gate or "requirement",
                    }
                )
            clarification_applied = clarification_applied_all[0]

        if parsed.intent == "greeting":
            return _success(
                parsed,
                "Hello. I can check module eligibility, show a curriculum year, "
                "find verified public courses, or explore career paths.",
            )
        if parsed.intent == "help":
            return _success(
                parsed,
                "Try asking 'Can I take ELEN4001A?', 'Show EFA04 year 4 "
                "electives', or 'Find an electric circuits course'.",
            )
        if parsed.intent == "profile_courses":
            return self._profile_courses(parsed, programme, completed, current)
        if parsed.intent == "programme_information":
            return self._programme_information(parsed, programme)
        if parsed.intent == "programme_comparison":
            return self._programme_comparison(message, parsed)
        if parsed.intent == "credit_information":
            return self._credit_information(parsed, programme)
        if parsed.intent == "eligibility":
            return self._eligibility(
                message,
                parsed,
                programme,
                completed,
                current,
                planned,
                effective_module_states,
                module_history_confirmed,
                repeating_modules or set(),
                clarification_attempted=pending_fact_reply,
                clarification_applied=clarification_applied,
                clarification_applied_all=clarification_applied_all,
                answered_facts=answered_facts,
            )
        if parsed.intent == "module_information":
            return self._module_information(
                message,
                parsed,
                programme,
                completed,
                current,
                planned,
                effective_module_states,
                module_history_confirmed,
                repeating_modules or set(),
            )
        if parsed.intent == "curriculum_list":
            if not programme:
                return _clarification(
                    parsed,
                    "Which programme are you in: EFA03 or EFA04?",
                    programme,
                )
            if parsed.requirement_type == "elective_pool" and (
                parsed.interests or parsed.career_preferences
            ):
                return self._elective_recommendations(
                    message,
                    parsed,
                    programme,
                    completed,
                    current,
                    planned,
                    effective_module_states,
                    module_history_confirmed,
                    repeating_modules or set(),
                )
            modules = self.service.modules(programme, parsed.year_of_study)
            if parsed.requirement_type:
                modules = [
                    module
                    for module in modules
                    if module["requirement_type"] == parsed.requirement_type
                ]
            return {
                "intent": parsed.intent,
                "status": "ok",
                "answer": _curriculum_answer(
                    programme,
                    parsed.year_of_study,
                    parsed.requirement_type,
                    modules,
                ),
                "modules": modules,
                "programme_code": programme,
                "year_of_study": parsed.year_of_study,
                "requirement_type": parsed.requirement_type,
                "conversation_context": ConversationContext().as_dict(),
            }
        if parsed.intent == "career_path" and _asks_career_outcomes(message):
            return self._career_information(message, parsed)
        if parsed.intent in {"public_course_search", "career_path"}:
            return self._course_recommendations(message, parsed, ranking_mode)
        return _clarification(
            parsed,
            "I only answer from the CurricuPath curriculum and verified-course data. "
            "Try module eligibility, curriculum requirements, public courses, or careers.",
            programme,
        )

    def _profile_courses(
        self,
        parsed: ParsedAdvisorRequest,
        programme: str | None,
        completed: set[str],
        current: set[str],
    ) -> dict[str, Any]:
        """Describe the curriculum modules selected in the student's profile."""

        completed_records = self._profile_module_records(
            completed, programme, "completed"
        )
        current_records = self._profile_module_records(current, programme, "current")

        answer_parts: list[str] = []
        if completed_records:
            answer_parts.append(
                "You have completed " + _module_name_list(completed_records) + "."
            )
        else:
            answer_parts.append("You have not marked any modules as completed.")

        if current_records:
            answer_parts.append(
                "You are currently taking " + _module_name_list(current_records) + "."
            )
        else:
            answer_parts.append("You have not marked any modules as current.")

        if not completed_records and not current_records:
            answer_parts.append(
                "Use Profile setup to select your completed and current modules."
            )
        else:
            answer_parts.append(
                "Open a module card for its full course information and source evidence."
            )

        return {
            "intent": parsed.intent,
            "status": "ok",
            "answer": " ".join(answer_parts),
            "programme_code": programme,
            "profile_courses": {
                "completed": completed_records,
                "current": current_records,
            },
            "conversation_context": ConversationContext().as_dict(),
        }

    def _credit_information(
        self,
        parsed: ParsedAdvisorRequest,
        programme: str | None,
    ) -> dict[str, Any]:
        if not programme:
            return _clarification(
                parsed,
                "Which programme should I total: EFA03 Electrical Engineering or EFA04 Information Engineering?",
                programme,
            )
        summary = self.service.programme_credit_summary(programme)
        if not summary["years"]:
            return {
                "intent": parsed.intent,
                "status": "not_found",
                "answer": f"No curriculum credit records are available for {programme}.",
                "conversation_context": ConversationContext().as_dict(),
            }
        yearly = "; ".join(
            f"Year {year['year_of_study']}: {year['total_credits']} credits"
            for year in summary["years"]
        )
        return {
            "intent": parsed.intent,
            "status": "ok",
            "answer": (
                f"The currently catalogued {summary['programme_name']} "
                f"({programme}) curriculum totals {summary['total_nqf_credits']} "
                f"NQF credits: {yearly}. Elective pools are counted using their "
                "recorded selection rules, not by adding every available option. "
                "This is a CurricuPath catalogue calculation; confirm official "
                "programme-credit requirements with Wits before registration."
            ),
            "programme_code": programme,
            "credit_summary": summary,
            "conversation_context": ConversationContext().as_dict(),
        }

    def _programme_information(
        self,
        parsed: ParsedAdvisorRequest,
        programme: str | None,
    ) -> dict[str, Any]:
        if not programme:
            return _clarification(
                parsed,
                "Which degree do you mean: Electrical Engineering or Information Engineering?",
                programme,
            )
        profile = self.service.programme_profile(programme)
        if profile is None:
            return {
                "intent": parsed.intent,
                "status": "not_found",
                "answer": f"No verified programme profile is available for {programme}.",
                "conversation_context": ConversationContext().as_dict(),
            }
        careers = ", ".join(profile["career_opportunities"])
        source = profile["source"]
        return {
            "intent": parsed.intent,
            "status": "ok",
            "answer": (
                f"{profile['programme_name']} ({programme}) is a "
                f"{profile['duration_years']}-year {profile['study_mode']} "
                f"{profile['qualification']} degree. {profile['overview']} "
                f"Career opportunities listed by Wits include {careers}. "
                f"Source: {source['title']}, accessed {profile['access_date']}."
            ),
            "programme_code": programme,
            "programme_profile": profile,
            "conversation_context": ConversationContext().as_dict(),
        }

    def _programme_comparison(
        self,
        message: str,
        parsed: ParsedAdvisorRequest,
    ) -> dict[str, Any]:
        electrical = self.service.programme_profile("EFA03")
        information = self.service.programme_profile("EFA04")
        if electrical is None or information is None:
            return {
                "intent": parsed.intent,
                "status": "not_found",
                "answer": "Verified programme comparison data is currently unavailable.",
                "conversation_context": ConversationContext().as_dict(),
            }

        normalized = normalise_text(message)
        physical_communications = bool(
            set(parsed.interests) & {"communications", "electric_circuits"}
            or re.search(
                r"\b(?:optical|wireless|antenna|radio|signal)\b", normalized
            )
        )
        software_networks = bool(
            set(parsed.interests)
            & {"software", "networking", "machine_learning", "data_science"}
        )
        if physical_communications and not software_networks:
            recommended = electrical
            alternative = information
            reason = (
                "Electrical Engineering is the closer fit for the physical "
                "communications side of your stated interest. This is an inference "
                "from its official focus on communications and its listed Antennas "
                "Engineering and Telecommunications Engineer career directions."
            )
            alternative_note = (
                "Information Engineering remains a strong alternative if you want to "
                "focus more on communication software, computer networks, or the "
                "systems built around those technologies."
            )
        elif software_networks and not physical_communications:
            recommended = information
            alternative = electrical
            reason = (
                "Information Engineering is the closer fit for the software, "
                "networking, and systems side of your stated interest. Its official "
                "focus is software engineering, telecommunications, and computer "
                "networking."
            )
            alternative_note = (
                "Electrical Engineering remains a strong alternative if you want to "
                "work closer to power, electronics, automation, or physical "
                "communications technology."
            )
        else:
            recommended = None
            alternative = None
            reason = (
                "Both degrees include telecommunications-related directions, but the "
                "current information does not identify which side of the field you "
                "prefer."
            )
            alternative_note = (
                "Choose Electrical Engineering for physical systems, power, "
                "electronics, and automation; choose Information Engineering for "
                "software engineering and computer networking."
            )

        branch_note = (
            " Wits describes the Information Engineering branch choice as occurring "
            "at the beginning of third year, so your second-year interests are useful "
            "for preparing that decision."
            if parsed.year_of_study == 2
            else ""
        )
        recommendation_text = (
            f"Based on what you said, {recommended['programme_name']} "
            f"({recommended['programme_code']}) is the closer direction. "
            if recommended is not None
            else ""
        )
        return {
            "intent": parsed.intent,
            "status": "ok",
            "answer": (
                recommendation_text
                + reason
                + " "
                + alternative_note
                + branch_note
                + " Neither programme page promises a specific optical-wireless "
                "specialisation, so use later module options and current CBOs to "
                "confirm the available depth."
            ),
            "recommendation": (
                {
                    "programme_code": recommended["programme_code"],
                    "programme_name": recommended["programme_name"],
                }
                if recommended is not None
                else None
            ),
            "programme_comparison": {
                "profiles": [electrical, information],
                "recommended_programme_code": (
                    recommended["programme_code"] if recommended else None
                ),
                "alternative_programme_code": (
                    alternative["programme_code"] if alternative else None
                ),
                "matched_interests": parsed.interests,
            },
            "conversation_context": ConversationContext().as_dict(),
        }

    def _profile_module_records(
        self,
        course_codes: set[str],
        programme: str | None,
        profile_status: str,
    ) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for course_code in course_codes:
            detail = self.service.module(course_code)
            if detail is None:
                continue
            membership = next(
                (
                    item
                    for item in detail.get("memberships", [])
                    if item["programme_code"] == programme
                ),
                (detail.get("memberships") or [{}])[0],
            )
            records.append(
                {
                    **detail,
                    "programme_code": membership.get("programme_code"),
                    "year_of_study": membership.get("year_of_study"),
                    "requirement_type": membership.get("requirement_type"),
                    "profile_status": profile_status,
                }
            )
        return sorted(
            records,
            key=lambda item: (
                item.get("year_of_study") or 99,
                item["course_code"],
            ),
        )

    def _prefer_exact_module_name(
        self,
        message: str,
        parsed: ParsedAdvisorRequest,
        programme: str | None,
    ) -> ParsedAdvisorRequest:
        """Treat an unqualified exact curriculum title as a module lookup."""

        if parsed.module_code or parsed.intent not in {
            "unknown",
            "public_course_search",
            "programme_information",
        }:
            return parsed
        normalized = normalise_text(message)
        module_information_request = any(
            phrase in normalized
            for phrase in (
                "tell me about",
                "course info",
                "course information",
                "course details",
                "module info",
                "module information",
                "module details",
                "who teaches",
                "who is the lecturer",
                "what content",
                "what is covered",
                "how many credits",
                "how much credit",
                "what year",
                "which year",
                "in what year",
            )
        )
        if any(
            term in normalized
            for term in (
                "find", "recommend", "suggest", "career", "online", "public",
                "learn", "tutorial", "certificate", "mooc", "resource",
            )
        ) or ("course" in normalized and not module_information_request):
            return parsed
        matches = self.service.module_name_matches(message, programme)
        if not matches:
            return parsed
        if all(match.score == 1.0 for match in matches):
            return parsed.model_copy(update={"intent": "module_information"})
        # A partial title shared by several modules ("signals", "Software Development")
        # becomes a module lookup so resolution can ask which one, but only for a short
        # query or an explicit module-information phrase, never for free-text requests.
        if parsed.intent in {"unknown", "public_course_search"} and (
            module_information_request or len(_module_query_words(message)) <= 3
        ):
            return parsed.model_copy(update={"intent": "module_information"})
        return parsed

    def prefer_module_information(
        self,
        message: str,
        parsed: ParsedAdvisorRequest,
        programme: str | None,
    ) -> ParsedAdvisorRequest:
        """Public entry used by the scope gate so both apply the same module-name decision."""

        return self._prefer_exact_module_name(message, parsed, programme)

    def _eligibility(
        self,
        message: str,
        parsed: ParsedAdvisorRequest,
        programme: str | None,
        completed: set[str],
        current: set[str],
        planned: set[str],
        module_states: dict[str, ModuleFactState] | None,
        module_history_confirmed: bool | None,
        repeating_modules: set[str],
        *,
        clarification_attempted: bool = False,
        clarification_applied: dict[str, str] | None = None,
        clarification_applied_all: list[dict[str, str]] | None = None,
        answered_facts: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        if not parsed.module_code:
            parsed, clarification = self._resolve_module_name(
                message, parsed, programme, "check"
            )
            if clarification is not None:
                return clarification
        if not programme:
            return _clarification(
                parsed, "Which programme are you in: EFA03 or EFA04?", programme
            )
        result = self.service.eligibility(
            parsed.module_code,
            programme,
            completed,
            current,
            planned,
            _manual_review_reasons(message),
            module_states,
            module_history_confirmed,
            repeating_modules=repeating_modules,
        )
        clarification = result.get("clarification") or {}
        # A reply that supplies at least one new status keeps the check going, so every
        # unknown module is eventually asked about; a reply that supplies none ends it.
        made_progress = bool(clarification_applied_all)
        clarification_exhausted = bool(
            clarification_attempted
            and result["decision"] == "needs_clarification"
            and not made_progress
        )
        if result["decision"] == "needs_clarification" and not clarification_exhausted:
            conversation_context = ConversationContext(
                pending_intent="eligibility",
                module_code=result["course_code"],
                programme_code=programme,
                pending_fact_course_code=clarification.get("target_predicate"),
                pending_fact_gate=_last_trace_gate(result.get("rule_trace", [])),
                clarification_attempted=False,
                pending_fact_course_codes=tuple(
                    clarification.get("target_predicates") or ()
                ),
                answered_facts=tuple((answered_facts or {}).items()),
            ).as_dict()
        else:
            conversation_context = ConversationContext().as_dict()
        result.update(
            {
                "intent": parsed.intent,
                "status": (
                    "completed"
                    if result["completed"]
                    else {
                        "eligible": "ok",
                        "ineligible": "not_eligible",
                        "needs_clarification": (
                            "clarification_unresolved"
                            if clarification_exhausted
                            else "clarification_required"
                        ),
                        "manual_review_required": "manual_review_required",
                    }[result["decision"]]
                ),
                "answer": (
                    _clarification_exhausted_answer(result, clarification_applied)
                    if clarification_exhausted
                    else _eligibility_answer(result)
                ),
                "clarification_question": (
                    None if clarification_exhausted else clarification.get("question")
                ),
                "clarification_options": (
                    [] if clarification_exhausted else clarification.get("options", [])
                ),
                "clarification_attempted": clarification_attempted,
                "clarification_exhausted": clarification_exhausted,
                "clarification_applied": clarification_applied,
                "clarification_applied_all": clarification_applied_all or [],
                "conversation_context": conversation_context,
            }
        )
        result["_candidate_log"] = [
            {
                "item_type": "module",
                "item_id": result["course_code"],
                "eligible": result["eligible"],
                "gate_outcomes": {
                    "completed": result["completed"],
                    "decision": result["decision"],
                    "reasons": result["reasons"],
                    "needs_clarification": result["needs_clarification"],
                    "manual_review_required": result["manual_review_required"],
                    "rule_trace": result["rule_trace"],
                    "unresolved_predicates": result["unresolved_predicates"],
                    "evidence_issues": result["evidence_issues"],
                    "clarification_attempted": clarification_attempted,
                    "clarification_exhausted": clarification_exhausted,
                    "clarification_applied": clarification_applied,
                },
                "score_components": {},
                "final_score": None,
                "selected": result["available_to_take"],
            }
        ]
        return result

    def _module_information(
        self,
        message: str,
        parsed: ParsedAdvisorRequest,
        programme: str | None,
        completed: set[str],
        current: set[str],
        planned: set[str],
        module_states: dict[str, ModuleFactState] | None,
        module_history_confirmed: bool | None,
        repeating_modules: set[str],
    ) -> dict[str, Any]:
        if not parsed.module_code:
            parsed, clarification = self._resolve_module_name(
                message, parsed, programme, "look up"
            )
            if clarification is not None:
                return clarification
        module = self.service.module(parsed.module_code)
        if module is None:
            return {
                "intent": parsed.intent,
                "status": "not_found",
                "answer": f"{parsed.module_code.upper()} is not in the curriculum dataset.",
                "conversation_context": ConversationContext().as_dict(),
            }
        response: dict[str, Any] = {
            "intent": parsed.intent,
            "status": "ok",
            "module": module,
            "answer": _module_information_answer(module, programme),
            "conversation_context": ConversationContext().as_dict(),
        }
        if programme:
            response["eligibility"] = self.service.eligibility(
                parsed.module_code,
                programme,
                completed,
                current,
                planned,
                module_states=module_states,
                module_history_confirmed=module_history_confirmed,
                repeating_modules=repeating_modules,
            )
        return response

    def _resolve_module_name(
        self,
        message: str,
        parsed: ParsedAdvisorRequest,
        programme: str | None,
        action: str,
    ) -> tuple[ParsedAdvisorRequest, dict[str, Any] | None]:
        matches = self.service.module_name_matches(message, programme)
        if len(matches) == 1 or (matches and not _ALLOW_CLARIFICATION.get()):
            # Without clarification the best-scoring candidate is taken: a silent guess.
            return parsed.model_copy(
                update={"module_code": matches[0].course_code}
            ), None
        if matches:
            choices = " or ".join(
                f"{match.course_code} ({match.course_name})" for match in matches
            )
            response = _clarification(
                parsed,
                f"Which module do you mean: {choices}?",
                programme,
            )
            response["module_matches"] = [
                {
                    "course_code": match.course_code,
                    "course_name": match.course_name,
                }
                for match in matches
            ]
            return parsed, response
        return parsed, _clarification(
            parsed,
            f"Which module code or full module name should I {action}?",
            programme,
        )

    def _elective_recommendations(
        self,
        message: str,
        parsed: ParsedAdvisorRequest,
        programme: str,
        completed: set[str],
        current: set[str],
        planned: set[str],
        module_states: dict[str, ModuleFactState] | None,
        module_history_confirmed: bool | None,
        repeating_modules: set[str],
    ) -> dict[str, Any]:
        year = parsed.year_of_study or 4
        memberships = [
            module
            for module in self.service.modules(programme, year)
            if module["requirement_type"] == "elective_pool"
        ]
        requested_tags = [*parsed.interests, *parsed.career_preferences]
        semantic_scores: dict[str, float] = {}
        matching_mode = "controlled_vocabulary"
        if self.semantic_matcher is not None:
            try:
                semantic_scores = self.semantic_matcher.module_scores(
                    message,
                    [module["course_code"] for module in memberships],
                )
            except (AttributeError, RuntimeError):
                semantic_scores = {}
            else:
                if semantic_scores:
                    matching_mode = "hybrid_semantic"

        academic_history_supplied = bool(
            completed
            or current
            or planned
            or module_states
            or repeating_modules
            or module_history_confirmed is True
        )
        candidates: list[dict[str, Any]] = []
        for membership in memberships:
            detail = self.service.module(membership["course_code"])
            if detail is None:
                continue
            relevance = score_module_relevance(
                requested_tags,
                detail,
                semantic_scores.get(membership["course_code"]),
            )
            if academic_history_supplied:
                eligibility: dict[str, Any] = {
                    "assessed": True,
                    **self.service.eligibility(
                        membership["course_code"],
                        programme,
                        completed,
                        current,
                        planned,
                        module_states=module_states,
                        module_history_confirmed=module_history_confirmed,
                        repeating_modules=repeating_modules,
                    ),
                }
            else:
                eligibility = {
                    "assessed": False,
                    "eligible": None,
                    "reasons": [
                        "Enter completed, current, and planned modules to check prerequisites."
                    ],
                    "needs_clarification": True,
                }
            candidates.append(
                {
                    **membership,
                    "course_information": detail["course_information"],
                    "sources": detail["sources"],
                    "eligibility": eligibility,
                    **relevance,
                }
            )

        ranked = sorted(
            candidates,
            key=lambda item: (-item["score"], item["course_code"]),
        )
        # Relevance and registration eligibility answer different questions. Keep
        # strong interest matches visible, then label whether each can be taken now.
        relevant = [item for item in ranked if item["score"] > 0]
        selection_count = next(
            (
                item["selection_count"]
                for item in memberships
                if item.get("selection_count")
            ),
            3,
        )
        matches = relevant[:selection_count]
        if not matches:
            response = _clarification(
                parsed,
                "Which subject or career should your electives focus on?",
                programme,
            )
            response["_candidate_log"] = _elective_candidate_log(ranked, set())
            return response

        selected_codes = {
            item["course_code"]
            for item in matches
            if not academic_history_supplied
            or item["eligibility"]["available_to_take"]
        }
        interest_names = ", ".join(tag.replace("_", " ") for tag in requested_tags)
        titles = ", ".join(
            f"{item['course_code']} ({item['course_name']})" for item in matches
        )
        if academic_history_supplied:
            eligible_count = sum(
                item["eligibility"]["available_to_take"] is True for item in matches
            )
            completed_count = sum(
                item["eligibility"]["completed"] is True for item in matches
            )
            if eligible_count:
                eligibility_note = (
                    f" {eligible_count} of these {len(matches)} matches are currently "
                    "available to take; each result shows its status and requirements."
                )
            elif completed_count == len(matches):
                eligibility_note = " All of these matches are already marked as completed."
            elif completed_count:
                eligibility_note = (
                    f" {completed_count} of these matches are already completed, and none "
                    "of the remaining matches currently pass all declared eligibility rules."
                )
            else:
                eligibility_note = (
                    " These are the strongest interest matches, but none currently pass "
                    "all declared eligibility rules. Review each result's unmet requirements."
                )
        else:
            eligibility_note = (
                " These are interest matches; add your module history to verify prerequisites."
            )
        return {
            "intent": parsed.intent,
            "status": "ok",
            "answer": (
                f"For {programme} Year {year}, the strongest elective matches for "
                f"{interest_names} are {titles}.{eligibility_note}"
            ),
            "recommendations": matches,
            "programme_code": programme,
            "year_of_study": year,
            "requirement_type": "elective_pool",
            "matching_mode": matching_mode,
            "recommendation_kind": "interest_suggestions",
            "_candidate_log": _elective_candidate_log(ranked, selected_codes),
            "conversation_context": ConversationContext().as_dict(),
        }

    def _course_recommendations(
        self,
        message: str,
        parsed: ParsedAdvisorRequest,
        requested_ranking_mode: Literal["auto", "deterministic", "prototype"],
    ) -> dict[str, Any]:
        if requested_ranking_mode == "prototype" and not parsed.workload_preference:
            return _clarification(
                parsed,
                "How much course load would you prefer: light, moderate, or heavy?",
                options=("Light workload", "Moderate workload", "Heavy workload"),
            )
        if requested_ranking_mode == "prototype" and not parsed.difficulty_preference:
            return _clarification(
                parsed,
                "Which difficulty level would you prefer: beginner or intermediate?",
                options=("Beginner", "Intermediate"),
            )
        candidates = self.service.courses(None, None, None, 100)
        if requested_ranking_mode == "prototype":
            candidates = _controlled_preference_candidates(candidates, parsed)
        if parsed.difficulty_preference:
            candidates = [
                course
                for course in candidates
                if course["level"] == parsed.difficulty_preference
            ]
        semantic_scores: dict[str, float] = {}
        matching_mode = "deterministic"
        if self.semantic_matcher is not None:
            try:
                semantic_scores = self.semantic_matcher.course_scores(
                    message,
                    [course["course_id"] for course in candidates],
                )
            except RuntimeError:
                semantic_scores = {}
            else:
                if semantic_scores:
                    matching_mode = "hybrid_semantic"
        use_learned_ranker = requested_ranking_mode in {"auto", "prototype"}
        ranker = (
            self.public_course_ranker
            if use_learned_ranker and self.public_course_ranker is not None
            else self._fallback_course_ranker
        )
        if (
            ranker is not self._fallback_course_ranker
            and getattr(ranker, "requires_semantic", False)
            and any(course["course_id"] not in semantic_scores for course in candidates)
        ):
            ranker = self._fallback_course_ranker
        try:
            scored = [
                ranker.score(
                    message,
                    parsed,
                    course,
                    semantic_scores.get(course["course_id"]),
                )
                for course in candidates
            ]
        except RankingUnavailableError:
            ranker = self._fallback_course_ranker
            scored = [
                ranker.score(
                    message,
                    parsed,
                    course,
                    semantic_scores.get(course["course_id"]),
                )
                for course in candidates
            ]
        if ranker is not self._fallback_course_ranker and parsed.workload_preference:
            scored = _apply_prototype_workload_preference(
                scored, parsed.workload_preference
            )
        ranking_mode = ranker.mode
        ranked = sorted(
            scored,
            key=lambda item: (-item["score"], item["course_id"]),
        )
        matches = [item for item in ranked if item["score"] > 0][:5]
        if not matches:
            return _clarification(
                parsed,
                "Which subject or career should the course options focus on?",
            )
        selected_ids = {item["course_id"] for item in matches}
        return {
            "intent": parsed.intent,
            "status": "ok",
            "answer": _course_answer(matches),
            "recommendations": matches,
            "matching_mode": matching_mode,
            "ranking_mode": ranking_mode,
            "preferences_applied": {
                "workload": parsed.workload_preference,
                "difficulty": parsed.difficulty_preference,
            },
            "_candidate_log": [
                {
                    "item_type": "public_course",
                    "item_id": item["course_id"],
                    "eligible": True,
                    "gate_outcomes": {
                        "source_verification": "passed",
                        "matching_mode": matching_mode,
                        "ranking_mode": ranking_mode,
                    },
                    "score_components": item["score_components"],
                    "final_score": item["score"],
                    "selected": item["course_id"] in selected_ids,
                }
                for item in ranked
            ],
            "conversation_context": ConversationContext().as_dict(),
        }

    def _career_information(
        self,
        message: str,
        parsed: ParsedAdvisorRequest,
    ) -> dict[str, Any]:
        """Describe possible career directions, with courses as supporting evidence."""

        elective = self._career_elective(message, parsed)
        courses = self.service.courses(None, None, None, 100)
        if elective is not None:
            directions = ELECTIVE_CAREER_DIRECTIONS[elective["course_code"]]
            options = []
            for direction in directions:
                supporting_courses = [
                    course["title"]
                    for course in courses
                    if direction["career_tag"] in course["career_tags"]
                ][:3]
                options.append({**direction, "supporting_courses": supporting_courses})

            names = ", ".join(option["display_name"] for option in options)
            return {
                "intent": parsed.intent,
                "status": "ok",
                "answer": (
                    f"{elective['course_code']} {elective['course_name']} can support "
                    f"career directions such as {names}. These are related pathways, "
                    "not employment guarantees; this elective is one part of the skills "
                    "and experience normally required."
                ),
                "career_subject": elective,
                "career_options": options,
                "matching_mode": "controlled_elective_career_mapping",
                "conversation_context": ConversationContext().as_dict(),
            }

        interests = set(parsed.interests)
        careers = set(parsed.career_preferences)
        related_courses = [
            course
            for course in courses
            if interests.intersection(course["interest_tags"])
            or careers.intersection(course["career_tags"])
        ]
        career_tags = {
            tag
            for course in related_courses
            for tag in course["career_tags"]
        }
        if not career_tags:
            career_tags = careers

        options = []
        for career_tag in sorted(career_tags):
            supporting_courses = [
                course["title"]
                for course in related_courses
                if career_tag in course["career_tags"]
            ][:3]
            options.append(
                {
                    "career_tag": career_tag,
                    "display_name": _career_display_name(career_tag),
                    "description": _career_description(career_tag),
                    "supporting_courses": supporting_courses,
                }
            )

        if not options:
            return _clarification(
                parsed,
                "Which career direction should I explore: data science, machine-learning engineering, or another supported path?",
            )

        names = ", ".join(option["display_name"] for option in options)
        return {
            "intent": parsed.intent,
            "status": "ok",
            "answer": (
                f"Possible career directions associated with {_display_tags(parsed.interests) or 'this course'} "
                f"include {names}. These are related pathways, not employment guarantees; "
                "a single course is only one part of the required skills and experience."
            ),
            "career_options": options,
            "matching_mode": "controlled_career_vocabulary",
            "conversation_context": ConversationContext().as_dict(),
        }

    def _career_elective(
        self,
        message: str,
        parsed: ParsedAdvisorRequest,
    ) -> dict[str, str] | None:
        """Resolve a career question to one supported fourth-year elective."""

        if parsed.module_code in ELECTIVE_CAREER_DIRECTIONS:
            module = self.service.module(parsed.module_code)
            if module is not None:
                return {
                    "course_code": module["course_code"],
                    "course_name": module["course_name"],
                }

        matches = [
            match
            for match in self.service.module_name_matches(message)
            if match.course_code in ELECTIVE_CAREER_DIRECTIONS
        ]
        if len(matches) != 1:
            return None
        return {
            "course_code": matches[0].course_code,
            "course_name": matches[0].course_name,
        }


def _elective_candidate_log(
    candidates: list[dict[str, Any]], selected_codes: set[str]
) -> list[dict[str, Any]]:
    return [
        {
            "item_type": "module",
            "item_id": item["course_code"],
            "eligible": item["eligibility"]["eligible"],
            "gate_outcomes": {
                "programme_membership": "passed",
                "eligibility_assessed": item["eligibility"]["assessed"],
                "completed": item["eligibility"].get("completed", False),
                "eligibility_reasons": item["eligibility"]["reasons"],
                "matched_tags": item["matched_tags"],
            },
            "score_components": item["score_components"],
            "final_score": item["score"],
            "selected": item["course_code"] in selected_codes,
        }
        for item in candidates
    ]


def _merge_modules(explicit: set[str] | None, extracted: list[str]) -> set[str]:
    return {value.upper() for value in (explicit or set()) | set(extracted)}


def _is_pending_fact_reply(
    current_request: ParsedAdvisorRequest,
    context: ConversationContext | None,
    message: str = "",
) -> bool:
    """A short unknown-intent turn, or one naming only the pending modules, is the reply."""

    if not (
        context
        and context.pending_intent == "eligibility"
        and context.pending_fact_course_code
        and not context.clarification_attempted
        and current_request.programme_code is None
    ):
        return False
    if current_request.intent == "unknown" and current_request.module_code is None:
        return True
    mentioned = {code.upper() for code in _MODULE_CODE_PATTERN.findall(message.upper())}
    pending = {code.upper() for code in context.pending_fact_course_codes}
    return bool(mentioned) and len(pending) > 1 and mentioned <= pending


_MODULE_CODE_PATTERN = re.compile(r"\b[A-Z]{4}\d{4}A?\b")


def _parse_module_fact_replies(
    message: str,
    pending_codes: tuple[str, ...],
    gate: str | None,
) -> dict[str, ModuleFactState]:
    """Map a reply to one status per pending module; unparsed modules are left out."""

    if len(pending_codes) <= 1:
        state = _parse_module_fact_reply(message, gate)
        return {pending_codes[0]: state} if state and pending_codes else {}
    normalized = normalise_text(message)
    if normalized == "all completed":
        return {code: "completed" for code in pending_codes}
    if normalized == "none completed":
        return {code: "not_completed" for code in pending_codes}
    return _parse_grouped_module_statuses(normalized, pending_codes, gate)


_STATUS_TOKEN = re.compile(
    r"(?P<rest>\b(?:the )?(?:rest|remaining|others?|everything else|all others)\b)"
    r"|(?P<not>\b(?:not(?: yet)?(?: (?:completed|passed|done|finished|taken))?"
    r"|haven t|have not|hasn t|has not|never|incomplete|no|none)\b)"
    r"|(?P<planned>\b(?:planned concurrently|planning(?: to take(?: it)?(?: concurrently)?)?"
    r"|planned|concurrently)\b)"
    r"|(?P<current>\b(?:currently (?:taking|enrolled)|current|taking it now|in progress)\b)"
    r"|(?P<completed>\b(?:completed|passed|done|finished|yes)\b)"
    r"|(?P<code>\b[a-z]{4}\d{4}a?\b)"
)


def _parse_grouped_module_statuses(
    normalized: str,
    pending_codes: tuple[str, ...],
    gate: str | None,
) -> dict[str, ModuleFactState]:
    """Read replies such as 'A and B are completed, the rest are not' or 'A completed, B not'.

    A status applies to the modules named just before it ('A and B are completed') or, when none
    were, to those named just after it ('not completed: C'). 'The rest' means every pending module
    not otherwise mentioned. Statuses not valid for the gate (current/planned for a prerequisite)
    are ignored, never guessed.
    """

    pending = tuple(code.upper() for code in pending_codes)
    allowed = {"completed", "not_completed"}
    if gate in {"corequisite", "exclusion"}:
        allowed |= {"current", "planned"}
    facts: dict[str, ModuleFactState] = {}
    group: list[str] = []
    carry: str | None = None
    rest_seen = False
    rest_state: str | None = None
    for match in _STATUS_TOKEN.finditer(normalized):
        kind = match.lastgroup
        if kind == "code":
            code = match.group(0).upper()
            if code not in pending:
                continue
            if carry is not None and not group:
                facts.setdefault(code, carry)  # type: ignore[arg-type]
            else:
                group.append(code)
        elif kind == "rest":
            rest_seen = True
        else:
            state = "not_completed" if kind == "not" else kind
            if state not in allowed:
                group, carry, rest_seen = [], None, False
                continue
            if group:
                for code in group:
                    facts.setdefault(code, state)  # type: ignore[arg-type]
                group, carry = [], None
            elif rest_seen:
                rest_state = state
                rest_seen, carry = False, None
            else:
                carry = state
    if rest_state is not None:
        for code in pending:
            facts.setdefault(code, rest_state)  # type: ignore[arg-type]
    return facts


def _parse_module_fact_reply(
    message: str,
    gate: str | None,
) -> ModuleFactState | None:
    """Map one controlled clarification reply to an explicit profile fact."""

    normalized = normalise_text(message)
    negative = {
        "no",
        "not completed",
        "not passed",
        "i have not completed it",
        "i have not passed it",
        "none of these",
    }
    completed = {
        "completed",
        "passed",
        "done",
        "yes",
        "yes completed",
        "i completed it",
        "i have completed it",
    }
    current = {
        "current",
        "currently taking it",
        "currently enrolled",
        "taking it now",
    }
    planned = {
        "planned",
        "planned concurrently",
        "planning to take it concurrently",
        "taking it concurrently",
    }

    if normalized in negative:
        return "not_completed"
    if normalized in completed:
        return "completed"
    if gate in {"corequisite", "exclusion"} and normalized in current:
        return "current"
    if gate in {"corequisite", "exclusion"} and normalized in planned:
        return "planned"
    return None


def _apply_module_fact(
    course_code: str,
    state: ModuleFactState,
    completed: set[str],
    current: set[str],
    planned: set[str],
    module_states: dict[str, ModuleFactState],
) -> None:
    """Apply one clarification fact consistently across legacy and typed profiles."""

    completed.discard(course_code)
    current.discard(course_code)
    planned.discard(course_code)
    if state == "completed":
        completed.add(course_code)
    elif state == "current":
        current.add(course_code)
    elif state == "planned":
        planned.add(course_code)
    module_states[course_code] = state


def _last_trace_gate(trace: object) -> str | None:
    if not isinstance(trace, list) or not trace:
        return None
    final = trace[-1]
    return str(final.get("gate")) if isinstance(final, dict) else None


def _unresolved_fact_reply(context: ConversationContext) -> dict[str, Any]:
    course_code = context.module_code or "the requested module"
    fact_code = context.pending_fact_course_code or "the required module"
    answer = (
        f"I could not interpret your status for {fact_code}. The clarification limit "
        f"for {course_code} has been reached. Update that module in Profile setup, "
        "then ask the eligibility question again."
    )
    return {
        "intent": "eligibility",
        "status": "clarification_unresolved",
        "decision": "needs_clarification",
        "eligible": False,
        "needs_clarification": True,
        "manual_review_required": False,
        "course_code": context.module_code,
        "programme_code": context.programme_code,
        "reasons": [f"The supplied status for {fact_code} was not recognized."],
        "unresolved_predicates": [fact_code],
        "clarification_question": None,
        "clarification_options": [],
        "clarification_attempted": True,
        "clarification_exhausted": True,
        "clarification_applied": None,
        "answer": answer,
        "conversation_context": ConversationContext().as_dict(),
        "_candidate_log": [
            {
                "item_type": "module",
                "item_id": context.module_code,
                "eligible": False,
                "gate_outcomes": {
                    "decision": "needs_clarification",
                    "clarification_exhausted": True,
                    "unresolved_predicates": [fact_code],
                },
                "score_components": {},
                "final_score": None,
                "selected": False,
            }
        ],
    }


def _clarification_exhausted_answer(
    result: dict[str, Any],
    applied: dict[str, str] | None,
) -> str:
    applied_text = ""
    if applied:
        applied_text = (
            f"I recorded {applied['course_code']} as "
            f"{applied['state'].replace('_', ' ')} for this check. "
        )
    unresolved = ", ".join(result.get("unresolved_predicates", []))
    return (
        f"{applied_text}I still cannot determine whether {result['course_code']} is "
        f"eligible because these module facts remain unknown: {unresolved}. "
        "The clarification limit has been reached. Update your modules in Profile "
        "setup, then ask again."
    )


def _clarification(
    parsed: ParsedAdvisorRequest,
    question: str,
    programme_code: str | None = None,
    options: tuple[str, ...] = (),
) -> dict[str, Any]:
    context = ConversationContext(
        pending_intent=parsed.intent if parsed.intent != "unknown" else None,
        module_code=parsed.module_code,
        programme_code=programme_code or parsed.programme_code,
        year_of_study=parsed.year_of_study,
        requirement_type=parsed.requirement_type,
        interests=tuple(parsed.interests),
        career_preferences=tuple(parsed.career_preferences),
        workload_preference=parsed.workload_preference,
        difficulty_preference=parsed.difficulty_preference,
        format_preference=parsed.format_preference,
    )
    return {
        "intent": parsed.intent,
        "status": "clarification_required",
        "answer": question,
        "clarification_question": question,
        "clarification_options": list(options),
        "conversation_context": context.as_dict(),
    }


def _controlled_preference_candidates(
    courses: list[dict[str, Any]], parsed: ParsedAdvisorRequest
) -> list[dict[str, Any]]:
    """Prefer exact controlled-tag candidates before semantic/model ranking."""

    interests = set(parsed.interests)
    careers = set(parsed.career_preferences)
    if not interests and not careers:
        return courses
    exact = [
        course
        for course in courses
        if interests.intersection(course["interest_tags"])
        or careers.intersection(course["career_tags"])
    ]
    return exact or courses


def _apply_prototype_workload_preference(
    courses: list[dict[str, Any]], preferred: str
) -> list[dict[str, Any]]:
    """Blend workload fit with normalized pairwise-model utility."""

    levels = {"light": 0, "moderate": 1, "heavy": 2}
    raw_scores = [
        float(course["score_components"].get("model_raw_score", course["score"]))
        for course in courses
    ]
    lower = min(raw_scores, default=0.0)
    upper = max(raw_scores, default=0.0)
    adjusted: list[dict[str, Any]] = []
    for course, raw_score in zip(courses, raw_scores, strict=True):
        normalized_model_score = (
            (raw_score - lower) / (upper - lower) if upper > lower else 1.0
        )
        distance = abs(levels[preferred] - levels.get(course["workload"], 1))
        workload_match = 1.0 - distance / 2.0
        adjusted_score = 0.30 * normalized_model_score + 0.70 * workload_match
        result = dict(course)
        result["score"] = round(max(0.0, min(1.0, adjusted_score)), 4)
        result["score_components"] = {
            **course["score_components"],
            "normalized_prototype_utility": round(normalized_model_score, 4),
            "explicit_workload_match": round(workload_match, 4),
            "workload_adjustment_weight": 0.70,
        }
        adjusted.append(result)
    return adjusted


def _success(parsed: ParsedAdvisorRequest, answer: str) -> dict[str, Any]:
    return {
        "intent": parsed.intent,
        "status": "ok",
        "answer": answer,
        "conversation_context": ConversationContext().as_dict(),
    }


def _merge_context(
    parsed: ParsedAdvisorRequest,
    context: ConversationContext | None,
) -> ParsedAdvisorRequest:
    if context is None:
        return parsed

    intent = parsed.intent
    if context.pending_intent and (
        intent == "unknown"
        or (
            context.pending_intent in {"eligibility", "module_information"}
            and intent in {"module_information", "public_course_search"}
        )
    ):
        intent = context.pending_intent

    return parsed.model_copy(
        update={
            "intent": intent,
            "module_code": parsed.module_code or context.module_code,
            "programme_code": parsed.programme_code or context.programme_code,
            "year_of_study": parsed.year_of_study or context.year_of_study,
            "requirement_type": (
                parsed.requirement_type or context.requirement_type
            ),
            "interests": _ordered_union(context.interests, parsed.interests),
            "career_preferences": _ordered_union(
                context.career_preferences, parsed.career_preferences
            ),
            "workload_preference": (
                parsed.workload_preference or context.workload_preference
            ),
            "difficulty_preference": (
                parsed.difficulty_preference or context.difficulty_preference
            ),
            "format_preference": parsed.format_preference or context.format_preference,
        }
    )


def _ordered_union(existing: tuple[str, ...], current: list[str]) -> list[str]:
    return list(dict.fromkeys([*existing, *current]))


def _module_name_list(modules: list[dict[str, Any]]) -> str:
    return ", ".join(
        f"{module['course_code']} ({module['course_name']})" for module in modules
    )


def _eligibility_answer(result: dict[str, Any]) -> str:
    clarification_question = None
    if result.get("completed"):
        return (
            f"{result['course_code']} is marked as completed in your profile. "
            "It will not be recommended as a module for you to take again."
        )
    if result.get("decision") == "needs_clarification":
        opening = (
            f"I need more information before deciding whether {result['course_code']} "
            "is eligible."
        )
        clarification_question = (result.get("clarification") or {}).get("question")
    elif result.get("decision") == "manual_review_required":
        opening = (
            f"{result['course_code']} requires manual academic review because the "
            "available evidence does not support an authoritative decision."
        )
    elif result.get("decision") == "eligible":
        opening = (
            f"{result['course_code']} is eligible for the declared "
            f"{result['programme_code']} profile."
        )
    else:
        opening = f"{result['course_code']} is not currently eligible."

    non_requirement_reasons = [
        reason
        for reason in result["reasons"]
        if not reason.startswith(("Prerequisite rule", "Corequisite rule"))
    ]
    requirements = result.get("requirements", {})
    prerequisite_text = _requirement_text(
        "Prerequisites",
        requirements.get("prerequisites", []),
        "These must be completed before registration.",
    )
    corequisite_text = _requirement_text(
        "Corequisites",
        requirements.get("corequisites", []),
        "These may be completed already, current, or planned concurrently.",
    )
    return " ".join(
        part
        for part in (
            opening,
            clarification_question,
            *non_requirement_reasons,
            prerequisite_text,
            corequisite_text,
        )
        if part
    )


def _manual_review_reasons(message: str) -> tuple[str, ...]:
    """Identify declared circumstances that require academic discretion."""

    normalized = normalise_text(message)
    reason_patterns = (
        (
            ("concession", "waiver", "permission from the lecturer"),
            "A prerequisite concession or waiver requires academic review.",
        ),
        (
            ("transfer credit", "credit transfer", "credits may count"),
            "Transfer-credit recognition requires academic review.",
        ),
        (
            ("records disagree", "records conflict", "contradictory record"),
            "Contradictory academic records require manual verification.",
        ),
        (
            ("result is not yet confirmed", "result not confirmed", "pending result"),
            "An unconfirmed result requires academic review.",
        ),
    )
    return tuple(
        reason
        for phrases, reason in reason_patterns
        if any(phrase in normalized for phrase in phrases)
    )


def _requirement_text(
    label: str,
    requirements: list[dict[str, Any]],
    policy: str,
) -> str:
    if not requirements:
        return f"{label}: none recorded."
    descriptions = "; ".join(
        f"{requirement['description']} "
        f"({'satisfied' if requirement['satisfied'] else 'not satisfied'})"
        for requirement in requirements
    )
    return f"{label}: {descriptions}. {policy}"


def _curriculum_answer(
    programme: str,
    year: int | None,
    requirement_type: str | None,
    modules: list[dict[str, Any]],
) -> str:
    level = f" Year {year}" if year else ""
    requirement = {
        "elective_pool": " elective",
        "compulsory": " compulsory",
    }.get(requirement_type, " curriculum")
    noun = "module" if len(modules) == 1 else "modules"
    programme_name = {
        "EFA03": "Electrical Engineering",
        "EFA04": "Information Engineering",
    }.get(programme, programme)
    return (
        f"Found {len(modules)}{level}{requirement} {noun} for "
        f"{programme_name} ({programme})."
    )


def _course_answer(matches: list[dict[str, Any]]) -> str:
    titles = ", ".join(item["title"] for item in matches[:3])
    return f"The strongest verified course matches are {titles}."


def _asks_career_outcomes(message: str) -> bool:
    normalized = normalise_text(message)
    return bool(
        re.search(
            r"\b(?:future careers?|career opportunities|career paths?|what careers?|what jobs?)\b",
            normalized,
        )
        or "should i expect" in normalized
        or "can i become" in normalized
    )


def _career_display_name(career_tag: str) -> str:
    return {
        "data_science": "Data science roles",
        "ml_engineering": "Machine-learning engineering roles",
        "software_development": "Software development roles",
        "network_engineering": "Network engineering roles",
        "cybersecurity": "Cybersecurity roles",
        "control_engineering": "Control engineering roles",
        "electrical_engineering": "Electrical engineering roles",
        "electronics_engineering": "Electronics engineering roles",
        "career_development": "General career development",
    }.get(career_tag, career_tag.replace("_", " ").title())


def _display_tags(tags: list[str]) -> str:
    return ", ".join(tag.replace("_", " ") for tag in tags)


def _career_description(career_tag: str) -> str:
    return {
        "data_science": "Work involving data analysis, statistical modelling, and evidence-based decisions.",
        "ml_engineering": "Work involving the development, evaluation, and deployment of machine-learning systems.",
        "software_development": "Work involving the design, implementation, testing, and maintenance of software.",
        "network_engineering": "Work involving the design, operation, and troubleshooting of computer networks.",
        "cybersecurity": "Work involving the protection of systems, networks, and information.",
    }.get(
        career_tag,
        "A related direction represented by the verified public-course catalogue.",
    )


def _module_information_answer(
    module: dict[str, Any], programme_code: str | None = None
) -> str:
    information = module["course_information"]
    memberships = module.get("memberships", [])
    selected_memberships = [
        membership
        for membership in memberships
        if membership.get("programme_code") == programme_code
    ] or memberships
    placement = "; ".join(
        f"{membership['programme_code']} Year {membership['year_of_study']} "
        f"{membership['requirement_type'].replace('_', ' ')}"
        for membership in selected_memberships
    )
    opening = (
        f"{module['course_code']} is {module['course_name']} "
        f"({module['nqf_credits']} NQF credits, approximately "
        f"{module['nqf_credits'] * 10} total notional learning hours). "
        f"It is taken as {placement}."
    )
    if not information["cbo_available"]:
        return (
            f"{opening} Verified lecturer and content details are unavailable. "
            f"{information['missing_reason']}"
        )

    coordinator = information.get("course_coordinator")
    coordinator_text = (
        f" Course coordinator: {coordinator}."
        if coordinator and coordinator != "Not explicitly designated"
        else " Course coordinator: not explicitly designated in the CBO."
    )
    verification_status = information.get("verification_status", "incomplete")
    if verification_status == "verified":
        source_text = f"Source: verified {information['academic_year']} CBO."
    else:
        source_text = (
            f"Source: {verification_status} {information['academic_year']} "
            "course-information evidence; a complete CBO is still required."
        )
    return (
        f"{opening} Academic staff/lecturer(s): {information['lecturer']}."
        f"{coordinator_text} Content covered: {information['scope']}"
        f" {source_text}"
    )


def _module_query_words(message: str) -> list[str]:
    """Content words left after removing question words and module-lookup filler."""

    return _normalise_name(message, remove_query_noise=True).split()


CLARIFICATION_STATUSES = frozenset({"clarification_required", "needs_clarification"})
_ALLOW_CLARIFICATION: ContextVar[bool] = ContextVar("allow_clarification", default=True)


def unresolved_without_clarification(intent: str) -> dict[str, Any]:
    """Final answer when clarification is disabled and the request cannot be determined."""

    return {
        "intent": intent,
        "status": "unresolved_without_clarification",
        "answer": "I could not determine what you meant, and clarification is disabled, so I cannot ask.",
        "conversation_context": ConversationContext().as_dict(),
    }
