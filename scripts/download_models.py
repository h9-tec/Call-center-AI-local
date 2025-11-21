#!/usr/bin/env python3
"""
Download all required AI models for the call center
"""
import os
import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.services.ai.model_manager import model_manager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def download_models():
    """Download all required models"""
    try:
        logger.info("Starting model download...")
        
        # Load all models (this will trigger downloads)
        await model_manager.load_models()
        
        # Verify models
        status = model_manager.get_status()
        logger.info(f"Model status: {status}")
        
        # Perform health check
        health = await model_manager.health_check()
        logger.info(f"Model health: {health}")
        
        if health["status"] == "healthy":
            logger.info("✅ All models downloaded and verified successfully!")
        else:
            logger.warning("⚠️ Some models may have issues. Check the health report above.")
        
        # Get model sizes
        model_dir = settings.models_path
        total_size = 0
        
        for subdir in ["whisper", "llm", "tts"]:
            dir_path = model_dir / subdir
            if dir_path.exists():
                size = sum(f.stat().st_size for f in dir_path.rglob("*") if f.is_file())
                size_mb = size / (1024 * 1024)
                logger.info(f"{subdir}: {size_mb:.1f} MB")
                total_size += size
        
        total_size_gb = total_size / (1024 * 1024 * 1024)
        logger.info(f"Total model size: {total_size_gb:.2f} GB")
        
    except Exception as e:
        logger.error(f"Failed to download models: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Clean up
        await model_manager.unload_models()


if __name__ == "__main__":
    import asyncio
    
    print("=" * 60)
    print("Call Center AI - Model Downloader")
    print("=" * 60)
    print()
    print("This will download the following models:")
    print(f"- Whisper STT: {settings.whisper_model}")
    print(f"- Ollama LLM: {settings.ollama_model}")
    print(f"- Kokoro TTS: {settings.tts_model}")
    print()
    print("Estimated total size: ~3 GB")
    print()
    
    response = input("Continue? [Y/n]: ").strip().lower()
    if response and response not in ["y", "yes"]:
        print("Download cancelled.")
        sys.exit(0)
    
    asyncio.run(download_models())
