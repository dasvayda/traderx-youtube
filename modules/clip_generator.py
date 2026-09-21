"""
clip_generator.py — AI-generated video clips for footage scenes.

Supports three backends with automatic fallback:
  1. HiggsFieldGenerator   — Higgsfield AI REST API (cloud, paid)
  2. WanGenerator          — Wan 2.2 (1.3B) local diffusers (VRAM 4–6 GB)
  3. LTXVideoGenerator     — LTX-Video 2.3 local diffusers (VRAM 8 GB+)

Factory usage::

    gen = create_clip_generator("higgsfield", api_key="...")
    path = gen.generate("Bull run on the stock exchange floor", duration=5.0,
                        output_path=Path("cache/clips/scene1.mp4"))

Fallback chain::

    gen = create_clip_generator(
        "auto",
        higgsfield_api_key="...",   # tried first
        wan_model_id="Wan-AI/Wan2.2-T2V-1.3B-Diffusers",
        ltx_model_id="Lightricks/LTX-Video",
    )
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class BaseClipGenerator(ABC):
    """Generate a short video clip from a text prompt."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        duration: float,
        output_path: Path,
    ) -> Path:
        """
        Args:
            prompt: English description of the desired footage.
            duration: Target clip length in seconds (best-effort; providers may round).
            output_path: Where to save the resulting .mp4 file.
        Returns:
            Path to the saved video file.
        """


# ---------------------------------------------------------------------------
# 1. Higgsfield
# ---------------------------------------------------------------------------

class HiggsFieldGenerator(BaseClipGenerator):
    """
    Higgsfield AI footage generator via REST API.

    Requires a Starter plan ($19/month) or higher — free tier watermarks clips
    and has strict credit limits.

    API flow:
      POST /generations        → job_id
      GET  /generations/{id}   → poll until status == "completed"
      download video_url       → save to output_path
    """

    _API_BASE = "https://api.higgsfield.ai/v1"
    _POLL_INTERVAL = 5      # seconds between status polls
    _TIMEOUT = 300          # max wait for a generation job

    def __init__(
        self,
        api_key: str,
        model: str = "higgsfield-v1",
        aspect_ratio: str = "9:16",
    ):
        self._api_key = api_key
        self._model = model
        self._aspect_ratio = aspect_ratio

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def generate(self, prompt: str, duration: float, output_path: Path) -> Path:
        import requests

        output_path.parent.mkdir(parents=True, exist_ok=True)
        duration_int = max(1, min(int(round(duration)), 10))   # 1–10 s

        logger.info("[Higgsfield] Submitting generation: %r (%.0fs)", prompt[:60], duration)
        resp = requests.post(
            f"{self._API_BASE}/generations",
            headers=self._headers(),
            json={
                "prompt": prompt,
                "model": self._model,
                "duration": duration_int,
                "aspect_ratio": self._aspect_ratio,
            },
            timeout=30,
        )
        resp.raise_for_status()
        job_id = resp.json()["id"]
        logger.info("[Higgsfield] Job submitted: %s", job_id)

        # Poll until complete
        deadline = time.time() + self._TIMEOUT
        while time.time() < deadline:
            time.sleep(self._POLL_INTERVAL)
            status_resp = requests.get(
                f"{self._API_BASE}/generations/{job_id}",
                headers=self._headers(),
                timeout=15,
            )
            status_resp.raise_for_status()
            data = status_resp.json()
            status = data.get("status", "")
            logger.debug("[Higgsfield] Job %s status: %s", job_id, status)

            if status == "completed":
                video_url = data["video_url"]
                dl = requests.get(video_url, timeout=60)
                dl.raise_for_status()
                output_path.write_bytes(dl.content)
                logger.info("[Higgsfield] Clip saved: %s", output_path)
                return output_path

            if status in ("failed", "cancelled"):
                raise RuntimeError(
                    f"Higgsfield job {job_id} ended with status={status!r}: "
                    f"{data.get('error', 'no detail')}"
                )

        raise TimeoutError(
            f"Higgsfield job {job_id} did not complete within {self._TIMEOUT}s"
        )


# ---------------------------------------------------------------------------
# 2. Wan 2.2 (1.3B) — local diffusers
# ---------------------------------------------------------------------------

