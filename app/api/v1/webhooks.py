"""
Webhooks for Twilio integration
"""
import logging
from fastapi import APIRouter, Request, Response
from fastapi.responses import PlainTextResponse
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream

from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/voice")
async def twilio_voice_webhook(request: Request) -> Response:
    """Handle incoming Twilio voice webhook"""
    form_data = await request.form()
    call_sid = form_data.get("CallSid")
    from_number = form_data.get("From")
    to_number = form_data.get("To")
    
    logger.info(f"Incoming call {call_sid} from {from_number} to {to_number}")
    
    # Create TwiML response
    response = VoiceResponse()
    
    # Say initial greeting
    response.say(
        f"Hello, this is {settings.agent_name or 'your AI assistant'}. How can I help you today?",
        voice="Polly.Amy"
    )
    
    # Connect to WebSocket for streaming
    connect = Connect()
    stream = Stream(
        url=f"wss://{settings.public_url.replace('http://', '').replace('https://', '')}/api/v1/ws/audio/{call_sid}"
    )
    stream.parameter(name="audioTrack", value="inbound")
    connect.append(stream)
    response.append(connect)
    
    # Keep the call alive
    response.pause(length=3600)
    
    return Response(content=str(response), media_type="application/xml")


@router.post("/status")
async def twilio_status_webhook(request: Request) -> Response:
    """Handle Twilio call status updates"""
    form_data = await request.form()
    call_sid = form_data.get("CallSid")
    call_status = form_data.get("CallStatus")
    
    logger.info(f"Call {call_sid} status update: {call_status}")
    
    # TODO: Update call record in database
    
    return PlainTextResponse("OK")


@router.post("/recording")
async def twilio_recording_webhook(request: Request) -> Response:
    """Handle Twilio recording status"""
    form_data = await request.form()
    recording_sid = form_data.get("RecordingSid")
    recording_url = form_data.get("RecordingUrl")
    call_sid = form_data.get("CallSid")
    
    logger.info(f"Recording {recording_sid} for call {call_sid} available at {recording_url}")
    
    # TODO: Store recording URL in database
    
    return PlainTextResponse("OK")
