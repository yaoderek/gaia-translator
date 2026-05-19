# RAG, LLM Integration, and System Architecture

This document explains how retrieval-augmented generation works in GAIA Translator, what the system prioritizes, how context feeds into the LLM, and the rationale behind the design.

**As of the persona-aware update**, retrieval is no longer pure semantic search — when a logged-in user has a non-empty persona, retrieval runs a candidate pool through a keyword-overlap reranker that mixes cosine similarity with persona match. See §1.2 and §6.

---

## 1. End-to-end RAG flow

### 1.1 Ingestion (write path)

When a PDF is uploaded, the following pipeline runs:

```
PDF bytes → PyMuPDF extract → text blocks + figures + captions
         → section-aware chunking → embeddings (OpenAI) → Postgres + Storage
```

**Step 1 — Extract (`extractor.py`)**

- **Text**: Each page is parsed with PyMuPDF `get_text("dict")`. Every text block gets `page`, `bbox`, `font_size`, and concatenated `text`. Non-text blocks (e.g. images) are skipped. Font size is used later to detect section headers.
- **Figures**: `get_images(full=True)` returns every embedded image. Each is extracted by xref, saved as PNG, and recorded with `paper_id`, `page`, dimensions. No filtering yet — logos and subfigures are included.
- **Captions**: A regex finds blocks that start with "Fig." or "Figure". Captions are grouped by page and later attached to figures on the same page (first caption per page to first figure on that page).

**Step 2 — Chunk (`chunker.py`)**

- **Section detection**: Median font size over all blocks is computed; blocks with font size ≥ median + 1.5 and fewer than 20 words are treated as section headers (e.g. "Abstract", "Methods"). Consecutive body blocks are grouped under the current header.
- **Chunk boundaries**: Within each section, text is concatenated and split into chunks of at most 512 tokens (whitespace-split). Consecutive chunks overlap by 100 tokens to avoid splitting concepts. Each chunk stores `section_title`, `page_start`, `page_end`.
- **Rationale**: Section-aware chunking keeps "Introduction" or "Results" content together when possible and gives the LLM clearer context (section title in metadata). Overlap reduces boundary effects for semantic search.

**Step 3 — Embed and store**

- Chunk text is sent to OpenAI `text-embedding-3-small` in batches of 100. Each chunk gets a 1536-dimensional vector.
- Paper metadata (title from filename heuristic or first non-journal large-font block), file hash, and S3 key are stored in `papers`. Each chunk is inserted into `chunks` with `content`, `embedding` (pgvector), `title`, `authors`, `section_title`, `page_start`, `page_end`, `discipline_tags` (currently always `"general"`). Figures are stored in `figures` with `s3_key`, `caption`, page.

**Step 4 — Figures**

- All extracted images are uploaded to Supabase Storage. Figures with captions are preferred at read time (see below) but no filtering is done at ingest.

---

### 1.2 Retrieval (read path)

When the user requests a translation:

```
User text → embed query → pgvector k-NN → top-8 chunks
         → figures for those chunks (by paper_id + page range) → filter to 10 meaningful figures
         → format context + figures into system prompt → LLM (streaming or not)
```

**Step 1 — Vector search + optional persona rerank (`retriever.py`)**

- The user’s input is embedded with the same OpenAI embedding model.
- Postgres runs `ORDER BY embedding <=> $query_vector LIMIT N`, where `N` is `CANDIDATE_POOL` (20) when a persona is present, or `n_results` (8) otherwise. `<=>` is pgvector cosine distance.
- The returned rows now include `page_start, page_end` (this used to be missing — see §7 *Known limitations / bug-fix log*).
- **If a persona is present** (any of `bio, tags, papers_of_interest, concepts_focus, methods_focus, tech_stack` non-empty), each candidate is scored as

  ```
  final_score = (1 - distance) + PERSONA_WEIGHT * persona_overlap
  ```

  where `persona_overlap ∈ [0, 1]` is a normalized token-overlap between the chunk (text + section_title + title) and the union of persona fields, lower-cased and stopword-filtered. The candidates are re-sorted by `final_score`.
