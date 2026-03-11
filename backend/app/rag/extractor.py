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
