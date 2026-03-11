import json
import logging

from app.core.prompts import build_translation_prompt, build_streaming_prompt
from app.llm.client import LLMClient
from app.models.schemas import (
    Citation,
    FigureRef,
    TranslateRequest,
    TranslateResponse,
)
from app.rag.retriever import Retriever

logger = logging.getLogger(__name__)

MAX_FIGURES = 10


def _filter_meaningful_figures(figures: list[dict]) -> list[dict]:
    """Keep only figures with captions (real figures, not PDF sub-images), capped."""
    with_captions = [f for f in figures if f.get("caption", "").strip()]
    if with_captions:
        return with_captions[:MAX_FIGURES]
    return figures[:MAX_FIGURES]


class TranslationEngine:
    def __init__(self, llm_client: LLMClient, retriever: Retriever) -> None:
        self._llm = llm_client
        self._retriever = retriever

    async def translate(self, request: TranslateRequest) -> TranslateResponse:
        discipline_filter = [
            request.source_discipline.value,
            request.target_discipline.value,
            "general",
        ]
        chunks = await self._retriever.search(
            query=request.text,
            n_results=8,
            discipline_filter=discipline_filter,
        )

        figures = _filter_meaningful_figures(
            self._retriever.get_figures_for_chunks(chunks)
        )

        messages = build_translation_prompt(
            source=request.source_discipline,
            target=request.target_discipline,
            retrieved_context=chunks,
            figure_descriptions=figures,
        )
        messages.append({"role": "user", "content": request.text})

        raw = await self._llm.chat(messages, temperature=0.3)
        return _parse_response(raw, chunks, figures)

    async def translate_stream(self, request: TranslateRequest):
        """Yield SSE-formatted events: metadata first, then plain-text tokens, then follow-ups."""
        discipline_filter = [
            request.source_discipline.value,
            request.target_discipline.value,
            "general",
        ]
        chunks = await self._retriever.search(
            query=request.text,
            n_results=8,
            discipline_filter=discipline_filter,
        )
        figures = _filter_meaningful_figures(
            self._retriever.get_figures_for_chunks(chunks)
        )

        messages = build_streaming_prompt(
            source=request.source_discipline,
            target=request.target_discipline,
            retrieved_context=chunks,
            figure_descriptions=figures,
        )
        messages.append({"role": "user", "content": request.text})

        metadata = {
            "type": "metadata",
            "citations": _build_citations(chunks),
            "figures": _build_figure_refs(figures),
        }
        yield f"data: {json.dumps(metadata)}\n\n"

        full_text = ""
        async for token in self._llm.chat_stream(messages, temperature=0.3):
            full_text += token
            payload = {"type": "token", "content": token}
            yield f"data: {json.dumps(payload)}\n\n"

        follow_ups = _extract_follow_ups(full_text)
        if follow_ups:
            yield f"data: {json.dumps({'type': 'follow_ups', 'questions': follow_ups})}\n\n"

        yield "data: [DONE]\n\n"


def _extract_follow_ups(text: str) -> list[str]:
    """Pull workstream items from the streamed text after the workstreams header."""
    for marker in ("Potentially Relevant Domain Workstreams", "Domain Workstreams", "Workstreams"):
        idx = text.lower().rfind(marker.lower())
        if idx != -1:
            break
    else:
        return []

    tail = text[idx:]
    items = []
    for line in tail.split("\n"):
        stripped = line.strip().lstrip("0123456789.-)*• ")
        if stripped and len(stripped) > 15 and not stripped.lower().startswith("potentially"):
            items.append(stripped)
    return items[:4]


def _build_citations(chunks: list[dict]) -> list[dict]:
    """One citation per unique paper_id. Merges excerpts from multiple chunks."""
    paper_order: list[str] = []
    paper_map: dict[str, dict] = {}

    for chunk in chunks:
        meta = chunk.get("metadata", {})
        paper_id = meta.get("paper_id", "unknown")
        if paper_id not in paper_map:
            paper_order.append(paper_id)
            paper_map[paper_id] = {
                "paper_id": paper_id,
                "title": meta.get("title", ""),
                "authors": meta.get("authors", ""),
                "excerpt": chunk.get("text", "")[:300],
                "doi": meta.get("doi"),
            }

    return [
        {"index": i + 1, **paper_map[pid]}
        for i, pid in enumerate(paper_order)
    ]


def _build_figure_refs(figures: list[dict]) -> list[dict]:
    return [
        {
            "figure_id": f.get("figure_id", ""),
            "paper_id": f.get("paper_id", ""),
            "caption": f.get("caption", ""),
            "page": f.get("page", 0),
        }
        for f in figures
    ]


def _parse_response(
    raw: str,
    chunks: list[dict],
    figures: list[dict],
) -> TranslateResponse:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("LLM response was not valid JSON, wrapping as translation text")
        data = {"translation": raw}

    llm_citations = data.get("citations", [])
    if llm_citations:
        citations = [Citation(**c) for c in llm_citations]
    else:
        citations = [Citation(**c) for c in _build_citations(chunks)]

    llm_figures = data.get("figures", [])
    if llm_figures:
        fig_refs = [FigureRef(**f) for f in llm_figures]
    else:
        fig_refs = [FigureRef(**f) for f in _build_figure_refs(figures)]

    return TranslateResponse(
        translation=data.get("translation", raw),
        citations=citations,
        figures=fig_refs,
        follow_up_questions=data.get("follow_up_questions", []),
    )
