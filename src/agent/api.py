"""FastAPI surface for the search service.

Run:  uvicorn src.agent.api:create_default_app --factory
HTTP status: 200 for complete / partial / clarify, 503 when the run failed (body still
carries the reasons), 409 when a revision was made against a stale condition version.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.agent.service import InvalidRevision, SearchService, TaskNotFound, VersionConflict

ROOT = Path(__file__).resolve().parent.parent.parent


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    proceed: bool = False  # search even if the conditions carry a clarification question


class RunRequest(BaseModel):
    expected_version: int


class ReviseRequest(BaseModel):
    expected_version: int
    strengths: dict[str, str] = Field(default_factory=dict)  # condition_id -> "hard" | "soft"
    remove: list[str] = Field(default_factory=list)


def _respond(body: dict) -> JSONResponse:
    return JSONResponse(body, status_code=503 if body["status"] == "failed" else 200)


def create_app(service: SearchService) -> FastAPI:
    app = FastAPI(title="Job Intelligence Agent")

    @app.exception_handler(TaskNotFound)
    def _not_found(_, exc: TaskNotFound):
        return JSONResponse({"detail": {"error": "not_found", "id": str(exc.args[0])}}, status_code=404)

    @app.exception_handler(VersionConflict)
    def _conflict(_, exc: VersionConflict):
        return JSONResponse(
            {"detail": {"error": "version_conflict", "current_version": exc.current, "expected_version": exc.expected}},
            status_code=409,
        )

    @app.exception_handler(InvalidRevision)
    def _invalid(_, exc: InvalidRevision):
        return JSONResponse({"detail": {"error": "invalid_revision", "message": str(exc)}}, status_code=422)

    @app.get("/health")
    def health():
        return {"ok": True, "jobs": len(service.index)}

    @app.post("/search")
    def search(req: SearchRequest):
        return _respond(service.start(req.query, proceed=req.proceed))

    @app.get("/tasks/{task_id}")
    def get_task(task_id: str, version: int | None = None):
        return service.get(task_id, version)

    @app.post("/tasks/{task_id}/run")
    def run_task(task_id: str, req: RunRequest):
        return _respond(service.run(task_id, req.expected_version))

    @app.post("/tasks/{task_id}/revise")
    def revise_task(task_id: str, req: ReviseRequest):
        return _respond(service.revise(task_id, req.expected_version, strengths=req.strengths, remove=req.remove))

    @app.get("/jobs/{job_key:path}")
    def get_job(job_key: str):
        try:
            snap = service.index.snapshot(job_key)
        except KeyError:
            raise HTTPException(status_code=404, detail={"error": "not_found", "id": job_key})
        return {
            "job_key": snap.job_key, "title": snap.title, "company": snap.company, "location": snap.location,
            "url": snap.url, "content_hash": snap.content_hash, "fetched_at": snap.fetched_at,
            "version": snap.version, "text": snap.text,
        }

    return app


def build_default_service(data_dir: str | Path | None = None, legacy_json: str | Path | None = None) -> SearchService:
    """Wire the real components: SQLite stores under `data_dir`, OpenAI embeddings, bge reranker."""
    from src.agent.embeddings import CachedEmbedder, EmbeddingCache, default_model_name, openai_embed_fn
    from src.agent.rerank import CrossEncoderScorer
    from src.agent.retrieval import JobIndex
    from src.agent.snapshots import SnapshotStore, import_legacy_json
    from src.agent.tasks import TaskStore
    from src.agent.verification import JudgmentCache, Verifier

    data = Path(data_dir or os.environ.get("JOB_AGENT_DATA", ROOT / "data" / "agent"))
    data.mkdir(parents=True, exist_ok=True)
    snapshots = SnapshotStore(data / "snapshots.db")
    if snapshots.count() == 0:
        import_legacy_json(legacy_json or ROOT / "data" / "structured_jobs.json", snapshots)
    embedder = CachedEmbedder(openai_embed_fn(), default_model_name(), EmbeddingCache(data / "embeddings.db"))
    index = JobIndex(snapshots.all_latest(), embedder)
    return SearchService(
        index, CrossEncoderScorer(), Verifier(JudgmentCache(data / "judgments.db")), TaskStore(data / "tasks.db")
    )


def create_default_app() -> FastAPI:
    return create_app(build_default_service())
