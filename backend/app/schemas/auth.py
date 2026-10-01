from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from app.models.entities import UserRole


class UserRegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, example="Pranab Phukan")
    email: EmailStr = Field(..., example="pranab.hse@oilindia.in")
    password: str = Field(..., min_length=6, max_length=128, example="OilIndia@2026")
    role: Optional[UserRole] = Field(default=UserRole.hse_officer, description="Role: hse_officer, site_manager, or admin")
    site_id: Optional[int] = Field(default=None, description="Assigned site ID for site managers")


class UserLoginRequest(BaseModel):
    email: EmailStr = Field(..., example="pranab.hse@oilindia.in")
    password: str = Field(..., example="OilIndia@2026")


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: UserRole
    site_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    user: UserResponse
