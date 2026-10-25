"""Personalised Wits module lists using the same gates as single-module checks."""
from __future__ import annotations

from typing import Any

from app.advisor.module_matching import score_module_relevance, MODULE_MATCH_TERMS, MODULE_RELATED_TERMS, _contains_phrase
from app.advisor.normalisation import normalise_text
from app.data.sessions import ConversationContext


def module_options(service, parsed, programme, completed, current, planned, *,
                   module_states=None, module_history_confirmed=None,
                   repeating_modules=None, manual_review_reasons=()):
    """Keep relevance and eligibility separate; never infer missing history."""
    module_history_confirmed = module_history_confirmed is True
    year = parsed.year_of_study or (4 if parsed.requirement_type == "elective_pool" else None)
    tags = list(dict.fromkeys([*parsed.interests, *parsed.career_preferences]))
    rows = service.modules(programme, year)
    if parsed.include_electives and year != 4:
        rows += [r for r in service.modules(programme, 4) if r["requirement_type"] == "elective_pool"]
    if parsed.requirement_type:
        rows = [r for r in rows if r["requirement_type"] == parsed.requirement_type]
    candidates = []
    for row in rows:
        code = row["course_code"]
        detail = service.module(code)
        if not detail:
            continue
        assessment = service.eligibility(
            code, programme, completed, current, planned,
            module_states=module_states,
            module_history_confirmed=module_history_confirmed,
            repeating_modules=repeating_modules or set(),
            manual_review_reasons=manual_review_reasons,
        )
        relevance = score_module_relevance(tags, detail)
        matched = relevance["matched_tags"]
        text = normalise_text(detail["course_name"] + " " + (detail["course_information"].get("scope") or ""))
        terms = list(dict.fromkeys(term for tag in matched for term in (tag.replace("_", " "), *MODULE_MATCH_TERMS.get(tag, ()), *MODULE_RELATED_TERMS.get(tag, ())) if _contains_phrase(text, term)))
        reason = (
            "Covers " + ", ".join(terms[:2]) + ", relevant to your interest in " + ", ".join(tag.replace("_", " ") for tag in matched) + "."
            if terms else "Recorded module content or reading relates to " + ", ".join(tag.replace("_", " ") for tag in matched) + "."
            if matched else "Listed in your Wits programme curriculum."
        )
        candidates.append({
            **row, **relevance,
            "course_information": detail["course_information"],
            "sources": detail.get("sources", []),
            "reasons": [reason],
            "eligibility": {"assessed": True, **assessment},
        })
    eligible = [r for r in candidates if r["eligibility"]["available_to_take"] and r["course_code"] not in current]
    unresolved = [r for r in candidates if r["eligibility"]["decision"] in {"needs_clarification", "manual_review_required"} and not r["eligibility"]["completed"] and r["course_code"] not in current]
    blocked = [r for r in candidates if r not in eligible and r not in unresolved]
    recommending = parsed.intent == "module_recommendations" or bool(tags)
    sort = lambda r: (-r["score"], r["year_of_study"], r["course_code"])
    blocked.sort(key=sort)
    eligible.sort(key=sort)
    unresolved.sort(key=sort)
    matches = [r for r in eligible if r["score"] > 0] if recommending else eligible
    possible = [r for r in unresolved if r["score"] > 0] if recommending else unresolved
    if recommending:
        matches = matches[:3]
        possible = possible[:3]
    future = [r for r in blocked if r["score"] > 0 and not r["eligibility"]["completed"] and r["course_code"] not in current][:3] if recommending else []
    noun = "electives" if parsed.requirement_type == "elective_pool" else "modules"
    scope = f"{rows[0].get('programme_name', programme)} ({programme})" if rows else programme
    scope += (f" Year {year}" if year else "") + (" and fourth-year electives" if parsed.include_electives else "")
    if matches:
        answer = f"For {scope}, " + ("these Wits modules match your interests and pass the recorded eligibility checks: " if recommending else f"you are eligible for these {noun}: ")
        answer += "; ".join(f"{r['course_code']} {r['course_name']}" for r in matches) + "."
    else:
        answer = f"For {scope}, no " + ("interest-matching " if recommending else "") + f"{noun} can currently be confirmed eligible from your declared history."
    if possible:
        if recommending:
            answer += " Interest matches to check: " + "; ".join(f"{r['course_code']} {r['course_name']}" for r in possible) + "."
        answer += f" {len(possible)} " + ("matching options need" if recommending else "other options need") + " missing module facts or academic review; they are listed separately."
    if future:
        answer += " Future interest matches: " + "; ".join(f"{r['course_code']} {r['course_name']}" for r in future) + ". These have unmet requirements and are not eligible choices yet."
    if recommending and not tags:
        answer += " Tell me what interests you (for example software, power systems or machine learning) so I can rank the Wits options."
    answer += " Each module shows its reason and requirement status."
    visible = matches + possible + future
    citations = list({(r.get("source_id"), str(r.get("handbook_page") or "")): {"source_id":r.get("source_id"), "page":str(r.get("handbook_page") or "")} for r in visible if r.get("source_id")}.values())
    return {
        "citations": citations,
        "intent": parsed.intent, "status": "ok", "answer": answer,
        **({"recommendations": matches} if recommending else {"modules": matches}),
        "unresolved_modules": possible,
        "other_modules": [r for r in blocked if r not in future],
        "interest_matches": future,
        "eligibility_summary": {"checked": len(candidates), "eligible": len(eligible), "needs_information_or_review": len(unresolved), "other": len(blocked)},
        "programme_code": programme, "year_of_study": year,
        "requirement_type": parsed.requirement_type,
        "recommendation_kind": "eligible_wits_modules" if recommending else None,
        "_candidate_log": [{"item_type":"module", "item_id":r["course_code"], "eligible":bool(r["eligibility"]["available_to_take"]), "selected":r in matches, "score":r["score"], "gate_outcomes":r["eligibility"]} for r in candidates],
        "conversation_context": ConversationContext().as_dict(),
    }
