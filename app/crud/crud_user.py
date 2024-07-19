from typing import Any, Dict, Optional, Union

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.security import get_password_hash, verify_password
from crud.base import CRUDBase
from models.user import User
from schemas.user import UserCreate, UserUpdate, UserInDB, User as UserSchema
from schemas.totp import NewTOTP

# from models import lazy_load
# lazy_load()

class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    async def get_by_email(self, db: AsyncSession, *, email: str) -> Optional[User]:
        result = await db.execute(select(User).filter(User.email == email))
        return result.scalars().first()

    async def create(self, db: AsyncSession, *, obj_in: UserCreate) -> User:
        db_obj = User(
            email=obj_in.email,
            hashed_password=get_password_hash(obj_in.password),
            full_name=obj_in.full_name,
            is_admin=obj_in.is_admin,
            is_active=obj_in.is_active,
            email_validated=obj_in.email_validated,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, db: AsyncSession, *, db_obj: User, obj_in: Union[UserUpdate, Dict[str, Any]]
    ) -> User:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
        if update_data.get("password"):
            hashed_password = get_password_hash(update_data["password"])
            del update_data["password"]
            update_data["hashed_password"] = hashed_password
        return await super().update(db, db_obj=db_obj, obj_in=update_data)

    async def authenticate(self, db: AsyncSession, *, email: str, password: str) -> Optional[User]:
        user = await self.get_by_email(db, email=email)
        if not user:
            return None
        if not verify_password(plain_password=password, hashed_password=user.hashed_password):
            return None
        return user
    
    async def authenticate(self, db: AsyncSession, *, email: str, password: str) -> Optional[User]:
        user = await self.get_by_email(db, email=email)
        if not user:
            return None
        if not verify_password(plain_password=password, hashed_password=user.hashed_password):
            return None
        return user
    
    # TODO add in validate email 

    async def activate_totp(self, db: AsyncSession, *, db_obj: User, totp_in: NewTOTP) -> User:
        obj_in = UserSchema.model_validate(db_obj)
        update_data = obj_in.model_dump(exclude_unset=True)
        update_data["totp_secret"] = totp_in.secret
        return await self.update(db=db, db_obj=db_obj, obj_in=update_data)
    
    async def deactivate_totp(self, db: AsyncSession, *, db_obj: User) -> User:
        obj_in = UserSchema.model_validate(db_obj)
        update_data = obj_in.model_dump(exclude_unset=True)
        update_data["totp_secret"] = None
        update_data["totp_counter"] = None
        return await self.update(db=db, db_obj=db_obj, obj_in=update_data)
    
    async def update_totp_counter(self, db: AsyncSession, *, db_obj: User, new_counter: int) -> User:
        obj_in = UserSchema.model_validate(db_obj)
        update_data = obj_in.model_dump(exclude_unset=True)
        update_data["totp_counter"] = new_counter
        return await self.update(db=db, db_obj=db_obj, obj_in=update_data)
    
    async def toggle_user_state(self, db: AsyncSession, *, obj_in: Union[UserUpdate, Dict[str, Any]]) -> Optional[User]:
        db_obj = await self.get_by_email(db, email=obj_in["email"] if isinstance(obj_in, dict) else obj_in.email)
        if not db_obj:
            return None
        return await self.update(db=db, db_obj=db_obj, obj_in=obj_in)

    def is_active(self, user: User) -> bool:
        return user.is_active

    def is_admin(self, user: User) -> bool:
        return user.is_admin
    
    def is_email_validated(self, user: User) -> bool:
        return user.email_validated

user = CRUDUser(User)
