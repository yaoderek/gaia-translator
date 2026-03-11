import logging

import asyncpg
import numpy as np
from pgvector.asyncpg import register_vector

from app.llm.client import LLMClient

logger = logging.getLogger(__name__)


class Retriever:
    def __init__(self, pool: asyncpg.Pool, llm_client: LLMClient) -> None:
        self._pool = pool
        self._llm = llm_client

    async def search(
        self,
        query: str,
        n_results: int = 8,
        discipline_filter: list[str] | None = None,
    ) -> list[dict]:
        query_embedding = (await self._llm.embed([query]))[0]
        vec = np.array(query_embedding, dtype=np.float32)

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, paper_id, section_title, content, title, authors,
                       discipline_tags, embedding <=> $1::vector AS distance
                FROM chunks
                ORDER BY embedding <=> $1::vector
                LIMIT $2
                """,
                vec,
                n_results,
            )

        return [
            {
                "text": row["content"],
                "metadata": {
                    "paper_id": row["paper_id"],
                    "section_title": row["section_title"] or "",
                    "title": row["title"] or "",
                    "authors": row["authors"] or "",
                    "discipline_tags": row["discipline_tags"] or "general",
                },
                "distance": float(row["distance"]),
            }
            for row in rows
        ]

    async def get_figures_for_chunks(
        self,
        chunk_results: list[dict],
    ) -> list[dict]:
        paper_ids: set[str] = set()
        pages: set[int] = set()
        for chunk in chunk_results:
            meta = chunk.get("metadata", {})
            pid = meta.get("paper_id")
            if pid:
                paper_ids.add(pid)
            for key in ("page", "page_start", "page_end"):
                p = meta.get(key)
                if p is not None:
                    pages.add(int(p))

        if not paper_ids:
            return []

        page_lo = min(pages) - 1 if pages else 0
        page_hi = max(pages) + 1 if pages else 9999

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, paper_id, page, s3_key, caption, width, height
                FROM figures
                WHERE paper_id = ANY($1::text[])
                  AND page >= $2 AND page <= $3
                """,
                list(paper_ids),
                page_lo,
                page_hi,
            )

        return [
            {
                "figure_id": row["id"],
                "paper_id": row["paper_id"],
                "page": row["page"],
                "s3_key": row["s3_key"],
                "caption": row["caption"] or "",
                "width": row["width"],
                "height": row["height"],
            }
            for row in rows
        ]
