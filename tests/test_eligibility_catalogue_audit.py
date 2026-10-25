"""Catalogue-wide truth-table checks and regressions for missing Faculty rules."""
import csv
import itertools
import json
from pathlib import Path

import pytest

from app.advisor.eligibility import (
    StudentProfile, check_prerequisites, check_corequisites,
    load_grid_requirement_rules, programme_year_course_map,
)
from app.backend import CurricuPathService
from app.data.repository import CsvCatalogueRepository

ROOT = Path(__file__).resolve().parents[1]

def rows(name):
    with (ROOT / 'data/processed' / name).open(encoding='utf8', newline='') as f:
        return list(csv.DictReader(f))

MODULES = rows('modules.csv')
YEAR_MAP = programme_year_course_map(MODULES)
RULES = [r for r in rows('rules.csv') if r['rule_type'] in {'prerequisite', 'corequisite'}]
GRID = [r for r in load_grid_requirement_rules(ROOT / 'data/rules/grid_rules.json') if r['has_requirement'] == 'true']

def expand(condition):
    if isinstance(condition, str):
        return condition
    if 'all_courses_in_programme_year' in condition:
        q = condition['all_courses_in_programme_year']
        return {'all_of': sorted(YEAR_MAP[(q['programme'], q['year'])])}
    return {key: [expand(c) for c in value] for key, value in condition.items()}

def atoms(condition):
    if isinstance(condition, str):
        return {condition}
    return set().union(*(atoms(c) for children in condition.values() for c in children))

def truth(condition, facts, allowed):
    # Independent three-valued reference: unknown can resolve to either truth value.
    if isinstance(condition, str):
        return {True, False} if facts[condition] == 'unknown' else {facts[condition] in allowed}
    key, children = next(iter(condition.items()))
    operation = all if key == 'all_of' else any
    return {operation(values) for values in itertools.product(*(truth(c, facts, allowed) for c in children))}

CASES = []
for source, rules in [('faculty', RULES), ('school', GRID)]:
    for rule in rules:
        condition = expand(json.loads(rule['condition_json']))
        codes = sorted(atoms(condition))
        # All-pass plus every individual fact changed to each supported state.
        profiles = [{'completed': codes}]
        for code in codes:
            for state in ['not_completed', 'current', 'planned', 'unknown']:
                profiles.append({c: state if c == code else 'completed' for c in codes})
        profiles[0] = dict.fromkeys(codes, 'completed')
        for state in ['not_completed', 'current', 'planned', 'unknown']:
            profiles.append(dict.fromkeys(codes, state))
        for code in codes:
            profiles.append({c: 'completed' if c == code else 'not_completed' for c in codes})
        for index, facts in enumerate(profiles):
            CASES.append(pytest.param(rule, condition, facts, id=f'{source}-{rule["rule_id"]}-{index}'))

@pytest.mark.parametrize('rule,condition,facts', CASES)
def test_every_recorded_requirement_against_reference(rule, condition, facts):
    profile = StudentProfile('EFA03', frozenset(), frozenset(), frozenset(), module_states=facts)
    function = check_prerequisites if rule['rule_type'] == 'prerequisite' else check_corequisites
    allowed = {'completed'} if rule['rule_type'] == 'prerequisite' else {'completed', 'current', 'planned'}
    # Isolate the rule's predicate from programme scoping, which has its own tests.
    isolated = dict(rule, scope='ALL', condition_json=json.dumps(condition))
    result = function(rule['target_course_code'], profile, [isolated], YEAR_MAP)
    expected = truth(condition, facts, allowed)
    assert result.decision == ({True: 'eligible', False: 'ineligible'}[next(iter(expected))] if len(expected) == 1 else 'needs_clarification')

@pytest.mark.parametrize('programme', ['EFA03', 'EFA04'])
@pytest.mark.parametrize('a,b', [('MATH1048A','MATH1049A'), ('MATH1042A','MATH1043A'), ('MATH1048A','MATH1043A'), ('MATH1042A','MATH1049A')])
@pytest.mark.parametrize('state,decision', [('completed','eligible'), ('not_completed','ineligible'), ('current','ineligible'), ('planned','ineligible'), ('unknown','needs_clarification')])
def test_math_ii_requires_both_first_year_passes(programme, a, b, state, decision):
    service = CurricuPathService(CsvCatalogueRepository(ROOT / 'data/processed'), str(ROOT))
    result = service.eligibility('MATH2014A', programme, set(), set(), set(),
        module_states={a:'completed', b:state}, module_history_confirmed=True)
    assert result['decision'] == decision
    assert any(r['rule_id'] == 'PRE_MATH2014' for r in result['rules'])

def test_grid_override_source_is_checked_before_using_its_rules():
    from app.advisor.eligibility import check_eligibility
    sources = [dict(s, verification_status='unverified') if s['source_id'] == 'EIE_REG_GRID_2026' else s for s in rows('sources.csv')]
    result = check_eligibility('MATH2014A', StudentProfile('EFA03', frozenset({'MATH1042A','MATH1043A'}), frozenset(), frozenset()), MODULES, rows('rules.csv'), sources, ROOT,
        grid_requirement_rules=GRID, enable_school_grid_requirements=True)
    assert result.decision == 'manual_review_required'
    assert any('EIE_REG_GRID_2026' in issue for issue in result.evidence_issues)
