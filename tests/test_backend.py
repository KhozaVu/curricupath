"""API tests for the deterministic backend contract."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient

from app.backend import CurricuPathService
from app.main import create_app


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REACT_SOURCE = PROJECT_ROOT / "frontend" / "src" / "App.jsx"


def _react_source() -> str:
    return REACT_SOURCE.read_text(encoding="utf-8")


class FakeRepository:
    backend_name = "fake"

    def is_healthy(self) -> bool:
        return True

    def get_aliases(self) -> tuple:
        return ()

    def list_programmes(self) -> list[dict[str, Any]]:
        return [{"programme_code": "EFA03", "programme_name": "Electrical Engineering"}]

    def list_modules(
        self, programme_code: str, year_of_study: int | None = None
    ) -> list[dict[str, Any]]:
        return [
            {
                "programme_code": programme_code,
                "course_code": "ELEN4001A",
                "year_of_study": year_of_study or 4,
            }
        ]

    def get_module(self, course_code: str) -> dict[str, Any] | None:
        if course_code != "ELEN4001A":
            return None
        return {"course_code": course_code, "course_name": "High Voltage Engineering"}

    def list_courses(
        self,
        category: str | None = None,
        interest: str | None = None,
        career: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        return [
            {
                "course_id": "CRS021",
                "category": category,
                "interest": interest,
                "career": career,
            }
        ][:limit]

    def eligibility_context(
        self, course_code: str
    ) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
        modules = [
            {
                "programme_code": "EFA03",
                "course_code": course_code,
                "source_id": "EBE_2026",
            }
        ]
        rules = [
            {
                "rule_id": "PRE_TEST",
                "scope": "EFA03",
                "rule_type": "prerequisite",
                "target_course_code": course_code,
                "condition_json": '{"all_of": ["ELEN3000A"]}',
                "source_id": "EBE_2026",
            }
        ]
        sources = [
            {
                "source_id": "EBE_2026",
                "title": "2026 EBE Handbook",
                "local_path": "data/raw/EBE_eBook.pdf",
                "url": "",
                "verification_status": "verified",
            }
        ]
        return modules, rules, sources


class FakeSemanticSearch:
    provider = SimpleNamespace(provider_name="huggingface", model_name="test-model")

    def search(self, query, *, item_type=None, limit=10):
        return [
            {
                "item_type": item_type or "public_course",
                "item_id": "CRS021",
                "similarity": 0.91,
            }
        ][:limit]

    def course_scores(self, query, course_ids):
        return {course_id: 0.91 for course_id in course_ids}


def _client() -> TestClient:
    service = CurricuPathService(FakeRepository(), str(PROJECT_ROOT))
    return TestClient(create_app(service))


def test_health_and_catalogue_endpoints() -> None:
    client = _client()

    page = client.get("/")
    assert page.status_code == 200
    assert 'id="root"' in page.text
    assert "CSV engine online" not in page.text
    assert 'type="module"' in page.text
    assert 'src="/assets/app.js?v=20260919-1"' in page.text
    assert client.get("/assets/app.js").status_code == 200
    assert client.get("/assets/app.css").status_code == 200
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/programmes").json()[0]["programme_code"] == "EFA03"
    assert client.get("/modules/ELEN4001A").status_code == 200
    assert client.get("/modules/UNKNOWN").status_code == 404


def test_advisor_rejects_out_of_scope_request_before_recommendation() -> None:
    response = _client().post(
        "/advisor",
        json={"message": "Predict my final engineering marks"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "out_of_scope"
    assert payload["scope"]["status"] == "out_of_scope"
    assert "recommendations" not in payload


def test_advisor_exposes_scope_and_deterministic_review_metadata() -> None:
    response = TestClient(create_app()).post(
        "/advisor",
        json={"message": "Tell me about ELEN2017A", "programme_code": "EFA04"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["scope"]["status"] == "supported"
    assert payload["review"]["status"] == "not_run"
    assert payload["review"]["invariants_passed"] is True


def test_react_renders_career_directions_separately_from_course_recommendations() -> None:
    script = _react_source()

    assert "data?.career_options" in script
    assert "function CareerOptions" in script


def test_advisor_script_has_dedicated_module_ambiguity_rendering() -> None:
    script = _react_source()

    assert 'data?.module_matches' in script
    assert '"Select this module"' in script
    assert 'String(value ?? "")' in script


def test_advisor_sidebar_can_be_retracted() -> None:
    script = _react_source()

    assert "curricupath-sidebar-collapsed" in script


def test_advisor_defaults_to_curricupath_after_system_preference_upgrade() -> None:
    script = _react_source()

    assert 'usePersistentString("curricupath-advisor-system-v2", "curricupath")' in script
    assert "function Sidebar" in script
    assert 'aria-label={collapsed ? "Expand navigation" : "Retract navigation"}' in script


def test_advisor_chat_renders_verified_module_staff_and_content() -> None:
    script = _react_source()

    assert "<ResultModuleCard item={data.module}" in script
    assert '<span><b>Lecturer</b>{info.lecturer' in script
    assert '<span><b>Content</b>{info.scope' in script


def test_module_detail_renders_plain_language_rules() -> None:
    script = _react_source()

    assert "rule.plain_language" in script
    assert "rule.condition_json" not in script
    assert 'handbook page ${rule.handbook_page}' in script


def test_module_endpoint_adds_programme_aware_plain_language_rules() -> None:
    response = TestClient(create_app()).get("/modules/ELEN4006A")

    assert response.status_code == 200
    rules = {rule["rule_id"]: rule for rule in response.json()["rules"]}
    assert rules["PRE_ELEN4006_EFA03"]["plain_language"] == (
        "For EFA03 students, before registering for this module, you must have "
        "completed all EFA03 Year 3 modules."
    )
    assert rules["PRE_ELEN4006_EFA04"]["plain_language"] == (
        "For EFA04 students, before registering for this module, you must have "
        "completed all EFA04 Year 3 modules."
    )


def test_advisor_guides_completion_selection_and_groups_curriculum_years() -> None:
    script = _react_source()

    assert "Modules are separated by year" in script
    assert 'className="year-group"' in script
    assert '[["completed", "Completed"], ["current", "Current"], ["planned", "Planned"]]' in script


def test_advisor_chat_is_revealed_after_curriculum_setup() -> None:
    script = _react_source()

    assert "Save profile and open advisor" in script
    assert 'destination === "advisor" && !ready ? "profile" : destination' in script
    assert 'page === "advisor" && ready && <AdvisorPage' in script
    assert 'setSavedProgramme(profile.programme)' in script


def test_achievements_and_visual_course_ratings_are_available() -> None:
    script = _react_source()

    assert '["achievements", Award, "Achievements"]' in script
    assert "function AchievementsPage" in script
    assert '"Fourth-year ready"' in script
    assert "function Stars" in script
    assert 'className="stars-fill"' in script


def test_course_filters_reach_the_service() -> None:
    response = _client().get(
        "/courses",
        params={"category": "electronics_control", "interest": "electric_circuits"},
    )

    assert response.status_code == 200
    assert response.json()[0] == {
        "course_id": "CRS021",
        "category": "electronics_control",
        "interest": "electric_circuits",
        "career": None,
    }


def test_semantic_search_endpoint_exposes_pgvector_results() -> None:
    service = CurricuPathService(FakeRepository(), str(PROJECT_ROOT))
    client = TestClient(create_app(service, semantic_search=FakeSemanticSearch()))

    response = client.post(
        "/search/semantic",
        json={"query": "electric circuits", "item_type": "public_course"},
    )

    assert response.status_code == 200
    assert response.json()["model"] == "test-model"
    assert response.json()["results"][0]["similarity"] == 0.91


def test_eligibility_endpoint_applies_prerequisite_gate() -> None:
    client = _client()
    missing = client.post(
        "/eligibility",
        json={"course_code": "ELEN4001A", "programme_code": "EFA03"},
    )
    satisfied = client.post(
        "/eligibility",
        json={
            "course_code": "ELEN4001A",
            "programme_code": "EFA03",
            "completed_modules": ["ELEN3000A"],
        },
    )

    assert missing.json()["eligible"] is False
    assert missing.json()["reasons"] == ["Prerequisite rule PRE_TEST is not satisfied."]
    assert missing.json()["requirements"]["prerequisites"] == [
        {
            "rule_id": "PRE_TEST",
            "description": "ELEN3000A",
            "satisfied": False,
            "source_id": "EBE_2026",
        }
    ]
    assert satisfied.json()["eligible"] is True


def test_eligibility_endpoint_marks_completed_module_separately() -> None:
    response = _client().post(
        "/eligibility",
        json={
            "course_code": "ELEN4001A",
            "programme_code": "EFA03",
            "completed_modules": ["ELEN4001A", "ELEN3000A"],
        },
    )

    assert response.status_code == 200
    assert response.json()["completed"] is True
    assert response.json()["available_to_take"] is False


def test_eligibility_endpoint_accepts_explicit_module_fact_states() -> None:
    response = _client().post(
        "/eligibility",
        json={
            "course_code": "ELEN4001A",
            "programme_code": "EFA03",
            "module_states": {"ELEN3000A": "unknown"},
            "module_history_confirmed": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "needs_clarification"
    assert payload["module_states"] == {"ELEN3000A": "unknown"}
    assert payload["module_history_confirmed"] is False
    assert payload["clarification"]["target_predicate"] == "ELEN3000A"
    assert payload["clarification"]["question"] == "Have you completed ELEN3000A?"
    assert payload["clarification"]["options"] == ["Completed", "Not completed"]


def test_react_profile_sends_history_confirmation_and_module_states() -> None:
    script = _react_source()

    assert "My module selections are complete" in script
    assert "module_history_confirmed: Boolean(profile.historyConfirmed)" in script
    assert "module_states: Object.fromEntries" in script


def test_recommendation_cards_render_completed_state_before_eligibility() -> None:
    script = _react_source()

    assert 'item.eligibility.completed ? "Completed"' in script
    assert 'className={item.eligibility.completed ? "eligibility-completed"' in script


def test_advisor_renders_completed_and_current_profile_course_groups() -> None:
    script = _react_source()

    assert 'title="Completed modules"' in script
    assert 'title="Currently taking"' in script
    assert "data.profile_courses.completed" in script
    assert "data.profile_courses.current" in script


def test_advisor_renders_source_backed_programme_profiles() -> None:
    script = _react_source()

    assert "function ProgrammeProfileCard" in script
    assert "Career opportunities" in script
    assert "View official Wits programme page" in script


def test_advisor_renders_programme_comparison_profiles() -> None:
    script = _react_source()

    assert "data.programme_comparison.profiles.map" in script
    assert "Closer fit for the stated interest" in script


def test_real_csv_advisor_endpoint_rejects_wrong_programme() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/advisor",
        json={"message": "Can I take ELEN4001A in EFA04?"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "not_eligible"
    assert response.json()["decision"] == "ineligible"
    assert response.json()["manual_review_required"] is False
    assert response.json()["reasons"] == [
        "ELEN4001A is not part of programme EFA04."
    ]


def test_module_endpoint_accepts_code_without_optional_suffix() -> None:
    response = TestClient(create_app()).get("/modules/ELEN2017")

    assert response.status_code == 200
    assert response.json()["course_code"] == "ELEN2017A"


def test_module_endpoint_accepts_lowercase_code() -> None:
    response = TestClient(create_app()).get("/modules/elen2017")

    assert response.status_code == 200
    assert response.json()["course_code"] == "ELEN2017A"


def test_advisor_session_keeps_clarification_context() -> None:
    client = TestClient(create_app())

    first = client.post("/advisor", json={"message": "module eligibility"}).json()
    second = client.post(
        "/advisor",
        json={"message": "ELEN4001A", "session_id": first["session_id"]},
    ).json()
    third = client.post(
        "/advisor",
        json={"message": "EFA04", "session_id": first["session_id"]},
    ).json()

    assert first["clarification_question"] == (
        "Which module code or full module name should I check?"
    )
    assert second["clarification_question"] == "Which programme are you in: EFA03 or EFA04?"
    assert third["status"] == "not_eligible"


def test_advisor_session_reuses_one_eligibility_fact() -> None:
    client = TestClient(create_app())

    first = client.post(
        "/advisor",
        json={
            "message": "Can I take MATH1049A in EFA04?",
            "module_history_confirmed": False,
        },
    ).json()
    second = client.post(
        "/advisor",
        json={
            "message": "Completed",
            "session_id": first["session_id"],
            "module_history_confirmed": False,
        },
    ).json()

    assert first["clarification_question"] == "Have you completed MATH1048A?"
    assert second["status"] == "ok"
    assert second["decision"] == "eligible"
    assert second["clarification_applied"] == {
        "course_code": "MATH1048A",
        "state": "completed",
        "gate": "prerequisite",
    }


def test_csv_discovery_endpoints_are_populated() -> None:
    client = TestClient(create_app())

    summary = client.get("/catalogue/summary").json()
    assert summary["recommendable_courses"] >= 20
    assert summary["public_course_ranking_mode"] == "deterministic"
    assert summary["external_references"] == 17
    assert client.get("/career-paths").json()
    evidence = client.get("/evidence").json()
    assert evidence["sources"]
    assert evidence["external_references"]
    assert evidence["missing_cbos"]
    assert evidence["orphan_cbos"][0]["course_code"] == "ELEN3020A"
    assert client.get("/cbos/missing").json()
    assert client.get("/courses/CRS001").json()["source"]["verification_status"] == "verified"


class FakeHandbookRagDemo:
    def answer(self, message, programme_code, completed_modules, current_modules, planned_modules):
        return {
            "system": "handbook_rag",
            "status": "valid",
            "decision": "eligible",
            "answer": "Fake baseline answer.",
            "citations": [{"source_id": "EBE_2026", "page": "printed page 56"}],
        }


class _ExplodingSessionStore:
    def load(self, session_id):
        raise AssertionError("session_store must not be used for the handbook_rag demo path")

    def save(self, session_id, context):
        raise AssertionError("session_store must not be used for the handbook_rag demo path")

    def clear(self, session_id):
        raise AssertionError("session_store must not be used for the handbook_rag demo path")


class _ExplodingRecommendationLogger:
    def log(self, session_id, result, candidates):
        raise AssertionError(
            "recommendation_logger must not be used for the handbook_rag demo path"
        )


def test_advisor_handbook_rag_system_returns_503_when_not_configured(monkeypatch) -> None:
    monkeypatch.setenv("HANDBOOK_RAG_DEMO_ENABLED", "false")
    response = _client().post(
        "/advisor",
        json={"message": "Can I take ELEN2017A?", "system": "handbook_rag"},
    )

    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


def test_advisor_handbook_rag_system_bypasses_session_and_recommendation_logging() -> None:
    service = CurricuPathService(FakeRepository(), str(PROJECT_ROOT))
    client = TestClient(
        create_app(
            service,
            session_store=_ExplodingSessionStore(),
            recommendation_logger=_ExplodingRecommendationLogger(),
            handbook_rag_demo=FakeHandbookRagDemo(),
        )
    )

    response = client.post(
        "/advisor",
        json={"message": "Can I take ELEN2017A?", "system": "handbook_rag"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["system"] == "handbook_rag"
    assert payload["decision"] == "eligible"
    assert payload["citations"] == [{"source_id": "EBE_2026", "page": "printed page 56"}]
    assert "recommendations" not in payload
    assert "run_id" not in payload
    assert payload["session_id"] == "baseline-demo"


def test_catalogue_summary_reports_handbook_rag_demo_availability(monkeypatch) -> None:
    monkeypatch.setenv("HANDBOOK_RAG_DEMO_ENABLED", "false")
    disabled = TestClient(create_app()).get("/catalogue/summary").json()
    assert disabled["handbook_rag_demo_enabled"] is False

    enabled = TestClient(
        create_app(handbook_rag_demo=FakeHandbookRagDemo())
    ).get("/catalogue/summary").json()
    assert enabled["handbook_rag_demo_enabled"] is True
