"""
Call data models
"""
from enum import Enum
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, DateTime, Float, JSON, Enum as SQLEnum
from sqlalchemy.sql import func

from app.db.connection import Base


class CallStatus(str, Enum):
    """Call status enum"""
    CREATED = "created"
    INITIATED = "initiated"
    RINGING = "ringing"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BUSY = "busy"
    NO_ANSWER = "no_answer"
    CANCELLED = "cancelled"


class CallDirection(str, Enum):
    """Call direction enum"""
    INBOUND = "inbound"
    OUTBOUND = "outbound"


# SQLAlchemy Model
class Call(Base):
    """Call database model"""
    __tablename__ = "calls"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    
    # Phone numbers
    from_number = Column(String, nullable=False)
    to_number = Column(String, nullable=False)
    
    # Call details
    status = Column(SQLEnum(CallStatus), default=CallStatus.CREATED, nullable=False, index=True)
    direction = Column(SQLEnum(CallDirection), default=CallDirection.OUTBOUND, nullable=False)
    provider_call_id = Column(String, nullable=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    
    # Duration in seconds
    duration = Column(Float, nullable=True)
    
    # Call metadata (conversation, recording URL, metrics, etc.)
    call_metadata = Column("metadata", JSON, default=dict, nullable=False)
    
    # Context passed at creation
    context = Column(JSON, default=dict, nullable=False)


# Pydantic Models
class CallBase(BaseModel):
    """Base call model"""
    from_number: str
    to_number: str
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)


class CallCreate(CallBase):
    """Call creation model"""
    pass


class CallUpdate(BaseModel):
    """Call update model"""
    status: Optional[CallStatus] = None
    provider_call_id: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class CallResponse(CallBase):
    """Call response model"""
    id: str
    user_id: str
    status: CallStatus
    direction: CallDirection
    provider_call_id: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)  # This maps to call_metadata column
    
    class Config:
        from_attributes = True


class CallMetrics(BaseModel):
    """Call metrics model"""
    transcription_confidence: float = Field(ge=0.0, le=1.0)
    response_latency_ms: float
    total_turns: int
    error_count: int = 0
    audio_quality: Optional[float] = Field(None, ge=0.0, le=1.0)
    customer_sentiment: Optional[str] = None
