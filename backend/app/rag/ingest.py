import hashlib
import logging
import os
import sqlite3
import uuid

import aiosqlite
import chromadb

from app.core.config import Settings
from app.llm.client import LLMClient
from app.rag.chunker import chunk_text
from app.rag.embeddings import embed_chunks
from app.rag.extractor import extract_captions, extract_figures, extract_text_blocks

logger = logging.getLogger(__name__)


async def init_db(db_path: str) -> None:
    """Create SQLite tables if they do not already exist."""
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS papers (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT '',
                authors TEXT NOT NULL DEFAULT '',
                file_hash TEXT UNIQUE NOT NULL,
                num_chunks INTEGER NOT NULL DEFAULT 0,
                num_figures INTEGER NOT NULL DEFAULT 0,
                ingested_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS figures (
                id TEXT PRIMARY KEY,
                paper_id TEXT NOT NULL,
                page INTEGER NOT NULL,
                filepath TEXT NOT NULL,
                caption TEXT DEFAULT '',
                width INTEGER DEFAULT 0,
                height INTEGER DEFAULT 0,
                FOREIGN KEY (paper_id) REFERENCES papers(id)
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                paper_id TEXT NOT NULL,
                section_title TEXT DEFAULT '',
                page_start INTEGER DEFAULT 0,
                page_end INTEGER DEFAULT 0,
                FOREIGN KEY (paper_id) REFERENCES papers(id)
            )
            """
        )
        await db.commit()


def _file_hash(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for block in iter(lambda: f.read(8192), b""):
            h.update(block)
    return h.hexdigest()


def _guess_title(text_blocks: list[dict]) -> str:
    """Use the first large-font block as a rough title guess."""
    if not text_blocks:
        return ""
    first = max(text_blocks[:10], key=lambda b: b["font_size"], default=None)
    return first["text"][:200].strip() if first else ""


async def ingest_papers(
    settings: Settings,
    llm_client: LLMClient,
    collection: chromadb.Collection,
) -> dict:
    papers_dir = settings.papers_dir
    figures_dir = settings.figures_dir
    db_path = settings.sqlite_db_path

    os.makedirs(papers_dir, exist_ok=True)
    os.makedirs(figures_dir, exist_ok=True)

    pdf_files = [
        f for f in os.listdir(papers_dir) if f.lower().endswith(".pdf")
    ]

    async with aiosqlite.connect(db_path) as db:
        existing = set()
        async with db.execute("SELECT file_hash FROM papers") as cursor:
            async for row in cursor:
                existing.add(row[0])

    total_papers = 0
    total_chunks = 0
    total_figures = 0

    for filename in pdf_files:
        pdf_path = os.path.join(papers_dir, filename)
        fhash = _file_hash(pdf_path)

        if fhash in existing:
            logger.info("Skipping already-ingested paper: %s", filename)
            continue

        logger.info("Ingesting paper: %s", filename)
        paper_id = uuid.uuid4().hex[:12]

        text_blocks = extract_text_blocks(pdf_path)
        figures = extract_figures(pdf_path, figures_dir, paper_id)
        captions = extract_captions(text_blocks)

        for fig in figures:
            page = fig["page"]
            page_captions = captions.get(page, [])
            fig["caption"] = page_captions.pop(0) if page_captions else ""

        chunks = chunk_text(text_blocks)
        if not chunks:
            logger.warning("No text chunks extracted from %s", filename)
            continue

        chunks = await embed_chunks(llm_client, chunks)

        title = _guess_title(text_blocks)

        ids = []
        documents = []
        embeddings = []
        metadatas = []
        for chunk in chunks:
            chunk_id = f"{paper_id}_{uuid.uuid4().hex[:8]}"
            ids.append(chunk_id)
            documents.append(chunk["text"])
            embeddings.append(chunk["embedding"])
            metadatas.append(
                {
                    "paper_id": paper_id,
                    "section_title": chunk["section_title"],
                    "page_start": chunk["page_start"],
                    "page_end": chunk["page_end"],
                    "discipline_tags": "general",
                    "title": title,
                    "authors": "",
                }
            )

        batch_size = 500
        for start in range(0, len(ids), batch_size):
            end = start + batch_size
            collection.upsert(
                ids=ids[start:end],
                documents=documents[start:end],
                embeddings=embeddings[start:end],
                metadatas=metadatas[start:end],
            )

        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                "INSERT INTO papers (id, filename, title, authors, file_hash, num_chunks, num_figures) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (paper_id, filename, title, "", fhash, len(chunks), len(figures)),
            )
            for fig in figures:
                await db.execute(
                    "INSERT INTO figures (id, paper_id, page, filepath, caption, width, height) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        fig["figure_id"],
                        paper_id,
                        fig["page"],
                        fig["filepath"],
                        fig.get("caption", ""),
                        fig["width"],
                        fig["height"],
                    ),
                )
            for chunk_id, chunk in zip(ids, chunks):
                await db.execute(
                    "INSERT INTO chunks (id, paper_id, section_title, page_start, page_end) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (
                        chunk_id,
                        paper_id,
                        chunk["section_title"],
                        chunk["page_start"],
                        chunk["page_end"],
                    ),
                )
            await db.commit()

        total_papers += 1
        total_chunks += len(chunks)
        total_figures += len(figures)
        logger.info(
            "Paper %s: %d chunks, %d figures", filename, len(chunks), len(figures)
        )

    return {
        "papers_ingested": total_papers,
        "total_chunks": total_chunks,
        "total_figures": total_figures,
    }
