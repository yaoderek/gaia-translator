import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.config import router as config_router
from app.api.figures import router as figures_router
from app.api.me import router as me_router
from app.api.papers import router as papers_router
from app.api.translate import router as translate_router
from app.core.config import get_settings
from app.db.postgres import close_pool, init_pool, init_tables
from app.llm.client import LLMClient
from app.llm.translator import TranslationEngine
from app.rag.retriever import Retriever

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("Initializing GAIA Translator backend...")
    if not (settings.supabase_jwt_secret or "").strip():
        logger.warning(
            "SUPABASE_JWT_SECRET is not set in backend/.env — login and My persona will return 401. "
            "Set it from Supabase Dashboard → API → Legacy JWT Secret (Reveal, then copy)."
        )

    pool = await init_pool(settings.database_url)
    await init_tables(pool)

    llm_client = LLMClient(settings)

    retriever = Retriever(pool, llm_client)
    translation_engine = TranslationEngine(llm_client, retriever)

    app.state.settings = settings
    app.state.llm_client = llm_client
    app.state.pool = pool
    app.state.retriever = retriever
    app.state.translation_engine = translation_engine

    logger.info("GAIA Translator backend ready.")
    yield
    logger.info("Shutting down GAIA Translator backend.")
    await close_pool()


app = FastAPI(
    title="GAIA Translator",
    description="Interdisciplinary scientific translation tool using RAG over scientific papers",
    version="0.2.0",
    lifespan=lifespan,
)

_settings = get_settings()
_cors_origins = [o.strip() for o in _settings.cors_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(config_router)
app.include_router(translate_router)
app.include_router(me_router)
app.include_router(papers_router)
app.include_router(figures_router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "gaia-translator"}


static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
