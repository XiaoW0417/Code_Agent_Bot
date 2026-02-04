"""
Password hashing utilities.
"""
import hashlib
import secrets
import hmac
from typing import Tuple


def _generate_salt(length: int = 32) -> str:
    """Generate a cryptographically secure salt."""
    return secrets.token_hex(length)


def _hash_with_salt(password: str, salt: str) -> str:
    """Hash password with salt using PBKDF2."""
    # Using hashlib's pbkdf2_hmac for secure hashing
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        iterations=100000,  # OWASP recommended minimum
        dklen=32
    )
    return key.hex()


def hash_password(password: str) -> str:
    """
    Hash a password for storage.
    
    Returns a string in format: algorithm$iterations$salt$hash
    """
    salt = _generate_salt()
    hash_value = _hash_with_salt(password, salt)
    return f"pbkdf2_sha256$100000${salt}${hash_value}"


def verify_password(password: str, hashed: str) -> bool:
    """
    Verify a password against a stored hash.
    
    Uses constant-time comparison to prevent timing attacks.
    """
    try:
        parts = hashed.split('$')
        if len(parts) != 4:
            return False
        
        algorithm, iterations, salt, stored_hash = parts
        
        if algorithm != 'pbkdf2_sha256':
            return False
        
        # Compute hash of provided password
        computed_hash = _hash_with_salt(password, salt)
        
        # Constant-time comparison
        return hmac.compare_digest(computed_hash, stored_hash)
    except Exception:
        return False


def is_password_strong(password: str, strict: bool = False) -> Tuple[bool, str]:
    """
    Check if password meets strength requirements.
    
    Args:
        password: The password to check
        strict: If True, enforce all complexity rules. If False, only check length.
    
    Returns (is_valid, message)
    """
    # Minimum length check (always enforced)
    if len(password) < 6:
        return False, "Password must be at least 6 characters long"
    
    # In non-strict mode, length is sufficient
    if not strict:
        return True, "Password is acceptable"
    
    # Strict mode: enforce complexity rules
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"
    
    return True, "Password is strong"
