from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from crud.base import CRUDBase
from models.user import User
from models.token import Token
from schemas import RefreshTokenCreate, RefreshTokenUpdate
from core.config import settings

# from models import lazy_load
# lazy_load()

class CRUDToken(CRUDBase[Token, RefreshTokenCreate, RefreshTokenUpdate]):
    async def create(self, db: AsyncSession, *, obj_in: str, user_obj: User) -> Token:
        existing_token = await db.execute(
            select(self.model).filter(
                self.model.token == obj_in,
                self.model.authenticates_id == user_obj.id
            )
        )
        if existing_token.scalars().first():
            raise ValueError("Token already exists for this user.")

        # Create new token
        new_token = RefreshTokenCreate(token=obj_in, authenticates_id=user_obj.id)
        return await super().create(db=db, obj_in=new_token)

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
