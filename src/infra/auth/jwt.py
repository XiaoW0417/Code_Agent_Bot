"""
JWT token utilities.
"""
import json
import hmac
import hashlib
import base64
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from dataclasses import dataclass

from src.core.config import settings
from src.core.exceptions import AuthenticationError, ErrorCode

logger = logging.getLogger(__name__)


@dataclass
class TokenData:
    """Decoded token data."""
    user_id: str
    username: str
    token_type: str  # "access" or "refresh"
    exp: datetime
    iat: datetime


def _base64url_encode(data: bytes) -> str:
    """URL-safe base64 encode without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')


def _base64url_decode(data: str) -> bytes:
    """URL-safe base64 decode with padding restoration."""
    padding = 4 - len(data) % 4
    if padding != 4:
        data += '=' * padding
    return base64.urlsafe_b64decode(data)


def _create_signature(message: str, secret: str) -> str:
    """Create HMAC-SHA256 signature."""
    signature = hmac.new(
        secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).digest()
    return _base64url_encode(signature)


def create_access_token(user_id: str, username: str) -> str:
    """
    Create a JWT access token.
    
    Args:
        user_id: User's unique identifier
        username: User's username
        
    Returns:
        JWT token string
    """
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=settings.auth.access_token_expire_minutes)
    
    header = {
        "alg": settings.auth.algorithm,
        "typ": "JWT"
    }
    
    payload = {
        "sub": user_id,
        "username": username,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp())
    }
    
    header_encoded = _base64url_encode(json.dumps(header, separators=(',', ':')).encode('utf-8'))
    payload_encoded = _base64url_encode(json.dumps(payload, separators=(',', ':')).encode('utf-8'))
    
    message = f"{header_encoded}.{payload_encoded}"
    signature = _create_signature(message, settings.auth.secret_key)
    
    return f"{message}.{signature}"


def create_refresh_token(user_id: str, username: str) -> str:
    """
    Create a JWT refresh token.
    
    Refresh tokens have longer expiration and are used to get new access tokens.
    """
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=settings.auth.refresh_token_expire_days)
    
    header = {
        "alg": settings.auth.algorithm,
        "typ": "JWT"
    }
    
    payload = {
        "sub": user_id,
        "username": username,
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp())
    }
    
    header_encoded = _base64url_encode(json.dumps(header, separators=(',', ':')).encode('utf-8'))
    payload_encoded = _base64url_encode(json.dumps(payload, separators=(',', ':')).encode('utf-8'))
    
    message = f"{header_encoded}.{payload_encoded}"
    signature = _create_signature(message, settings.auth.secret_key)
    
    return f"{message}.{signature}"


def decode_token(token: str) -> TokenData:
    """
    Decode and validate a JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        TokenData with decoded claims
        
    Raises:
        AuthenticationError: If token is invalid or expired
    """
    try:
        parts = token.split('.')
        if len(parts) != 3:
            raise AuthenticationError(
                "Invalid token format",
                code=ErrorCode.INVALID_TOKEN
            )
        
        header_encoded, payload_encoded, signature = parts
        
        # Verify signature
        message = f"{header_encoded}.{payload_encoded}"
        expected_signature = _create_signature(message, settings.auth.secret_key)
        
        if not hmac.compare_digest(signature, expected_signature):
            raise AuthenticationError(
                "Invalid token signature",
                code=ErrorCode.INVALID_TOKEN
            )
        
        # Decode payload
        payload_json = _base64url_decode(payload_encoded)
        payload = json.loads(payload_json)
        
        # Check expiration
        exp_timestamp = payload.get("exp", 0)
        if datetime.now(timezone.utc).timestamp() > exp_timestamp:
            raise AuthenticationError(
                "Token has expired",
                code=ErrorCode.TOKEN_EXPIRED
            )
        
        return TokenData(
            user_id=payload.get("sub", ""),
            username=payload.get("username", ""),
            token_type=payload.get("type", "access"),
            exp=datetime.fromtimestamp(exp_timestamp, tz=timezone.utc),
            iat=datetime.fromtimestamp(payload.get("iat", 0), tz=timezone.utc)
        )
        
    except AuthenticationError:
        raise
    except Exception as e:
        logger.error(f"Token decode error: {e}")
        raise AuthenticationError(
            "Invalid token",
            code=ErrorCode.INVALID_TOKEN
        )
