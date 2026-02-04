"""
Authentication module.
"""
from src.infra.auth.password import hash_password, verify_password
from src.infra.auth.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    TokenData
)
from src.infra.auth.dependencies import (
    get_current_user,
    get_current_active_user,
    get_optional_user
)

__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "TokenData",
    "get_current_user",
    "get_current_active_user",
    "get_optional_user"
]
