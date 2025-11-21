"""
Text-to-Speech service using Kokoro
"""
import logging
from typing import Optional, Dict, Any, List
import numpy as np
import soundfile as sf
from kokoro import KPipeline
import scipy.signal

from app.core.config import settings

logger = logging.getLogger(__name__)


class KokoroTTS:
    """Kokoro Text-to-Speech service"""
    
    def __init__(self):
        self._pipeline: Optional[KPipeline] = None
        self._model_name = settings.tts_model
        self._default_voice = settings.tts_voice
        
    async def initialize(self):
        """Initialize Kokoro TTS model"""
        await self._ensure_model_loaded()
        
    def _ensure_model_loaded(self):
        """Lazy load the Kokoro model"""
        if self._pipeline is None:
            logger.info(f"Loading Kokoro TTS model")
            
            # Initialize Kokoro pipeline
            self._pipeline = KPipeline(
                lang_code="a",  # Auto-detect language
                cache_dir=str(settings.models_path / "tts")
            )
            
            logger.info("Kokoro TTS model loaded successfully")
    
    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: float = 1.0,
        pitch: float = 1.0,
        output_sample_rate: int = 8000,
        output_format: str = "pcm",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Synthesize text to speech
        
        Args:
            text: Text to synthesize
            voice: Voice ID (defaults to configured voice)
            speed: Speech speed multiplier
            pitch: Pitch adjustment
            output_sample_rate: Output sample rate (8kHz for telephony)
            output_format: Output format (pcm, wav, mp3)
            **kwargs: Additional synthesis parameters
            
        Returns:
            Audio data and metadata
        """
        self._ensure_model_loaded()
        
        if not text.strip():
            return {
                "audio": np.array([], dtype=np.int16),
                "sample_rate": output_sample_rate,
                "format": output_format,
                "duration": 0.0
            }
        
        try:
            # Use default voice if not specified
            voice = voice or self._default_voice
            
            # Generate audio
            audio_chunks = []
            generator = self._pipeline(
                text,
                voice=voice,
                speed=speed,
                **kwargs
            )
            
            for _, _, audio in generator:
                if audio is not None and len(audio) > 0:
                    audio_chunks.append(audio)
            
            if not audio_chunks:
                return {
                    "audio": np.array([], dtype=np.int16),
                    "sample_rate": output_sample_rate,
                    "format": output_format,
                    "duration": 0.0
                }
            
            # Concatenate audio chunks
            audio_data = np.concatenate(audio_chunks)
            
            # Kokoro outputs at 24kHz, resample if needed
            if output_sample_rate != 24000:
                # Calculate resampling ratio
                resample_ratio = output_sample_rate / 24000
                num_samples = int(len(audio_data) * resample_ratio)
                
                # Resample audio
                audio_data = scipy.signal.resample(audio_data, num_samples)
            
            # Convert to appropriate format
            if output_format == "pcm":
                # Convert to 16-bit PCM
                audio_data = np.clip(audio_data * 32767, -32768, 32767).astype(np.int16)
            
            # Calculate duration
            duration = len(audio_data) / output_sample_rate
            
            return {
                "audio": audio_data,
                "sample_rate": output_sample_rate,
                "format": output_format,
                "duration": duration,
                "voice": voice,
                "text_length": len(text)
            }
            
        except Exception as e:
            logger.error(f"TTS synthesis error: {e}", exc_info=True)
            raise
    
    async def get_available_voices(self) -> List[Dict[str, str]]:
        """Get list of available voices"""
        # Kokoro voices
        voices = [
            {"id": "af_heart", "name": "Heart (American Female)", "language": "en-US"},
            {"id": "am_michael", "name": "Michael (American Male)", "language": "en-US"},
            {"id": "bf_emma", "name": "Emma (British Female)", "language": "en-GB"},
            {"id": "bm_george", "name": "George (British Male)", "language": "en-GB"},
        ]
        return voices
    
    def unload(self):
        """Unload model from memory"""
        if self._pipeline is not None:
            del self._pipeline
            self._pipeline = None
        
        logger.info("Kokoro TTS model unloaded")
