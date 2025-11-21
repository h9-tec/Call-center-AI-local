#!/usr/bin/env python3
"""
Twilio Voice Handler for Call Center AI
Manages real-time voice processing, transcription, and AI responses
"""

import os
import json
import asyncio
import logging
import aiohttp
import websockets
import base64
import time
import numpy as np
from typing import Optional, Dict, Any, List
from datetime import datetime
from twilio.twiml.voice_response import VoiceResponse, Stream, Say, Gather
from dotenv import load_dotenv

# Local audio processing (Whisper-tiny STT + Kokoro TTS)
from app.services.audio_processor import AudioProcessor

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Temporarily set to DEBUG for troubleshooting

class TwilioVoiceHandler:
    """Handles real-time voice processing for Twilio calls"""

    def __init__(self):
        """Initialize the voice handler with service configurations"""
        # Twilio settings
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.phone_number = os.getenv('TWILIO_PHONE_NUMBER')

        # Service URLs (LLM only; STT/TTS are handled locally via AudioProcessor)
        self.whisper_url = os.getenv('WHISPER_URL', 'http://localhost:9000')
        self.piper_host = os.getenv('PIPER_HOST', 'localhost')
        self.piper_port = int(os.getenv('PIPER_PORT', '10200'))
        self.ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')

        # Model settings (LLM only; STT/TTS model config lives in AudioProcessor)
        self.whisper_model = os.getenv('WHISPER_MODEL', 'base')
        self.whisper_language = os.getenv('WHISPER_LANGUAGE', 'en')
        self.ollama_model = os.getenv('OLLAMA_MODEL', 'llama3.2:3b')
        self.piper_voice = os.getenv('PIPER_VOICE', 'en_US-amy-medium')

        # Audio settings
        self.sample_rate = int(os.getenv('AUDIO_SAMPLE_RATE', '8000'))
        self.channels = int(os.getenv('AUDIO_CHANNELS', '1'))
        self.chunk_size = int(os.getenv('AUDIO_CHUNK_SIZE', '320'))
        self.silence_threshold = int(os.getenv('AUDIO_SILENCE_THRESHOLD', '10'))

        # Agent settings
        self.agent_name = os.getenv('AGENT_NAME', 'Alex')
        self.company_name = os.getenv('COMPANY_NAME', 'AI Support Center')
        self.personality = os.getenv('AGENT_PERSONALITY', 'professional, helpful, empathetic')

        # Conversation settings
        self.context_turns = int(os.getenv('CONVERSATION_CONTEXT_TURNS', '3'))
        self.max_duration = int(os.getenv('MAX_CALL_DURATION', '3600'))

        # Active sessions
        self.sessions: Dict[str, Dict[str, Any]] = {}

        # Local audio processor (Whisper-tiny STT + Kokoro TTS)
        self.audio_processor = AudioProcessor()

        logger.info("Twilio Voice Handler initialized")

    async def create_stream_response(self, call_sid: str) -> str:
        """Create a TwiML response with media streaming"""
        response = VoiceResponse()

        # Initial greeting – use a Twilio-supported voice (do NOT derive from agent name)
        response.say(
            f"Hello, this is {self.agent_name} from {self.company_name}. How can I help you today?",
            voice="Polly.Amy",
            language="en-US",
        )

        # Build a valid WebSocket URL for Twilio Media Streams
        public_url = os.getenv("PUBLIC_URL", "localhost:8000")
        # Strip any scheme if the env mistakenly includes http/https
        public_url = public_url.replace("https://", "").replace("http://", "").strip("/")

        # Start media stream for real-time audio processing.
        # Use Twilio-recommended structure: <Connect><Stream>...</Stream></Connect>
        from twilio.twiml.voice_response import Connect  # local import to avoid unused when not used

        connect = Connect()
        stream = Stream(url=f"wss://{public_url}/ws/audio/{call_sid}")
        stream.parameter(name="audioTrack", value="inbound")
        connect.append(stream)
        response.append(connect)

        # Optional: keep the call alive in case stream disconnects
        response.pause(length=self.max_duration)

        return str(response)

    async def handle_audio_stream(self, websocket, path):
        """Handle WebSocket audio stream from Twilio"""
        call_sid = path.split('/')[-1]
        logger.info(f"Audio stream connected for call: {call_sid}")

        # Initialize session
        self.sessions[call_sid] = {
            'start_time': datetime.now(),
            'conversation': [],
            'audio_buffer': bytearray(),
            'is_speaking': False,
            'last_activity': datetime.now()
        }

        try:
            async for message in websocket:
                data = json.loads(message)
                event = data.get('event')

                if event == 'connected':
                    logger.info(f"Stream connected for call {call_sid}")
                    await self._send_greeting(websocket, call_sid)

                elif event == 'media':
                    # Process incoming audio
                    await self._process_audio_chunk(
                        websocket,
                        call_sid,
                        data['media']['payload']
                    )

                elif event == 'stop':
                    logger.info(f"Stream stopped for call {call_sid}")
                    break

        except Exception as e:
            logger.error(f"Error in audio stream for {call_sid}: {str(e)}")
        finally:
            # Cleanup session
            if call_sid in self.sessions:
                del self.sessions[call_sid]
            logger.info(f"Audio stream closed for call: {call_sid}")

    async def _process_audio_chunk(self, websocket, call_sid: str, audio_payload: str):
        """Process incoming audio chunk - SIMPLIFIED FOR TESTING"""
        logger.debug(f"_process_audio_chunk called for {call_sid}")
        try:
            session = self.sessions.get(call_sid)
            if not session:
                logger.error(f"No session found for call {call_sid}")
                logger.error(f"Available sessions: {list(self.sessions.keys())}")
                return
            logger.debug(f"Session found for {call_sid}")

            # Decode audio
            audio_data = base64.b64decode(audio_payload)
            
            # Log first chunk
            if not session.get('first_chunk_logged'):
                logger.info(f"First audio chunk received: {len(audio_data)} bytes for call {call_sid}")
                session['first_chunk_logged'] = True
            else:
                logger.debug(f"Audio chunk {len(audio_data)} bytes for call {call_sid}")
        
            # Skip processing if assistant is speaking
            if session.get('is_speaking', False):
                return
                
            # Add to buffer
            session['audio_buffer'].extend(audio_data)
            current_time = time.time()
            
            # Initialize simple timer
            if 'test_timer' not in session:
                session['test_timer'] = current_time
                logger.info(f"Timer initialized for call {call_sid}")
        
            # Process every 3 seconds for testing
            time_elapsed = current_time - session['test_timer']
            buffer_size = len(session['audio_buffer'])
            
            logger.debug(f"Timer check: elapsed={time_elapsed:.1f}s, buffer_size={buffer_size}")
            
            if time_elapsed >= 3.0 and buffer_size >= 16000:  # 3 seconds and at least 2 seconds of audio
                logger.info(f"TEST MODE: Processing after {time_elapsed:.1f}s, buffer: {buffer_size} bytes")
                
                # Reset timer
                session['test_timer'] = current_time
                
                # Extract audio
                audio_to_process = bytes(session['audio_buffer'])
                session['audio_buffer'] = bytearray()
                
                # Mark as speaking
                session['is_speaking'] = True
                
                try:
                    # Check audio energy before sending to Whisper
                    audio_array = np.frombuffer(audio_to_process, dtype=np.uint8)
                    energy = np.mean(np.abs(audio_array.astype(np.float32) - 128))
                    logger.info(f"Audio energy: {energy:.2f}, buffer size: {len(audio_to_process)} bytes")
                    
                    # Send to Whisper
                    logger.info(f"Sending {len(audio_to_process)} bytes to Whisper")
                    transcript = await self._transcribe_audio(audio_to_process)
                    logger.info(f"Whisper result: '{transcript}'")
                    
                    if transcript and transcript.strip():
                        # Add to conversation
                        session['conversation'].append({
                            'role': 'user',
                            'content': transcript,
                            'timestamp': datetime.now().isoformat()
                        })
                        
                        # Get AI response
                        logger.info(f"Getting AI response for: '{transcript}'")
                        response = await self._get_ai_response(session['conversation'])
                        
                        if response:
                            # Add to conversation
                            session['conversation'].append({
                                'role': 'assistant',
                                'content': response,
                                'timestamp': datetime.now().isoformat()
                            })
                            
                            # Send TTS
                            logger.info(f"Sending TTS response: '{response}'")
                            await self._send_speech_response(websocket, call_sid, response)
                            
                            # Wait dynamically based on response length
                            words = len(response.split())
                            wait_time = max(2.0, words / 2.5 + 1.0)
                            logger.debug(f"Waiting {wait_time:.1f}s after response")
                            await asyncio.sleep(wait_time)
                    else:
                        logger.warning("No transcript received or empty transcript")
                        
                except Exception as e:
                    logger.error(f"Processing error: {str(e)}", exc_info=True)
                finally:
                    session['is_speaking'] = False
                    
                return  # Skip all the complex VAD logic
            
            # COMMENTED OUT FOR TESTING - Complex VAD logic below
            return  # Early return for testing
            
            """
        # Initialize tracking variables
        if 'vad_state' not in session:
            session['vad_state'] = {
                'speech_active': False,
                'speech_start_time': None,
                'silence_start_time': None,
                'last_speech_time': None,
                'consecutive_silence_chunks': 0,
                'consecutive_speech_chunks': 0,
                'min_speech_chunks': 5,  # ~0.5 seconds of speech
                'min_silence_chunks': 15  # ~1.5 seconds of silence
            }
            
        vad = session['vad_state']
        
        # Analyze audio chunk for speech/silence
        # Convert μ-law to linear for analysis
        chunk_has_speech = False
        if len(audio_data) >= 80:  # At least 10ms of audio
            # Sample every 10th byte for efficiency
            samples = [abs(b - 128) for b in audio_data[::10]]
            if samples:
                avg_amplitude = sum(samples) / len(samples)
                max_amplitude = max(samples)
                # Dynamic thresholds for better detection
                chunk_has_speech = avg_amplitude > 3 or max_amplitude > 25
        
        # Update VAD state
        if chunk_has_speech:
            vad['consecutive_speech_chunks'] += 1
            vad['consecutive_silence_chunks'] = 0
            vad['last_speech_time'] = current_time
            
            # Start of speech detection
            if not vad['speech_active'] and vad['consecutive_speech_chunks'] >= vad['min_speech_chunks']:
                vad['speech_active'] = True
                vad['speech_start_time'] = current_time
                vad['silence_start_time'] = None
                logger.info(f"Speech started for call {call_sid}")
        else:
            vad['consecutive_silence_chunks'] += 1
            vad['consecutive_speech_chunks'] = 0
            
            # Start silence timer if speech was active
            if vad['speech_active'] and vad['silence_start_time'] is None:
                vad['silence_start_time'] = current_time
                
        # Calculate durations
        buffer_size = len(session['audio_buffer'])
        buffer_duration = buffer_size / 8000.0
        
        # Determine if we should process
        should_process = False
        reason = ""
        
        if vad['speech_active']:
            if vad['consecutive_silence_chunks'] >= vad['min_silence_chunks']:
                # Enough silence after speech
                should_process = True
                reason = "End of speech detected"
            elif buffer_duration >= 7.0:
                # Buffer getting too large
                should_process = True
                reason = "Buffer limit reached"
                
        # Debug logging
        if vad['speech_active'] and vad['consecutive_silence_chunks'] > 0:
            silence_duration = vad['consecutive_silence_chunks'] * 0.1  # approx seconds
            logger.debug(
                f"Call {call_sid} - Buffer: {buffer_duration:.1f}s, "
                f"Silence chunks: {vad['consecutive_silence_chunks']}, "
                f"Silence: {silence_duration:.1f}s"
            )
        
        # Process if conditions are met
        if should_process and buffer_size >= 4000:  # At least 0.5 seconds
            logger.info(f"Processing audio for call {call_sid} - Reason: {reason}")
            
            # Extract audio and reset state
            audio_to_process = bytes(session['audio_buffer'])
            session['audio_buffer'] = bytearray()
            
            # Reset VAD state
            vad['speech_active'] = False
            vad['speech_start_time'] = None
            vad['silence_start_time'] = None
            vad['consecutive_silence_chunks'] = 0
            vad['consecutive_speech_chunks'] = 0
            
            # Mark as speaking to prevent interruptions
            session['is_speaking'] = True
            
            try:
                # Check if audio has enough energy (not just silence)
                # Sample check - convert a portion to check energy
                sample_size = min(1600, len(audio_to_process))  # 0.2 seconds
                if sample_size > 0:
                    samples = [abs(b - 128) for b in audio_to_process[:sample_size]]
                    avg_energy = sum(samples) / len(samples) if samples else 0
                    
                    if avg_energy < 2:
                        logger.warning(f"Audio energy too low ({avg_energy:.2f}), skipping transcription")
                        return
                
                # Send to Whisper for transcription
                logger.debug(f"Sending {len(audio_to_process)} bytes to Whisper (avg energy: {avg_energy:.2f})")
                transcript = await self._transcribe_audio(audio_to_process)
                logger.debug(f"Whisper returned: '{transcript}'")

                if transcript and transcript.strip() and len(transcript.strip()) > 1:
                    logger.info(f"User said: {transcript}")

                    # Add to conversation
                    session['conversation'].append({
                        'role': 'user',
                        'content': transcript,
                        'timestamp': datetime.now().isoformat()
                    })

                    # Get AI response
                    response = await self._get_ai_response(session['conversation'])

                    if response:
                        # Add to conversation
                        session['conversation'].append({
                            'role': 'assistant',
                            'content': response,
                            'timestamp': datetime.now().isoformat()
                        })

                        # Convert to speech and send
                        await self._send_speech_response(websocket, call_sid, response)
                        
                        # Wait for audio to finish playing (estimate based on response length)
                        # Rough estimate: ~150 words per minute = 2.5 words per second
                        words = len(response.split())
                        wait_time = max(2.0, words / 2.5 + 1.0)  # At least 2 seconds
                        await asyncio.sleep(wait_time)
                else:
                    logger.warning(f"No valid transcript from audio of {len(audio_to_process)} bytes")
                        
            finally:
                # Always clear speaking flag
                session['is_speaking'] = False
                
        # Prevent buffer from growing too large
        elif buffer_size > 32000:  # 4 seconds max
            # Keep last 2 seconds
            session['audio_buffer'] = session['audio_buffer'][-16000:]
        """  # End of commented VAD logic
            
        except Exception as e:
            logger.error(f"Error processing audio chunk: {str(e)}", exc_info=True)

    async def _transcribe_audio(self, audio_data: bytearray) -> Optional[str]:
        """Transcribe audio using local Whisper-tiny via AudioProcessor."""
        try:
            # Twilio sends μ-law 8kHz audio by default; AudioProcessor knows how to handle that.
            text = await self.audio_processor.transcribe_audio(
                bytes(audio_data),
                is_ulaw=True,
            )
            return text or None

        except Exception as e:
            logger.error(f"Transcription error: {str(e)}")
            return None

    async def _get_ai_response(self, conversation: List[Dict]) -> Optional[str]:
        """Get response from Ollama LLM"""
        try:
            async with aiohttp.ClientSession() as session:
                # Prepare conversation context
                messages = []

                # System prompt
                messages.append({
                    'role': 'system',
                    'content': f"""You are {self.agent_name}, a customer service agent at {self.company_name}.
Your personality: {self.personality}

CRITICAL INSTRUCTIONS:
- Keep responses VERY SHORT - maximum 1-2 sentences
- Only speak when necessary
- Wait for the customer to finish their complete thought
- Do not over-explain or ramble
- Simple acknowledgments like "Yes", "I understand", "Sure" are perfect
- Only provide detailed information when specifically asked
- Never repeat what you just said
- Be natural and conversational, not robotic

Remember: This is a phone call. Short, natural responses only."""
                })

                # Add recent conversation (limited by context_turns)
                recent_turns = conversation[-self.context_turns * 2:] if len(conversation) > self.context_turns * 2 else conversation
                for turn in recent_turns:
                    messages.append({
                        'role': turn['role'],
                        'content': turn['content']
                    })

                # Get response from Ollama
                async with session.post(
                    f"{self.ollama_host}/api/chat",
                    json={
                        'model': self.ollama_model,
                        'messages': messages,
                        'stream': False,
                        'options': {
                            'temperature': 0.7,
                            'max_tokens': 50,  # Much shorter responses
                            'top_p': 0.9
                        }
                    }
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        # Debug log to see what Ollama returns
                        logger.debug(f"Ollama response: {result}")
                        
                        # Handle different response formats
                        if isinstance(result.get('message'), dict):
                            return result.get('message', {}).get('content', '').strip()
                        elif isinstance(result.get('message'), str):
                            return result.get('message', '').strip()
                        elif 'response' in result:
                            return result.get('response', '').strip()
                        else:
                            logger.error(f"Unexpected Ollama response format: {result}")
                            return "I'm having trouble processing that."
                    else:
                        logger.error(f"Ollama error: {response.status}")
                        return None

        except Exception as e:
            logger.error(f"AI response error: {str(e)}")
            return "I'm having trouble understanding. Could you please repeat that?"

    async def _send_speech_response(self, websocket, call_sid: str, text: str):
        """Convert text to speech (local Kokoro) and send via WebSocket."""
        try:
            # Generate μ-law 8kHz audio using AudioProcessor (Kokoro TTS).
            logger.debug(f"Synthesizing speech for text: {text[:50]}...")
            audio_data = await self.audio_processor.synthesize_speech(
                text,
                voice="af_heart",
            )
            logger.debug(f"Audio data type: {type(audio_data)}, length: {len(audio_data) if audio_data else 0}")

            if audio_data:
                # Send audio to Twilio via WebSocket
                import base64

                # Twilio expects μ-law 8kHz audio
                # Get the stream SID from the session
                session = self.sessions.get(call_sid, {})
                stream_sid = session.get('stream_sid')
                
                if not stream_sid:
                    logger.warning(f"No stream_sid found for call {call_sid}, using call_sid as fallback")
                    stream_sid = call_sid
                
                payload = base64.b64encode(audio_data).decode("utf-8")
                message = {
                    "event": "media",
                    "streamSid": stream_sid,
                    "media": {
                        "payload": payload,
                    },
                }

                await websocket.send_text(json.dumps(message))
                logger.info("Sent speech response for call %s", call_sid)
                
                # Send a mark event to know when audio finishes playing
                mark_message = {
                    "event": "mark",
                    "streamSid": stream_sid,
                    "mark": {
                        "name": f"audio_{call_sid}_{len(audio_data)}"
                    }
                }
                await websocket.send_text(json.dumps(mark_message))
                logger.debug(f"Sent mark event for call {call_sid}")

        except Exception as e:
            logger.error(f"Speech response error: {str(e)}", exc_info=True)

    async def _text_to_speech(self, text: str) -> Optional[bytes]:
        """
        Backwards-compatible wrapper: delegate to AudioProcessor-based TTS.

        Kept for potential re-use; main flow calls _send_speech_response directly.
        """
        try:
            return await self.audio_processor.synthesize_speech(
                text,
                voice="af_heart",
            )
        except Exception as e:
            logger.error(f"TTS error: {str(e)}")
            return None

    async def _send_greeting(self, websocket, call_sid: str):
        """Send initial greeting"""
        greeting = f"Hello, this is {self.agent_name}. How can I help?"
        await self._send_speech_response(websocket, call_sid, greeting)

    def handle_gather_input(self, digits: str, call_sid: str) -> str:
        """Handle DTMF input from user"""
        response = VoiceResponse()

        # Process based on digits
        if digits == "1":
            response.say("Connecting you to sales.", voice='Polly.Amy')
            response.dial("+1234567890")  # Replace with actual number
        elif digits == "2":
            response.say("Connecting you to support.", voice='Polly.Amy')
            response.redirect(f"/ai/agent/{call_sid}")
        elif digits == "3":
            response.say("Please leave a message after the beep.", voice='Polly.Amy')
            response.record(max_length=60, action="/voicemail/save")
        else:
            response.say("Invalid option. Please try again.", voice='Polly.Amy')
            response.redirect("/menu")

        return str(response)

    def create_menu_response(self) -> str:
        """Create an IVR menu"""
        response = VoiceResponse()

        gather = Gather(
            num_digits=1,
            action='/menu/process',
            method='POST',
            timeout=10
        )

        gather.say(
            f"Welcome to {self.company_name}. "
            "Press 1 for sales, 2 for support, or 3 to leave a message.",
            voice='Polly.Amy'
        )

        response.append(gather)

        # If no input, repeat
        response.redirect('/menu')

        return str(response)

    async def get_call_summary(self, call_sid: str) -> Dict[str, Any]:
        """Get summary of a call session"""
        if call_sid not in self.sessions:
            return {'error': 'Session not found'}

        session = self.sessions[call_sid]

        # Generate summary using AI
        summary_prompt = f"""Summarize this customer service call:

{json.dumps(session['conversation'], indent=2)}

Provide:
1. Main issue/request
2. Resolution provided
3. Customer sentiment
4. Follow-up needed (yes/no)
"""

        summary = await self._get_ai_response([{
            'role': 'user',
            'content': summary_prompt
        }])

        return {
            'call_sid': call_sid,
            'duration': (datetime.now() - session['start_time']).total_seconds(),
            'turns': len(session['conversation']),
            'summary': summary,
            'conversation': session['conversation']
        }

    def handle_voicemail(self, recording_url: str, call_sid: str) -> str:
        """Handle voicemail recording"""
        response = VoiceResponse()
        response.say(
            "Thank you for your message. We'll get back to you soon.",
            voice='Polly.Amy'
        )
        response.hangup()

        # TODO: Process voicemail (transcribe, save, notify)
        logger.info(f"Voicemail received for call {call_sid}: {recording_url}")

        return str(response)


class CallManager:
    """Manages call lifecycle and routing"""

    def __init__(self, voice_handler: TwilioVoiceHandler):
        self.voice_handler = voice_handler
        self.active_calls: Dict[str, Dict[str, Any]] = {}

    async def start_call(self, call_sid: str, from_number: str, to_number: str):
        """Initialize a new call"""
        self.active_calls[call_sid] = {
            'from': from_number,
            'to': to_number,
            'start_time': datetime.now(),
            'status': 'initiated'
        }
        logger.info(f"Call started: {call_sid} from {from_number} to {to_number}")

    async def end_call(self, call_sid: str):
        """End a call and cleanup"""
        if call_sid in self.active_calls:
            call_data = self.active_calls[call_sid]
            call_data['end_time'] = datetime.now()
            call_data['status'] = 'completed'

            # Get call summary
            summary = await self.voice_handler.get_call_summary(call_sid)

            # TODO: Save to database
            logger.info(f"Call ended: {call_sid}, duration: {summary.get('duration')} seconds")

            # Cleanup
            del self.active_calls[call_sid]


if __name__ == "__main__":
    # Test initialization
    handler = TwilioVoiceHandler()
    manager = CallManager(handler)

    print(f"Voice Handler initialized for {handler.company_name}")
    print(f"Agent: {handler.agent_name}")
    print(f"Using Whisper model: {handler.whisper_model}")
    print(f"Using Ollama model: {handler.ollama_model}")
    print(f"Using Piper voice: {handler.piper_voice}")