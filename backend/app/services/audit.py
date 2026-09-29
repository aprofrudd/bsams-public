"""Security audit logging service."""

import logging
from typing import Optional
from uuid import UUID

from fastapi import Request

from app.core.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


def log_event(
    user_id: Optional[UUID],
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[UUID] = None,
    details: Optional[dict] = None,
    request: Optional[Request] = None,
) -> None:
    """
    Log a security/audit event.

    Args:
        user_id: The user performing the action
        action: Action type (e.g., 'login', 'data_export', 'athlete_delete')
        resource_type: Type of resource affected (e.g., 'athlete', 'session')
        resource_id: ID of the affected resource
        details: Additional context as JSON
        request: FastAPI request for IP extraction
    """
    client = get_supabase_client()
    if not client:
        logger.warning("Cannot log audit event: no database connection")
        return

    ip_address = None
    if request and request.client:
        ip_address = request.client.host

    record = {
        "action": action,
    }

    if user_id:
        record["user_id"] = str(user_id)
    if resource_type:
        record["resource_type"] = resource_type
    if resource_id:
        record["resource_id"] = str(resource_id)
    if ip_address:
        record["ip_address"] = ip_address
    if details:
        record["details"] = details

    try:
        client.table("audit_log").insert(record).execute()
    except Exception:
        logger.exception("Failed to write audit log entry: action=%s", action)


def log_deletion(
    deleted_by: UUID,
    entity_type: str,
    entity_id: UUID,
    entity_summary: Optional[dict] = None,
) -> None:
    """
    Log a data deletion event (GDPR right to erasure audit trail).

    Args:
        deleted_by: User who performed the deletion
        entity_type: Type of entity deleted (e.g., 'athlete', 'account')
        entity_id: ID of the deleted entity
        entity_summary: Summary of deleted data for audit purposes
    """
    client = get_supabase_client()
    if not client:
        logger.warning("Cannot log deletion: no database connection")
        return

    record = {
        "deleted_by": str(deleted_by),
        "entity_type": entity_type,
        "entity_id": str(entity_id),
    }

    if entity_summary:
        record["entity_summary"] = entity_summary

    try:
        client.table("deletion_log").insert(record).execute()
    except Exception:
        logger.exception("Failed to write deletion log: entity_type=%s", entity_type)
