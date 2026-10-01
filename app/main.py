"""FastAPI entry point for the deterministic CurricuPath backend."""

from __future__ import annotations

import json
import warnings
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.advisor.baseline_demo import HandbookRagDemo
from app.advisor.eligibility import ModuleFactState
from app.advisor.engine import AdvisorEngine, unresolved_without_clarification
from app.advisor.interpretation_fallback import (
    ClaudeInterpreter,
    GeminiInterpreter,
    InterpretationFallback,
    capped_fallback_mode,
    is_new_programme_question,
    needs_fallback,
)
from app.advisor.intent import build_intent_extractor
from app.advisor.intent import DeterministicIntentExtractor
from app.advisor.reviewer import (
    GeminiResponseReviewer,
    ResponseReviewer,
    ReviewCoordinator,
)
from app.advisor.scope import classify_scope, is_prohibited, out_of_scope_response
from app.advisor.ranking import PairwiseLogisticRanker, PublicCourseRanker
from app.backend import CurricuPathService
from app.config import PROJECT_ROOT, Settings, get_settings
from app.data.database import create_database_engine
from app.data.embeddings import (
    HuggingFaceHostedEmbeddings,
    PostgresSemanticSearch,
    SemanticSearchError,
)
from app.data.postgres_repository import PostgresCatalogueRepository
from app.data.recommendation_log import (
    PostgresRecommendationLogger,
    RecommendationLogger,
    catalogue_version,
)
from app.data.repository import CsvCatalogueRepository
from app.data.sessions import (
    ConversationContext,
    InMemorySessionStore,
    PostgresSessionStore,
    SessionStore,
)
from app.evaluation.runner import GeminiDecisionClient
from app.ui.advisor_page import advisor_page_html


class EligibilityRequest(BaseModel):
    """Declared student state used by the deterministic eligibility gates."""

    course_code: str = Field(pattern=r"^[A-Za-z]{4}\d{4}[Aa]?$")
    programme_code: str = Field(pattern=r"^[Ee][Ff][Aa]\d{2}$")
    completed_modules: set[str] = Field(default_factory=set)
    current_modules: set[str] = Field(default_factory=set)
    planned_modules: set[str] = Field(default_factory=set)
    repeating_modules: set[str] = Field(default_factory=set)
    module_states: dict[str, ModuleFactState] = Field(default_factory=dict)
    module_history_confirmed: bool | None = None


class AdvisorRequest(BaseModel):
    """One advisor message plus any profile state explicitly set by the UI."""

    message: str = Field(min_length=1, max_length=2000)
    session_id: str | None = Field(default=None, max_length=64)
    programme_code: str | None = Field(
        default=None, pattern=r"^[Ee][Ff][Aa]\d{2}$"
    )
    completed_modules: set[str] = Field(default_factory=set)
    current_modules: set[str] = Field(default_factory=set)
    planned_modules: set[str] = Field(default_factory=set)
    repeating_modules: set[str] = Field(default_factory=set)
    module_states: dict[str, ModuleFactState] = Field(default_factory=dict)
    module_history_confirmed: bool | None = None
    ranking_mode: Literal["deterministic", "prototype"] = "deterministic"
    system: Literal["curricupath", "handbook_rag"] = "curricupath"
    # False gives the no-clarification ablation: CurricuPath answers without ever asking.
    allow_clarification: bool = True
    # Interpretation fallback for unresolved messages; None uses the server setting. A request
    # can only lower the server setting (llm > fuzzy > off), never raise it.
    interpretation_fallback: Literal["off", "fuzzy", "llm"] | None = None


class SemanticSearchRequest(BaseModel):
    """One hosted query embedding evaluated against stored pgvector chunks."""

    query: str = Field(min_length=1, max_length=1000)
    item_type: Literal["module", "public_course"] | None = None
    limit: int = Field(default=10, ge=1, le=50)


