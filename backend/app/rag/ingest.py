import hashlib
import logging
import os
import tempfile
import uuid

import asyncpg
import numpy as np

from app.core.config import Settings
from app.llm.client import LLMClient
from app.rag.chunker import chunk_text
from app.rag.embeddings import embed_chunks
from app.rag.extractor import extract_captions, extract_figures, extract_text_blocks
from app.storage.s3 import upload_file as s3_upload

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Title-extraction helpers (unchanged logic)
# ---------------------------------------------------------------------------

_JOURNAL_PATTERNS = {
    "geophysical research letters", "journal of geophysical research",
    "science advances", "science", "nature", "nature geoscience",
    "nature communications", "reviews of geophysics", "eos",
    "bulletin of the seismological society", "geophysical journal international",
    "seismological research letters", "water resources research",
    "journal of hydrology", "advances in water resources",
    "atmospheric chemistry and physics", "journal of climate",
    "monthly weather review", "geological society", "tectonophysics",
    "earth and planetary science letters", "proceedings of the national academy",
}


def _is_journal_name(text: str) -> bool:
    normalized = text.strip().lower()
    return any(j in normalized for j in _JOURNAL_PATTERNS)


def _title_from_filename(filename: str) -> str:
    stem = filename.rsplit(".", 1)[0]
    parts = [p.strip() for p in stem.split(" - ")]
    if len(parts) >= 4:
        return parts[-1][:200]
    return ""


def _guess_title(text_blocks: list[dict], filename: str = "") -> str:
    from_name = _title_from_filename(filename)
    if from_name:
        return from_name
    if not text_blocks:
        return ""
    candidates = sorted(text_blocks[:10], key=lambda b: b["font_size"], reverse=True)
    for block in candidates:
        txt = block["text"].strip()
        if not txt or len(txt.split()) < 4:
            continue
        if _is_journal_name(txt):
            continue
        return txt[:200]
    fallback = max(text_blocks[:10], key=lambda b: b["font_size"], default=None)
    return fallback["text"][:200].strip() if fallback else ""


def _bytes_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Single-paper ingestion (used by upload endpoint)
# ---------------------------------------------------------------------------

async def ingest_pdf(
    settings: Settings,
    pool: asyncpg.Pool,
    llm_client: LLMClient,
    pdf_bytes: bytes,
    filename: str,
) -> dict:
    """Ingest a single PDF: upload to S3, extract, embed, store in Postgres.

    Returns dict with paper_id, title, num_chunks, num_figures.
    """
    fhash = _bytes_hash(pdf_bytes)

    existing = await pool.fetchval(
        "SELECT id FROM papers WHERE file_hash = $1", fhash
    )
    if existing:
        logger.info("Skipping already-ingested paper: %s", filename)
        return {"paper_id": existing, "title": "", "num_chunks": 0, "num_figures": 0, "skipped": True}

    paper_id = uuid.uuid4().hex[:12]

    # Upload PDF to S3
    s3_pdf_key = f"papers/{paper_id}/{filename}"
    s3_upload(settings, s3_pdf_key, pdf_bytes, content_type="application/pdf")

    # Write to temp file for PyMuPDF processing
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = os.path.join(tmpdir, filename)
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)

        figures_dir = os.path.join(tmpdir, "figures")
        os.makedirs(figures_dir, exist_ok=True)

        text_blocks = extract_text_blocks(pdf_path)
        figures = extract_figures(pdf_path, figures_dir, paper_id)
        captions = extract_captions(text_blocks)

        for fig in figures:
            page = fig["page"]
            page_captions = captions.get(page, [])
            fig["caption"] = page_captions.pop(0) if page_captions else ""

        # Upload figure images to S3
        for fig in figures:
            local_path = fig["filepath"]
            if os.path.isfile(local_path):
                with open(local_path, "rb") as img_f:
                    s3_fig_key = f"figures/{fig['figure_id']}.png"
                    s3_upload(settings, s3_fig_key, img_f.read(), content_type="image/png")
                    fig["s3_key"] = s3_fig_key

    chunks = chunk_text(text_blocks)
    if not chunks:
        logger.warning("No text chunks extracted from %s", filename)
        return {"paper_id": paper_id, "title": "", "num_chunks": 0, "num_figures": 0, "skipped": False}

    chunks = await embed_chunks(llm_client, chunks)
    title = _guess_title(text_blocks, filename)

    # Store everything in Postgres
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                """INSERT INTO papers (id, filename, title, authors, file_hash, s3_pdf_key, num_chunks, num_figures)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
                paper_id, filename, title, "", fhash, s3_pdf_key, len(chunks), len(figures),
            )

            for fig in figures:
                await conn.execute(
                    """INSERT INTO figures (id, paper_id, page, s3_key, caption, width, height)
                       VALUES ($1, $2, $3, $4, $5, $6, $7)""",
                    fig["figure_id"], paper_id, fig["page"],
                    fig.get("s3_key", ""), fig.get("caption", ""),
                    fig["width"], fig["height"],
                )

            for chunk in chunks:
                chunk_id = f"{paper_id}_{uuid.uuid4().hex[:8]}"
                vec = np.array(chunk["embedding"], dtype=np.float32)
                await conn.execute(
                    """INSERT INTO chunks (id, paper_id, section_title, page_start, page_end,
                                          content, embedding, title, authors, discipline_tags)
                       VALUES ($1, $2, $3, $4, $5, $6, $7::vector, $8, $9, $10)""",
                    chunk_id, paper_id, chunk["section_title"],
                    chunk["page_start"], chunk["page_end"],
                    chunk["text"], vec, title, "", "general",
                )

    logger.info("Paper %s: %d chunks, %d figures", filename, len(chunks), len(figures))
    return {
        "paper_id": paper_id,
        "title": title,
        "num_chunks": len(chunks),
        "num_figures": len(figures),
        "skipped": False,
    }


# ---------------------------------------------------------------------------
# Bulk ingestion from a local directory (for initial seeding / backward compat)
# ---------------------------------------------------------------------------

async def ingest_papers_from_dir(
    settings: Settings,
    pool: asyncpg.Pool,
    llm_client: LLMClient,
) -> dict:
    """Scan settings.papers_dir and ingest any new PDFs."""
    papers_dir = settings.papers_dir
    os.makedirs(papers_dir, exist_ok=True)

    pdf_files = [f for f in os.listdir(papers_dir) if f.lower().endswith(".pdf")]

    total_papers = 0
    total_chunks = 0
    total_figures = 0

    for filename in pdf_files:
        pdf_path = os.path.join(papers_dir, filename)
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        result = await ingest_pdf(settings, pool, llm_client, pdf_bytes, filename)
        if not result.get("skipped"):
            total_papers += 1
            total_chunks += result["num_chunks"]
            total_figures += result["num_figures"]

    return {
        "papers_ingested": total_papers,
        "total_chunks": total_chunks,
        "total_figures": total_figures,
    }
