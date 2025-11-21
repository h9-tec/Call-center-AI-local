"""
Call management service
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
import uuid

from app.models.call import Call, CallStatus
from app.db.repositories.call_repository import CallRepository

logger = logging.getLogger(__name__)


class CallManager:
    """Manages call lifecycle and data"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = CallRepository(db)
        self._active_calls: Dict[str, Dict[str, Any]] = {}
    
    async def create_call(
        self,
        to_number: str,
        from_number: str,
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Call:
        """Create a new call record"""
        call_id = str(uuid.uuid4())
        
        call = await self.repository.create(
            id=call_id,
            to_number=to_number,
            from_number=from_number,
            user_id=user_id,
            status=CallStatus.CREATED,
            direction="outbound",
            context=context or {},
            created_at=datetime.utcnow()
        )
        
        # Track active call
        self._active_calls[call_id] = {
            "started_at": datetime.utcnow(),
            "status": CallStatus.CREATED,
            "conversation": [],
            "metadata": {}
        }
        
        logger.info(f"Created call {call_id} from {from_number} to {to_number}")
        return call
    
    async def update_call(
        self,
        call_id: str,
        **kwargs
    ) -> Optional[Call]:
        """Update call record"""
        call = await self.repository.update(call_id, **kwargs)
        
        if call and call_id in self._active_calls:
            self._active_calls[call_id]["status"] = kwargs.get("status", call.status)
            if "metadata" in kwargs:
                self._active_calls[call_id]["metadata"].update(kwargs["metadata"])
        
        return call
    
    async def get_call(self, call_id: str) -> Optional[Call]:
        """Get call by ID"""
        return await self.repository.get(call_id)
    
    async def list_calls(
        self,
        user_id: Optional[str] = None,
        status: Optional[CallStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Call]:
        """List calls with filtering"""
        return await self.repository.list(
            user_id=user_id,
            status=status,
            skip=skip,
            limit=limit
        )
    
    async def end_call(self, call_id: str) -> bool:
        """End an active call"""
        call = await self.get_call(call_id)
        if not call:
            return False
        
        # Calculate duration
        duration = None
        if call.started_at:
            duration = (datetime.utcnow() - call.started_at).total_seconds()
        
        # Update call record
        await self.update_call(
            call_id,
            status=CallStatus.COMPLETED,
            ended_at=datetime.utcnow(),
            duration=duration
        )
        
        # Remove from active calls
        if call_id in self._active_calls:
            del self._active_calls[call_id]
        
        logger.info(f"Ended call {call_id} with duration {duration}s")
        return True
    
    async def add_to_conversation(
        self,
        call_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Add message to conversation history"""
        if call_id not in self._active_calls:
            logger.warning(f"Call {call_id} not found in active calls")
            return
        
        message = {
            "timestamp": datetime.utcnow().isoformat(),
            "role": role,
            "content": content,
            "metadata": metadata or {}
        }
        
        self._active_calls[call_id]["conversation"].append(message)
        
        # Also update in database
        call = await self.get_call(call_id)
        if call:
            conversation = call.call_metadata.get("conversation", [])
            conversation.append(message)
            
            await self.update_call(
                call_id,
                metadata={
                    **call.call_metadata,
                    "conversation": conversation
                }
            )
    
    async def get_conversation(self, call_id: str) -> List[Dict[str, Any]]:
        """Get conversation history for a call"""
        if call_id in self._active_calls:
            return self._active_calls[call_id]["conversation"]
        
        call = await self.get_call(call_id)
        if call:
            return call.call_metadata.get("conversation", [])
        
        return []
    
    async def get_transcript(self, call_id: str) -> Optional[str]:
        """Get formatted transcript for a call"""
        conversation = await self.get_conversation(call_id)
        if not conversation:
            return None
        
        transcript_lines = []
        for msg in conversation:
            timestamp = msg.get("timestamp", "")
            role = msg.get("role", "Unknown")
            content = msg.get("content", "")
            
            transcript_lines.append(f"[{timestamp}] {role}: {content}")
        
        return "\n".join(transcript_lines)
    
    async def get_recording_url(self, call_id: str) -> Optional[str]:
        """Get recording URL for a call"""
        call = await self.get_call(call_id)
        if call:
            return call.call_metadata.get("recording_url")
        return None
    
    async def update_call_metrics(
        self,
        call_id: str,
        metrics: Dict[str, Any]
    ):
        """Update call metrics"""
        call = await self.get_call(call_id)
        if call:
            current_metrics = call.call_metadata.get("metrics", {})
            current_metrics.update(metrics)
            
            await self.update_call(
                call_id,
                metadata={
                    **call.call_metadata,
                    "metrics": current_metrics
                }
            )
    
    def get_active_calls(self) -> Dict[str, Dict[str, Any]]:
        """Get all active calls"""
        return self._active_calls.copy()
    
    def get_active_call_count(self) -> int:
        """Get count of active calls"""
        return len(self._active_calls)
