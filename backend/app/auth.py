"""Supabase JWT verification for optional and required auth."""

import logging

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False)


def get_current_user_id_optional(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str | None:
    """Return auth user id (sub) if valid JWT present, else None."""
    if cred is None or not cred.credentials:
        return None
    settings = get_settings()
    if not settings.supabase_jwt_secret:
        return None
    try:
        payload = jwt.decode(
            cred.credentials,
            settings.supabase_jwt_secret,
            audience="authenticated",
            algorithms=["HS256"],
        )
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
    settings = get_settings()
    if not settings.supabase_jwt_secret:
        logger.warning("Auth failed: SUPABASE_JWT_SECRET not set in backend .env")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required (server misconfigured: missing JWT secret).",
        )
    try:
        payload = jwt.decode(
            cred.credentials,
            settings.supabase_jwt_secret,
            audience="authenticated",
            algorithms=["HS256"],
        )
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
            detail="Authentication required (invalid token). Ensure backend SUPABASE_JWT_SECRET matches Supabase Legacy JWT Secret.",
        ) from None