class WanGenerator(BaseClipGenerator):
    """
    Wan 2.2 (1.3B) text-to-video via Hugging Face diffusers.

    Requirements:
      pip install diffusers>=0.30 transformers accelerate torch
      VRAM: 4–6 GB (fp16 + attention slicing)
      Default model: Wan-AI/Wan2.2-T2V-1.3B-Diffusers

    Output: 480×832 (9:16), 16 fps, ~5 seconds per clip.
    """

    _DEFAULT_MODEL = "Wan-AI/Wan2.2-T2V-1.3B-Diffusers"
    _FPS = 16
    _HEIGHT = 832
    _WIDTH = 480

    def __init__(
        self,
        model_id: str = _DEFAULT_MODEL,
        device: str = "cuda",
        num_inference_steps: int = 25,
    ):
        self._model_id = model_id
        self._device = device
        self._num_steps = num_inference_steps
        self._pipe = None

    def _load_pipeline(self):
        if self._pipe is not None:
            return
        import torch
        from diffusers import AutoPipelineForText2Video

        logger.info("[Wan] Loading pipeline: %s", self._model_id)
        pipe = AutoPipelineForText2Video.from_pretrained(
            self._model_id,
            torch_dtype=torch.float16,
        )
        pipe = pipe.to(self._device)
        pipe.enable_attention_slicing()
        self._pipe = pipe
        logger.info("[Wan] Pipeline loaded on %s", self._device)

    def generate(self, prompt: str, duration: float, output_path: Path) -> Path:
        self._load_pipeline()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        num_frames = max(8, int(duration * self._FPS))
        logger.info("[Wan] Generating %d frames for: %r", num_frames, prompt[:60])

        result = self._pipe(
            prompt=prompt,
            height=self._HEIGHT,
            width=self._WIDTH,
            num_frames=num_frames,
            num_inference_steps=self._num_steps,
        )
        frames = result.frames[0]   # list of PIL images

        self._save_frames(frames, output_path)
        logger.info("[Wan] Clip saved: %s", output_path)
        return output_path

    def _save_frames(self, frames, output_path: Path) -> None:
        try:
            from diffusers.utils import export_to_video
            export_to_video(frames, str(output_path), fps=self._FPS)
        except Exception:
            # Fallback: imageio
            import imageio
            import numpy as np
            writer = imageio.get_writer(str(output_path), fps=self._FPS, codec="libx264")
            for frame in frames:
                writer.append_data(np.array(frame))
            writer.close()


# ---------------------------------------------------------------------------
# 3. LTX-Video 2.3 — local diffusers
# ---------------------------------------------------------------------------