- A **paper-diversity cap** (`MAX_CHUNKS_PER_PAPER`, default 3) then trims so no single paper monopolizes the prompt. Finally we keep the top `n_results`.
- Tuning knobs (module-level so notebooks can monkey-patch): `CANDIDATE_POOL=20`, `PERSONA_WEIGHT=0.35`, `MAX_CHUNKS_PER_PAPER=3`.

**Step 2 — Figures for retrieved chunks**

- From the 8 chunks we collect all `paper_id`s and the union of `page_start`/`page_end` (and any `page` in metadata).
- We query `figures` for those papers and pages in the expanded range `[min_page - 1, max_page + 1]` so figures near the retrieved text are included.
- **Prioritization**: Up to 10 figures are passed to the prompt. We prefer figures that have a non-empty caption (assumed to be real figures, not logos/subfigures). `_filter_meaningful_figures`: if any figure has a caption, we take only those (up to 10); otherwise we take the first 10. So the system prioritizes **figures with captions** and **figures on pages close to retrieved chunks**.

**Step 3 — Citation numbering**

- Chunks can come from multiple papers and multiple chunks per paper. For the LLM we assign **one citation index per unique paper** (and deduplicate by normalized title so the same paper under two ingestions doesn’t get two numbers). So the prompt might show chunks labeled `[1]`, `[1]`, `[2]`, `[2]`, `[2]`, `[3]` — the LLM is told that `[n]` denotes a unique paper and must only cite those indices. The references panel is built from the same deduplicated list, so citation indices in the text match the list.

---

## 2. What the RAG prioritizes

- **Semantic relevance**: The only retrieval criterion is cosine similarity between the query embedding and chunk embeddings. The 8 closest chunks are used regardless of paper or section. So the system prioritizes **meaning** over source or structure.
- **Section and paper context**: Each chunk carries `section_title` and paper `title` in metadata. The prompt formats these so the model knows which paper and section a passage came from and can cite and describe relevance accordingly.
- **Figures near the evidence**: Figures are not chosen by embedding; they are chosen by **proximity** to the retrieved chunks (same papers, nearby pages). Then we prioritize up to 10 figures **with captions** to avoid clutter from small or decorative images.
- **Stable, deduplicated citations**: By assigning one index per unique paper (and merging by title), we avoid duplicate references and keep citation indices aligned between prompt and UI.

What we do **not** do (by design, for simplicity): filter by discipline at retrieval time, re-rank chunks with a cross-encoder, or embed figure images.

---

## 3. How RAG feeds into the LLM

### 3.1 Message structure

- **System message**: One large system message that includes:
  - **Role and task**: GAIA, translate from source discipline to target discipline for a geohazard lab.
  - **Discipline definitions**: Short descriptions and key concepts for source and target (from `DISCIPLINE_INFO`).
  - **Translation guidelines**: Map jargon, be practical, be concrete about implications, cite with `[n]`.
  - **Output structure**: For streaming, the required three sections (overview, relevance, workstreams) and the HTML comment markers.
  - **Retrieved literature**: Block of text with each chunk prefixed by `[n] paper_id=... | title="..." | section="..."` and then the chunk text. The LLM is told that `[n]` is the citation index for that paper.
  - **Figures**: A list of `[Fig: paper_id/fig_id] page X: caption` so the model can refer to figures when relevant.
- **User message**: The raw user input (the text to translate).

So the model sees: fixed instructions + full retrieved text + figure captions + the exact user string. It never sees the PDF or images; only text and captions.

### 3.2 Streaming vs non-streaming

- **Streaming** (default in the UI): We use `build_streaming_prompt`, which asks for plain markdown in three sections with `<!-- SECTION: ... -->` markers. We do not use `response_format: json_object`. The stream is sent to the client; citations and figures were already sent in a first SSE event from `_build_citations(chunks)` and `_build_figure_refs(figures)` so the UI can show references and thumbnails immediately. Follow-ups are parsed from the streamed text (e.g. after "Potentially Relevant Domain Workstreams") and sent in a separate SSE event.
- **Non-streaming**: Uses `build_translation_prompt` and requests JSON (translation, citations, figures, follow_up_questions). Used for non-UI callers if any.

