from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.crud.base import CRUDBase
from app.models import User, Token
from app.schemas import RefreshTokenCreate, RefreshTokenUpdate
from app.core.config import settings

class CRUDToken(CRUDBase[Token, RefreshTokenCreate, RefreshTokenUpdate]):
    async def create(self, db: AsyncSession, *, token: str, user: User) -> Token:
        existing_token = await db.execute(select(Token).filter(Token.token == token, Token.authenticates == user))
        if existing_token.scalars().first():
            raise ValueError("Token already exists for this user.")
        
        obj_in = RefreshTokenCreate(token=token, authenticates_id=user.id)
        return await super().create(db=db, obj_in=obj_in)

    async def get(self, db: AsyncSession, *, user: User, token: str) -> Optional[Token]:
        result = await db.execute(select(Token).filter(Token.token == token, Token.authenticates == user))
        return result.scalars().first()

    async def get_multi(self, db: AsyncSession, *, user: User, skip: int = 0, limit: int = settings.MULTI_MAX) -> List[Token]:
        # multiple sessions/tokens
        result = await db.execute(
            select(Token)
            .filter(Token.authenticates == user)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
    
    async def remove(self, db: AsyncSession, *, token: Token) -> None:
        await db.delete(token)
        await db.commit()

    async def remove_all(self, db: AsyncSession, *, user: User) -> None:
        await db.execute(select(Token).filter(Token.authenticates == user).delete())
        await db.commit()

token = CRUDToken(Token)