def create_app(
    service: CurricuPathService | None = None,
    advisor_engine: AdvisorEngine | None = None,
    session_store: SessionStore | None = None,
    semantic_search: PostgresSemanticSearch | None = None,
    enable_semantic_search: bool = False,
    recommendation_logger: RecommendationLogger | None = None,
    public_course_ranker: PublicCourseRanker | None = None,
    response_reviewer: ResponseReviewer | None = None,
    handbook_rag_demo: HandbookRagDemo | None = None,
) -> FastAPI:
    """Create an API whose service can be replaced in focused tests."""

    if service is None:
        settings = get_settings()
        repository = _build_catalogue_repository(settings)
        service = CurricuPathService(
            repository,
            str(PROJECT_ROOT),
            timetable_clash_gate_enabled=settings.timetable_clash_gate_enabled,
        )
    else:
        settings = get_settings()

    if semantic_search is None and enable_semantic_search:
        semantic_search = _build_semantic_search(settings)

    if public_course_ranker is None and settings.public_course_ranker_enabled:
        public_course_ranker = _build_public_course_ranker(
            settings,
            service.repository,
            semantic_search,
        )

    if advisor_engine is None:
        aliases = service.repository.get_aliases()
        extractor = build_intent_extractor(
            aliases,
            settings.gemini_api_key,
            settings.gemini_model,
        )
        advisor_engine = AdvisorEngine(
            service,
            extractor,
            semantic_search,
            public_course_ranker,
        )
    else:
        aliases = service.repository.get_aliases()
    scope_extractor = DeterministicIntentExtractor(aliases)
    if response_reviewer is None and settings.reasoning_reviewer_enabled:
        response_reviewer = _build_response_reviewer(settings)
    review_coordinator = ReviewCoordinator(response_reviewer)
    if handbook_rag_demo is None and settings.handbook_rag_demo_enabled:
        handbook_rag_demo = _build_handbook_rag_demo(settings)
    interpretation_fallback = InterpretationFallback(service, _build_interpreters(settings))
    if session_store is None:
        session_store = _build_session_store(service.repository)
    if recommendation_logger is None:
        recommendation_logger = _build_recommendation_logger(service.repository)

    api = FastAPI(
        title="CurricuPath API",
        version="0.1.0",
        description=(
            "Source-verified curriculum API with deterministic eligibility and "
            "optional hosted-embedding pgvector matching."
        ),
    )
    api.mount(
        "/assets",
        StaticFiles(directory=PROJECT_ROOT / "app" / "ui" / "assets"),
        name="assets",
    )

    @api.get("/", response_class=HTMLResponse, include_in_schema=False)
    def advisor_page() -> str:
        return advisor_page_html()

    @api.get("/health")
    def health() -> dict[str, str]:
        result = service.health()
        if result["status"] != "ok":
            raise HTTPException(status_code=503, detail="Database unavailable")
        return result

    @api.get("/programmes")
    def programmes() -> list[dict[str, object]]:
        return service.programmes()

    @api.get("/catalogue/summary")
    def catalogue_summary() -> dict[str, object]:
        learned_ranker_available = advisor_engine.public_course_ranker is not None
        return {
            **service.summary(),
            "public_course_ranking_mode": (
                advisor_engine.public_course_ranker.mode
                if learned_ranker_available
                else "deterministic"
            ),
            "available_public_course_ranking_modes": (
                ["deterministic", "prototype"]
                if learned_ranker_available
                else ["deterministic"]
            ),
            "reasoning_reviewer_enabled": response_reviewer is not None,
            "handbook_rag_demo_enabled": handbook_rag_demo is not None,
        }

    @api.get("/programmes/{programme_code}/modules")
    def modules(
        programme_code: str,
        year_of_study: Annotated[int | None, Query(ge=1, le=4)] = None,
    ) -> list[dict[str, object]]:
        return service.modules(programme_code.upper(), year_of_study)

    @api.get("/modules/{course_code}")
    def module(course_code: str) -> dict[str, object]:
        result = service.module(course_code)
        if result is None:
            raise HTTPException(status_code=404, detail="Module not found")
        return result

    @api.get("/courses")
    def courses(
        category: str | None = None,
        interest: str | None = None,
        career: str | None = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
    ) -> list[dict[str, object]]:
        return service.courses(category, interest, career, limit)

    @api.get("/courses/{course_id}")
    def course(course_id: str) -> dict[str, object]:
        result = service.course(course_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Course not found")
        return result

    @api.get("/career-paths")
    def career_paths() -> list[dict[str, object]]:
        return service.career_paths()

    @api.get("/evidence")
    def evidence() -> dict[str, object]:
        return service.evidence()

    @api.get("/cbos/missing")
    def missing_cbos() -> list[dict[str, object]]:
        return service.missing_cbos()

    @api.post("/search/semantic")
    def search_semantically(request: SemanticSearchRequest) -> dict[str, object]:
        if semantic_search is None:
            raise HTTPException(
                status_code=503,
                detail="Semantic search is not configured.",
            )
        try:
            results = semantic_search.search(
                request.query,
                item_type=request.item_type,
                limit=request.limit,
            )
        except SemanticSearchError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        return {
            "provider": semantic_search.provider.provider_name,
            "model": semantic_search.provider.model_name,
            "results": results,
        }

    @api.post("/eligibility")
    def eligibility(request: EligibilityRequest) -> dict[str, object]:
        return service.eligibility(
            request.course_code,
            request.programme_code,
            request.completed_modules,
            request.current_modules,
            request.planned_modules,
            module_states=request.module_states,
            module_history_confirmed=request.module_history_confirmed,
            repeating_modules=request.repeating_modules,
        )

    @api.post("/advisor")
    def advisor(request: AdvisorRequest) -> dict[str, object]:
        if request.system == "handbook_rag":
            if handbook_rag_demo is None:
                raise HTTPException(
                    status_code=503,
                    detail=(
                        "The experimental handbook-RAG baseline is not "
                        "configured on this server."
                    ),
                )
            result = handbook_rag_demo.answer(
                request.message,
                request.programme_code,
                request.completed_modules,
                request.current_modules,
                request.planned_modules,
            )
            result["session_id"] = request.session_id or "baseline-demo"
            return result
        session_id, context = session_store.load(request.session_id)
        prefer_module = getattr(advisor_engine, "prefer_module_information", None)
        prohibited = is_prohibited(request.message)

        def interpret(text: str):
            parsed = scope_extractor.extract(text)
            # Apply the engine's module-name decision first, so a curriculum title is not
            # refused as out of scope before module resolution can run.
            if prefer_module is not None and not prohibited:
                parsed = prefer_module(text, parsed, request.programme_code)
            return parsed

        message = request.message
        scope_request = interpret(message)
        fallback_used = None
        mode = capped_fallback_mode(request.interpretation_fallback, settings.interpretation_fallback)
        pending = context.pending_intent is not None
        if not prohibited and (
            needs_fallback(message, scope_request.intent, scope_request.module_code)
            if not pending
            else is_new_programme_question(message, scope_request.intent, scope_request.module_code)
        ):
            recovered = interpretation_fallback.recover(
                message, request.programme_code, mode,
                lambda text: not needs_fallback(text, interpret(text).intent, interpret(text).module_code),
            )
            if recovered is not None:
                fallback_used = recovered.metadata(message)
                message = recovered.message
                scope_request = interpret(message)
        scope = classify_scope(
            message,
            scope_request,
            has_active_context=context.pending_intent is not None,
        )
        if scope.status == "out_of_scope":
            result = out_of_scope_response(scope_request, scope)
        elif scope.status == "ambiguous" and not request.allow_clarification:
            result = unresolved_without_clarification(scope_request.intent)
            result["scope"] = scope.model_dump()
        elif scope.status == "ambiguous":
            question = scope.clarification_question or (
                "Could you clarify which CurricuPath feature you want to use?"
            )
            result = {
                "intent": scope_request.intent,
                "status": "clarification_required",
                "answer": question,
                "clarification_question": question,
                "clarification_options": [],
                "scope": scope.model_dump(),
                "conversation_context": context.as_dict(),
            }
        else:
            result = advisor_engine.advise(
                message,
                request.programme_code,
                request.completed_modules,
                request.current_modules,
                request.planned_modules,
                context,
                request.ranking_mode,
                module_states=request.module_states,
                module_history_confirmed=request.module_history_confirmed,
                allow_clarification=request.allow_clarification,
                repeating_modules=request.repeating_modules,
            )
            result["scope"] = scope.model_dump()
            result = review_coordinator.process(message, result)
        candidate_log = result.pop("_candidate_log", [])
        for candidate in candidate_log:
            candidate.setdefault("gate_outcomes", {})["response_review"] = result.get(
                "review", {}
            )
        session_store.save(
            session_id,
            _conversation_context(result["conversation_context"]),
        )
        run_id = recommendation_logger.log(session_id, result, candidate_log)
        if run_id:
            result["run_id"] = run_id
        result["session_id"] = session_id
        if fallback_used is not None:
            result["interpretation_fallback"] = fallback_used
        return result

    @api.delete("/advisor/sessions/{session_id}")
    def reset_advisor_session(session_id: str) -> dict[str, str]:
        session_store.clear(session_id)
        return {"status": "cleared"}

    return api


def _conversation_context(value: object) -> ConversationContext:
    return ConversationContext.from_dict(value)


def _build_semantic_search(settings: Settings) -> PostgresSemanticSearch | None:
    token = settings.hf_token
    if not token:
        return None
    provider = HuggingFaceHostedEmbeddings(
        token,
        settings.embedding_model,
        settings.embedding_dimension,
    )
    engine = create_database_engine(settings.database_url)
    return PostgresSemanticSearch(engine, provider)


def _build_response_reviewer(settings: Settings) -> ResponseReviewer | None:
    if not settings.gemini_api_key:
        warnings.warn(
            "Reasoning reviewer is enabled but GEMINI_API_KEY is unavailable; "
            "using deterministic response invariants only.",
            RuntimeWarning,
            stacklevel=2,
        )
        return None
    return GeminiResponseReviewer(
        settings.gemini_api_key,
        settings.reasoning_reviewer_model,
        settings.reasoning_reviewer_timeout_ms,
    )


def _build_handbook_rag_demo(settings: Settings) -> HandbookRagDemo | None:
    if not settings.gemini_api_key or not settings.hf_token:
        warnings.warn(
            "Handbook-RAG demo is enabled but GEMINI_API_KEY or HF_TOKEN is "
            "unavailable; the live baseline toggle will stay unavailable.",
            RuntimeWarning,
            stacklevel=2,
        )
        return None
    evaluation_directory = (
        PROJECT_ROOT / "experiments" / "evaluation" / "v2_5"
    )
    config = json.loads(
        (evaluation_directory / "rag_retrieval_config.json").read_text(
            encoding="utf-8"
        )
    )
    top_k = config.get("selected_top_k")
    if not isinstance(top_k, int):
        warnings.warn(
            "Handbook-RAG demo is enabled but no top_k has been selected and "
            "frozen in rag_retrieval_config.json; the live baseline toggle "
            "will stay unavailable.",
            RuntimeWarning,
            stacklevel=2,
        )
        return None
    provider = HuggingFaceHostedEmbeddings(
        settings.hf_token,
        settings.embedding_model,
        settings.embedding_dimension,
    )
    search = PostgresSemanticSearch(
        create_database_engine(settings.database_url), provider
    )
    client = GeminiDecisionClient(
        settings.gemini_api_key, settings.handbook_rag_demo_model
    )
    return HandbookRagDemo(
        search,
        client,
        evaluation_directory,
        top_k,
        str(config.get("eligibility_corpus_item_type", "evaluation_handbook")),
    )


def _build_catalogue_repository(settings: Settings):
    if settings.catalogue_backend == "csv":
        return CsvCatalogueRepository(settings.processed_data_directory)
    if settings.catalogue_backend != "postgresql":
        raise ValueError(
            "CATALOGUE_BACKEND must be either 'postgresql' or 'csv'."
        )

    repository = PostgresCatalogueRepository(
        create_database_engine(settings.database_url)
    )
    if repository.is_healthy():
        return repository
    if settings.catalogue_csv_fallback:
        return CsvCatalogueRepository(settings.processed_data_directory)
    raise RuntimeError(
        "PostgreSQL catalogue is unavailable and CSV fallback is disabled."
    )


def _build_public_course_ranker(
    settings: Settings,
    repository,
    semantic_search: PostgresSemanticSearch | None,
) -> PairwiseLogisticRanker | None:
    """Load an approved ranker or retain the deterministic production fallback."""

    if not isinstance(repository, PostgresCatalogueRepository):
        warnings.warn(
            "The learned ranker requires the fingerprinted PostgreSQL catalogue; "
            "using deterministic ranking.",
            RuntimeWarning,
            stacklevel=2,
        )
        return None
    if semantic_search is None:
        warnings.warn(
            "The learned ranker requires semantic search; using deterministic ranking.",
            RuntimeWarning,
            stacklevel=2,
        )
        return None
    try:
        return PairwiseLogisticRanker.load(
            settings.public_course_ranker_model,
            catalogue_fingerprint=catalogue_version(repository.engine),
            embedding_model=settings.embedding_model,
            require_deployment_eligible=not settings.allow_experimental_ranker,
        )
    except (OSError, ValueError) as error:
        warnings.warn(
            f"Learned ranker was not loaded ({error}); using deterministic ranking.",
            RuntimeWarning,
            stacklevel=2,
        )
        return None


def _build_session_store(repository) -> SessionStore:
    if isinstance(repository, PostgresCatalogueRepository):
        return PostgresSessionStore(repository.engine)
    return InMemorySessionStore()


def _build_recommendation_logger(repository) -> RecommendationLogger:
    if isinstance(repository, PostgresCatalogueRepository):
        return PostgresRecommendationLogger(repository.engine)
    return _NullRecommendationLogger()


class _NullRecommendationLogger:
    def log(self, session_id, result, candidates):
        return None


def _build_interpreters(settings: Settings) -> list:
    """Gemini first; Claude Haiku only when an Anthropic key and SDK are available."""

    providers: list = []
    if settings.gemini_api_key:
        providers.append(GeminiInterpreter(settings.gemini_api_key, settings.interpretation_model))
    if settings.anthropic_api_key:
        try:
            providers.append(ClaudeInterpreter(settings.claude_fallback_model))
        except ImportError:
            warnings.warn("ANTHROPIC_API_KEY is set but the anthropic package is not installed; "
                          "the Claude fallback is unavailable.", RuntimeWarning, stacklevel=2)
    return providers


app = create_app(enable_semantic_search=get_settings().semantic_search_enabled)


def main() -> None:
    """Run the CurricuPath application."""

    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)

if __name__ == "__main__":
    main()
