import statistics


def chunk_text(
    text_blocks: list[dict],
    max_tokens: int = 512,
    overlap_tokens: int = 100,
) -> list[dict]:
    """Section-aware text chunking.

    Detects section headers via font-size heuristics and splits text into
    chunks that respect section boundaries where possible.
    """
    if not text_blocks:
        return []

    header_threshold = _detect_header_threshold(text_blocks)
    sections = _group_into_sections(text_blocks, header_threshold)
    chunks: list[dict] = []

    for section_title, blocks in sections:
        combined_text = " ".join(b["text"] for b in blocks)
        page_start = blocks[0]["page"]
        page_end = blocks[-1]["page"]
        tokens = combined_text.split()

        if len(tokens) <= max_tokens:
            chunks.append(
                {
                    "text": combined_text,
                    "section_title": section_title,
                    "page_start": page_start,
                    "page_end": page_end,
                    "token_count": len(tokens),
                }
            )
        else:
            start = 0
            while start < len(tokens):
                end = min(start + max_tokens, len(tokens))
                chunk_tokens = tokens[start:end]
                chunks.append(
                    {
                        "text": " ".join(chunk_tokens),
                        "section_title": section_title,
                        "page_start": page_start,
                        "page_end": page_end,
                        "token_count": len(chunk_tokens),
                    }
                )
                if end >= len(tokens):
                    break
                start = end - overlap_tokens

    return chunks


def _detect_header_threshold(text_blocks: list[dict]) -> float:
    """Determine font-size threshold above which text is a header.

    Uses the median font size + 1.5 as a heuristic divider.
    """
    sizes = [b["font_size"] for b in text_blocks if b["font_size"] > 0]
    if not sizes:
        return 999.0
    median = statistics.median(sizes)
    return median + 1.5


def _group_into_sections(
    text_blocks: list[dict],
    header_threshold: float,
) -> list[tuple[str, list[dict]]]:
    """Group consecutive text blocks by detected section headers."""
    sections: list[tuple[str, list[dict]]] = []
    current_title = "Untitled"
    current_blocks: list[dict] = []

    for block in text_blocks:
        if block["font_size"] >= header_threshold and len(block["text"].split()) < 20:
            if current_blocks:
                sections.append((current_title, current_blocks))
            current_title = block["text"].strip()
            current_blocks = []
        else:
            current_blocks.append(block)

    if current_blocks:
        sections.append((current_title, current_blocks))

    return sections
