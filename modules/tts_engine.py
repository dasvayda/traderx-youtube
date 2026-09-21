"""
tts_engine.py — Pluggable Japanese TTS narration engine.

Supported providers: OpenAI TTS, Azure Speech, Google Cloud TTS, ElevenLabs, XTTS-v2.
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
# XTTS-v2 (Coqui TTS) — local voice cloning
# ---------------------------------------------------------------------------

class XTTSEngine(BaseTTSEngine):
    """
    XTTS-v2 by Coqui — fully local, zero API cost, voice cloning from a short sample.

    Requirements::

        pip install TTS>=0.22.0 torch torchaudio

    The model (~2 GB) is auto-downloaded on first use to ~/.local/share/tts/.

    Voice cloning:
        Pass a WAV/MP3 reference file (3–30 seconds of clean speech) to
        ``speaker_wav``.  The model reproduces the timbre, accent, and pace
        from that sample while synthesising new text.

    Supported languages (XTTS-v2):
        ja, en, zh, ko, de, fr, es, pt, it, pl, tr, ru, nl, cs, ar, hu, ...

    Example::

        engine = XTTSEngine(
            speaker_wav="samples/my_voice.wav",
            language="ja",
        )
        result = engine.synthesize("こんにちは、テスラの株価をお伝えします。",
                                   Path("assets/audio/narration.wav"))
    """

    _MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"

    def __init__(
        self,
        speaker_wav: str | Path,
        language: str = "ja",
        device: str = "",           # "" = auto-detect (cuda if available, else cpu)
        use_deepspeed: bool = False,
        gpu_layers: int = 0,
    ):
        self._speaker_wav = str(Path(speaker_wav).resolve())
        self._language = language
        self._device = device
        self._use_deepspeed = use_deepspeed
        self._gpu_layers = gpu_layers
        self._tts = None

    def _load_model(self) -> None:
        if self._tts is not None:
            return

        try:
            from TTS.api import TTS
        except ImportError as e:
            raise ImportError(
                "pip install TTS>=0.22.0 torch torchaudio"
            ) from e

        import torch

        device = self._device
        if not device:
            device = "cuda" if torch.cuda.is_available() else "cpu"

        logger.info("[XTTS] Loading model on %s (first run downloads ~2 GB) …", device)
        self._tts = TTS(
            model_name=self._MODEL_NAME,
            progress_bar=False,
        ).to(device)
        logger.info("[XTTS] Model ready")

    def synthesize(self, text: str, output_path: Path) -> TTSResult:
        self._load_model()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # XTTS outputs WAV; rename if caller expects .mp3
        wav_path = output_path.with_suffix(".wav")

        logger.info(
            "[XTTS] Synthesising %d chars (lang=%s) → %s",
            len(text), self._language, wav_path,
        )
        self._tts.tts_to_file(
            text=text,
            speaker_wav=self._speaker_wav,
            language=self._language,
            file_path=str(wav_path),
        )

        # If caller wants .mp3, convert with pydub
        if output_path.suffix.lower() == ".mp3":
            try:
                from pydub import AudioSegment
                AudioSegment.from_wav(str(wav_path)).export(
                    str(output_path), format="mp3"
                )
                wav_path.unlink(missing_ok=True)
            except Exception as exc:
                logger.warning("[XTTS] MP3 conversion failed (%s); keeping WAV", exc)
                output_path = wav_path
        else:
            output_path = wav_path

        duration = self._get_audio_duration(output_path)
        logger.info("[XTTS] Done: %.1fs → %s", duration, output_path)
        return TTSResult(output_path, duration, "xtts", self._speaker_wav)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_tts_engine(provider: str = "openai", **kwargs) -> BaseTTSEngine:
    registry: dict[str, type[BaseTTSEngine]] = {
        "openai": OpenAITTSEngine,
        "azure": AzureTTSEngine,
        "google": GoogleTTSEngine,
        "elevenlabs": ElevenLabsTTSEngine,
        "xtts": XTTSEngine,
    }
    cls = registry.get(provider.lower())
    if cls is None:
        raise ValueError(f"Unknown TTS provider: {provider!r}. Choose from {list(registry)}")
    return cls(**kwargs)
