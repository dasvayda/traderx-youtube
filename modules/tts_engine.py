"""
tts_engine.py — Pluggable Japanese TTS narration engine.

Supported providers: OpenAI TTS, Azure Speech, Google Cloud TTS, ElevenLabs.
All providers produce WAV or MP3 files at the specified output path.
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

@dataclass
class TTSResult:
    audio_path: Path
    duration_seconds: float   # estimated; actual may differ slightly
    provider: str
    voice: str


# ---------------------------------------------------------------------------
# Duration estimator (fallback before audio is measured)
# ---------------------------------------------------------------------------

def estimate_duration(text: str, chars_per_second: float = 4.5) -> float:
    """Rough Japanese TTS duration estimate."""
    return max(1.0, len(text) / chars_per_second)


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class BaseTTSEngine(ABC):
    @abstractmethod
    def synthesize(self, text: str, output_path: Path) -> TTSResult:
        ...

    def _get_audio_duration(self, path: Path) -> float:
        """Measure actual audio duration using pydub."""
        try:
            from pydub import AudioSegment
            seg = AudioSegment.from_file(str(path))
            return len(seg) / 1000.0
        except Exception:
            return estimate_duration("x" * 50)   # safe fallback


# ---------------------------------------------------------------------------
# OpenAI TTS
# ---------------------------------------------------------------------------

class OpenAITTSEngine(BaseTTSEngine):
    VOICES = ("alloy", "echo", "fable", "onyx", "nova", "shimmer")

    def __init__(self, voice: str = "shimmer", model: str = "tts-1-hd"):
        from openai import OpenAI
        self._client = OpenAI()
        self._voice = voice
        self._model = model

    def synthesize(self, text: str, output_path: Path) -> TTSResult:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("OpenAI TTS: synthesizing %d chars → %s", len(text), output_path)

        response = self._client.audio.speech.create(
            model=self._model,
            voice=self._voice,
            input=text,
            response_format="mp3",
        )
        response.stream_to_file(str(output_path))

        duration = self._get_audio_duration(output_path)
        return TTSResult(output_path, duration, "openai", self._voice)


# ---------------------------------------------------------------------------
# Azure Speech
# ---------------------------------------------------------------------------

class AzureTTSEngine(BaseTTSEngine):
    def __init__(
        self,
        voice: str = "ja-JP-NanamiNeural",
        region: str = "japaneast",
        api_key: str = "",
    ):
        self._voice = voice
        self._region = region
        self._api_key = api_key or os.environ.get("AZURE_SPEECH_KEY", "")

    def synthesize(self, text: str, output_path: Path) -> TTSResult:
        try:
            import azure.cognitiveservices.speech as speechsdk
        except ImportError as e:
            raise ImportError("pip install azure-cognitiveservices-speech") from e

        output_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Azure TTS: synthesizing %d chars → %s", len(text), output_path)

        speech_config = speechsdk.SpeechConfig(
            subscription=self._api_key, region=self._region
        )
        speech_config.speech_synthesis_voice_name = self._voice
        audio_config = speechsdk.audio.AudioOutputConfig(filename=str(output_path))

        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config, audio_config=audio_config
        )
        result = synthesizer.speak_text_async(text).get()

        if result.reason.name != "SynthesizingAudioCompleted":
            raise RuntimeError(f"Azure TTS failed: {result.reason}")

        duration = self._get_audio_duration(output_path)
        return TTSResult(output_path, duration, "azure", self._voice)


# ---------------------------------------------------------------------------
# Google Cloud TTS
# ---------------------------------------------------------------------------

class GoogleTTSEngine(BaseTTSEngine):
    def __init__(self, voice: str = "ja-JP-Neural2-B", language_code: str = "ja-JP"):
        self._voice = voice
        self._language_code = language_code

    def synthesize(self, text: str, output_path: Path) -> TTSResult:
        try:
            from google.cloud import texttospeech
        except ImportError as e:
            raise ImportError("pip install google-cloud-texttospeech") from e

        output_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Google TTS: synthesizing %d chars → %s", len(text), output_path)

        client = texttospeech.TextToSpeechClient()
        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code=self._language_code,
            name=self._voice,
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        output_path.write_bytes(response.audio_content)

        duration = self._get_audio_duration(output_path)
        return TTSResult(output_path, duration, "google", self._voice)


# ---------------------------------------------------------------------------
# ElevenLabs
# ---------------------------------------------------------------------------

class ElevenLabsTTSEngine(BaseTTSEngine):
    BASE_URL = "https://api.elevenlabs.io/v1"

    def __init__(self, voice_id: str, api_key: str = ""):
        self._voice_id = voice_id
        self._api_key = api_key or os.environ.get("ELEVENLABS_API_KEY", "")

    def synthesize(self, text: str, output_path: Path) -> TTSResult:
        import requests

        output_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("ElevenLabs TTS: synthesizing %d chars → %s", len(text), output_path)

        url = f"{self.BASE_URL}/text-to-speech/{self._voice_id}"
        headers = {"xi-api-key": self._api_key, "Content-Type": "application/json"}
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        output_path.write_bytes(resp.content)

        duration = self._get_audio_duration(output_path)
        return TTSResult(output_path, duration, "elevenlabs", self._voice_id)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_tts_engine(provider: str = "openai", **kwargs) -> BaseTTSEngine:
    registry: dict[str, type[BaseTTSEngine]] = {
        "openai": OpenAITTSEngine,
        "azure": AzureTTSEngine,
        "google": GoogleTTSEngine,
        "elevenlabs": ElevenLabsTTSEngine,
    }
    cls = registry.get(provider.lower())
    if cls is None:
        raise ValueError(f"Unknown TTS provider: {provider!r}. Choose from {list(registry)}")
    return cls(**kwargs)
