"""
FastAPI authentication dependencies.
"""
import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from src.infra.database.connection import get_db
from src.infra.database.models import User
from src.infra.database.repositories import UserRepository
from src.infra.auth.jwt import decode_token, TokenData
from src.core.exceptions import AuthenticationError

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer(auto_error=False)


async def get_token_data(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[TokenData]:
    """
    Extract and validate token from request.
    Returns None if no token provided.
    """
    if credentials is None:
        return None
    
    try:
        token_data = decode_token(credentials.credentials)
        return token_data
    except AuthenticationError:
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the current authenticated user.
    Raises 401 if not authenticated.
    """
    try:
        token_data = decode_token(credentials.credentials)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(token_data.user_id)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get the current active user.
    Raises 403 if user is inactive.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    return current_user


async def get_optional_user(
    token_data: Optional[TokenData] = Depends(get_token_data),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get the current user if authenticated, None otherwise.
    Does not raise errors for missing/invalid tokens.
    """
    if token_data is None:
        return None
    
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(token_data.user_id)
    
    if user is None or not user.is_active:
        return None
    
    return user


async def require_superuser(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Require superuser privileges.
    Raises 403 if not a superuser.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser privileges required"
        )
    return current_user
