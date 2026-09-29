"""Invitation request and response schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class InvitationCreate(BaseModel):
    """Request to create an invitation for an athlete."""

    athlete_id: UUID


class InvitationResponse(BaseModel):
    """Full invitation details."""

    id: UUID
    athlete_id: UUID
    coach_id: UUID
    invite_code: str
    expires_at: datetime
    used_at: Optional[datetime] = None
    used_by: Optional[UUID] = None
    created_at: datetime


class InvitationValidateResponse(BaseModel):
    """Response from validating an invitation code."""

    valid: bool
    athlete_first_name: Optional[str] = None
    expires_at: Optional[datetime] = None
