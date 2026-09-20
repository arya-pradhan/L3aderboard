"""Auth-related request/response schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserRead(BaseModel):
    id: int
    username: str
    # Plain str on output: the value is already stored, and re-validating it
    # here would turn any stored email the validator dislikes into a 500 on
    # /auth/me. Input is still strictly validated via RegisterRequest.
    email: str | None = None
    steam_id: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
