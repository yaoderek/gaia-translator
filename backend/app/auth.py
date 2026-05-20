"""Supabase JWT verification for optional and required auth.

Supports both:
- HS256 legacy JWTs signed with SUPABASE_JWT_SECRET (older projects)
- ES256/RS256 asymmetric JWTs signed with Supabase's JWT signing keys (newer
  projects). For these, public keys are fetched from
  {SUPABASE_URL}/auth/v1/.well-known/jwks.json and verified by `kid`.
"""

import logging
from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False)


@lru_cache(maxsize=1)
def _jwks_client() -> jwt.PyJWKClient | None:
    settings = get_settings()
    if not settings.supabase_url:
        return None
    url = settings.supabase_url.rstrip("/") + "/auth/v1/.well-known/jwks.json"
    return jwt.PyJWKClient(url, cache_keys=True)


def _decode_token(token: str) -> dict:
    """Decode and verify a Supabase JWT. Tries asymmetric (JWKS) first, then HS256."""
    settings = get_settings()
    header = jwt.get_unverified_header(token)
    alg = header.get("alg", "")

    if alg.startswith(("ES", "RS")):
        client = _jwks_client()
        if client is None:
            raise jwt.InvalidKeyError("JWKS client unavailable (SUPABASE_URL not set)")
        signing_key = client.get_signing_key_from_jwt(token).key
        return jwt.decode(
            token,
            signing_key,
            audience="authenticated",
            algorithms=[alg],
        )

    if not settings.supabase_jwt_secret:
        raise jwt.InvalidKeyError("SUPABASE_JWT_SECRET not configured")
    return jwt.decode(
        token,
        settings.supabase_jwt_secret,
        audience="authenticated",
        algorithms=["HS256"],
    )


def get_current_user_id_optional(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str | None:
    """Return auth user id (sub) if valid JWT present, else None."""
    if cred is None or not cred.credentials:
        return None
    try:
        payload = _decode_token(cred.credentials)
        return payload.get("sub")
    except jwt.PyJWTError:
        return None


def get_current_user_id(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    """Return auth user id; raise 401 if missing or invalid."""
    if cred is None or not cred.credentials:
        logger.warning("Auth failed: no Authorization header or token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required (no token sent). Check that the request includes Authorization: Bearer <token>.",
        )
    try:
        payload = _decode_token(cred.credentials)
        user_id = payload.get("sub")
        if not user_id:
            logger.warning("Auth failed: JWT missing sub claim")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required (invalid token).",
            )
        return user_id
    except jwt.ExpiredSignatureError:
        logger.warning("Auth failed: token expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required (token expired). Try logging in again.",
        ) from None
    except jwt.PyJWTError as e:
        logger.warning("Auth failed: JWT decode error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication required (invalid token: {e}).",
        ) from None
