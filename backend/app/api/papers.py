import os

import aiosqlite
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from app.core.disciplines import DISCIPLINE_INFO, Discipline
from app.models.schemas import IngestResponse, PaperInfo
from app.rag.ingest import ingest_papers

router = APIRouter()


@router.get("/api/papers", response_model=list[PaperInfo])
async def list_papers(request: Request):
    settings = request.app.state.settings
    async with aiosqlite.connect(settings.sqlite_db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, title, authors, filename, num_chunks, num_figures, ingested_at FROM papers"
        ) as cursor:
            rows = await cursor.fetchall()

    return [
        PaperInfo(
            paper_id=row["id"],
            title=row["title"],
            authors=row["authors"],
            filename=row["filename"],
            num_chunks=row["num_chunks"],
            num_figures=row["num_figures"],
            ingested_at=row["ingested_at"],
        )
        for row in rows
    ]


@router.get("/api/papers/{paper_id}/pdf")
async def get_paper_pdf(paper_id: str, request: Request):
    settings = request.app.state.settings
    async with aiosqlite.connect(settings.sqlite_db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT filename FROM papers WHERE id = ?", (paper_id,)
        ) as cursor:
            row = await cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Paper not found")

    filepath = os.path.join(settings.papers_dir, row["filename"])
    if not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail="PDF file missing from disk")

    return FileResponse(filepath, media_type="application/pdf", filename=row["filename"])


@router.post("/api/ingest", response_model=IngestResponse)
async def ingest(request: Request):
    settings = request.app.state.settings
    llm_client = request.app.state.llm_client
    collection = request.app.state.collection

    result = await ingest_papers(settings, llm_client, collection)
    return IngestResponse(**result)


@router.get("/api/disciplines")
async def list_disciplines():
    return [
        {
            "value": d.value,
            "label": info["label"],
            "description": info["description"],
            "key_concepts": info["key_concepts"],
        }
        for d, info in DISCIPLINE_INFO.items()
    ]
