import sqlite3

import chromadb

from app.llm.client import LLMClient


class Retriever:
    def __init__(self, collection: chromadb.Collection, llm_client: LLMClient) -> None:
        self._collection = collection
        self._llm = llm_client

    async def search(
        self,
        query: str,
        n_results: int = 8,
        discipline_filter: list[str] | None = None,
    ) -> list[dict]:
        query_embedding = (await self._llm.embed([query]))[0]

        where_filter = None
        if discipline_filter:
            where_filter = {
                "$or": [
                    {"discipline_tags": {"$eq": tag}} for tag in discipline_filter
                ]
            }

        try:
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_filter,
                include=["documents", "metadatas", "distances"],
            )
        except Exception:
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=["documents", "metadatas", "distances"],
            )

        output: list[dict] = []
        if not results or not results.get("ids") or not results["ids"][0]:
            return output

        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            output.append(
                {
                    "text": doc,
                    "metadata": meta or {},
                    "distance": dist,
                }
            )
        return output

    def get_figures_for_chunks(
        self,
        chunk_results: list[dict],
        db_path: str | None = None,
    ) -> list[dict]:
        """Query SQLite for figures near retrieved chunks."""
        if db_path is None:
            from app.core.config import get_settings
            db_path = get_settings().sqlite_db_path

        paper_ids = set()
        pages = set()
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

        page_range = (min(pages) - 1, max(pages) + 1) if pages else (0, 9999)

        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            placeholders = ",".join("?" for _ in paper_ids)
            query = (
                f"SELECT id, paper_id, page, filepath, caption, width, height "
                f"FROM figures WHERE paper_id IN ({placeholders}) "
                f"AND page >= ? AND page <= ?"
            )
            params = list(paper_ids) + [page_range[0], page_range[1]]
            rows = conn.execute(query, params).fetchall()
            conn.close()
        except Exception:
            return []

        return [
            {
                "figure_id": row["id"],
                "paper_id": row["paper_id"],
                "page": row["page"],
                "filepath": row["filepath"],
                "caption": row["caption"] or "",
                "width": row["width"],
                "height": row["height"],
            }
            for row in rows
        ]
