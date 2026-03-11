"""Supabase Storage client -- simple REST API wrapper using httpx."""

import logging

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)

_client: httpx.Client | None = None


def _get_client(settings: Settings) -> httpx.Client:
    global _client
    if _client is not None:
        return _client
    _client = httpx.Client(
        base_url=f"{settings.supabase_url}/storage/v1",
        headers={
            "apikey": settings.supabase_service_key,
            "Authorization": f"Bearer {settings.supabase_service_key}",
        },
        timeout=60.0,
    )
    logger.info("Supabase Storage client initialized")
    return _client


def upload_file(
    settings: Settings,
    key: str,
    data: bytes,
    content_type: str = "application/octet-stream",
) -> str:
    client = _get_client(settings)
    bucket = settings.supabase_storage_bucket
    resp = client.post(
        f"/object/{bucket}/{key}",
        content=data,
        headers={"Content-Type": content_type, "x-upsert": "true"},
    )
    resp.raise_for_status()
    logger.info("Uploaded %s (%d bytes)", key, len(data))
    return key


def download_file(settings: Settings, key: str) -> bytes:
    client = _get_client(settings)
    bucket = settings.supabase_storage_bucket
    resp = client.get(f"/object/{bucket}/{key}")
    resp.raise_for_status()
    return resp.content


def get_public_url(settings: Settings, key: str) -> str:
    bucket = settings.supabase_storage_bucket
    return f"{settings.supabase_url}/storage/v1/object/public/{bucket}/{key}"


def delete_file(settings: Settings, key: str) -> None:
    client = _get_client(settings)
    bucket = settings.supabase_storage_bucket
    resp = client.delete(
        f"/object/{bucket}",
        json={"prefixes": [key]},
    )
    resp.raise_for_status()
    logger.info("Deleted %s", key)
