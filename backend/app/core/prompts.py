from app.core.disciplines import Discipline, DISCIPLINE_INFO


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
) -> list[dict]:
    """Build a prompt for streaming that outputs plain text (not JSON)."""
    src_info = DISCIPLINE_INFO[source]
    tgt_info = DISCIPLINE_INFO[target]

    context_block = _format_context(retrieved_context)
    figures_block = _format_figures(figure_descriptions)

    system_content = f"""{_core_system_prompt(src_info, tgt_info)}

## Formatting Rules
- Write clear, concise prose. Aim for 150-250 words in the main translation -- be dense with insight, not verbose.
- Use **bold text** for section headers, NEVER use ### or ## markdown headers in your output.
- Use [n] bracket notation to cite literature inline.
- When relevant, mention [Fig: paper_id/fig_num].
- End with a section headed **Potentially Relevant Domain Workstreams** listing 2-3 concrete, \
actionable workstreams where {tgt_info['label']} expertise would directly advance the lab's \
geohazard mission in light of what was just translated. Each should be specific enough that the \
reader could start working on it.
- Do NOT wrap your response in JSON or code fences.

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
4. **Cite literature** with [n] bracket notation from the provided context."""


def _format_context(chunks: list[dict]) -> str:
    if not chunks:
        return "## Retrieved Literature\nNo relevant literature was retrieved."

    lines = ["## Retrieved Literature"]
    for i, chunk in enumerate(chunks, 1):
        meta = chunk.get("metadata", {})
        paper_id = meta.get("paper_id", "unknown")
        section = meta.get("section_title", "")
        text = chunk.get("text", "")
        header = f"[{i}] paper_id={paper_id}"
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
