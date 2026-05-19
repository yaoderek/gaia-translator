from app.core.disciplines import Discipline, DISCIPLINE_INFO


def _target_info_from_persona(persona: dict) -> dict:
    """Build target block for prompt from user persona.

    Merges discipline-derived concepts with any user-declared focus concepts.
    """
    discipline = (persona.get("discipline") or "").strip()
    bio = (persona.get("bio") or "").strip()
    label = "You (the reader)"
    key_concepts: list[str] = []
    if discipline and discipline in [d.value for d in Discipline]:
        disc = Discipline(discipline)
        key_concepts = list(DISCIPLINE_INFO[disc]["key_concepts"])

    # Merge user-declared concepts (newline- or comma-separated)
    extra = _split_lines(persona.get("concepts_focus") or "")
    for c in extra:
        if c and c not in key_concepts:
            key_concepts.append(c)

    return {
        "label": label,
        "description": bio if bio else "Reader context not specified.",
        "key_concepts": key_concepts,
    }


def _split_lines(text: str) -> list[str]:
    """Split a textarea blob on newlines OR commas, trim, drop empties."""
    if not text:
        return []
    out: list[str] = []
    for part in text.replace(",", "\n").split("\n"):
        s = part.strip(" \t-•*")
        if s:
            out.append(s)
    return out


def _format_persona_block(persona: dict) -> str:
    """Render the structured persona fields as a 'Reader Context' block.

    Only included if at least one field is non-empty.
    """
    sections: list[tuple[str, list[str]]] = [
        ("Papers of interest", _split_lines(persona.get("papers_of_interest") or "")),
        ("Concepts they want emphasized", _split_lines(persona.get("concepts_focus") or "")),
        ("Methodologies they use", _split_lines(persona.get("methods_focus") or "")),
        ("Tech stack / tools", _split_lines(persona.get("tech_stack") or "")),
    ]
    sections = [(h, items) for h, items in sections if items]
    if not sections:
        return ""
    lines = [
        "## Reader Context",
        "Personalize the translation toward this reader. Frame examples and analogies "
        "using their tools and methods; prioritize the concepts they care about.",
        "",
    ]
    for header, items in sections:
        lines.append(f"**{header}:**")
        for item in items[:30]:
            lines.append(f"- {item}")
        lines.append("")
    return "\n".join(lines)


def build_translation_prompt(
    source: Discipline,
    target: Discipline,
    retrieved_context: list[dict],
    figure_descriptions: list[dict],
) -> list[dict]:
    src_info = DISCIPLINE_INFO[source]
    tgt_info = DISCIPLINE_INFO[target]

    context_block = _format_context(retrieved_context)
    figures_block = _format_figures(figure_descriptions)

    system_content = f"""{_core_system_prompt(src_info, tgt_info)}

## Response Format
Return a JSON object with these fields:
- "translation": string — the translated explanation with inline [n] citations
- "citations": array of objects, each with "index" (int), "paper_id" (str), "title" (str), "authors" (str), "excerpt" (str), "doi" (str or null)
- "figures": array of objects, each with "figure_id" (str), "paper_id" (str), "caption" (str), "page" (int)
- "follow_up_questions": array of strings (2-3 actionable workstreams)

{context_block}

{figures_block}"""

    return [
        {"role": "system", "content": system_content},
    ]


def build_streaming_prompt(
    source: Discipline,
    target: Discipline,
    retrieved_context: list[dict],
    figure_descriptions: list[dict],
    target_persona: dict | None = None,
) -> list[dict]:
    """Build a prompt for streaming. If target_persona has a non-empty bio, use it as the target audience."""
    src_info = DISCIPLINE_INFO[source]
    persona_has_signal = bool(target_persona and any(
        (target_persona.get(k) or "").strip()
        for k in ("bio", "papers_of_interest", "concepts_focus", "methods_focus", "tech_stack")
    ))
    if persona_has_signal:
        tgt_info = _target_info_from_persona(target_persona or {})
    else:
        tgt_info = DISCIPLINE_INFO[target]

    context_block = _format_context(retrieved_context)
    figures_block = _format_figures(figure_descriptions)
    persona_block = _format_persona_block(target_persona or {}) if persona_has_signal else ""

    system_content = f"""{_core_system_prompt(src_info, tgt_info)}

## Output Structure
Your response MUST contain exactly three sections separated by HTML comment markers.
Follow this template exactly:

<!-- SECTION: overview -->
**Translation for {tgt_info['label']}**
A concise overview (3-5 sentences) of what the source text is saying, translated into terms \
this reader can act on. Map the key jargon and give them the gist.

<!-- SECTION: relevance -->
**Why This Matters for This Reader**
A deeper explanation (1-2 paragraphs) of the specific, practical implications for this reader's \
work. Be concrete: name specific pipelines, datasets, models, measurements, or analyses that \
are affected. Connect to the lab's geohazard mission.

<!-- SECTION: workstreams -->
**Potentially Relevant Domain Workstreams**
List 2-3 concrete, actionable workstreams that would directly advance the lab's geohazard mission \
in light of what was just translated. Format each as: **Workstream Name**: description. Each should \
be specific enough that the reader could start working on it.

## Formatting Rules
- Use **bold text** for headers, NEVER use ### or ## markdown headers.
- Use [n] bracket notation to cite literature inline.
- When relevant, mention [Fig: paper_id/fig_num].
- Do NOT wrap your response in JSON or code fences.
- The <!-- SECTION: ... --> markers are mandatory and must appear exactly as shown.

{persona_block}

{context_block}

{figures_block}"""

    return [
        {"role": "system", "content": system_content},
    ]


