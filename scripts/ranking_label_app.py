"""Run the local blinded relevance-labelling interface on port 8010."""

from __future__ import annotations

import csv
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Annotated


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.advisor.ranking_labels import RankingLabelStore
from app.data.repository import CsvCatalogueRepository


repository = CsvCatalogueRepository(PROJECT_ROOT / "data" / "processed")
courses = repository.list_courses(limit=100)
store = RankingLabelStore(
    PROJECT_ROOT / "experiments" / "ranking",
    [course["course_id"] for course in courses],
)
PROTOTYPE_LABEL_PATH = PROJECT_ROOT / "experiments" / "ranking" / "prototype_judgements.csv"
PROTOTYPE_MODEL_PATH = (
    PROJECT_ROOT
    / "experiments"
    / "models"
    / "public_course_pairwise_logistic_prototype_v1.json"
)
app = FastAPI(title="CurricuPath Ranking Label Lab", version="0.1.0")
app.mount(
    "/lab-assets",
    StaticFiles(directory=PROJECT_ROOT / "app" / "ui" / "ranking_lab_assets"),
    name="lab-assets",
)


class ProfileApproval(BaseModel):
    reviewer: str = Field(min_length=2, max_length=100)


class GradeSubmission(BaseModel):
    slot: int = Field(ge=1, le=2)
    judge_id: str = Field(min_length=2, max_length=100)
    profile_id: str = Field(min_length=1, max_length=30)
    course_id: str = Field(min_length=1, max_length=30)
    grade: int = Field(ge=0, le=3)


class AdjudicationSubmission(BaseModel):
    profile_id: str = Field(min_length=1, max_length=30)
    course_id: str = Field(min_length=1, max_length=30)
    final_grade: int = Field(ge=0, le=3)
    notes: str = Field(default="", max_length=1000)


@app.exception_handler(ValueError)
async def value_error_handler(_, error: ValueError):
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=409, content={"detail": str(error)})


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def lab_page() -> str:
    return (PROJECT_ROOT / "app" / "ui" / "ranking_lab.html").read_text(
        encoding="utf-8"
    )


@app.get("/api/setup")
def setup() -> dict[str, object]:
    return {
        "readiness": store.readiness(),
        "prototype": _prototype_status(),
        "profiles": [
            asdict(profile) for profile in store.profiles(require_approved=False)
        ],
        "courses": courses,
    }


def _prototype_status() -> dict[str, object]:
    label_count = 0
    if PROTOTYPE_LABEL_PATH.exists():
        with PROTOTYPE_LABEL_PATH.open(newline="", encoding="utf-8") as label_file:
            label_count = sum(1 for _ in csv.DictReader(label_file))
    provenance = None
    deployment_eligible = False
    if PROTOTYPE_MODEL_PATH.exists():
        artifact = json.loads(PROTOTYPE_MODEL_PATH.read_text(encoding="utf-8"))
        provenance = artifact.get("label_provenance")
        deployment_eligible = bool(artifact.get("deployment_eligible", False))
    expected = len(store.profiles(require_approved=False)) * len(courses)
    return {
        "labels": label_count,
        "expected_labels": expected,
        "labels_complete": label_count == expected,
        "model_trained": PROTOTYPE_MODEL_PATH.exists(),
        "label_provenance": provenance,
        "deployment_eligible": deployment_eligible,
    }


@app.post("/api/profiles/approve")
def approve_profiles(request: ProfileApproval) -> dict[str, object]:
    store.approve_profiles(request.reviewer)
    return store.readiness()


@app.get("/api/judge")
def judge_state(
    slot: Annotated[int, Query(ge=1, le=2)],
    judge_id: Annotated[str, Query(min_length=2, max_length=100)],
) -> dict[str, object]:
    store.profiles(require_approved=True)
    return store.judge_state(slot, judge_id)


@app.post("/api/judge/grade")
def save_grade(request: GradeSubmission) -> dict[str, object]:
    store.save_grade(
        request.slot,
        request.judge_id,
        request.profile_id,
        request.course_id,
        request.grade,
    )
    return store.judge_state(request.slot, request.judge_id)


@app.post("/api/adjudication/prepare")
def prepare_adjudication() -> dict[str, object]:
    return store.prepare_adjudication()


@app.get("/api/adjudication")
def disagreements() -> dict[str, object]:
    readiness = store.readiness()
    expected = readiness["expected_judgements_per_judge"]
    if (
        readiness["judge_1_completed"] != expected
        or readiness["judge_2_completed"] != expected
    ):
        raise HTTPException(status_code=409, detail="Both judges must finish first.")
    return {
        "readiness": readiness,
        "disagreements": store.disagreements(),
    }


@app.post("/api/adjudication")
def adjudicate(request: AdjudicationSubmission) -> dict[str, object]:
    store.save_adjudication(
        request.profile_id,
        request.course_id,
        request.final_grade,
        request.notes,
    )
    return store.readiness()


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8010)


if __name__ == "__main__":
    main()
