import logging

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from starlette.responses import RedirectResponse

from app.core.disciplines import DISCIPLINE_INFO
from app.db.postgres import get_pool
from app.models.schemas import IngestResponse, PaperInfo
from app.rag.ingest import ingest_pdf, ingest_papers_from_dir
from app.storage.s3 import get_public_url

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB


@router.get("/api/papers", response_model=list[PaperInfo])
async def list_papers(request: Request):
    pool = get_pool()
    rows = await pool.fetch(
        "SELECT id, title, authors, filename, num_chunks, num_figures, ingested_at FROM papers"
    )
    return [
        PaperInfo(
            paper_id=row["id"],
            title=row["title"],
            authors=row["authors"],
            filename=row["filename"],
            num_chunks=row["num_chunks"],
            num_figures=row["num_figures"],
            ingested_at=str(row["ingested_at"]),
        )
        for row in rows
    ]


@router.get("/api/papers/{paper_id}/pdf")
async def get_paper_pdf(paper_id: str, request: Request):
    settings = request.app.state.settings
    pool = get_pool()
    row = await pool.fetchrow(
        "SELECT s3_pdf_key, filename FROM papers WHERE id = $1", paper_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Paper not found")

    url = get_public_url(settings, row["s3_pdf_key"])
    return RedirectResponse(url=url)


@router.post("/api/papers/upload")
async def upload_paper(request: Request, file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    pdf_bytes = await file.read()
    if len(pdf_bytes) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds 50 MB limit")

    settings = request.app.state.settings
    pool = get_pool()
    llm_client = request.app.state.llm_client

    result = await ingest_pdf(settings, pool, llm_client, pdf_bytes, file.filename)

    if result.get("skipped"):
        return {
            "status": "skipped",
            "message": "This paper has already been ingested",
            "paper_id": result["paper_id"],
        }

    return {
        "status": "ok",
        "paper_id": result["paper_id"],
        "title": result["title"],
        "num_chunks": result["num_chunks"],
        "num_figures": result["num_figures"],
    }


@router.post("/api/ingest", response_model=IngestResponse)
async def ingest(request: Request):
    settings = request.app.state.settings
    pool = get_pool()
    llm_client = request.app.state.llm_client
    result = await ingest_papers_from_dir(settings, pool, llm_client)
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
