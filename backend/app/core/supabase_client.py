"""Supabase client singleton."""

from functools import lru_cache
from typing import Optional

from fastapi import HTTPException, status
from supabase import Client, create_client

from app.core.config import get_settings


@lru_cache
def get_supabase_client() -> Optional[Client]:
    """
    Get a cached Supabase client instance.

    Returns:
        Client or None if Supabase is not configured.
    """
    settings = get_settings()

    if not settings.supabase_url or not settings.supabase_key:
        return None

    return create_client(settings.supabase_url, settings.supabase_key)


def get_client_or_503() -> Client:
    """Get Supabase client, raising 503 if not configured."""
    client = get_supabase_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not configured",
        )
    return client


def raise_on_duplicate(e: Exception, detail: str) -> None:
    """Re-raise as 409 if the exception is a unique constraint violation, otherwise re-raise original."""
    error_str = str(e).lower()
    if "duplicate key" in error_str or "unique" in error_str:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
    raise
