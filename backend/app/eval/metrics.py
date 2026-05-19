"""Retrieval and personalization metrics for the RAG eval harness.

Design philosophy: every metric is implemented as a small, pure function that
takes the list of retrieved chunks (dicts) and a gold spec, and returns a
float (or dict). They are intentionally interpretable — no learned judges —
so the eval notebook can explain *why* a number moved.

Metric reference
================

retrieval
---------
- `recall_at_k(chunks, gold_substrings, k)` —
    Did any chunk in the top-k come from a *gold* paper (title contains any
    of the gold substrings)? Returns 1.0 or 0.0. Most basic "did we find it"
    signal. This is the headline metric.

- `mean_reciprocal_rank(chunks, gold_substrings)` —
    1 / (rank of first gold chunk), or 0 if none. Higher = the right paper
    came up sooner. Sensitive to ordering, unlike Recall@k.

- `precision_at_k(chunks, gold_substrings, k)` —
    Fraction of top-k chunks that are from gold papers. Useful when *multiple*
    gold papers exist (the persona pairs use multi-gold).

- `paper_diversity(chunks)` —
    Unique papers in top-k / len(top-k). 1.0 = every chunk a different paper.
    Low values mean one paper is monopolizing the prompt — bad for translation.

- `mean_cosine_similarity(chunks)` —
    Average (1 - distance) over top-k. A *raw* signal of how confident the
    semantic search was. Useful as a comparator, not a quality metric.

personalization
---------------
- `persona_drift(baseline_chunks, persona_chunks)` —
    1 - Jaccard(chunk_ids_baseline, chunk_ids_persona). 0 = persona changed
    nothing; 1 = top-k completely different. Diagnostic: tells you whether
    your persona signal is even reaching the retriever.

- `persona_concept_coverage(chunks, persona)` —
    Fraction of persona-declared concept tokens that appear in at least one
    retrieved chunk's text. Measures "did we surface anything relevant to
    what the user cares about?"

- `persona_score_gain(baseline_chunks, persona_chunks)` —
    Mean(final_score) for persona-rerank minus mean(base_score) for the
    same chunks under the baseline. Reports the absolute score lift.

citation faithfulness (text-overlap based, no LLM judge)
--------------------------------------------------------
- `citation_faithfulness(rendered_text, citations, chunks)` —
    For each [n] citation made in the rendered translation, check that *some*
    chunk from paper-n contributes at least one trigram to the surrounding
    claim text. This is conservative but fast and deterministic. Returns
    {n_cited: int, n_supported: int, fraction: float}.
"""

import re

# Reuse the same tokenizer as the retriever for consistency.
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


def _tokens(text: str) -> set[str]:
    if not text:
        return set()
    return {t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS}


def _trigrams(text: str) -> set[str]:
    toks = _TOKEN_RE.findall((text or "").lower())
    return {" ".join(toks[i : i + 3]) for i in range(len(toks) - 2)}


def _chunk_is_gold(chunk: dict, gold_substrings: list[str]) -> bool:
    title = (chunk.get("metadata", {}).get("title") or "").lower()
    return any(s.lower() in title for s in gold_substrings)


# ---------------------------------------------------------------------------
# Retrieval metrics
# ---------------------------------------------------------------------------


def recall_at_k(chunks: list[dict], gold_substrings: list[str], k: int = 8) -> float:
    if not gold_substrings:
        return 0.0
    for c in chunks[:k]:
        if _chunk_is_gold(c, gold_substrings):
            return 1.0
    return 0.0


def mean_reciprocal_rank(chunks: list[dict], gold_substrings: list[str]) -> float:
    if not gold_substrings:
        return 0.0
    for i, c in enumerate(chunks, 1):
        if _chunk_is_gold(c, gold_substrings):
            return 1.0 / i
    return 0.0


def precision_at_k(chunks: list[dict], gold_substrings: list[str], k: int = 8) -> float:
    if not chunks or not gold_substrings:
        return 0.0
    top = chunks[:k]
    hits = sum(1 for c in top if _chunk_is_gold(c, gold_substrings))
    return hits / len(top)


def paper_diversity(chunks: list[dict]) -> float:
    if not chunks:
        return 0.0
    papers = {c.get("metadata", {}).get("paper_id", "?") for c in chunks}
    return len(papers) / len(chunks)


