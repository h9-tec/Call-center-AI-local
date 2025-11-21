# AI Models Directory

This directory stores downloaded AI models for the call center application. Models are organized by type:

## Directory Structure

- **llm/** - Large Language Models (Ollama models)
- **whisper/** - Speech-to-Text models (OpenAI Whisper)
- **tts/** - Text-to-Speech models (Kokoro)

## Model Management

Models are automatically downloaded on first use or can be pre-downloaded using:

```bash
python scripts/download_models.py
```

## Storage Requirements

- **Whisper Tiny**: ~39MB
- **Llama 3.2:3b**: ~2GB
- **Kokoro**: ~200MB

Total estimated storage: ~3GB

## Caching

Models are cached in these directories to avoid re-downloading. The application will automatically manage the cache based on available disk space.

## Manual Model Management

### Download specific models:

```bash
# Download Whisper
python -c "from transformers import WhisperProcessor, WhisperForConditionalGeneration; WhisperProcessor.from_pretrained('openai/whisper-tiny', cache_dir='./whisper'); WhisperForConditionalGeneration.from_pretrained('openai/whisper-tiny', cache_dir='./whisper')"

# Download Ollama model
ollama pull llama3.2:3b

# Kokoro downloads automatically on first use
```

### Clear model cache:

```bash
# Remove all models
rm -rf llm/* whisper/* tts/*

# Remove specific model type
rm -rf whisper/*
```

## Note

These directories should be excluded from version control and are included in `.gitignore`. Only the README files are tracked.
