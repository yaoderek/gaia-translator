import os
import re

import fitz


def extract_text_blocks(pdf_path: str) -> list[dict]:
    """Extract text blocks with page number, bbox, font size, and text content."""
    doc = fitz.open(pdf_path)
    blocks: list[dict] = []
    for page_num, page in enumerate(doc, 1):
        raw_blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
        for block in raw_blocks:
            if block.get("type") != 0:
                continue
            lines_text = []
            max_font_size = 0.0
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    lines_text.append(span["text"])
                    if span["size"] > max_font_size:
                        max_font_size = span["size"]
            text = " ".join(lines_text).strip()
            if not text:
                continue
            blocks.append(
                {
                    "page": page_num,
                    "bbox": list(block["bbox"]),
                    "font_size": max_font_size,
                    "text": text,
                }
            )
    doc.close()
    return blocks


def extract_figures(pdf_path: str, output_dir: str, paper_id: str) -> list[dict]:
    """Extract images from PDF pages and save as PNG files."""
    os.makedirs(output_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    figures: list[dict] = []
    for page_num, page in enumerate(doc, 1):
        images = page.get_images(full=True)
        for idx, img_info in enumerate(images):
            xref = img_info[0]
            try:
                base_image = doc.extract_image(xref)
            except Exception:
                continue
            if not base_image or not base_image.get("image"):
                continue
            image_bytes = base_image["image"]
            width = base_image.get("width", 0)
            height = base_image.get("height", 0)

            figure_id = f"{paper_id}_p{page_num}_{idx}"
            filename = f"{figure_id}.png"
            filepath = os.path.join(output_dir, filename)
            with open(filepath, "wb") as f:
                f.write(image_bytes)

            figures.append(
                {
                    "figure_id": figure_id,
                    "paper_id": paper_id,
                    "page": page_num,
                    "filepath": filepath,
                    "width": width,
                    "height": height,
                }
            )
    doc.close()
    return figures


_AUTHOR_AFFILIATION_NOISE = re.compile(
    r"\b(university|institute|laboratory|department|school of|division of|"
    r"college of|center for|centre for|inc\.|corp\.|ltd\.|@|orcid|"
    r"corresponding author|received|accepted|revised|copyright|©|abstract|keywords)\b",
    re.IGNORECASE,
)
_AUTHOR_NAME_TOKEN = re.compile(r"[A-Z][a-zA-Z'\-À-ſ]+")
_AND_SEP = re.compile(r"\s+and\s+|\s*&\s*|;", re.IGNORECASE)


def extract_authors(text_blocks: list[dict], title: str = "") -> str:
    """Best-effort author extraction from the front-matter of a paper.

    Strategy: scan blocks on page 1 (after the title) for a line that looks like
    a comma-and-and-separated list of capitalized names without affiliation noise.
    Returns a comma-separated string, or "" if no good candidate found.
    """
    if not text_blocks:
        return ""
    page1 = [b for b in text_blocks if b.get("page") == 1]
    if not page1:
        return ""

    title_norm = (title or "").strip().lower()
    seen_title = False
    for block in page1[:25]:
        text = (block.get("text") or "").strip()
        if not text or len(text) > 400:
            if title_norm and not seen_title and title_norm in text.lower():
                seen_title = True
            continue
        if title_norm and not seen_title:
            if title_norm in text.lower():
                seen_title = True
            continue
        if _AUTHOR_AFFILIATION_NOISE.search(text):
            continue
        # Strip trailing superscripts/numbers and parenthetical affiliations
        candidate = re.sub(r"[\d\*†‡§¶]+", "", text)
        candidate = re.sub(r"\([^)]*\)", "", candidate).strip(" ,.;")
        parts = [p.strip(" ,.") for p in _AND_SEP.split(candidate) if p.strip()]
        # Comma-separated authors are common too
        if len(parts) == 1 and "," in parts[0]:
            parts = [p.strip() for p in parts[0].split(",") if p.strip()]
        good = [
            p for p in parts
            if 2 <= len(p.split()) <= 5
            and len(_AUTHOR_NAME_TOKEN.findall(p)) >= 2
            and not any(ch.isdigit() for ch in p)
        ]
        if len(good) >= 2:
            return ", ".join(good[:20])
        if len(good) == 1 and seen_title:
            return good[0]
    return ""


def extract_captions(text_blocks: list[dict]) -> dict[int, list[str]]:
    """Find figure captions grouped by page.

    Heuristic: lines starting with "Fig." or "Figure" (case-insensitive).
    """
    caption_pattern = re.compile(r"^(Fig\.|Figure)\s", re.IGNORECASE)
    captions: dict[int, list[str]] = {}
    for block in text_blocks:
        text = block["text"].strip()
        if caption_pattern.match(text):
            page = block["page"]
            captions.setdefault(page, []).append(text)
    return captions
