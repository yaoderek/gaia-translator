import logging

import asyncpg
from pgvector.asyncpg import register_vector

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS papers (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    authors TEXT NOT NULL DEFAULT '',
    file_hash TEXT UNIQUE NOT NULL,
    s3_pdf_key TEXT NOT NULL DEFAULT '',
    num_chunks INT DEFAULT 0,
    num_figures INT DEFAULT 0,
    ingested_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    paper_id TEXT REFERENCES papers(id) ON DELETE CASCADE,
    section_title TEXT DEFAULT '',
    page_start INT DEFAULT 0,
    page_end INT DEFAULT 0,
    content TEXT NOT NULL,
    embedding vector(1536),
    title TEXT DEFAULT '',
    authors TEXT DEFAULT '',
    discipline_tags TEXT DEFAULT 'general'
);

CREATE TABLE IF NOT EXISTS figures (
    id TEXT PRIMARY KEY,
    paper_id TEXT REFERENCES papers(id) ON DELETE CASCADE,
    page INT NOT NULL,
    s3_key TEXT NOT NULL DEFAULT '',
    caption TEXT DEFAULT '',
    width INT DEFAULT 0,
    height INT DEFAULT 0
);
"""


async def _init_connection(conn: asyncpg.Connection) -> None:
    await register_vector(conn)


async def init_pool(database_url: str) -> asyncpg.Pool:
    global _pool

    # First, create the pgvector extension via a standalone connection
    # (must happen before pool init tries to register the vector type)
    conn = await asyncpg.connect(database_url, statement_cache_size=0)
    try:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        logger.info("pgvector extension ensured")
    finally:
        await conn.close()

    _pool = await asyncpg.create_pool(
        database_url,
        min_size=2,
        max_size=10,
        init=_init_connection,
        statement_cache_size=0,  # required for Supabase transaction pooler
    )
    logger.info("Postgres connection pool created")
    return _pool


async def init_tables(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await conn.execute(_SCHEMA_SQL)
    logger.info("Database tables initialized")


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Postgres connection pool closed")


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database pool not initialized")
    return _pool
