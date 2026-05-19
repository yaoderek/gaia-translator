"""Vector retrieval with optional persona-aware re-ranking.

Pipeline (with persona):
  query → embed → pgvector top-K (K=candidate_pool, e.g. 20)
        → score(chunk) = (1 - cosine_distance) + λ * persona_overlap(chunk, persona)
        → diversity-cap (≤ max_per_paper chunks per paper)
        → top n_results

Pipeline (no persona):
  query → embed → pgvector top n_results (semantic only, original behavior)

Persona overlap is a normalized keyword Jaccard between the chunk
(text + section_title + paper title) and the union of persona fields:
papers_of_interest, concepts_focus, methods_focus, tech_stack, tags, bio.
"""

import logging
import re

import asyncpg
import numpy as np

from app.llm.client import LLMClient

logger = logging.getLogger(__name__)

# Tuning knobs. Kept module-level so eval notebook can monkey-patch them.
CANDIDATE_POOL = 20
PERSONA_WEIGHT = 0.35  # λ in the score formula
MAX_CHUNKS_PER_PAPER = 3

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9\-]{2,}")
_STOPWORDS = frozenset(
    {
        "the", "and", "for", "with", "from", "this", "that", "those", "these",
        "into", "over", "under", "between", "among", "than", "their", "there",
        "which", "where", "when", "while", "such", "have", "has", "had", "been",
        "being", "are", "was", "were", "will", "would", "could", "should",
        "about", "above", "after", "before", "across", "through", "within",
        "using", "used", "use", "uses", "also", "more", "less", "most", "least",
        "your", "you", "our", "ours", "they", "them", "its", "his", "her",
        "one", "two", "three", "many", "much", "some", "any", "all", "each",
        "other", "another", "based", "data", "model", "study", "paper",
    }
)


def _tokenize(text: str) -> set[str]:
    if not text:
        return set()
    return {t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS}


def _persona_tokens(persona: dict | None) -> set[str]:
    if not persona:
        return set()
    bag: set[str] = set()
    for key in (
        "papers_of_interest",
        "concepts_focus",
        "methods_focus",
        "tech_stack",
        "tags",
        "bio",
    ):
        bag |= _tokenize(persona.get(key) or "")
    return bag


def _persona_overlap_score(chunk: dict, persona_tokens: set[str]) -> float:
    """Normalized overlap in [0, 1]. Jaccard-like but uses chunk-token-count as denominator
    so a wide persona doesn't artificially deflate scores."""
    if not persona_tokens:
        return 0.0
    meta = chunk.get("metadata", {})
    chunk_tokens = (
        _tokenize(chunk.get("text", ""))
        | _tokenize(meta.get("section_title", ""))
        | _tokenize(meta.get("title", ""))
    )
    if not chunk_tokens:
        return 0.0
    overlap = chunk_tokens & persona_tokens
    return len(overlap) / max(1, min(len(chunk_tokens), 50))


def _apply_diversity_cap(chunks: list[dict], max_per_paper: int) -> list[dict]:
    seen: dict[str, int] = {}
    out: list[dict] = []
    for c in chunks:
        pid = c.get("metadata", {}).get("paper_id", "unknown")
        if seen.get(pid, 0) >= max_per_paper:
            continue
        seen[pid] = seen.get(pid, 0) + 1
        out.append(c)
    return out


class Retriever:
    def __init__(self, pool: asyncpg.Pool, llm_client: LLMClient) -> None:
        self._pool = pool
        self._llm = llm_client

    async def search(
        self,
        query: str,
        n_results: int = 8,
        discipline_filter: list[str] | None = None,
        persona: dict | None = None,
        candidate_pool: int | None = None,
        persona_weight: float | None = None,
        max_chunks_per_paper: int | None = None,
    ) -> list[dict]:
        """Search for relevant chunks, optionally re-ranking by persona overlap.

        Returns chunks shaped as {text, metadata{...page_start, page_end...}, distance,
        base_score, persona_score (if persona), final_score}.
        """
        del discipline_filter  # accepted for backward-compat; not used yet
        persona_tokens = _persona_tokens(persona)
        use_persona = bool(persona_tokens)

        pool_size = candidate_pool or (CANDIDATE_POOL if use_persona else n_results)
        weight = persona_weight if persona_weight is not None else PERSONA_WEIGHT
        cap = max_chunks_per_paper or MAX_CHUNKS_PER_PAPER

        query_embedding = (await self._llm.embed([query]))[0]
        vec = np.array(query_embedding, dtype=np.float32)

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, paper_id, section_title, page_start, page_end, content,
                       title, authors, discipline_tags,
                       embedding <=> $1::vector AS distance
                FROM chunks
                ORDER BY embedding <=> $1::vector
                LIMIT $2
                """,
                vec,
                pool_size,
            )

        candidates: list[dict] = []
        for row in rows:
            distance = float(row["distance"])
            base_score = max(0.0, 1.0 - distance)
            candidate = {
                "text": row["content"],
                "metadata": {
                    "paper_id": row["paper_id"],
                    "section_title": row["section_title"] or "",
                    "title": row["title"] or "",
                    "authors": row["authors"] or "",
                    "discipline_tags": row["discipline_tags"] or "general",
                    "page_start": int(row["page_start"] or 0),
                    "page_end": int(row["page_end"] or 0),
                },
                "distance": distance,
                "base_score": base_score,
                "persona_score": 0.0,
                "final_score": base_score,
            }
            candidates.append(candidate)

        if use_persona:
            for c in candidates:
                p_score = _persona_overlap_score(c, persona_tokens)
                c["persona_score"] = p_score
                c["final_score"] = c["base_score"] + weight * p_score
            candidates.sort(key=lambda c: c["final_score"], reverse=True)

        capped = _apply_diversity_cap(candidates, cap)
        return capped[:n_results]

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
                    try:
                        pi = int(p)
                    except (TypeError, ValueError):
                        continue
                    if pi > 0:
                        pages.add(pi)

        if not paper_ids:
            return []

        # If no real page info, fall back to all figures in the matched papers
        # (better than nothing — but means proximity is disabled for that query).
        if pages:
            page_lo = max(0, min(pages) - 1)
            page_hi = max(pages) + 1
        else:
            page_lo, page_hi = 0, 9999

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
