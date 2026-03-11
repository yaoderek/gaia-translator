from pydantic import BaseModel

from app.core.disciplines import Discipline


class TranslateRequest(BaseModel):
    text: str
    source_discipline: Discipline
    target_discipline: Discipline
    conversation_id: str | None = None


class Citation(BaseModel):
    index: int
    paper_id: str
    title: str
    authors: str
    excerpt: str
    doi: str | None = None


class FigureRef(BaseModel):
    figure_id: str
    paper_id: str
    caption: str
    page: int


class TranslateResponse(BaseModel):
    translation: str
    citations: list[Citation]
    figures: list[FigureRef]
    follow_up_questions: list[str]


class PaperInfo(BaseModel):
    paper_id: str
    title: str
    authors: str
    filename: str
    num_chunks: int
    num_figures: int
    ingested_at: str


class IngestResponse(BaseModel):
    papers_ingested: int
    total_chunks: int
    total_figures: int
