"""
subtitle_generator.py — Subtitle timing, ASS/SRT file generation, and FFmpeg burn-in.

Generates .ass (Advanced SubStation Alpha) subtitle files with full style control:
font, size, colour, outline, shadow, and vertical position.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Style config
# ---------------------------------------------------------------------------

@dataclass
class SubtitleStyle:
    font_name: str = "NotoSansJP-Bold"
    font_size: int = 52
    primary_color: str = "&H00FFFFFF"    # white  (ASS ABGR hex)
    outline_color: str = "&H00000000"   # black
    back_color: str = "&H80000000"      # semi-transparent black shadow
    bold: bool = True
    outline: int = 3
    shadow: int = 1
    margin_v: int = 80                  # pixels from bottom/top
    alignment: int = 2                  # 2=bottom-center (numpad layout)


# ---------------------------------------------------------------------------
# Timed subtitle entry
# ---------------------------------------------------------------------------

@dataclass
class SubtitleEntry:
    start: float    # seconds
    end: float      # seconds
    text: str


# ---------------------------------------------------------------------------
# ASS Generator
# ---------------------------------------------------------------------------

class ASSGenerator:
    """Generates an .ass subtitle file from a list of SubtitleEntry objects."""

    def __init__(self, style: Optional[SubtitleStyle] = None,
                 video_width: int = 1080, video_height: int = 1920):
        self._style = style or SubtitleStyle()
        self._w = video_width
        self._h = video_height

    # ------------------------------------------------------------------

    def generate(self, entries: list[SubtitleEntry], output_path: Path) -> Path:
        """Write .ass file and return its path."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        content = self._build_ass(entries)
        output_path.write_text(content, encoding="utf-8-sig")
        logger.info("ASS subtitle written: %s (%d entries)", output_path, len(entries))
        return output_path

    # ------------------------------------------------------------------

    def _build_ass(self, entries: list[SubtitleEntry]) -> str:
        s = self._style
        header = f"""\
[Script Info]
ScriptType: v4.00+
PlayResX: {self._w}
PlayResY: {self._h}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{s.font_name},{s.font_size},{s.primary_color},&H000000FF,{s.outline_color},{s.back_color},{int(s.bold)},0,0,0,100,100,0,0,1,{s.outline},{s.shadow},{s.alignment},10,10,{s.margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        events = "\n".join(
            f"Dialogue: 0,{self._fmt_time(e.start)},{self._fmt_time(e.end)},Default,,0,0,0,,{self._escape(e.text)}"
            for e in entries
        )
        return header + events + "\n"

    @staticmethod
    def _fmt_time(seconds: float) -> str:
        """Convert seconds to ASS timestamp H:MM:SS.cs"""
        cs = int(round(seconds * 100))
        h, remainder = divmod(cs, 360000)
        m, remainder = divmod(remainder, 6000)
        s, cs = divmod(remainder, 100)
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    @staticmethod
    def _escape(text: str) -> str:
        """Escape ASS special characters."""
        return text.replace("{", r"\{").replace("}", r"\}")


# ---------------------------------------------------------------------------
# SRT Generator (secondary format)
# ---------------------------------------------------------------------------

class SRTGenerator:
    def generate(self, entries: list[SubtitleEntry], output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        lines: list[str] = []
        for i, e in enumerate(entries, start=1):
            lines.append(str(i))
            lines.append(f"{self._fmt(e.start)} --> {self._fmt(e.end)}")
            lines.append(e.text)
            lines.append("")
        output_path.write_text("\n".join(lines), encoding="utf-8-sig")
        logger.info("SRT subtitle written: %s", output_path)
        return output_path

    @staticmethod
    def _fmt(seconds: float) -> str:
        ms = int(round((seconds % 1) * 1000))
        total_s = int(seconds)
        h, rem = divmod(total_s, 3600)
        m, s = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


# ---------------------------------------------------------------------------
# Subtitle Builder — converts scenes + TTS results into subtitle entries
# ---------------------------------------------------------------------------

class SubtitleBuilder:
    """
    Build subtitle entries from scene list + TTS duration results.

    Each scene contributes one subtitle entry that spans the narration duration.
    A small gap (0.1s) is inserted between entries.
    """

    GAP = 0.1   # seconds between subtitles

    def build(
        self,
        scenes: list,
        tts_durations: list[float],
        time_offsets: list[float],
    ) -> list[SubtitleEntry]:
        """
        Args:
            scenes: list of SceneDefinition
            tts_durations: actual audio durations per scene
            time_offsets: start time of each scene in the composed video
        """
        entries: list[SubtitleEntry] = []
        for scene, duration, offset in zip(scenes, tts_durations, time_offsets):
            start = offset
            end = offset + duration - self.GAP
            entries.append(SubtitleEntry(start=start, end=end, text=scene.subtitle))
        return entries


# ---------------------------------------------------------------------------
# FFmpeg subtitle burn-in
# ---------------------------------------------------------------------------

def burn_subtitles(
    input_video: Path,
    subtitle_file: Path,
    output_video: Path,
    ffmpeg_bin: str = "",
) -> Path:
    """
    Burn .ass subtitles into video using FFmpeg.

    Windows 경로 문제를 피하기 위해 자막 파일을 임시 디렉터리로 복사한 뒤 실행합니다.
    Returns path to the output video.
    """
    import shutil
    import tempfile

    output_video.parent.mkdir(parents=True, exist_ok=True)

    # ffmpeg 바이너리 탐색 순서: 인자 → PATH → imageio_ffmpeg 번들
    if not ffmpeg_bin:
        ffmpeg_bin = shutil.which("ffmpeg") or ""
    if not ffmpeg_bin:
        try:
            import imageio_ffmpeg
            ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            pass
    if not ffmpeg_bin:
        raise RuntimeError("ffmpeg를 찾을 수 없습니다. PATH에 ffmpeg를 추가하거나 pip install imageio-ffmpeg 를 실행하세요.")

    # Windows FFmpeg ass 필터는 드라이브 문자(C:)를 경로 구분자로 잘못 파싱합니다.
    # 해결책: subtitle 파일이 있는 디렉터리에서 FFmpeg을 실행하고 파일명만 전달합니다.
    sub_dir = subtitle_file.parent.resolve()
    sub_name = subtitle_file.name

    # 폰트를 Windows 시스템 폰트로 교체
    ass_content = subtitle_file.read_text(encoding="utf-8-sig")
    ass_content = ass_content.replace("NotoSansJP-Bold", "Meiryo")
    subtitle_file.write_text(ass_content, encoding="utf-8-sig")

    cmd = [
        ffmpeg_bin, "-y",
        "-i", str(input_video.resolve()),
        "-vf", f"ass={sub_name}",
        "-c:v", "libx264",
        "-crf", "23",
        "-preset", "medium",
        "-c:a", "copy",
        str(output_video.resolve()),
    ]
    logger.info("자막 삽입 실행 (cwd=%s): %s", sub_dir, " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(sub_dir))

    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg subtitle burn failed:\n{result.stderr[-2000:]}")

    logger.info("자막 삽입 완료: %s", output_video)
    return output_video
