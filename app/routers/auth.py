import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import UserRegister, UserResponse, UserLogin
from app.security import (
    hash_password,
    verify_password,
    generate_verification_token,
    hash_verification_token,
    get_verification_expiry,
    create_access_token
)
from app.email_service import create_verification_email
from app.email_sender import send_email


BASE_URL = os.getenv(
    "BINLOCK_BASE_URL",
    "http://127.0.0.1:8000"
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
def register_user(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    existing_user = db.query(User).filter(
        User.email == user_data.email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists."
        )

    hashed_password = hash_password(user_data.password)

    verification_token = generate_verification_token()

    token_hash = hash_verification_token(
        verification_token
    )

    token_expiry = get_verification_expiry()

    verification_link = (
        f"{BASE_URL}/auth/verify-email?token={verification_token}"
    )

    email_message = create_verification_email(
        user_data.email,
        verification_link
    )


    new_user = User(
        full_name=user_data.full_name,
        email=user_data.email,
        hashed_password=hashed_password,
        role="user",
        is_active=False,
        is_verified=False,
        verification_token_hash=token_hash,
        verification_token_expires_at=token_expiry
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    send_email(email_message)

    return new_user

@router.post("/resend-verification")
def resend_verification_email(
    email: str,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.email == email
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found."
        )

    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email has already been verified."
        )

    verification_token = generate_verification_token()

    user.verification_token_hash = hash_verification_token(
        verification_token
    )

    user.verification_token_expires_at = get_verification_expiry()

    verification_link = (
        f"{BASE_URL}/auth/verify-email?token={verification_token}"
    )

    email_message = create_verification_email(
        user.email,
        verification_link
    )

    db.commit()

    send_email(email_message)

    return {
        "message": "A new verification email has been sent."
    }

@router.get("/verify-email")
def verify_email(
    token: str,
    db: Session = Depends(get_db)
):
    token_hash = hash_verification_token(token)

    user = db.query(User).filter(
        User.verification_token_hash == token_hash
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token."
        )

    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email has already been verified."
        )

    if (
        user.verification_token_expires_at is None
        or user.verification_token_expires_at < datetime.now(timezone.utc)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token has expired."
        )

    user.is_verified = True
    user.is_active = True
    user.verification_token_hash = None
    user.verification_token_expires_at = None

    db.commit()

    return {
        "message": "Email verified successfully. Your BinLock account is now active."
    }

@router.post("/login")
def login_user(
    user_data: UserLogin,
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(
        User.email == user_data.email
    ).first()

    if not user or not verify_password(
        user_data.password,
        user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Ensure email has been verified
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before logging in."
        )

    # Ensure account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is inactive."
        )

    # Generate JWT access token
    access_token = create_access_token(user.id)

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }