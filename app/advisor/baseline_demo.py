"""Live, ad-hoc adapter for the frozen handbook-RAG evaluation baseline.

Reuses the stateless `EvaluationRunner`/`GeminiDecisionClient` from
`app.evaluation.runner` (unmodified) to answer one-off demo questions outside
the frozen 60-case evaluation set. This path is intentionally separate from
the audited CurricuPath session and recommendation-log trail; it exists only
for a live, clearly-labelled comparison demo.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.data.embeddings import PostgresSemanticSearch
from app.evaluation.runner import EvaluationRunner, GeminiDecisionClient


_FALLBACK_ANSWER = (
    "The experimental baseline could not produce a decision for this question."
)


class HandbookRagDemo:
    """Answer one live question with the frozen handbook-RAG baseline."""

    def __init__(
        self,
        search: PostgresSemanticSearch,
        client: GeminiDecisionClient,
        prompt_directory: Path,
        top_k: int,
        retrieval_item_type: str = "evaluation_handbook",
    ) -> None:
        self._runner = EvaluationRunner(
            search,
            client,
            prompt_directory,
            rules=[],
            source_states=[],
            top_k=top_k,
            retrieval_item_type=retrieval_item_type,
        )

    def answer(
        self,
        message: str,
        programme_code: str | None,
        completed_modules: set[str],
        current_modules: set[str],
        planned_modules: set[str],
    ) -> dict[str, Any]:
        case = {
            "case_id": "live",
            "question": message,
            "student_profile": {
                "programme_code": programme_code,
                "completed_modules": sorted(completed_modules),
                "current_modules": sorted(current_modules),
                "planned_modules": sorted(planned_modules),
            },
        }
        run = self._runner.run_case(case, "handbook_rag", run_number=1)
        parsed = run.parsed_output if run.status == "valid" else None
        return {
            "system": "handbook_rag",
            "status": run.status,
            "decision": parsed.get("decision") if parsed else None,
            "answer": parsed.get("answer") if parsed else _FALLBACK_ANSWER,
            "citations": parsed.get("citations", []) if parsed else [],
        }
