"""
Call management API endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.core.config import settings
from app.services.call_manager import CallManager
from app.services.telephony.base import TelephonyProvider
from app.models.call import Call, CallStatus, CallCreate, CallResponse
from app.api.deps import get_call_manager, get_telephony_provider, get_current_user

router = APIRouter()


@router.post("/calls", response_model=CallResponse)
async def create_call(
    call_data: CallCreate,
    call_manager: CallManager = Depends(get_call_manager),
    telephony: TelephonyProvider = Depends(get_telephony_provider),
    current_user = Depends(get_current_user)
) -> CallResponse:
    """Initiate a new outbound call"""
    try:
        # Create call record
        call = await call_manager.create_call(
            to_number=call_data.to_number,
            from_number=call_data.from_number,
            context=call_data.context,
            user_id=current_user.id
        )
        
        # Initiate call through telephony provider
        provider_call_id = await telephony.make_call(
            to_number=call_data.to_number,
            from_number=call_data.from_number,
            webhook_url=f"{settings.public_url}/api/v1/webhooks/voice/{call.id}"
        )
        
        # Update call with provider ID
        call = await call_manager.update_call(
            call.id,
            provider_call_id=provider_call_id,
            status=CallStatus.INITIATED
        )
        
        return CallResponse.from_orm(call)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate call: {str(e)}"
        )


@router.get("/calls", response_model=List[CallResponse])
async def list_calls(
    skip: int = 0,
    limit: int = 100,
    status: Optional[CallStatus] = None,
    call_manager: CallManager = Depends(get_call_manager),
    current_user = Depends(get_current_user)
) -> List[CallResponse]:
    """List calls with optional filtering"""
    calls = await call_manager.list_calls(
        user_id=current_user.id,
        status=status,
        skip=skip,
        limit=limit
    )
    return [CallResponse.from_orm(call) for call in calls]


@router.get("/calls/{call_id}", response_model=CallResponse)
async def get_call(
    call_id: str,
    call_manager: CallManager = Depends(get_call_manager),
    current_user = Depends(get_current_user)
) -> CallResponse:
    """Get call details"""
    call = await call_manager.get_call(call_id)
    
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )
    
    # Check ownership
    if call.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return CallResponse.from_orm(call)


@router.delete("/calls/{call_id}")
async def end_call(
    call_id: str,
    call_manager: CallManager = Depends(get_call_manager),
    telephony: TelephonyProvider = Depends(get_telephony_provider),
    current_user = Depends(get_current_user)
) -> dict:
    """End an active call"""
    call = await call_manager.get_call(call_id)
    
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )
    
    # Check ownership
    if call.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # End call through telephony provider
    if call.provider_call_id:
        await telephony.end_call(call.provider_call_id)
    
    # Update call status
    await call_manager.update_call(
        call_id,
        status=CallStatus.COMPLETED,
        ended_at=datetime.utcnow()
    )
    
    return {"message": "Call ended successfully"}


@router.get("/calls/{call_id}/transcript")
async def get_call_transcript(
    call_id: str,
    call_manager: CallManager = Depends(get_call_manager),
    current_user = Depends(get_current_user)
) -> dict:
    """Get call transcript"""
    call = await call_manager.get_call(call_id)
    
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )
    
    # Check ownership
    if call.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    transcript = await call_manager.get_transcript(call_id)
    
    if not transcript:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcript not available"
        )
    
    return {
        "call_id": call_id,
        "transcript": transcript,
        "duration": call.duration,
        "created_at": call.created_at
    }


@router.get("/calls/{call_id}/recording")
async def get_call_recording(
    call_id: str,
    call_manager: CallManager = Depends(get_call_manager),
    current_user = Depends(get_current_user)
) -> dict:
    """Get call recording URL"""
    call = await call_manager.get_call(call_id)
    
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )
    
    # Check ownership
    if call.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    recording_url = await call_manager.get_recording_url(call_id)
    
    if not recording_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recording not available"
        )
    
    return {
        "call_id": call_id,
        "recording_url": recording_url,
        "duration": call.duration,
        "expires_at": datetime.utcnow().timestamp() + 3600  # 1 hour expiry
    }
