"""Build the clarification test set (v2 draft) from the rule data.

Every 'ask' case is a student whose status for one or more modules is UNKNOWN (module history
unconfirmed), so a correct system must ask before it can decide. A scripted reply then supplies
the missing fact(s). Each ask case has a matched 'control' (same student, same fact already
known, so no question is needed) and some 'irrelevant' controls (an unrelated module is unknown;
no question is needed).

Reference labels are the logical consequence of the stated fact and one cited rule
(for example: the only unknown prerequisite is completed -> eligible; not completed ->
ineligible). They are DEVELOPER-PROPOSED and pending academic review; they are not independent
evidence. The engine is used only as a construction filter: a case is kept only if (a) with the
fact known the decision flips cleanly as the label logic says, and (b) with the fact unknown the
engine asks about exactly the intended module(s).
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
OUT = PROJECT_ROOT / "experiments" / "evaluation" / "clarification_set_v2"

from app.advisor.engine import AdvisorEngine
from app.advisor.intent import DeterministicIntentExtractor
from scripts.run_test_set_v1 import curricupath_components

QUESTION = "Can I take {target} in programme {programme}?"


def simple_all_of(condition):
    if isinstance(condition, dict) and set(condition) == {"all_of"} and all(
        isinstance(x, str) for x in condition["all_of"]
    ):
        return list(condition["all_of"])
    return None


def load_rules(service):
    rows = list(csv.DictReader((PROJECT_ROOT / "data/processed/rules.csv").open(encoding="utf-8")))
    table = {}
    for r in rows:
        if r["rule_type"] not in {"prerequisite", "corequisite"}:
            continue
        try:
            items = simple_all_of(json.loads(r["condition_json"]))
        except Exception:
            items = None
        if items:
            table.setdefault((r["target_course_code"], r["rule_type"]), []).append((r["scope"], items, r["rule_id"]))
    return table


def applies(scope, programme):
    return scope in {"ALL", "ALL_EFA03_EFA04"} or programme in scope.split("|")


class Builder:
    def __init__(self):
        self.service, self.app = curricupath_components()
        self.engine = AdvisorEngine(
            self.service, DeterministicIntentExtractor(self.service.repository.get_aliases())
        )
        self.rules = load_rules(self.service)
        self.cases: list[dict] = []
        self.n = 0

    # -- engine used only as a construction filter ----------------------------------------
    def full_info(self, target, programme, completed, current, planned, states, repeating=()):
        r = self.service.eligibility(
            target, programme, set(completed), set(current), set(planned), (), dict(states),
            True, repeating_modules=set(repeating),
        )
        return r["decision"]

    def first_question(self, target, programme, completed, current, planned, repeating=()):
        r = self.engine.advise(
            QUESTION.format(target=target, programme=programme), programme,
            set(completed), set(current), set(planned), module_history_confirmed=False,
            repeating_modules=set(repeating),
        )
        ctx = r.get("conversation_context") or {}
        return r.get("status"), ctx.get("pending_fact_gate"), list(ctx.get("pending_fact_course_codes") or [])

    # -- case records -----------------------------------------------------------------------
    def add(self, pair, kind, fact_type, target, programme, profile, unknown, reply, style, label,
            citation, expected_questions):
        self.n += 1
        self.cases.append({
            "case_id": f"CL{self.n:03d}",
            "pair_id": pair,
            "kind": kind,
            "fact_type": fact_type,
            "question": QUESTION.format(target=target, programme=programme),
            "target_course_code": target,
            "programme_code": programme,
            "student_profile_json": json.dumps(profile, sort_keys=True),
            "unknown_modules": ";".join(unknown),
            "scripted_reply": reply,
            "reply_style": style,
            "expected_questions": expected_questions,
            "reference_label": label,
            "label_basis": "logical consequence of the stated fact and the cited rule; developer-proposed",
            "rule_citation": citation,
            "approval_state": "developer_proposed_pending_review",
            "reviewer_ids": "",
        })

    def profile(self, completed, current=(), planned=(), repeating=(), states=None, confirmed=False):
        return {"completed_modules": sorted(completed), "current_modules": sorted(current),
                "planned_modules": sorted(planned), "repeating_modules": sorted(repeating),
                "module_states": dict(states or {}), "module_history_confirmed": confirmed}

    def pair(self, fact_type, target, programme, base_completed, unknown, replies, citation,
             base_current=(), base_planned=(), repeating=(), irrelevant_unknown=None):
        """replies: list of (reply_text, style, {module: state}, label)."""

        for idx, (reply, style, facts, label) in enumerate(replies):
            pair_id = f"{fact_type}-{target}-{programme}-{idx + 1}"
            completed = set(base_completed) | {m for m, s in facts.items() if s == "completed"}
            current = set(base_current) | {m for m, s in facts.items() if s == "current"}
            planned = set(base_planned) | {m for m, s in facts.items() if s == "planned"}
            states = {m: s for m, s in facts.items() if m not in unknown or True}
            if fact_type == "clash":
                rep = set(repeating) | {m for m, s in facts.items() if s == "repeating"}
                known_states = {m: s for m, s in facts.items() if s in {"completed", "current", "planned", "not_completed"}}
                decision = self.full_info(target, programme, completed, current, planned, known_states, rep)
            else:
                rep = set(repeating)
                decision = self.full_info(target, programme, completed, current, planned, states)
            if decision != label:
                return False  # fact does not flip the decision cleanly; skip this target
        asks = []
        for idx, (reply, style, facts, label) in enumerate(replies):
            pair_id = f"{fact_type}-{target}-{programme}-{idx + 1}"
            ask_profile = self.profile(base_completed, base_current, base_planned, repeating)
            status, gate, codes = self.first_question(target, programme, base_completed, base_current, base_planned, repeating)
            if status != "clarification_required" or sorted(codes) != sorted(unknown):
                return False
            asks.append((pair_id, ask_profile, reply, style, facts, label))
        for pair_id, ask_profile, reply, style, facts, label in asks:
            self.add(pair_id, "ask", fact_type, target, programme, ask_profile, unknown, reply, style,
                     label, citation, 1)
            known_completed = set(base_completed) | {m for m, s in facts.items() if s == "completed"}
            known_current = set(base_current) | {m for m, s in facts.items() if s == "current"}
            known_planned = set(base_planned) | {m for m, s in facts.items() if s == "planned"}
            known_rep = set(repeating) | {m for m, s in facts.items() if s == "repeating"}
            states = {m: s for m, s in facts.items() if s in {"completed", "current", "planned", "not_completed"}}
            for m, s in facts.items():
                if s == "none":
                    states[m] = "not_completed"
            control_profile = self.profile(known_completed, known_current, known_planned, known_rep,
                                           states, confirmed=False)
            self.add(pair_id, "control", fact_type, target, programme, control_profile, [], "", "",
                     label, citation, 0)
        return True


def main() -> None:
    if (OUT / "clarification_set_v2.csv").exists():
        raise SystemExit("clarification_set_v2.csv already exists; it is frozen. Make a v3 instead.")
    b = Builder()
    rules = b.rules
    programmes = ("EFA03", "EFA04")
    made = {"prereq_single": 0, "prereq_multi": 0, "coreq": 0, "clash": 0}

    def rule_lists(target, kind, programme):
        out = []
        for scope, items, rid in rules.get((target, kind), []):
            if applies(scope, programme):
                out.append((items, rid))
        return out

    modules = {p: sorted(m["course_code"] for m in b.service.repository.list_modules(p)) for p in programmes}
    styles = ["button", "sentence", "named"]

    # Type A: one unknown prerequisite
    for programme in programmes:
        for target in modules[programme]:
            if made["prereq_single"] >= 12:
                break
            pre = rule_lists(target, "prerequisite", programme)
            co = rule_lists(target, "corequisite", programme)
            if len(pre) != 1 or len(pre[0][0]) < 1:
                continue
            prereqs, rid = pre[0]
            coreqs = co[0][0] if co else []
            unknown = prereqs[0]
            base = (set(prereqs) - {unknown}) | set(coreqs)
            style = styles[made["prereq_single"] % 3]
            say = {"button": ("Completed", "Not completed"),
                   "sentence": ("I have completed it", "I have not completed it"),
                   "named": (f"I have completed {unknown}", f"{unknown} not completed")}[style]
            ok = b.pair("prereq_single", target, programme, base, [unknown],
                        [(say[0], style, {unknown: "completed"}, "eligible"),
                         (say[1], style, {unknown: "not_completed"}, "ineligible")],
                        f"{rid}: {unknown} must be completed before {target}")
            if ok:
                made["prereq_single"] += 2

    # Type B: two unknown prerequisites, one grouped reply
    for programme in programmes:
        for target in modules[programme]:
            if made["prereq_multi"] >= 6:
                break
            pre = rule_lists(target, "prerequisite", programme)
            co = rule_lists(target, "corequisite", programme)
            if len(pre) != 1 or len(pre[0][0]) < 3:
                continue
            prereqs, rid = pre[0]
            coreqs = co[0][0] if co else []
            u1, u2 = prereqs[0], prereqs[1]
            base = (set(prereqs) - {u1, u2}) | set(coreqs)
            ok = b.pair("prereq_multi", target, programme, base, [u1, u2],
                        [("All completed", "button", {u1: "completed", u2: "completed"}, "eligible"),
                         (f"{u1} completed, {u2} not completed", "named", {u1: "completed", u2: "not_completed"}, "ineligible"),
                         (f"{u1} is completed the rest are not", "grouped", {u1: "completed", u2: "not_completed"}, "ineligible")],
                        f"{rid}: {u1} and {u2} must both be completed before {target}")
            if ok:
                made["prereq_multi"] += 3

    # Type C: one unknown corequisite
    for programme in programmes:
        for target in modules[programme]:
            if made["coreq"] >= 9:
                break
            pre = rule_lists(target, "prerequisite", programme)
            co = rule_lists(target, "corequisite", programme)
            if len(co) != 1 or len(co[0][0]) != 1:
                continue
            coreqs, rid = co[0]
            unknown = coreqs[0]
            base = set(pre[0][0]) if pre else set()
            ok = b.pair("coreq", target, programme, base, [unknown],
                        [("Planned concurrently", "button", {unknown: "planned"}, "eligible"),
                         ("Currently taking it", "sentence", {unknown: "current"}, "eligible"),
                         ("Not completed", "button", {unknown: "not_completed"}, "ineligible")],
                        f"{rid}: {unknown} must be completed, current or planned with {target}")
            if ok:
                made["coreq"] += 3

    # Type D: timetable clash with a module whose status is unknown
    clash = list(csv.DictReader((PROJECT_ROOT / "data/rules/grid_clash_rules.csv").open(encoding="utf-8")))
    for r in clash:
        if made["clash"] >= 6:
            break
        programme = r["scope"].split("|")[0]
        if programme not in programmes:
            continue
        target, partner = r["target_course_code"], r["repeating_course"]
        if target not in modules[programme] or partner not in modules[programme]:
            continue
        pre = rule_lists(target, "prerequisite", programme)
        co = rule_lists(target, "corequisite", programme)
        base = set(pre[0][0]) if pre else set()
        base |= set(co[0][0]) if co else set()
        base.discard(partner)
        ok = b.pair("clash", target, programme, base, [partner],
                    [("Repeating", "button", {partner: "repeating"}, "ineligible"),
                     ("None of these", "button", {partner: "none"}, "eligible")],
                    f"{r['rule_id']}: {target} clashes with {partner} (School registration reference)")
        if ok:
            made["clash"] += 2

    # Irrelevant-unknown controls: everything relevant is known; an unrelated module is not.
    extra = 0
    for programme in programmes:
        for target in modules[programme]:
            if extra >= 6:
                break
            pre = rule_lists(target, "prerequisite", programme)
            co = rule_lists(target, "corequisite", programme)
            if len(pre) != 1 or not pre[0][0]:
                continue
            known = set(pre[0][0]) | (set(co[0][0]) if co else set())
            if b.full_info(target, programme, known, [], [], {}) != "eligible":
                continue
            status, gate, codes = b.first_question(target, programme, known, (), ())
            if status == "clarification_required":
                continue
            states = {m: "completed" for m in known}
            profile = b.profile(known, states=states, confirmed=False)
            b.add(f"irrelevant-{target}-{programme}", "irrelevant", "none_needed", target, programme,
                  profile, [], "", "", "eligible",
                  f"{pre[0][1]}: all stated requirements are completed; other modules are unknown but not required", 0)
            extra += 1

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "clarification_set_v2.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(b.cases[0]))
        writer.writeheader()
        writer.writerows(b.cases)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    kinds = {k: sum(c["kind"] == k for c in b.cases) for k in ("ask", "control", "irrelevant")}
    types = {t: sum(c["fact_type"] == t and c["kind"] == "ask" for c in b.cases) for t in made}
    labels = {l: sum(c["reference_label"] == l for c in b.cases) for l in ("eligible", "ineligible")}
    (OUT / "freeze.json").write_text(json.dumps({
        "file": path.name, "sha256": digest, "cases": len(b.cases), "kinds": kinds,
        "ask_cases_by_fact_type": types, "labels": labels,
        "label_status": "developer-proposed, pending academic review; NOT independent evidence",
        "rule": "Frozen at creation. Do not edit; make a v3 and a deviations entry instead.",
    }, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"cases": len(b.cases), "kinds": kinds, "ask_by_type": types, "labels": labels,
                      "sha256": digest[:16]}, indent=2))


if __name__ == "__main__":
    main()
