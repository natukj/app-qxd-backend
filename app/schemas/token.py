from pydantic import BaseModel
from uuid import UUID

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenPayload(BaseModel):
    sub: UUID | None = None

class RefreshToken(BaseModel):
    token: str
    authenticates_id: UUID