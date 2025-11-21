"""
Speech-to-Text service using Whisper
"""
import logging
from typing import Optional, Dict, Any
import numpy as np
import torch
from transformers import WhisperProcessor, WhisperForConditionalGeneration

from app.core.config import settings

logger = logging.getLogger(__name__)


class WhisperSTT:
    """Whisper Speech-to-Text service"""
    
    def __init__(self):
        self._processor: Optional[WhisperProcessor] = None
        self._model: Optional[WhisperForConditionalGeneration] = None
        self._device = settings.whisper_device
        self._model_name = settings.whisper_model
        
    async def initialize(self):
        """Initialize Whisper model"""
        await self._ensure_model_loaded()
        
    def _ensure_model_loaded(self):
        """Lazy load the Whisper model"""
        if self._processor is None or self._model is None:
            logger.info(f"Loading Whisper model: {self._model_name}")
            
            self._processor = WhisperProcessor.from_pretrained(
                self._model_name,
                cache_dir=str(settings.models_path / "whisper")
            )
            
            self._model = WhisperForConditionalGeneration.from_pretrained(
                self._model_name,
                cache_dir=str(settings.models_path / "whisper")
            )
            
            # Configure for optimal performance
            if self._device == "cuda" and torch.cuda.is_available():
                self._model = self._model.to("cuda")
                if hasattr(self._model, "half"):
                    self._model = self._model.half()
            
            # Set generation config
            self._model.config.forced_decoder_ids = None
            
            logger.info("Whisper model loaded successfully")
    
    async def transcribe(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        language: str = "en",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Transcribe audio to text
        
        Args:
            audio: Audio waveform as numpy array
            sample_rate: Sample rate (must be 16kHz for Whisper)
            language: Language code
            **kwargs: Additional generation parameters
            
        Returns:
            Transcription result with text and confidence
        """
        self._ensure_model_loaded()
        
        try:
            # Process audio
            inputs = self._processor(
                audio,
                sampling_rate=sample_rate,
                return_tensors="pt"
            )
            
            if self._device == "cuda":
                inputs = inputs.to("cuda")
            
            # Generate transcription
            with torch.no_grad():
                generated_ids = self._model.generate(
                    inputs.input_features,
                    language=language,
                    task="transcribe",
                    temperature=kwargs.get("temperature", 0.0),
                    no_speech_threshold=kwargs.get("no_speech_threshold", 0.6),
                    logprob_threshold=kwargs.get("logprob_threshold", -1.0),
                    compression_ratio_threshold=kwargs.get("compression_ratio_threshold", 2.4),
                    return_scores=True,
                    output_scores=True,
                )
            
            # Decode transcription
            transcription = self._processor.batch_decode(
                generated_ids,
                skip_special_tokens=True
            )[0]
            
            # Calculate confidence (simplified)
            confidence = 0.95 if transcription.strip() else 0.0
            
            return {
                "text": transcription.strip(),
                "confidence": confidence,
                "language": language,
            }
            
        except Exception as e:
            logger.error(f"Transcription error: {e}", exc_info=True)
            raise
    
    def unload(self):
        """Unload model from memory"""
        if self._model is not None:
            del self._model
            self._model = None
        if self._processor is not None:
            del self._processor
            self._processor = None
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        logger.info("Whisper model unloaded")
