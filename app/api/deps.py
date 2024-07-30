from typing import AsyncGenerator, Callable
from fastapi import Form, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from neo4j import AsyncSession as Neo4jAsyncSession
from neo4j import AsyncDriver

import crud, models, schemas
from core.config import settings
from db.session import SessionLocal
from gdb.session import Neo4jSessionLocal

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/oauth",
    auto_error=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def get_gdb() -> AsyncGenerator[tuple[Neo4jAsyncSession, AsyncDriver], None]:
    # TODO: implement Neo4jSessionManager to manage multiple instances
    async with Neo4jSessionLocal() as (session, driver):
        yield session, driver

async def get_token_payload(token: str ) -> schemas.TokenPayload:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGO]
        )
        token_payload = schemas.TokenPayload(**payload)
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    return token_payload

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> models.User:
    token_payload = await get_token_payload(token)
    user = await crud.user.get(db, id=token_payload.sub)
    if token_payload.refresh: # or not token_payload.totp:
        # refresh token is not a valid access token and 
        # TOTP False cannot be used to validate TOTP
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="TOTP verification required",
        )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

async def get_totp_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> models.User:
    token_payload = await get_token_payload(token)
    if token_payload.refresh or not token_payload.totp:
        # refresh token is not a valid access token and 
        # TOTP False cannot be used to validate TOTP
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="TOTP verification required",
        )
    user = await crud.user.get(db, id=token_payload.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

async def get_current_active_user(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    if not crud.user.is_active(current_user):
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_refresh_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> models.User:
    async with db.begin():
        token_payload = await get_token_payload(token)
        if not token_payload.refresh:
            # access token is not a valid refresh token
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Refresh token required",
            )
        user = await crud.user.get(db, id=token_payload.sub)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if not crud.user.is_active(user):
            raise HTTPException(status_code=400, detail="Inactive user")
        # check and revoke this refresh token
        token_obj = await crud.token.get(token=token, user=user)
        if not token_obj:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Could not validate credentials",
            )
        await crud.token.remove(db, db_obj=token_obj)
    return user

async def get_current_active_admin_user(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    if not crud.user.is_active(current_user):
        raise HTTPException(status_code=400, detail="Inactive user")
    if not crud.user.is_admin(current_user):
        raise HTTPException(status_code=400, detail="The user is not an admin user")
    return current_user


# class OAuth2EmailPasswordRequestForm(OAuth2PasswordRequestForm):
#     def __init__(
#         self,
#         *,
#         grant_type: str = Form(default=None, regex="password"),
#         username: str = Form(),
#         email: str = Form(),
#         password: str = Form(),
#         scope: str = Form(default=""),
#         client_id: str | None = Form(default=None),
#         client_secret: str | None = Form(default=None),
#     ):
#         super().__init__(grant_type=grant_type, username=username, password=password, 
#                          scope=scope, client_id=client_id, client_secret=client_secret)
#         self.email = email

# class OAuth2PasswordBearerWithCookie(OAuth2PasswordBearer):
#     async def __call__(self, request: Request) -> Optional[str]:
#         authorization: str = request.headers.get("Authorization")
#         scheme, _, param = authorization.partition(" ") if authorization else (None, None, None)
#         if not authorization or scheme.lower() != "bearer":
#             if self.auto_error:
#                 raise HTTPException(
#                     status_code=status.HTTP_401_UNAUTHORIZED,
#                     detail="Not authenticated",
#                     headers={"WWW-Authenticate": "Bearer"},
#                 )
#             else:
#                 return None
#         return param

# oauth2_scheme = OAuth2PasswordBearerWithCookie(
#     tokenUrl=f"{settings.API_V1_STR}/login/oauth",
#     auto_error=False
# )
