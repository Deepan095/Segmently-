"""Pydantic schemas for the authentication module."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    """Payload for ``POST /auth/register``."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=100)


class Token(BaseModel):
    """Access + refresh token pair returned by login / refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# Backwards-friendly alias - some callers expect ``LoginResponse``.
LoginResponse = Token


class RefreshRequest(BaseModel):
    """Payload for ``POST /auth/refresh`` and ``POST /auth/logout``."""

    refresh_token: str


class UpdateProfileRequest(BaseModel):
    """Payload for ``PUT /auth/me``."""

    full_name: str | None = Field(default=None, max_length=100)


class UserResponse(BaseModel):
    """Public representation of a user account."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    # Plain str on output - the address was validated as EmailStr on the way in.
    # Re-validating here would reject seed accounts on reserved TLDs (.local).
    email: str
    full_name: str | None
    is_active: bool
    is_verified: bool
    is_admin: bool
    oauth_provider: str | None
    created_at: datetime
