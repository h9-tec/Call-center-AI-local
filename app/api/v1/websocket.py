"""
WebSocket handlers for real-time audio streaming
"""
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Optional

from app.services.call_manager import CallManager
from app.services.telephony.twilio_handler import TwilioVoiceHandler
from app.api.deps import get_call_manager, get_voice_handler
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/ws/audio/{call_sid}")
async def audio_websocket(
    websocket: WebSocket,
    call_sid: str,
    call_manager: CallManager = Depends(get_call_manager),
    voice_handler: TwilioVoiceHandler = Depends(get_voice_handler)
):
    """WebSocket endpoint for Twilio Media Streams"""
    await websocket.accept()
    logger.info(f"WebSocket connected for call {call_sid}")
    
    # Initialize session
    voice_handler.sessions[call_sid] = {
        "start_time": __import__("datetime").datetime.now(),
        "conversation": [],
        "audio_buffer": bytearray(),
        "is_speaking": False,
        "last_activity": __import__("datetime").datetime.now(),
    }
    
    stream_sid = None
    
    try:
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)
            event = data.get("event")
            
            logger.debug(f"Received event: {event}")
            
            if event == "connected":
                logger.info(f"Twilio WebSocket connected for call {call_sid}")
                
            elif event == "start":
                stream_sid = data.get("streamSid")
                if stream_sid:
                    voice_handler.sessions[call_sid]["stream_sid"] = stream_sid
                    logger.info(f"Twilio stream started for call {call_sid} with streamSid {stream_sid}")
                    await voice_handler._send_greeting(websocket, call_sid)
                    
            elif event == "media":
                media = data.get("media") or {}
                payload = media.get("payload")
                if payload:
                    logger.debug(f"Processing audio chunk for {call_sid}")
                    await voice_handler._process_audio_chunk(
                        websocket,
                        call_sid,
                        payload,
                    )
                    
            elif event == "stop":
                logger.info(f"Twilio stream stopped for call {call_sid}")
                break
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for call {call_sid}")
    except Exception as e:
        logger.error(f"Error in WebSocket for call {call_sid}: {e}", exc_info=True)
    finally:
        # Clean up session
        if call_sid in voice_handler.sessions:
            del voice_handler.sessions[call_sid]
        await call_manager.end_call(call_sid)
        logger.info(f"WebSocket closed for call {call_sid}")


@router.websocket("/ws/client/{session_id}")
async def client_websocket(
    websocket: WebSocket,
    session_id: str
):
    """WebSocket endpoint for web clients (future feature)"""
    await websocket.accept()
    logger.info(f"Client WebSocket connected: {session_id}")
    
    try:
        while True:
            # Handle client messages
            data = await websocket.receive_json()
            message_type = data.get("type")
            
            if message_type == "audio":
                # Process audio from client
                pass
            elif message_type == "control":
                # Handle control messages
                pass
                
    except WebSocketDisconnect:
        logger.info(f"Client WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"Error in client WebSocket {session_id}: {e}", exc_info=True)
