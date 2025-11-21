#!/usr/bin/env python3
"""
Audio Processing Service for Call Center AI

This module provides:
- STT using HuggingFace Transformers Whisper (openai/whisper-tiny)
- TTS using Kokoro (local TTS model)

Audio input/output for the telephony side remains 8kHz μ-law (Asterisk compatible).
"""

import asyncio
import logging
import os
import struct
import io
import wave
from pathlib import Path
from typing import Optional

import numpy as np
from scipy import signal as sps
import torch
from transformers import WhisperForConditionalGeneration, WhisperProcessor
from kokoro import KPipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AudioProcessor:
    """Handle audio processing: STT (Whisper-tiny) and TTS (Kokoro)."""

    def __init__(self):
        # Audio parameters (telephony side)
        self.sample_rate = 8000  # Asterisk default
        self.channels = 1  # Mono
        self.sample_width = 2  # 16-bit

        # Whisper (STT) components
        self._whisper_processor: Optional[WhisperProcessor] = None
        self._whisper_model: Optional[WhisperForConditionalGeneration] = None

        # Kokoro (TTS) pipeline
        self._kokoro_pipeline: Optional[KPipeline] = None

    # ------------------------------------------------------------------
    # Initialisation helpers
    # ------------------------------------------------------------------

    def _ensure_whisper(self) -> None:
        """Lazy-load Whisper processor and model."""
        if self._whisper_processor is not None and self._whisper_model is not None:
            return

        logger.info("Loading Whisper tiny model for STT...")
        self._whisper_processor = WhisperProcessor.from_pretrained("openai/whisper-tiny")
        self._whisper_model = WhisperForConditionalGeneration.from_pretrained("openai/whisper-tiny")
        # Allow free-form decoding (no forced lang/task tokens)
        self._whisper_model.config.forced_decoder_ids = None
        self._whisper_model.eval()

    def _ensure_kokoro(self) -> None:
        """Lazy-load Kokoro TTS pipeline."""
        if self._kokoro_pipeline is not None:
            return

        logger.info("Loading Kokoro TTS pipeline...")
        # lang_code='a' = automatic English variants per Kokoro docs
        self._kokoro_pipeline = KPipeline(lang_code="a")

    def convert_ulaw_to_pcm(self, ulaw_data: bytes) -> bytes:
        """Convert μ-law audio to 16‑bit PCM for processing."""
        # μ-law to PCM conversion table
        ULAW_TO_PCM = [
            -32124, -31100, -30076, -29052, -28028, -27004, -25980, -24956,
            -23932, -22908, -21884, -20860, -19836, -18812, -17788, -16764,
            -15996, -15484, -14972, -14460, -13948, -13436, -12924, -12412,
            -11900, -11388, -10876, -10364, -9852, -9340, -8828, -8316,
            -7932, -7676, -7420, -7164, -6908, -6652, -6396, -6140,
            -5884, -5628, -5372, -5116, -4860, -4604, -4348, -4092,
            -3900, -3772, -3644, -3516, -3388, -3260, -3132, -3004,
            -2876, -2748, -2620, -2492, -2364, -2236, -2108, -1980,
            -1884, -1820, -1756, -1692, -1628, -1564, -1500, -1436,
            -1372, -1308, -1244, -1180, -1116, -1052, -988, -924,
            -876, -844, -812, -780, -748, -716, -684, -652,
            -620, -588, -556, -524, -492, -460, -428, -396,
            -372, -356, -340, -324, -308, -292, -276, -260,
            -244, -228, -212, -196, -180, -164, -148, -132,
            -120, -112, -104, -96, -88, -80, -72, -64,
            -56, -48, -40, -32, -24, -16, -8, 0,
            32124, 31100, 30076, 29052, 28028, 27004, 25980, 24956,
            23932, 22908, 21884, 20860, 19836, 18812, 17788, 16764,
            15996, 15484, 14972, 14460, 13948, 13436, 12924, 12412,
            11900, 11388, 10876, 10364, 9852, 9340, 8828, 8316,
            7932, 7676, 7420, 7164, 6908, 6652, 6396, 6140,
            5884, 5628, 5372, 5116, 4860, 4604, 4348, 4092,
            3900, 3772, 3644, 3516, 3388, 3260, 3132, 3004,
            2876, 2748, 2620, 2492, 2364, 2236, 2108, 1980,
            1884, 1820, 1756, 1692, 1628, 1564, 1500, 1436,
            1372, 1308, 1244, 1180, 1116, 1052, 988, 924,
            876, 844, 812, 780, 748, 716, 684, 652,
            620, 588, 556, 524, 492, 460, 428, 396,
            372, 356, 340, 324, 308, 292, 276, 260,
            244, 228, 212, 196, 180, 164, 148, 132,
            120, 112, 104, 96, 88, 80, 72, 64,
            56, 48, 40, 32, 24, 16, 8, 0
        ]

        pcm_data = bytearray()
        for byte in ulaw_data:
            pcm_value = ULAW_TO_PCM[byte]
            # Convert to 16-bit little-endian
            pcm_data.extend(struct.pack("<h", pcm_value))

        return bytes(pcm_data)

    def convert_pcm_to_ulaw(self, pcm_data: bytes) -> bytes:
        """Convert 16‑bit PCM audio to μ‑law for Asterisk."""

        def pcm_to_ulaw(pcm_val: int) -> int:
            # Simplified μ-law encoding
            if pcm_val < 0:
                pcm_val = -pcm_val
                sign = 0x80
            else:
                sign = 0

            if pcm_val > 32635:
                pcm_val = 32635

            pcm_val += 0x84
            if pcm_val > 0x7FFF:
                pcm_val = 0x7FFF

            # Find segment
            segment = 0
            for i in range(8):
                if pcm_val <= (0xFF << (i + 3)):
                    segment = i
                    break

            # Compute ulaw value
            if segment >= 8:
                ulaw_val = 0x7F ^ sign
            else:
                shift = segment + 3
                ulaw_val = ((segment << 4) | ((pcm_val >> shift) & 0x0F)) ^ sign ^ 0xFF

            return ulaw_val

        ulaw_data = bytearray()
        # Process 16-bit PCM samples
        for i in range(0, len(pcm_data), 2):
            if i + 1 < len(pcm_data):
                pcm_val = struct.unpack("<h", pcm_data[i : i + 2])[0]
                ulaw_data.append(pcm_to_ulaw(pcm_val))

        return bytes(ulaw_data)

    # ------------------------------------------------------------------
    # STT: Whisper tiny (local)
    # ------------------------------------------------------------------

    async def transcribe_audio(self, audio_data: bytes, is_ulaw: bool = True) -> str:
        """
        Convert audio to text using local Whisper-tiny.

        - Expects 8kHz μ-law by default (is_ulaw=True).
        - Internally resamples to 16kHz as expected by Whisper.
        - Returns a plain text transcription.
        """
        try:
            self._ensure_whisper()

            # Convert μ-law to PCM if needed (8kHz telephony signal)
            if is_ulaw:
                pcm_data = self.convert_ulaw_to_pcm(audio_data)
            else:
                pcm_data = audio_data

            # Convert 16‑bit PCM to float32 waveform in [-1, 1]
            waveform_8k = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Apply simple noise reduction and normalization
            # Remove DC offset
            waveform_8k = waveform_8k - np.mean(waveform_8k)
            
            # Check if audio has enough energy (not just noise)
            energy = np.mean(waveform_8k ** 2)
            if energy < 0.0001:  # Very quiet, likely just noise
                logger.debug("Audio energy too low, skipping transcription")
                return ""
            
            # Normalize volume if too quiet
            max_val = np.max(np.abs(waveform_8k))
            if max_val > 0.01:  # Avoid amplifying silence
                waveform_8k = waveform_8k / max_val * 0.95

            # Resample 8kHz -> 16kHz for Whisper
            orig_sr = self.sample_rate  # 8000
            target_sr = 16000
            num_samples = int(len(waveform_8k) * target_sr / orig_sr)
            if num_samples <= 0:
                return ""
            waveform_16k = sps.resample(waveform_8k, num_samples)

            inputs = self._whisper_processor(
                waveform_16k,
                sampling_rate=target_sr,
                return_tensors="pt",
            )

            with torch.no_grad():
                # Generate with better parameters for telephony audio
                predicted_ids = self._whisper_model.generate(
                    inputs.input_features,
                    language="en",  # Force English
                    task="transcribe",  # Transcribe, not translate
                    temperature=0.0,  # Deterministic
                    no_speech_threshold=0.6,  # Filter out noise
                    logprob_threshold=-1.0,
                    compression_ratio_threshold=2.4,
                )

            transcription = self._whisper_processor.batch_decode(
                predicted_ids, skip_special_tokens=True
            )
            if not transcription:
                return ""

            text = transcription[0].strip()
            logger.debug("Whisper transcription: %s", text)
            return text

        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return ""

    # ------------------------------------------------------------------
    # TTS: Kokoro (local)
    # ------------------------------------------------------------------

    async def synthesize_speech(self, text: str, voice: str = "af_heart") -> bytes:
        """
        Convert text to speech using Kokoro.

        - Generates 24kHz audio via Kokoro, then resamples to 8kHz.
        - Returns μ‑law audio bytes suitable for Asterisk.
        """
        try:
            if not text:
                return self.generate_silence(100)

            self._ensure_kokoro()

            # Kokoro pipeline yields (global_style, phoneme_style, audio_chunk)
            generator = self._kokoro_pipeline(text, voice=voice)
            chunks = []
            for _, _, audio in generator:
                chunks.append(audio)

            if not chunks:
                logger.warning("Kokoro returned no audio; falling back to beep.")
                return self.generate_beep()

            audio_24k = np.concatenate(chunks)

            # Resample 24kHz -> 8kHz for telephony
            orig_sr = 24000
            target_sr = self.sample_rate
            num_samples = int(len(audio_24k) * target_sr / orig_sr)
            audio_8k = sps.resample(audio_24k, num_samples)

            # Convert float32 [-1,1] to 16‑bit PCM
            audio_8k = np.clip(audio_8k, -1.0, 1.0)
            pcm_data = (audio_8k * 32767).astype(np.int16).tobytes()

            # Convert to μ‑law for Asterisk
            ulaw_data = self.convert_pcm_to_ulaw(pcm_data)
            return ulaw_data

        except Exception as e:
            logger.error(f"TTS error: {e}")
            # Return a simple beep as fallback
            return self.generate_beep()

    def generate_beep(self, duration_ms: int = 200, frequency: int = 440) -> bytes:
        """Generate a simple beep tone in μ-law format."""
        samples = int(self.sample_rate * duration_ms / 1000)
        pcm_data = bytearray()

        for i in range(samples):
            # Generate sine wave
            t = i / self.sample_rate
            value = int(32767 * 0.3 * np.sin(2 * np.pi * frequency * t))
            pcm_data.extend(struct.pack("<h", value))

        return self.convert_pcm_to_ulaw(bytes(pcm_data))

    def generate_silence(self, duration_ms: int = 20) -> bytes:
        """Generate silence in μ-law format."""
        samples = int(self.sample_rate * duration_ms / 1000)
        # μ-law silence is 0xFF
        return bytes([0xFF] * samples)


# Test function
async def test_audio_processing():
    """Test the audio processing pipeline"""
    processor = AudioProcessor()

    # Test beep generation
    beep = processor.generate_beep()
    print(f"Generated beep: {len(beep)} bytes")

    # Test silence generation
    silence = processor.generate_silence(100)
    print(f"Generated silence: {len(silence)} bytes")

    # Test text
    test_text = "Hello, this is a test of the audio system."

    # Generate speech (if Piper is available)
    try:
        audio = await processor.synthesize_speech(test_text)
        print(f"Generated speech: {len(audio)} bytes")
    except:
        print("Piper TTS not available")

    print("Audio processing test complete!")


if __name__ == "__main__":
    asyncio.run(test_audio_processing())