"""Run the eval set against the live RAG pipeline and dump JSON for the notebook.

Usage (from `backend/`):
    python -m app.eval.run --out eval_results.json

The script connects to the same Postgres + OpenAI that the running app uses
(reads .env via app.core.config). It does NOT call the LLM for translation —
it only runs retrieval and computes retrieval/personalization metrics. This
keeps eval cost cheap and deterministic.

For citation-faithfulness scoring, run the optional `--with-llm` flag which
also generates a translation for each item via the streaming engine and
computes citation_faithfulness. That hits the LLM and is slow.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from dataclasses import asdict, dataclass
from typing import Any

from app.core.config import get_settings
from app.db.postgres import close_pool, init_pool
from app.eval.eval_set import GOLD_SET
from app.eval.metrics import (
    citation_faithfulness,
    persona_concept_coverage,
    persona_drift,
    persona_score_gain,
    score_query,
)
from app.llm.client import LLMClient
from app.rag.retriever import Retriever

logging.basicConfig(level=logging.WARNING)


@dataclass
class RunResult:
    item_id: str
    query: str
    source_discipline: str
    target_discipline: str
    has_persona: bool
    chunks: list[dict[str, Any]]
    metrics: dict[str, float]
    persona_metrics: dict[str, float] | None = None
    citation_eval: dict | None = None


async def _run_one(
    retriever: Retriever,
    item: dict,
    persona: dict | None = None,
) -> tuple[list[dict], dict]:
    chunks = await retriever.search(
        query=item["query"],
        n_results=8,
        persona=persona,
    )
    metrics = score_query(chunks, item.get("gold_title_substrings", []))
    return chunks, metrics


async def run_all(out_path: str, with_llm: bool = False) -> None:
    settings = get_settings()
    pool = await init_pool(settings.database_url)
    try:
        llm_client = LLMClient(settings)
        retriever = Retriever(pool, llm_client)

        results: list[dict] = []
        for item in GOLD_SET:
            baseline_chunks, baseline_metrics = await _run_one(retriever, item, persona=None)

            persona = item.get("persona")
            persona_chunks: list[dict] | None = None
            persona_metrics_block: dict | None = None
            if persona:
                persona_chunks, persona_metrics = await _run_one(
                    retriever, item, persona=persona
                )
                persona_metrics_block = {
                    "retrieval": persona_metrics,
                    "drift_vs_baseline": persona_drift(baseline_chunks, persona_chunks),
                    "concept_coverage": persona_concept_coverage(persona_chunks, persona),
                    "score_gain": persona_score_gain(baseline_chunks, persona_chunks),
                }

            citation_block = None
            if with_llm:
                # Local import to avoid loading translation engine when not needed
                from app.llm.translator import TranslationEngine, _build_citations
                from app.models.schemas import TranslateRequest
                from app.core.disciplines import Discipline

                engine = TranslationEngine(llm_client, retriever)
                req = TranslateRequest(
                    text=item["query"],
                    source_discipline=Discipline(item["source_discipline"]),
                    target_discipline=Discipline(item["target_discipline"]),
                )
                # Stream and collect full text
                full = ""
                async for ev in engine.translate_stream(req, target_persona=persona):
                    if ev.startswith("data: ") and '"type": "token"' in ev:
                        payload = json.loads(ev[6:].strip())
                        full += payload.get("content", "")
                used_chunks = persona_chunks if persona_chunks else baseline_chunks
                cites = _build_citations(used_chunks)
                citation_block = citation_faithfulness(full, cites, used_chunks)
                citation_block["rendered_excerpt"] = full[:600]

            results.append(asdict(RunResult(
                item_id=item.get("id", "?"),
                query=item["query"],
                source_discipline=item["source_discipline"],
                target_discipline=item["target_discipline"],
                has_persona=bool(persona),
                chunks=_clean_chunks(persona_chunks or baseline_chunks),
                metrics=baseline_metrics,
                persona_metrics=persona_metrics_block,
                citation_eval=citation_block,
            )))
            # Always also include the baseline chunks under a sibling key for plotting
            results[-1]["baseline_chunks"] = _clean_chunks(baseline_chunks)
            results[-1]["baseline_metrics"] = baseline_metrics
            print(
                f"[{item.get('id')}] recall@8={baseline_metrics['recall_at_k']:.2f} "
                f"mrr={baseline_metrics['mrr']:.2f} "
                f"diversity={baseline_metrics['paper_diversity']:.2f}"
                + (f" | drift={persona_metrics_block['drift_vs_baseline']:.2f}" if persona_metrics_block else "")
            )

        with open(out_path, "w") as f:
            json.dump({"results": results}, f, indent=2)
        print(f"\nWrote {len(results)} items to {out_path}")
    finally:
        await close_pool()


def _clean_chunks(chunks: list[dict]) -> list[dict]:
    """Strip embeddings/large fields so JSON stays manageable."""
    out = []
    for c in chunks:
        meta = c.get("metadata", {})
        out.append({
            "paper_id": meta.get("paper_id"),
            "title": meta.get("title"),
            "section_title": meta.get("section_title"),
            "page_start": meta.get("page_start"),
            "page_end": meta.get("page_end"),
            "text_excerpt": (c.get("text") or "")[:300],
            "distance": c.get("distance"),
            "base_score": c.get("base_score"),
            "persona_score": c.get("persona_score"),
            "final_score": c.get("final_score"),
        })
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="eval_results.json")
    parser.add_argument(
        "--with-llm",
        action="store_true",
        help="Also call the LLM to compute citation-faithfulness (slower, costs tokens).",
    )
    args = parser.parse_args()
    asyncio.run(run_all(args.out, with_llm=args.with_llm))


if __name__ == "__main__":
    sys.exit(main())
