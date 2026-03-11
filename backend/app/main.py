import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.figures import router as figures_router
from app.api.papers import router as papers_router
from app.api.translate import router as translate_router
from app.core.config import get_settings
from app.llm.client import LLMClient
from app.llm.translator import TranslationEngine
from app.rag.ingest import init_db, ingest_papers
from app.rag.retriever import Retriever
from app.rag.vectorstore import get_chroma_client, get_or_create_collection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def _background_ingest(settings, llm_client, collection):
    """Run paper ingestion in the background so the server can start accepting requests."""
    await asyncio.sleep(1)
    try:
        logger.info("Background auto-ingestion starting...")
        result = await ingest_papers(settings, llm_client, collection)
        logger.info(
            "Auto-ingested %d paper(s): %d chunks, %d figures",
            result["papers_ingested"], result["total_chunks"], result["total_figures"],
        )
    except Exception:
        logger.exception("Background ingestion failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("Initializing GAIA Translator backend...")

    await init_db(settings.sqlite_db_path)

    llm_client = LLMClient(settings)

    chroma_client = get_chroma_client(settings.chroma_persist_dir)
    collection = get_or_create_collection(chroma_client)

    retriever = Retriever(collection, llm_client)
    translation_engine = TranslationEngine(llm_client, retriever)

    app.state.settings = settings
    app.state.llm_client = llm_client
    app.state.chroma_client = chroma_client
    app.state.collection = collection
    app.state.retriever = retriever
    app.state.translation_engine = translation_engine

    if collection.count() == 0:
        asyncio.create_task(_background_ingest(settings, llm_client, collection))

    logger.info("GAIA Translator backend ready.")
    yield
    logger.info("Shutting down GAIA Translator backend.")


app = FastAPI(
    title="GAIA Translator",
    description="Interdisciplinary scientific translation tool using RAG over scientific papers",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(translate_router)
app.include_router(papers_router)
app.include_router(figures_router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "gaia-translator"}


static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