class LTXVideoGenerator(BaseClipGenerator):
    """
    LTX-Video 2.3 by Lightricks via Hugging Face diffusers.

    Requirements:
      pip install diffusers>=0.30 transformers accelerate torch
      VRAM: 8 GB+ (fp16)
      Default model: Lightricks/LTX-Video

    Output: 704×1216 (close to 9:16), 24 fps, ~5 seconds per clip.
    RTX 4090: ~1 min per 5-second 720p clip.
    """

    _DEFAULT_MODEL = "Lightricks/LTX-Video"
    _FPS = 24
    _HEIGHT = 1216
    _WIDTH = 704

    def __init__(
        self,
        model_id: str = _DEFAULT_MODEL,
        device: str = "cuda",
        num_inference_steps: int = 40,
    ):
        self._model_id = model_id
        self._device = device
        self._num_steps = num_inference_steps
        self._pipe = None

    def _load_pipeline(self):
        if self._pipe is not None:
            return
        import torch
        from diffusers import LTXPipeline

        logger.info("[LTXVideo] Loading pipeline: %s", self._model_id)
        pipe = LTXPipeline.from_pretrained(
            self._model_id,
            torch_dtype=torch.bfloat16,
        )
        pipe = pipe.to(self._device)
        pipe.enable_attention_slicing()
        self._pipe = pipe
        logger.info("[LTXVideo] Pipeline loaded on %s", self._device)

    def generate(self, prompt: str, duration: float, output_path: Path) -> Path:
        self._load_pipeline()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        num_frames = max(8, int(duration * self._FPS))
        # LTX-Video requires frames = 8k+1
        num_frames = ((num_frames - 1) // 8) * 8 + 1

        logger.info("[LTXVideo] Generating %d frames for: %r", num_frames, prompt[:60])

        result = self._pipe(
            prompt=prompt,
            negative_prompt="worst quality, low quality, deformed, blurry",
            height=self._HEIGHT,
            width=self._WIDTH,
            num_frames=num_frames,
            num_inference_steps=self._num_steps,
        )
        frames = result.frames[0]

        self._save_frames(frames, output_path)
        logger.info("[LTXVideo] Clip saved: %s", output_path)
        return output_path

    def _save_frames(self, frames, output_path: Path) -> None:
        try:
            from diffusers.utils import export_to_video
            export_to_video(frames, str(output_path), fps=self._FPS)
        except Exception:
            import imageio
            import numpy as np
            writer = imageio.get_writer(str(output_path), fps=self._FPS, codec="libx264")
            for frame in frames:
                writer.append_data(np.array(frame))
            writer.close()


# ---------------------------------------------------------------------------
# 4. Auto fallback chain
# ---------------------------------------------------------------------------

class AutoClipGenerator(BaseClipGenerator):
    """
    Tries each provider in priority order and falls back on failure.

    Priority: Higgsfield → Wan 2.2 → LTX-Video
    A provider is skipped if it is not configured (e.g. no API key or CUDA unavailable).
    """

    def __init__(self, generators: list[BaseClipGenerator]):
        if not generators:
            raise ValueError("At least one generator must be provided")
        self._generators = generators

    def generate(self, prompt: str, duration: float, output_path: Path) -> Path:
        last_exc: Optional[Exception] = None
        for gen in self._generators:
            try:
                return gen.generate(prompt, duration, output_path)
            except Exception as exc:
                logger.warning(
                    "[AutoClipGenerator] %s failed: %s — trying next",
                    gen.__class__.__name__, exc,
                )
                last_exc = exc
        raise RuntimeError(
            f"All clip generators failed. Last error: {last_exc}"
        ) from last_exc


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_clip_generator(
    provider: str = "auto",
    *,
    higgsfield_api_key: str = "",
    higgsfield_model: str = "higgsfield-v1",
    wan_model_id: str = WanGenerator._DEFAULT_MODEL,
    wan_device: str = "cuda",
    wan_steps: int = 25,
    ltx_model_id: str = LTXVideoGenerator._DEFAULT_MODEL,
    ltx_device: str = "cuda",
    ltx_steps: int = 40,
) -> BaseClipGenerator:
    """
    Create a clip generator for the given provider.

    provider options:
      "higgsfield" — Higgsfield API only (requires api_key)
      "wan"        — Wan 2.2 local only
      "ltx"        — LTX-Video 2.3 local only
      "auto"       — Higgsfield → Wan → LTX fallback chain
                     (providers with missing config are skipped)
    """
    import os

    if provider == "higgsfield":
        key = higgsfield_api_key or os.environ.get("HIGGSFIELD_API_KEY", "")
        if not key:
            raise ValueError(
                "Higgsfield API key required. Set HIGGSFIELD_API_KEY in .env "
                "or pass higgsfield_api_key=."
            )
        return HiggsFieldGenerator(api_key=key, model=higgsfield_model)

    if provider == "wan":
        return WanGenerator(model_id=wan_model_id, device=wan_device,
                            num_inference_steps=wan_steps)

    if provider == "ltx":
        return LTXVideoGenerator(model_id=ltx_model_id, device=ltx_device,
                                 num_inference_steps=ltx_steps)

    if provider == "auto":
        chain: list[BaseClipGenerator] = []

        key = higgsfield_api_key or os.environ.get("HIGGSFIELD_API_KEY", "")
        if key:
            chain.append(HiggsFieldGenerator(api_key=key, model=higgsfield_model))

        try:
            import torch
            if torch.cuda.is_available():
                chain.append(WanGenerator(model_id=wan_model_id, device=wan_device,
                                          num_inference_steps=wan_steps))
                chain.append(LTXVideoGenerator(model_id=ltx_model_id, device=ltx_device,
                                               num_inference_steps=ltx_steps))
            else:
                logger.warning(
                    "[create_clip_generator] CUDA not available; "
                    "local generators (Wan / LTX-Video) will not be added to chain"
                )
        except ImportError:
            logger.warning(
                "[create_clip_generator] torch not installed; "
                "local generators skipped"
            )

        if not chain:
            raise RuntimeError(
                "No clip generator could be configured. Provide HIGGSFIELD_API_KEY "
                "or install torch with CUDA support for local inference."
            )
        return AutoClipGenerator(chain)

    raise ValueError(f"Unknown clip generator provider: {provider!r}. "
                     f"Valid options: higgsfield, wan, ltx, auto")
