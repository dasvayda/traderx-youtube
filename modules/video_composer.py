"""
video_composer.py — MoviePy 2.x 기반 영상 조립 엔진.

1080×1920 (9:16) YouTube Shorts MP4를 생성합니다.
- 정지 이미지: Ken Burns 줌 효과
- 영상 클립: 9:16 크롭
- 트랜지션: CrossFadeIn / CrossFadeOut
- TTS 내레이션 오디오 + BGM 믹싱
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class VideoConfig:
    width: int = 1080
    height: int = 1920
    fps: int = 30
    codec: str = "libx264"
    audio_codec: str = "aac"
    audio_bitrate: str = "128k"
    crf: int = 23
    preset: str = "medium"


# ---------------------------------------------------------------------------
# 씬 클립 빌더
# ---------------------------------------------------------------------------

def _build_image_clip(image_path: Path, duration: float, w: int, h: int):
    """정지 이미지 → Ken Burns 줌 효과가 있는 VideoClip"""
    import numpy as np
    from moviepy import ImageClip, VideoClip
    from PIL import Image

    img = Image.open(str(image_path)).convert("RGB")

    # cover 스케일링 (9:16 프레임에 꽉 채우기)
    img_w, img_h = img.size
    scale = max(w / img_w, h / img_h) * 1.06  # 줌 여유분
    new_w = int(img_w * scale)
    new_h = int(img_h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    arr = np.array(img)

    # Ken Burns: 서서히 줌인 (1.0 → 1.05)
    def make_frame(t: float):
        progress = t / max(duration, 0.001)
        zoom = 1.0 + 0.05 * progress
        cur_w = int(w / zoom)
        cur_h = int(h / zoom)
        x0 = (new_w - cur_w) // 2
        y0 = (new_h - cur_h) // 2
        crop = arr[y0:y0 + cur_h, x0:x0 + cur_w]
        from PIL import Image as PILImage
        return np.array(PILImage.fromarray(crop).resize((w, h), PILImage.LANCZOS))

    return VideoClip(make_frame, duration=duration).with_fps(30)


def _build_video_clip(video_path: Path, duration: float, w: int, h: int):
    """영상 클립 → 9:16 크롭 + 길이 조정"""
    from moviepy import VideoFileClip, concatenate_videoclips
    from moviepy import vfx

    clip = VideoFileClip(str(video_path), audio=False)

    # 길이 조정
    if clip.duration > duration:
        clip = clip.subclipped(0, duration)
    elif clip.duration < duration:
        loops = int(duration / clip.duration) + 1
        clip = concatenate_videoclips([clip] * loops).subclipped(0, duration)

    # cover 스케일
    clip_ar = clip.w / clip.h
    target_ar = w / h
    if clip_ar > target_ar:
        clip = clip.with_effects([vfx.Resize(height=h)])
    else:
        clip = clip.with_effects([vfx.Resize(width=w)])

    # 중앙 크롭
    clip = clip.with_effects([vfx.Crop(
        x_center=clip.w / 2,
        y_center=clip.h / 2,
        width=w,
        height=h,
    )])
    return clip


def _build_title_card(text: str, duration: float, w: int, h: int):
    """
    단색 배경 클립 (이미지 없는 씬 폴백).
    자막 텍스트는 FFmpeg burn-in 단계에서 표시되므로 여기서는 배경만 생성합니다.
    """
    from moviepy import ColorClip
    return ColorClip(size=(w, h), color=(30, 30, 46), duration=duration).with_fps(30)


# ---------------------------------------------------------------------------
# Video Composer
# ---------------------------------------------------------------------------

class VideoComposer:
    def __init__(self, config: Optional[VideoConfig] = None,
                 output_dir: str | Path = "output"):
        self._cfg = config or VideoConfig()
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def compose(
        self,
        scenes: list,
        asset_paths: list[Optional[Path]],
        narration_paths: list[Optional[Path]],
        bgm_path: Optional[Path] = None,
        output_name: str = "output.mp4",
    ) -> Path:
        from moviepy import (
            AudioFileClip, CompositeAudioClip, concatenate_videoclips
        )
        from moviepy import vfx

        w, h, fps = self._cfg.width, self._cfg.height, self._cfg.fps
        clips = []

        for i, (scene, asset_path, narration_path) in enumerate(
            zip(scenes, asset_paths, narration_paths)
        ):
            duration = scene.duration
            logger.info("씬 %d/%d 조립 중 (%s, %.1fs)", i + 1, len(scenes),
                        scene.visual_type, duration)

            # ── 비주얼 클립 ─────────────────────────────────────────
            visual = self._build_visual(scene, asset_path, duration, w, h)

            # ── 내레이션 오디오 ──────────────────────────────────────
            if narration_path and narration_path.exists():
                audio = AudioFileClip(str(narration_path))
                if audio.duration > duration:
                    audio = audio.subclipped(0, duration)
                visual = visual.with_audio(audio)

            clips.append(visual)

        # ── 클립 연결 ────────────────────────────────────────────────
        final = concatenate_videoclips(clips, method="compose")

        # ── BGM 믹싱 ─────────────────────────────────────────────────
        if bgm_path and bgm_path.exists():
            bgm_audio = AudioFileClip(str(bgm_path))
            if bgm_audio.duration > final.duration:
                bgm_audio = bgm_audio.subclipped(0, final.duration)

            if final.audio:
                mixed = CompositeAudioClip([final.audio, bgm_audio])
                final = final.with_audio(mixed)
            else:
                final = final.with_audio(bgm_audio)

        # ── 인코딩 ───────────────────────────────────────────────────
        out_path = self._output_dir / output_name
        final.write_videofile(
            str(out_path),
            fps=fps,
            codec=self._cfg.codec,
            audio_codec=self._cfg.audio_codec,
            audio_bitrate=self._cfg.audio_bitrate,
            ffmpeg_params=["-crf", str(self._cfg.crf), "-preset", self._cfg.preset],
            logger=None,
        )
        logger.info("영상 저장: %s", out_path)
        return out_path

    def _build_visual(self, scene, asset_path: Optional[Path],
                      duration: float, w: int, h: int):
        if asset_path is None or scene.visual_type == "title_card":
            return _build_title_card(scene.subtitle, duration, w, h)

        suffix = asset_path.suffix.lower()
        if suffix in (".jpg", ".jpeg", ".png", ".webp"):
            try:
                return _build_image_clip(asset_path, duration, w, h)
            except Exception as e:
                logger.warning("이미지 클립 생성 실패: %s", e)
                return _build_title_card(scene.subtitle, duration, w, h)
        elif suffix in (".mp4", ".mov", ".avi", ".webm"):
            try:
                return _build_video_clip(asset_path, duration, w, h)
            except Exception as e:
                logger.warning("영상 클립 생성 실패: %s", e)
                return _build_title_card(scene.subtitle, duration, w, h)
        else:
            return _build_title_card(scene.subtitle, duration, w, h)
