"""Authentication request and response schemas."""

import re
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


def _validate_password_strength(password: str) -> str:
    """Validate password meets strength requirements."""
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit")
    return password


class AuthRequest(BaseModel):
    """Login request body (no password strength check — user may have legacy password)."""

    email: EmailStr
    password: str


class SignupRequest(BaseModel):
    """Signup request body (enforces password strength)."""

    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class AthleteSignupRequest(BaseModel):
    """Athlete signup request with invitation code."""

    email: EmailStr
    password: str = Field(..., min_length=8)
    invite_code: str = Field(..., min_length=1)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class AuthResponse(BaseModel):
    """Authentication response with user info (token sent via HttpOnly cookie only)."""

    user_id: str
    email: str


class ForgotPasswordRequest(BaseModel):
    """Request body for forgot password (email only)."""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Request body for resetting password via recovery token or PKCE code."""
    access_token: Optional[str] = None
    code: Optional[str] = None
    new_password: str

    @model_validator(mode="after")
    def require_token_or_code(self) -> "ResetPasswordRequest":
        if not self.access_token and not self.code:
            raise ValueError("Either access_token or code must be provided")
        return self

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class ChangePasswordRequest(BaseModel):
    """Request body for changing password (authenticated)."""
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class ChangeEmailRequest(BaseModel):
    """Request body for changing email (authenticated)."""
    current_password: str
    new_email: EmailStr
