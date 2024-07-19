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
    
    access_token = security.create_access_token(subject=user.id)
    refresh_token = security.create_refresh_token(subject=user.id)
    
    print(f"Debug - access_token: {access_token}")
    print(f"Debug - refresh_token: {refresh_token}")
    print(f"Debug - user.id: {user.id}")
    try:
        await crud.token.create(db=db, obj_in=refresh_token, user_obj=user)
    except ValueError as e:
        # Handle the case where the token already exists
        print(f"Error creating token: {str(e)}")
        await crud.user.remove(db=db, id=user.id)
        raise HTTPException(status_code=400, detail="Token creation failed")
    
    return {
        "access_token": access_token,
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








# from fastapi import APIRouter, Depends, HTTPException, status
# from fastapi.security import OAuth2PasswordRequestForm
# from jose import JWTError, jwt
# from datetime import datetime, timedelta
# from pydantic import BaseModel
# import db


# from sqlalchemy.ext.asyncio import AsyncSession

# router = APIRouter()

# # This should be a more secure way to store secrets in a real application
# SECRET_KEY = "your-secret-key"
# ALGORITHM = "HS256"
# ACCESS_TOKEN_EXPIRE_MINUTES = 6000

# class Token(BaseModel):
#     access_token: str
#     token_type: str

# class TokenData(BaseModel):
#     username: str | None = None

# def authenticate_user(username: str, password: str):
#     user = db.get_user(username)
#     if not user:
#         return False
#     if not db.verify_password(username, password):
#         return False
#     return user

# def create_access_token(data: dict, expires_delta: timedelta | None = None):
#     to_encode = data.copy()
#     if expires_delta:
#         expire = datetime.utcnow() + expires_delta
#     else:
#         expire = datetime.utcnow() + timedelta(minutes=6000)
#     to_encode.update({"exp": expire})
#     encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
#     return encoded_jwt

# @router.post("/token", response_model=Token)
# async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
#     user = authenticate_user(form_data.username, form_data.password)
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Incorrect username or password",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
#     access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
#     access_token = create_access_token(
#         data={"sub": user['username']}, expires_delta=access_token_expires
#     )
#     return {"access_token": access_token, "token_type": "bearer"}