def _core_system_prompt(src_info: dict, tgt_info: dict) -> str:
    return f"""You are GAIA, a scientific translator for an interdisciplinary geohazard research lab.

**Lab Mission**: Build shared understanding of soil through seismic and other geophysical models, \
integrating multimodal and multidisciplinary data to predict and understand geohazard events \
(debris flows, landslides, slope failures).

**Your Task**: Translate the user's text from **{src_info['label']}** into terms a \
**{tgt_info['label']}** researcher can act on.

**Source — {src_info['label']}**: {src_info['description']}
Key concepts: {', '.join(src_info['key_concepts'])}

**Target — {tgt_info['label']}**: {tgt_info['description']}
Key concepts: {', '.join(tgt_info['key_concepts'])}

## Translation Guidelines
1. **Map jargon**: Identify domain-specific terms and map them to {tgt_info['label']} equivalents. \
Where no equivalent exists, explain the concept in {tgt_info['label']} fundamentals.
2. **Make it practical**: Don't just say a concept "relates to" the target discipline. Explain \
specifically what it means for the {tgt_info['label']} person's actual work -- what pipeline, \
model, dataset, analysis, or experiment is affected and how. Connect it to the lab's mission of \
aggregating multimodal data for soil understanding and geohazard prediction.
3. **Be concrete about implications**: For example, if a seismologist talks about velocity changes, \
tell the computer scientist which input features or data channels this corresponds to in their \
modeling pipeline, or tell the hydrologist what this implies about pore pressure or infiltration \
rates they should be measuring.
4. **Cite literature** with [n] bracket notation from the provided context. Each [n] corresponds \
to a unique paper -- multiple passages from the same paper share the same number. Only use [n] values \
that appear in the retrieved literature section."""


def _format_context(chunks: list[dict]) -> str:
    if not chunks:
        return "## Retrieved Literature\nNo relevant literature was retrieved."

    paper_index: dict[str, int] = {}
    title_to_idx: dict[str, int] = {}
    counter = 0
    for chunk in chunks:
        meta = chunk.get("metadata", {})
        pid = meta.get("paper_id", "unknown")
        if pid in paper_index:
            continue
        title = meta.get("title", "")
        norm = " ".join(title.strip().lower().rstrip(".").split())
        if norm and norm in title_to_idx:
            paper_index[pid] = title_to_idx[norm]
            continue
        counter += 1
        paper_index[pid] = counter
        if norm:
            title_to_idx[norm] = counter

    lines = [
        "## Retrieved Literature",
        "Each [n] refers to a unique paper. Multiple passages from the same paper share the same [n].",
        "",
    ]
    for chunk in chunks:
        meta = chunk.get("metadata", {})
        pid = meta.get("paper_id", "unknown")
        idx = paper_index[pid]
        title = meta.get("title", "")
        section = meta.get("section_title", "")
        text = chunk.get("text", "")
        header = f"[{idx}] paper_id={pid}"
        if title:
            header += f' | title="{title}"'
        if section:
            header += f' | section="{section}"'
        lines.append(header)
        lines.append(text)
        lines.append("")
    return "\n".join(lines)


def _format_figures(figures: list[dict]) -> str:
    if not figures:
        return "## Figures\nNo figures available for the retrieved context."

    lines = ["## Figures"]
    for fig in figures:
        fig_id = fig.get("figure_id", "unknown")
        paper_id = fig.get("paper_id", "unknown")
        caption = fig.get("caption", "No caption")
        page = fig.get("page", "?")
        lines.append(f"- [Fig: {paper_id}/{fig_id}] page {page}: {caption}")
    return "\n".join(lines)