def mean_cosine_similarity(chunks: list[dict]) -> float:
    if not chunks:
        return 0.0
    sims = [max(0.0, 1.0 - float(c.get("distance", 1.0))) for c in chunks]
    return sum(sims) / len(sims)


# ---------------------------------------------------------------------------
# Personalization metrics
# ---------------------------------------------------------------------------


def _chunk_id(chunk: dict) -> str:
    """Use (paper_id, first 60 chars of text) as a stable id across reranks."""
    meta = chunk.get("metadata", {})
    pid = meta.get("paper_id", "?")
    text_head = (chunk.get("text") or "")[:60]
    return f"{pid}::{text_head}"


def persona_drift(baseline_chunks: list[dict], persona_chunks: list[dict]) -> float:
    a = {_chunk_id(c) for c in baseline_chunks}
    b = {_chunk_id(c) for c in persona_chunks}
    if not a and not b:
        return 0.0
    return 1.0 - (len(a & b) / max(1, len(a | b)))


def persona_concept_coverage(chunks: list[dict], persona: dict) -> float:
    persona_text = " ".join(
        (persona.get(k) or "")
        for k in ("concepts_focus", "methods_focus", "tech_stack", "papers_of_interest")
    )
    persona_toks = _tokens(persona_text)
    if not persona_toks:
        return 0.0
    all_chunk_toks: set[str] = set()
    for c in chunks:
        all_chunk_toks |= _tokens(c.get("text", ""))
    if not all_chunk_toks:
        return 0.0
    return len(persona_toks & all_chunk_toks) / len(persona_toks)


def persona_score_gain(
    baseline_chunks: list[dict], persona_chunks: list[dict]
) -> float:
    """Average per-chunk final_score - base_score for the persona run.

    Reports how much the rerank actually lifted scores.
    """
    del baseline_chunks
    gains = [
        float(c.get("final_score", 0.0)) - float(c.get("base_score", 0.0))
        for c in persona_chunks
    ]
    if not gains:
        return 0.0
    return sum(gains) / len(gains)


# ---------------------------------------------------------------------------
# Citation faithfulness
# ---------------------------------------------------------------------------


def citation_faithfulness(
    rendered_text: str, citations: list[dict], chunks: list[dict]
) -> dict:
    """For every [n] cite in `rendered_text`, check that the chunk(s) attributed
    to citation n share at least one trigram with the sentence containing [n].
    """
    # Map citation index -> paper_id (and excerpt fallback).
    idx_to_paper: dict[int, str] = {
        int(c.get("index", 0)): c.get("paper_id", "")
        for c in citations
        if c.get("index") is not None
    }
    paper_to_chunks: dict[str, list[dict]] = {}
    for c in chunks:
        pid = c.get("metadata", {}).get("paper_id", "")
        paper_to_chunks.setdefault(pid, []).append(c)

    # Split into sentences (cheap heuristic).
    sentences = re.split(r"(?<=[.!?])\s+", rendered_text or "")
    n_cited = 0
    n_supported = 0
    detail: list[dict] = []
    cite_re = re.compile(r"\[(\d+)\]")
    for sent in sentences:
        matches = cite_re.findall(sent)
        if not matches:
            continue
        sent_trigrams = _trigrams(sent)
        for raw in matches:
            n = int(raw)
            n_cited += 1
            paper_id = idx_to_paper.get(n, "")
            chunks_for = paper_to_chunks.get(paper_id, [])
            supported = False
            for ch in chunks_for:
                if sent_trigrams & _trigrams(ch.get("text", "")):
                    supported = True
                    break
            if supported:
                n_supported += 1
            detail.append({"n": n, "sentence": sent.strip()[:160], "supported": supported})
    return {
        "n_cited": n_cited,
        "n_supported": n_supported,
        "fraction": (n_supported / n_cited) if n_cited else 0.0,
        "detail": detail,
    }


# ---------------------------------------------------------------------------
# Composite scorer
# ---------------------------------------------------------------------------


def score_query(
    chunks: list[dict], gold_substrings: list[str], k: int = 8
) -> dict:
    """Bundle all retrieval-only metrics into one dict for a single query run."""
    return {
        "recall_at_k": recall_at_k(chunks, gold_substrings, k),
        "mrr": mean_reciprocal_rank(chunks, gold_substrings),
        "precision_at_k": precision_at_k(chunks, gold_substrings, k),
        "paper_diversity": paper_diversity(chunks),
        "mean_cosine": mean_cosine_similarity(chunks),
    }
