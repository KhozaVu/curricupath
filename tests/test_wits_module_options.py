from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.advisor.engine import AdvisorEngine
from app.advisor.intent import DeterministicIntentExtractor
from app.backend import CurricuPathService
from app.data.repository import CsvCatalogueRepository
from app.data.sessions import ConversationContext
from app.main import create_app

ROOT=Path(__file__).resolve().parents[1]
@pytest.fixture
def engine():
    repo=CsvCatalogueRepository(ROOT/'data/processed')
    return AdvisorEngine(CurricuPathService(repo,str(ROOT),school_grid_requirements_enabled=True,timetable_clash_gate_enabled=True),DeterministicIntentExtractor(repo.get_aliases()))

@pytest.mark.parametrize('question,year,kind',[
    ('Which third year modules am I eligible for?',3,None),
    ('Which 3rd-year courses can I register for?',3,None),
    ('What electives can I take?',None,'elective_pool'),
    ('List eligible EFA04 year 4 electives',4,'elective_pool'),
])
def test_plural_eligibility_is_a_list(engine,question,year,kind):
    parsed=engine.extractor.extract(question)
    assert parsed.intent=='eligible_modules'
    assert parsed.year_of_study==year
    assert parsed.requirement_type==kind

@pytest.mark.parametrize('programme',['EFA03','EFA04'])
def test_bulk_eligibility_matches_each_individual_gate(engine,programme):
    completed={r['course_code'] for r in engine.service.modules(programme,None) if r['year_of_study']<=2}
    result=engine.advise('Which third year modules am I eligible for?',programme,completed,module_history_confirmed=True)
    expected={r['course_code'] for r in engine.service.modules(programme,3) if engine.service.eligibility(r['course_code'],programme,completed,set(),set(),module_history_confirmed=True)['available_to_take']}
    assert {r['course_code'] for r in result['modules']}==expected
    assert result['eligibility_summary']['checked']==len(engine.service.modules(programme,3))
    assert all(r['year_of_study']==3 and r['eligibility']['assessed'] for r in result['modules'])
    assert result['eligibility_summary']['checked']==sum(result['eligibility_summary'][k] for k in ['eligible','needs_information_or_review','other'])

def test_unknown_history_stays_unresolved(engine):
    result=engine.advise('Which third year modules am I eligible for?','EFA04',module_history_confirmed=False)
    assert result['unresolved_modules']
    assert all(r['eligibility']['available_to_take'] for r in result['modules'])
    assert all(not r['eligibility']['available_to_take'] for r in result['unresolved_modules'])

def test_asking_for_year_and_electives_checks_both(engine):
    result=engine.advise('Which third year modules and electives can I take?','EFA04',module_history_confirmed=False)
    expected=len(engine.service.modules('EFA04',3))+len([r for r in engine.service.modules('EFA04',4) if r['requirement_type']=='elective_pool'])
    assert result['eligibility_summary']['checked']==expected

def test_wits_interest_reasons_and_future_matches(engine,monkeypatch):
    monkeypatch.setattr(engine.service,'courses',lambda *a:pytest.fail('Public catalogue was queried'))
    result=engine.advise('Recommend Wits electives for machine learning','EFA04',module_history_confirmed=True)
    rows=result.get('recommendations',[])+result['interest_matches']+result['unresolved_modules']
    assert rows
    assert all(r['course_code'] and 'course_id' not in r and r['reasons'] and r['matched_tags'] for r in rows)
    assert all(r['eligibility']['available_to_take'] for r in result.get('recommendations',[]))
    assert all(not r['eligibility']['available_to_take'] for r in result['interest_matches'])

def test_recommendations_honour_review_requirement(engine):
    completed={r['course_code'] for r in engine.service.modules('EFA04',None) if r['year_of_study']<4}
    result=engine.advise('Recommend electives for machine learning','EFA04',completed,module_history_confirmed=True,manual_review_reasons=('I have a concession requiring review',))
    assert not result['recommendations']
    assert all(not r['eligibility']['available_to_take'] for r in result['unresolved_modules'])

def test_missing_programme_keeps_bulk_request(engine):
    first=engine.advise('Which third year modules am I eligible for?')
    assert first['status']=='clarification_required'
    reply=engine.advise('EFA04',context=ConversationContext(**first['conversation_context']))
    assert reply['intent']=='eligible_modules' and reply['year_of_study']==3

def test_single_named_module_still_uses_single_check(engine):
    assert engine.extractor.extract('Can I take Control II?').intent=='eligibility'
    assert engine.advise('Tell me about Control II','EFA04')['intent']=='module_information'

def test_api_removes_public_features_and_uses_profile_interests(engine):
    with TestClient(create_app(service=engine.service,advisor_engine=engine)) as client:
        assert all(client.get(path).status_code==404 for path in ['/courses','/courses/COUR001','/career-paths'])
        summary=client.get('/catalogue/summary').json()
        assert 'recommendable_courses' not in summary and 'public_course_ranking_mode' not in summary
        evidence=client.get('/evidence').json()
        assert not any(s['document_type']=='public_course_provider' for s in evidence['sources'])
        result=client.post('/advisor',json={'message':'Recommend Wits electives for my interests','programme_code':'EFA04','interests':['machine_learning'],'module_history_confirmed':False}).json()
        assert result['status']=='ok'
        assert result['unresolved_modules']
        assert result['review']['invariants_passed']
        assert 'public_course' not in str(result)


@pytest.mark.parametrize('message',[
    'Which EE electives fit my interest in renewable energy? Give brief reasons.',
    'Which modules suit my interest in software?',
    'I like software and intelligent systems',
])
def test_interest_wording_does_not_turn_into_a_single_title_lookup(engine,message):
    result=engine.advise(message,'EFA03',module_history_confirmed=False)
    assert result['intent']=='module_recommendations'
    assert 'module' not in result
    assert result['unresolved_modules'] or result['recommendations'] or result['interest_matches']
