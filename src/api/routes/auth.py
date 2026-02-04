"""
Authentication endpoints.
"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy.orm import Session

from src.infra.database.connection import get_db
from src.infra.database.models import User
from src.infra.database.repositories import UserRepository
from src.infra.auth.password import hash_password, verify_password, is_password_strong
from src.infra.auth.jwt import create_access_token, create_refresh_token, decode_token
from src.infra.auth.dependencies import get_current_active_user

logger = logging.getLogger(__name__)
router = APIRouter()


# Request/Response Models
class UserRegisterRequest(BaseModel):
    """User registration request."""
    username: str = Field(..., min_length=3, max_length=50, pattern=r'^[a-zA-Z0-9_-]+$')
    email: EmailStr
    password: str = Field(..., min_length=6)
    display_name: Optional[str] = Field(None, max_length=100)

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        # Use non-strict mode for easier development
        is_strong, message = is_password_strong(v, strict=False)
        if not is_strong:
            raise ValueError(message)
        return v


class UserLoginRequest(BaseModel):
    """User login request."""
    username: str = Field(..., description="Username or email")
    password: str


class TokenResponse(BaseModel):
    """Token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str


class UserResponse(BaseModel):
    """User response."""
    id: str
    username: str
    email: str
    display_name: Optional[str]
    avatar_url: Optional[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    """User update request."""
    display_name: Optional[str] = Field(None, max_length=100)
    avatar_url: Optional[str] = Field(None, max_length=500)


class PasswordChangeRequest(BaseModel):
    """Password change request."""
    current_password: str
    new_password: str = Field(..., min_length=6)

    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        is_strong, message = is_password_strong(v, strict=False)
        if not is_strong:
            raise ValueError(message)
        return v


# Endpoints
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: UserRegisterRequest,
    db: Session = Depends(get_db)
) -> User:
    """
    Register a new user account.
    """
    user_repo = UserRepository(db)
    
    # Check if username exists
    if user_repo.get_by_username(request.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already registered"
        )
    
    # Check if email exists
    if user_repo.get_by_email(request.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    # Create user
    user = user_repo.create(
        username=request.username,
        email=request.email,
        hashed_password=hash_password(request.password),
        display_name=request.display_name or request.username
    )
    
    logger.info(f"New user registered: {user.username}")
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    request: UserLoginRequest,
    db: Session = Depends(get_db)
) -> TokenResponse:
    """
    Authenticate user and return tokens.
    """
    user_repo = UserRepository(db)
    
    # Find user by username or email
    user = user_repo.get_by_username_or_email(request.username)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    # Update last login
    user_repo.update_last_login(user.id)
    
    # Generate tokens
    access_token = create_access_token(user.id, user.username)
    refresh_token = create_refresh_token(user.id, user.username)
    
    logger.info(f"User logged in: {user.username}")
    
    from src.core.config import settings
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.auth.access_token_expire_minutes * 60
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
) -> TokenResponse:
    """
    Refresh access token using refresh token.
    """
    try:
        token_data = decode_token(request.refresh_token)
        
        if token_data.token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Verify user still exists and is active
        user_repo = UserRepository(db)
        user = user_repo.get_by_id(token_data.user_id)
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Generate new tokens
        access_token = create_access_token(user.id, user.username)
        refresh_token = create_refresh_token(user.id, user.username)
        
        from src.core.config import settings
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.auth.access_token_expire_minutes * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Get current user information.
    """
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    request: UserUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> User:
    """
    Update current user profile.
    """
    user_repo = UserRepository(db)
    
    update_data = request.model_dump(exclude_unset=True)
    if update_data:
        user = user_repo.update(current_user.id, **update_data)
        return user
    
    return current_user


@router.post("/change-password")
async def change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    Change user password.
    """
    # Verify current password
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    user_repo = UserRepository(db)
    user_repo.update(
        current_user.id,
        hashed_password=hash_password(request.new_password)
    )
    
    logger.info(f"Password changed for user: {current_user.username}")
    return {"message": "Password changed successfully"}
