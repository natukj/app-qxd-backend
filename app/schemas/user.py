from pydantic import BaseModel, EmailStr, ConfigDict, Field, field_validator
from typing import Optional
from uuid import UUID
from app.schemas.base_schema import BaseSchema

class UserBase(BaseSchema):
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool = True
    is_admin: bool = False
    email_validated: bool = False

class UserCreate(UserBase):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=64)

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8, max_length=64)
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    email_validated: Optional[bool] = None
    original_password: str = Field(..., min_length=8, max_length=64)

class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=64)

class UserInDBBase(UserBase):
    id: Optional[UUID] = None
    model_config = ConfigDict(from_attributes=True)

# additional properties to return via API
class User(UserInDBBase):
    hashed_password: bool = Field(default=False, alias="password")
    totp_secret: bool = Field(default=False, alias="totp")

    class Config:
        populate_by_name = True

    @field_validator("hashed_password")
    def evaluate_hashed_password(cls, hashed_password):
        return bool(hashed_password)
    
    @field_validator("totp_secret")
    def evaluate_totp_secret(cls, totp_secret):
        if totp_secret:
            return True
        return False

# additional properties stored in DB
class UserInDB(UserInDBBase):
    hashed_password: Optional[str] = None
    totp_secret: Optional[str] = None
    totp_counter: Optional[int] = None

