"""
AI Model Manager - Coordinates all AI services
"""
import logging
from typing import Optional, Dict, Any
import asyncio

from app.services.ai.stt import WhisperSTT
from app.services.ai.tts import KokoroTTS
from app.services.ai.llm import OllamaLLM
from app.core.config import settings

logger = logging.getLogger(__name__)


class ModelManager:
    """Manages all AI models and services"""
    
    _instance: Optional["ModelManager"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self.stt: Optional[WhisperSTT] = None
            self.tts: Optional[KokoroTTS] = None
            self.llm: Optional[OllamaLLM] = None
            self._models_loaded = False
            self._loading_lock = asyncio.Lock()
    
    async def load_models(self, models: Optional[List[str]] = None):
        """
        Load AI models
        
        Args:
            models: List of models to load ('stt', 'tts', 'llm').
                   If None, loads all models.
        """
        async with self._loading_lock:
            if self._models_loaded and models is None:
                logger.info("Models already loaded")
                return
            
            models_to_load = models or ["stt", "tts", "llm"]
            
            try:
                # Load STT
                if "stt" in models_to_load and self.stt is None:
                    logger.info("Loading Speech-to-Text model...")
                    self.stt = WhisperSTT()
                    await self.stt.initialize()
                    logger.info("STT model loaded successfully")
                
                # Load TTS
                if "tts" in models_to_load and self.tts is None:
                    logger.info("Loading Text-to-Speech model...")
                    self.tts = KokoroTTS()
                    await self.tts.initialize()
                    logger.info("TTS model loaded successfully")
                
                # Load LLM
                if "llm" in models_to_load and self.llm is None:
                    logger.info("Loading Language Model...")
                    self.llm = OllamaLLM()
                    await self.llm.initialize()
                    logger.info("LLM loaded successfully")
                
                if models is None:
                    self._models_loaded = True
                    
            except Exception as e:
                logger.error(f"Failed to load models: {e}", exc_info=True)
                raise
    
    async def unload_models(self, models: Optional[List[str]] = None):
        """
        Unload AI models to free memory
        
        Args:
            models: List of models to unload. If None, unloads all.
        """
        models_to_unload = models or ["stt", "tts", "llm"]
        
        try:
            if "stt" in models_to_unload and self.stt is not None:
                logger.info("Unloading STT model...")
                self.stt.unload()
                self.stt = None
            
            if "tts" in models_to_unload and self.tts is not None:
                logger.info("Unloading TTS model...")
                self.tts.unload()
                self.tts = None
            
            if "llm" in models_to_unload and self.llm is not None:
                logger.info("Unloading LLM...")
                await self.llm.close()
                self.llm = None
            
            if models is None:
                self._models_loaded = False
                
        except Exception as e:
            logger.error(f"Failed to unload models: {e}", exc_info=True)
    
    async def transcribe(self, audio: Any, **kwargs) -> Dict[str, Any]:
        """Transcribe audio to text"""
        if self.stt is None:
            await self.load_models(["stt"])
        return await self.stt.transcribe(audio, **kwargs)
    
    async def synthesize(self, text: str, **kwargs) -> Dict[str, Any]:
        """Synthesize text to speech"""
        if self.tts is None:
            await self.load_models(["tts"])
        return await self.tts.synthesize(text, **kwargs)
    
    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate text using LLM"""
        if self.llm is None:
            await self.load_models(["llm"])
        return await self.llm.generate(prompt, **kwargs)
    
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Chat completion using LLM"""
        if self.llm is None:
            await self.load_models(["llm"])
        return await self.llm.chat(messages, **kwargs)
    
    def get_status(self) -> Dict[str, bool]:
        """Get status of loaded models"""
        return {
            "stt": self.stt is not None,
            "tts": self.tts is not None,
            "llm": self.llm is not None,
            "all_loaded": self._models_loaded
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all models"""
        health = {
            "status": "healthy",
            "models": {}
        }
        
        # Check STT
        if self.stt is not None:
            try:
                # Simple test with silence
                import numpy as np
                silence = np.zeros(16000, dtype=np.float32)
                result = await self.stt.transcribe(silence)
                health["models"]["stt"] = {
                    "status": "healthy",
                    "model": settings.whisper_model
                }
            except Exception as e:
                health["models"]["stt"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                health["status"] = "degraded"
        
        # Check TTS
        if self.tts is not None:
            try:
                result = await self.tts.synthesize("Test")
                health["models"]["tts"] = {
                    "status": "healthy",
                    "model": settings.tts_model
                }
            except Exception as e:
                health["models"]["tts"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                health["status"] = "degraded"
        
        # Check LLM
        if self.llm is not None:
            try:
                result = await self.llm.generate("Hello", max_tokens=5)
                health["models"]["llm"] = {
                    "status": "healthy",
                    "model": settings.ollama_model
                }
            except Exception as e:
                health["models"]["llm"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                health["status"] = "degraded"
        
        return health


# Singleton instance
model_manager = ModelManager()
