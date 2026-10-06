from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.deps import DbSession
from app.models import Profile, User
from app.schemas.auth import RegisterRequest, TokenResponse, UserOut
from app.security import DUMMY_HASH, create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: DbSession):
    """Create a user plus an empty profile (only the username is set)."""
    email = payload.email.lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    if db.scalar(select(Profile.id).where(func.lower(Profile.username) == payload.username.lower())):
        raise HTTPException(status.HTTP_409_CONFLICT, "Username already taken")

    user = User(email=email, hashed_password=hash_password(payload.password))
    user.profile = Profile(username=payload.username)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # lost a race on email/username
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Email or username already in use")
    return user


@router.post("/token", response_model=TokenResponse)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession):
    """OAuth2 password flow. The form's `username` field carries the account email."""
    user = db.scalar(select(User).where(User.email == form.username.strip().lower()))
    password_ok = verify_password(form.password, user.hashed_password if user else DUMMY_HASH)
    if not user or not password_ok or not user.is_active:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(access_token=create_access_token(user.id))
