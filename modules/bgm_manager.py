"""
bgm_manager.py — Background music looping, trimming, and volume ducking.

Uses pydub for audio manipulation. BGM is looped/trimmed to match video
duration, then ducked (volume reduced) during narration segments.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass
class BGMConfig:
    bgm_path: Path
    video_duration: float          # seconds
    default_volume: float = 0.12   # 0.0 – 1.0
    duck_volume: float = 0.04      # volume when narration is active
    fade_in: float = 1.0           # seconds
    fade_out: float = 2.0          # seconds


# ---------------------------------------------------------------------------
# BGMManager
# ---------------------------------------------------------------------------

class BGMManager:
    """
    Prepares a background music track for video composition.

    Workflow:
    1. Load BGM file.
    2. Loop or trim to match video duration.
    3. Apply fade-in and fade-out.
    4. Duck volume during narration windows.
    5. Export as WAV for MoviePy mixing.
    """

    def __init__(self, output_dir: str | Path = "assets/audio"):
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------

    def prepare(
        self,
        config: BGMConfig,
        narration_windows: Optional[list[tuple[float, float]]] = None,
        output_name: str = "bgm_prepared.wav",
    ) -> Path:
        """
        Prepare and export a BGM track.

        Args:
            config: BGMConfig with path and volume settings.
            narration_windows: list of (start, end) seconds where narration is active.
                               BGM will be ducked in these windows.
            output_name: filename for the output WAV.

        Returns:
            Path to the prepared BGM WAV file.
        """
        try:
            from pydub import AudioSegment
        except ImportError as e:
            raise ImportError("pip install pydub") from e

        logger.info("Preparing BGM: %s (duration=%.1fs)", config.bgm_path, config.video_duration)

        bgm = AudioSegment.from_file(str(config.bgm_path))

        # ── Loop / trim to video duration ────────────────────────────
        target_ms = int(config.video_duration * 1000)
        bgm = self._loop_to_length(bgm, target_ms)
        bgm = bgm[:target_ms]

        # ── Apply global volume ──────────────────────────────────────
        bgm = bgm + self._db_change(config.default_volume)

        # ── Volume ducking ───────────────────────────────────────────
        if narration_windows:
            bgm = self._duck(bgm, narration_windows, config.duck_volume, config.default_volume)

        # ── Fade in / out ────────────────────────────────────────────
        fade_in_ms = int(config.fade_in * 1000)
        fade_out_ms = int(config.fade_out * 1000)
        bgm = bgm.fade_in(fade_in_ms).fade_out(fade_out_ms)

        # ── Export ───────────────────────────────────────────────────
        out_path = self._output_dir / output_name
        bgm.export(str(out_path), format="wav")
        logger.info("BGM prepared: %s", out_path)
        return out_path

    # ------------------------------------------------------------------

    def _loop_to_length(self, audio, target_ms: int):
        from pydub import AudioSegment
        loops_needed = (target_ms // len(audio)) + 1
        return audio * loops_needed

    def _db_change(self, volume_ratio: float) -> float:
        """Convert 0–1 volume ratio to dB change (relative to 0dB baseline)."""
        import math
        if volume_ratio <= 0:
            return -60.0
        return 20 * math.log10(volume_ratio)

    def _duck(
        self,
        bgm,
        windows: list[tuple[float, float]],
        duck_vol: float,
        base_vol: float,
    ):
        """
        Apply volume ducking on narration windows using pydub.

        Splits the audio into segments and adjusts volume per window.
        """
        from pydub import AudioSegment

        duck_db = self._db_change(duck_vol) - self._db_change(base_vol)  # relative dB change
        total_ms = len(bgm)

        result = AudioSegment.empty()
        prev_ms = 0

        # Sort windows
        sorted_windows = sorted(windows, key=lambda w: w[0])

        for start_s, end_s in sorted_windows:
            start_ms = int(start_s * 1000)
            end_ms = int(end_s * 1000)

            # Normal segment before duck
            if start_ms > prev_ms:
                result += bgm[prev_ms:start_ms]

            # Ducked segment
            duck_segment = bgm[start_ms:end_ms]
            result += duck_segment + duck_db

            prev_ms = end_ms

        # Remainder after last window
        if prev_ms < total_ms:
            result += bgm[prev_ms:total_ms]

        return result
