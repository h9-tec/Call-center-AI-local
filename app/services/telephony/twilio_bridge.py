#!/usr/bin/env python3
"""
Twilio Bridge Service for Call Center AI
Handles Twilio API integration and call routing
"""

import os
import logging
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Dial, Say
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TwilioBridge:
    """Bridge between Twilio and local Call Center AI services"""

    def __init__(self):
        """Initialize Twilio client with credentials from environment"""
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.phone_number = os.getenv('TWILIO_PHONE_NUMBER')
        self.webhook_url = os.getenv('TWILIO_WEBHOOK_URL')

        if not all([self.account_sid, self.auth_token, self.phone_number]):
            raise ValueError("Missing Twilio credentials in environment variables")

        self.client = Client(self.account_sid, self.auth_token)
        logger.info(f"Twilio Bridge initialized with number: {self.phone_number}")

    def make_call(self, to_number, twiml_url=None):
        """Initiate an outbound call"""
        try:
            call = self.client.calls.create(
                to=to_number,
                from_=self.phone_number,
                # Our FastAPI server exposes /twilio/voice (not /twiml/voice)
                url=twiml_url or f"{self.webhook_url}/twilio/voice",
                method='POST'
            )
            logger.info(f"Call initiated to {to_number}, SID: {call.sid}")
            return call.sid
        except Exception as e:
            logger.error(f"Error making call: {str(e)}")
            raise

    def send_sms(self, to_number, message):
        """Send an SMS message"""
        try:
            message = self.client.messages.create(
                to=to_number,
                from_=self.phone_number,
                body=message
            )
            logger.info(f"SMS sent to {to_number}, SID: {message.sid}")
            return message.sid
        except Exception as e:
            logger.error(f"Error sending SMS: {str(e)}")
            raise

    def create_voice_response(self, message=None, action_url=None):
        """Create a TwiML voice response"""
        response = VoiceResponse()

        if message:
            response.say(message, voice='Polly.Amy', language='en-US')

        if action_url:
            response.redirect(action_url)

        return str(response)

    def handle_incoming_call(self, from_number, call_sid):
        """Handle an incoming call"""
        logger.info(f"Handling incoming call from {from_number}, SID: {call_sid}")

        response = VoiceResponse()
        response.say(
            f"Welcome to {os.getenv('COMPANY_NAME', 'AI Support Center')}. "
            "Please hold while we connect you to an agent.",
            voice='Polly.Amy'
        )

        # Connect to AI agent endpoint
        response.redirect(f"{self.webhook_url}/ai/agent")

        return str(response)

    def get_call_status(self, call_sid):
        """Get the status of a call"""
        try:
            call = self.client.calls(call_sid).fetch()
            return {
                'status': call.status,
                'duration': call.duration,
                'from': call.from_,
                'to': call.to,
                'direction': call.direction
            }
        except Exception as e:
            logger.error(f"Error getting call status: {str(e)}")
            return None

if __name__ == "__main__":
    # Test the bridge
    bridge = TwilioBridge()
    print(f"Twilio Bridge ready with number: {bridge.phone_number}")