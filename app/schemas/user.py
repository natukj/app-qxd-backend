from pydantic import BaseModel, EmailStr, constr, Field, field_validator
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
    password: constr(min_length=8, max_length=64) # type: ignore

class UserInDBBase(UserBase):
    id: Optional[UUID] = None

    class Config:
        orm_mode = True

# additional properties to return via API
class User(UserInDBBase):
    hashed_password: bool = Field(default=False, alias="password")

    class Config:
        allow_population_by_field_name = True

    @field_validator("hashed_password", pre=True)
    def evaluate_hashed_password(cls, hashed_password):
        return bool(hashed_password)

# additional properties stored in DB
class UserInDB(UserInDBBase):
    hashed_password: str

