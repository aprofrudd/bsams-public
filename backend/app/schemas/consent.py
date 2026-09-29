"""Consent schemas for data sharing."""

from typing import Optional

from pydantic import BaseModel


CONSENT_INFO_TEXT = (
    "By opting in, you agree to share your anonymised athlete data with Boxing Science "
    "for educational and research purposes. Athletes will be identified by number only "
    "(not by name). You can revoke this consent at any time without giving any reason, "
    "and your data will immediately be removed from Boxing Science's view."
)


class ConsentResponse(BaseModel):
    """Response for consent status."""

    data_sharing_enabled: bool
    consented_at: Optional[str] = None
    revoked_at: Optional[str] = None
    info_text: str = CONSENT_INFO_TEXT


class ConsentUpdate(BaseModel):
    """Request to update consent status."""

    data_sharing_enabled: bool
