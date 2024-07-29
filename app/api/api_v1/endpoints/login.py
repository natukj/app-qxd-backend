from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt

import crud, models, schemas
from api import deps
from core import security
from core.config import settings

router = APIRouter()

@router.post("/oauth", response_model=schemas.TokenSchema)
async def login_with_oauth2(
    db: AsyncSession = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> schemas.TokenSchema:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    print("Received form data:", form_data.__dict__)
    user = await crud.user.authenticate(
        db, email=form_data.username, password=form_data.password
    )
    if not form_data.password or not user or not crud.user.is_active(user):
        raise HTTPException(status_code=400, detail="Login failed; incorrect email or password")
    # check if totp active
    refresh_token = None
    force_totp = True
    if not user.totp_secret:
        force_totp = False
        refresh_token = security.create_refresh_token(subject=user.id)
        await crud.token.create(db=db, obj_in=refresh_token, user_obj=user)
    return {
        "access_token": security.create_access_token(subject=user.id, force_totp=force_totp),
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }

@router.post("/signup", response_model=schemas.TokenSchema)
async def signup_with_oauth2(
    db: AsyncSession = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> schemas.TokenSchema:
    print("Received form data:", form_data.__dict__)
    existing_user = await crud.user.get_by_email(db, email=form_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    user_in = schemas.UserCreate(
        email=form_data.username,
        password=form_data.password
    )
    user = await crud.user.create(db, obj_in=user_in)
    if not user:
        raise HTTPException(status_code=400, detail="Signup failed")
    
    refresh_token = security.create_refresh_token(subject=user.id)    
    await crud.token.create(db=db, obj_in=refresh_token, user_obj=user)
    return {
        "access_token": security.create_access_token(subject=user.id),
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }

@router.post("/refresh", response_model=schemas.TokenSchema)
async def refresh_token(
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_refresh_user),
) -> schemas.TokenSchema:
    """
    Refresh tokens for future requests
    """
    refresh_token = security.create_refresh_token(subject=current_user.id)
    await crud.token.create(db=db, obj_in=refresh_token, user_obj=current_user)
    return {
        "access_token": security.create_access_token(subject=current_user.id),
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }