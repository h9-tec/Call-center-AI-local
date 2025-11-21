"""
API Dependencies
"""
from typing import Generator, Optional
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.db.connection import SessionLocal
from app.core.config import settings
from app.core.security import verify_token
from app.services.call_manager import CallManager
from app.services.telephony.base import TelephonyProvider
from app.services.telephony.twilio_handler import TwilioVoiceHandler

# Security
security = HTTPBearer()

# Database dependency
async def get_db() -> Generator[AsyncSession, None, None]:
    """Get database session"""
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# Redis dependency
_redis_pool = None

async def get_redis_pool():
    """Get or create Redis connection pool"""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = await aioredis.from_url(
            settings.redis_url,
            max_connections=10,
            decode_responses=True
        )
    return _redis_pool


async def get_redis() -> aioredis.Redis:
    """Get Redis connection"""
    pool = await get_redis_pool()
    return pool


# Service dependencies
_call_manager = None

def get_call_manager(db: AsyncSession = Depends(get_db)) -> CallManager:
    """Get call manager instance"""
    global _call_manager
    if _call_manager is None:
        _call_manager = CallManager(db)
    return _call_manager


_telephony_provider = None

def get_telephony_provider() -> TelephonyProvider:
    """Get telephony provider based on configuration"""
    global _telephony_provider
    if _telephony_provider is None:
        if settings.telephony_provider == "twilio":
            from app.services.telephony.twilio_handler import TwilioProvider
            _telephony_provider = TwilioProvider()
        elif settings.telephony_provider == "asterisk":
            from app.services.telephony.asterisk_handler import AsteriskProvider
            _telephony_provider = AsteriskProvider()
        else:
            raise ValueError(f"Unknown telephony provider: {settings.telephony_provider}")
    return _telephony_provider


_voice_handler = None

def get_voice_handler() -> TwilioVoiceHandler:
    """Get voice handler instance"""
    global _voice_handler
    if _voice_handler is None:
        _voice_handler = TwilioVoiceHandler()
    return _voice_handler


# Authentication dependencies
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Get current authenticated user"""
    token = credentials.credentials
    
    try:
        payload = verify_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # In production, you would fetch user from database
    # For now, return a mock user
    return {
        "id": user_id,
        "email": f"user_{user_id}@example.com",
        "is_active": True
    }


async def get_current_active_user(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Get current active user"""
    if not current_user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user