Design choice: streaming improves perceived performance and allows the frontend to show citations/figures before the full answer; the tradeoff is that we don’t get structured JSON from the stream, so we rely on section markers and post-hoc parsing for follow-ups.

### 3.3 Temperature and determinism

- Temperature is fixed at 0.3 to keep outputs stable and grounded in the retrieved context rather than drifting.

---

## 4. System design architecture

### 4.1 High-level layout

```
┌─────────────────────────────────────────────────────────────────┐
│                         Browser (React)                          │
│  TranslatorPanel, PaperUpload, TranslationOutput, CitationPanel  │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP / SSE
┌────────────────────────────▼────────────────────────────────────┐
│                    Fly.io (stateless app)                        │
│  FastAPI: /api/translate (SSE), /api/papers, /api/papers/upload, │
│           /api/figures/{id}, /api/papers/{id}/pdf                │
│  TranslationEngine ← Retriever + LLMClient                       │
└──────────┬─────────────────────────────────────┬─────────────────┘
           │                                     │
           │ asyncpg                             │ httpx (OpenAI + Supabase Storage)
           ▼                                     ▼
┌──────────────────────┐              ┌─────────────────────────────┐
│  Supabase Postgres   │              │  OpenAI API                 │
│  • papers            │              │  • embeddings (text-embedding-3-small) │
│  • chunks (pgvector)  │              │  • chat (gpt-4o)             │
│  • figures           │              └─────────────────────────────┘
└──────────────────────┘              ┌─────────────────────────────┐
                                      │  Supabase Storage            │
                                      │  • papers/{id}/{filename}    │
                                      │  • figures/{id}.png          │
                                      └─────────────────────────────┘
```

### 4.2 Design decisions

- **Single embedding model for query and chunks**: Same model (OpenAI text-embedding-3-small) for indexing and querying keeps the similarity space consistent and avoids cross-model mismatch.
- **No discipline filter in SQL**: Chunks are not yet tagged by discipline; retrieval is purely semantic. Filtering can be added later with a `WHERE discipline_tags = ANY($filter)` when we have per-chunk or per-paper tags.
- **Section-aware chunking**: Preserves document structure and gives the model section context (e.g. "Methods") without extra re-ranking or multi-vector schemes.
- **Figures by proximity, not by embedding**: Figures are expensive to embed and not all PDF figures are meaningful. We use page proximity to retrieved chunks and caption presence as a proxy for "meaningful figure," which is simple and avoids a separate figure-embedding pipeline.
- **Citations from retrieval, not from LLM**: The references list is built from the retrieved chunks (deduplicated by paper and title). The LLM only produces inline `[n]` references. So we never trust the model to invent citations; we only trust it to point into the provided context.
- **Stateless app + Supabase**: The Fly process holds no durable state. All state is in Postgres and Storage so we can scale, restart, and deploy without re-ingesting or attaching volumes.
- **Streaming with early metadata**: Sending citations and figure refs in the first SSE event lets the UI render references and thumbnails while the model streams the answer, improving perceived speed and clarity.

---

## 6. Persona-aware personalization

### 6.1 What's stored

The `personas` table now has these user-editable text columns:

| Column | Used by | Purpose |
| --- | --- | --- |
| `username` | display only | Header label. |
| `discipline` | prompt | Picks the target's domain-default key concepts. |
| `bio` | prompt + rerank | Free-text reader context (first-person paragraph). |
| `tags` | rerank | Free-form keywords. Lowest-priority signal. |
| `papers_of_interest` | rerank + prompt | Titles / DOIs the user reads or cites. Newline-separated. |
| `concepts_focus` | rerank + prompt | Concepts the user wants emphasized. |
| `methods_focus` | rerank + prompt | Methodologies the user uses or wants to learn. |
| `tech_stack` | rerank + prompt | Tools, languages, libraries — used to frame examples. |

All are TEXT (newline- or comma-separated for v1). JSONB is a future migration if structure becomes useful.

### 6.2 How persona reaches the LLM

Two separate paths:

