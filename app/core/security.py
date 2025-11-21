"""
Security utilities
"""
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
import secrets
from passlib.context import CryptContext
from jose import JWTError, jwt

from app.core.config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
ALGORITHM = settings.jwt_algorithm
SECRET_KEY = settings.secret_key
ACCESS_TOKEN_EXPIRE_HOURS = settings.jwt_expiry_hours


def create_access_token(
    subject: str | Any,
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[Dict[str, Any]] = None
) -> str:
    """Create JWT access token"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "iat": datetime.utcnow(),
        "type": "access"
    }
    
    if additional_claims:
        to_encode.update(additional_claims)
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Dict[str, Any]:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise ValueError("Invalid token")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password"""
    return pwd_context.hash(password)


def generate_api_key() -> str:
    """Generate secure API key"""
    return secrets.token_urlsafe(32)


def generate_secret_key() -> str:
    """Generate secret key for sessions"""
    return secrets.token_hex(32)


def validate_api_key(api_key: str) -> bool:
    """Validate API key format"""
    # Basic validation - in production, check against database
    return len(api_key) >= 32 and api_key.replace("-", "").replace("_", "").isalnum()


def sanitize_phone_number(phone: str) -> str:
    """Sanitize phone number for security"""
    # Remove all non-digit characters except +
    cleaned = "".join(c for c in phone if c.isdigit() or c == "+")
    
    # Ensure it starts with + for international format
    if cleaned and not cleaned.startswith("+"):
        cleaned = "+" + cleaned
    
    # Basic length validation
    if len(cleaned) < 10 or len(cleaned) > 16:
        raise ValueError("Invalid phone number length")
    
    return cleaned


def mask_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Mask sensitive fields in data"""
    sensitive_fields = [
        "password", "token", "api_key", "auth_token",
        "credit_card", "ssn", "phone_number", "email"
    ]
    
    masked_data = data.copy()
    
    for field in sensitive_fields:
        if field in masked_data:
            value = str(masked_data[field])
            if len(value) > 4:
                masked_data[field] = value[:2] + "*" * (len(value) - 4) + value[-2:]
            else:
                masked_data[field] = "*" * len(value)
    
    return masked_data
