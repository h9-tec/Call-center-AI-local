"""
Language Model service using Ollama
"""
import logging
from typing import Optional, Dict, Any, List, AsyncGenerator
import aiohttp
import json
from datetime import datetime

from app.core.config import settings

logger = logging.getLogger(__name__)


class OllamaLLM:
    """Ollama Language Model service"""
    
    def __init__(self):
        self.host = settings.ollama_host
        self.model = settings.ollama_model
        self._session: Optional[aiohttp.ClientSession] = None
        
    async def initialize(self):
        """Initialize Ollama connection"""
        if self._session is None:
            self._session = aiohttp.ClientSession()
        
        # Check if model is available
        await self._ensure_model_available()
    
    async def _ensure_model_available(self):
        """Ensure the model is pulled and available"""
        try:
            # Check if model exists
            async with self._session.get(f"{self.host}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    models = [m["name"] for m in data.get("models", [])]
                    
                    if self.model not in models:
                        logger.info(f"Pulling Ollama model: {self.model}")
                        await self._pull_model()
        except Exception as e:
            logger.error(f"Failed to check Ollama models: {e}")
    
    async def _pull_model(self):
        """Pull model from Ollama registry"""
        try:
            async with self._session.post(
                f"{self.host}/api/pull",
                json={"name": self.model}
            ) as response:
                async for line in response.content:
                    if line:
                        data = json.loads(line)
                        if "status" in data:
                            logger.info(f"Pulling model: {data['status']}")
        except Exception as e:
            logger.error(f"Failed to pull model: {e}")
            raise
    
    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 150,
        top_p: float = 0.9,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any] | AsyncGenerator[Dict[str, Any], None]:
        """
        Generate text using Ollama
        
        Args:
            prompt: User prompt
            system: System prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            top_p: Top-p sampling
            stream: Whether to stream responses
            **kwargs: Additional generation parameters
            
        Returns:
            Generated text or stream of tokens
        """
        if self._session is None:
            await self.initialize()
        
        # Build request
        request_data = {
            "model": self.model,
            "prompt": prompt,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "top_p": top_p,
                "top_k": kwargs.get("top_k", 40),
                "repeat_penalty": kwargs.get("repeat_penalty", 1.1),
            },
            "stream": stream
        }
        
        if system:
            request_data["system"] = system
        
        try:
            if stream:
                return self._stream_generate(request_data)
            else:
                return await self._generate(request_data)
        except Exception as e:
            logger.error(f"LLM generation error: {e}", exc_info=True)
            raise
    
    async def _generate(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Non-streaming generation"""
        async with self._session.post(
            f"{self.host}/api/generate",
            json=request_data
        ) as response:
            if response.status != 200:
                raise Exception(f"Ollama error: {response.status}")
            
            data = await response.json()
            
            return {
                "text": data.get("response", ""),
                "model": data.get("model", self.model),
                "created_at": data.get("created_at", datetime.utcnow().isoformat()),
                "total_duration": data.get("total_duration", 0),
                "load_duration": data.get("load_duration", 0),
                "prompt_eval_duration": data.get("prompt_eval_duration", 0),
                "eval_duration": data.get("eval_duration", 0),
                "eval_count": data.get("eval_count", 0),
            }
    
    async def _stream_generate(
        self, 
        request_data: Dict[str, Any]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Streaming generation"""
        async with self._session.post(
            f"{self.host}/api/generate",
            json=request_data
        ) as response:
            if response.status != 200:
                raise Exception(f"Ollama error: {response.status}")
            
            async for line in response.content:
                if line:
                    data = json.loads(line)
                    
                    yield {
                        "token": data.get("response", ""),
                        "done": data.get("done", False),
                        "model": data.get("model", self.model),
                        "created_at": data.get("created_at", datetime.utcnow().isoformat()),
                    }
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 150,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any] | AsyncGenerator[Dict[str, Any], None]:
        """
        Chat completion using Ollama
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stream: Whether to stream responses
            **kwargs: Additional generation parameters
            
        Returns:
            Generated response or stream of tokens
        """
        if self._session is None:
            await self.initialize()
        
        request_data = {
            "model": self.model,
            "messages": messages,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "top_p": kwargs.get("top_p", 0.9),
                "top_k": kwargs.get("top_k", 40),
            },
            "stream": stream
        }
        
        try:
            if stream:
                return self._stream_chat(request_data)
            else:
                return await self._chat(request_data)
        except Exception as e:
            logger.error(f"LLM chat error: {e}", exc_info=True)
            raise
    
    async def _chat(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Non-streaming chat"""
        async with self._session.post(
            f"{self.host}/api/chat",
            json=request_data
        ) as response:
            if response.status != 200:
                raise Exception(f"Ollama error: {response.status}")
            
            data = await response.json()
            
            return {
                "message": data.get("message", {}),
                "model": data.get("model", self.model),
                "created_at": data.get("created_at", datetime.utcnow().isoformat()),
                "done": data.get("done", True),
                "total_duration": data.get("total_duration", 0),
            }
    
    async def _stream_chat(
        self,
        request_data: Dict[str, Any]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Streaming chat"""
        async with self._session.post(
            f"{self.host}/api/chat",
            json=request_data
        ) as response:
            if response.status != 200:
                raise Exception(f"Ollama error: {response.status}")
            
            async for line in response.content:
                if line:
                    data = json.loads(line)
                    
                    yield {
                        "message": data.get("message", {}),
                        "done": data.get("done", False),
                        "model": data.get("model", self.model),
                    }
    
    async def close(self):
        """Close the session"""
        if self._session:
            await self._session.close()
            self._session = None