1. **Retrieval rerank** (mechanical, deterministic): persona tokens shift which chunks reach the top-8. This is the *only* way personalization affects *what facts* the LLM has access to.
2. **System prompt** (`_format_persona_block` in `core/prompts.py`): when at least one persona field is non-empty, we inject a `## Reader Context` block listing the user's papers / concepts / methods / stack as bullets, with the instruction to frame examples in those terms. This affects *how* the LLM presents the facts, not *which* facts it has.

Both are silent no-ops when the user has no persona — anonymous users get the unpersonalized pipeline unchanged.

### 6.3 Frontend surface

A new dedicated **Profile** tab (rendered by `components/ProfilePage.tsx`) provides full editing of all persona fields. The existing quick-edit `PersonaModal` still works for username/discipline/bio/tags. Users toggle between **Translate** and **Profile** in the header.

### 6.4 What this does NOT do

- No vector embedding of the persona. The signal is purely lexical/keyword. This is intentional — interpretable and zero added latency. A future iteration could embed the persona and add a dense similarity term to `final_score`.
- No cross-encoder reranker (e.g. bge-reranker). Persona overlap is fast and explainable; a learned reranker would be the next upgrade if evals show ceiling.
- No personalization for anonymous users. The translate endpoint reads persona only when a Supabase JWT is present.

---

## 7. Known limitations and recently-fixed bugs

| Status | Item | Notes |
| --- | --- | --- |
| ✅ Fixed | Retriever SELECT did not return `page_start`/`page_end`, silently disabling the figure-proximity filter (`get_figures_for_chunks` always saw zero pages → `page_lo=0, page_hi=9999`). | Now selected and returned in metadata. |
| ✅ Fixed | `authors` was always inserted as `""` during ingest. | `extract_authors` does best-effort PDF front-matter parsing. Imperfect — review for important papers. |
| ✅ Fixed | No paper-diversity in top-8 — one paper could fill all slots. | `MAX_CHUNKS_PER_PAPER=3` cap. |
| 🟡 Open | Per-chunk page tracking is coarse: when a section spans pages 3–10 and splits into 3 chunks, all 3 chunks claim `page_start=3, page_end=10`. Affects figure-proximity precision. | Requires chunker rewrite to track per-token page. Deferred until evals show it matters. |
| 🟡 Open | Long user queries are embedded as one vector — semantic signal averages out. | Consider query expansion or sentence-level retrieval. |
| 🟡 Open | `discipline_filter` is plumbed but unused (all chunks `discipline_tags='general'`). | Activate when papers are tagged at ingest. |
| 🟡 Open | `doi` referenced in `Citation` but never populated. Minor cosmetic. | Needs DOI extraction in ingest. |

---

## 8. Evaluation

The eval harness lives at `backend/app/eval/` with:

- `eval_set.py` — hand-curated gold queries (with optional personas) keyed against the 6 starter papers.
- `metrics.py` — pure-function retrieval and personalization metrics (Recall@k, MRR, precision, paper diversity, persona drift, concept coverage, citation faithfulness).
- `run.py` — entry point: `python -m app.eval.run --out eval_results.json [--with-llm]`.

The companion notebook `notebooks/rag_evals.ipynb` loads results, visualizes each metric, and explains how to interpret + debug low numbers. Designed to be read end-to-end as a teaching artifact.

---

## 9. Summary

- **RAG**: User text is embedded; the 8 closest chunks by cosine distance are fetched from Postgres. Figures from the same papers and nearby pages are added (up to 10, preferring captioned). Chunks and figure captions are formatted into the system prompt with per-paper citation indices; the user message is the raw input. The LLM translates and cites using only that context.
- **Priorities**: Semantic relevance first, then section/paper context in metadata, then figure proximity and caption presence. Citations are deduplicated and aligned with the references list.
- **LLM role**: The model is instructed to translate, be practical, cite with `[n]`, and (in streaming mode) output three sections with markers. It never sees PDFs or images, only retrieved text and captions.
- **Architecture**: Stateless FastAPI on Fly, Postgres + pgvector for papers/chunks/figures, Supabase Storage for files, OpenAI for embeddings and chat. Design favors simplicity (single embedding model, no discipline filter yet, figure selection by proximity and captions) and a clear separation between retrieval (our responsibility) and generation (LLM’s, constrained by that retrieval).
