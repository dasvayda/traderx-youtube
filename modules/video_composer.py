"""
video_composer.py — MoviePy 2.x 기반 영상 조립 엔진.

레이아웃 (1080×1920):
  ┌─────────────────┐  0px
  │   상단 헤더     │         종목명 · 타이틀  (HEADER_H = 400px)
  ├─────────────────┤  400px
  │                 │
  │  차트 / 비주얼  │         16:9 차트 letterbox  (CHART_ZONE_H = 1080px)
  │                 │
  ├─────────────────┤  1480px
  │   자막 영역     │         ASS 자막 burn-in 전용  (FOOTER_H = 440px)
  └─────────────────┘  1920px

YouTube Shorts UI 안전 영역:
  - 상단 15% (288px): YouTube 검색·제목 UI → 헤더 텍스트는 300px 아래부터
  - 하단 20% (384px): 좋아요·구독 버튼 UI → 자막은 상단 1480~1536px 구간에 표시
  - 우측 11% (119px): 반응 버튼 UI → 텍스트 우측 여백 140px 이상 확보
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# ── 레이아웃 상수 ─────────────────────────────────────────────────────────────
HEADER_H    = 400   # 상단 헤더  (0 ~ 400px)
CHART_ZONE_H = 1080  # 차트 영역 (400 ~ 1480px)
FOOTER_H    = 440   # 자막 여백 (1480 ~ 1920px)

# ── 색상 팔레트 ───────────────────────────────────────────────────────────────
BG_COLOR       = (18, 18, 30)       # 다크 네이비 배경
ACCENT_COLOR   = (38, 166, 154)     # 청록 포인트 라인
TEXT_PRIMARY   = (255, 255, 255)    # 흰색 (티커·타이틀)
TEXT_SECONDARY = (180, 180, 200)    # 연보라 (부제·자막 힌트)


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
# PIL 유틸
# ---------------------------------------------------------------------------

def _load_font(size: int):
    from PIL import ImageFont
    candidates = [
        "C:/Windows/Fonts/meiryo.ttc",
        "C:/Windows/Fonts/YuGothB.ttc",
        "C:/Windows/Fonts/msgothic.ttc",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _wrap_text(text: str, max_chars: int) -> list[str]:
    lines, buf = [], text
    while len(buf) > max_chars:
        lines.append(buf[:max_chars])
        buf = buf[max_chars:]
    if buf:
        lines.append(buf)
    return lines


def _make_dark_canvas(w: int, h: int):
    """다크 배경 PIL 이미지 반환"""
    from PIL import Image
    return Image.new("RGB", (w, h), BG_COLOR)


def _draw_header(img, scene, w: int) -> None:
    """
    상단 헤더 영역(0~400px)에 종목명·타이틀 텍스트를 그립니다.

    레이아웃:
      300px  : YouTube UI 안전선
      320px  : 종목명 (ticker) — 큰 글자
      330px  : 포인트 언더바
      348px  : 구분선
      360px  : 부제 (subtitle 앞 30자)
      398px  : 하단 액센트 라인 (헤더 경계)
    """
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)

    ticker   = (getattr(scene, "ticker",   None) or "").strip()
    subtitle = (getattr(scene, "subtitle", None) or "").strip()
    is_valid_ticker = ticker and ticker not in ("N/A", "None", "")

    # 헤더 하단 경계선
    draw.line([(0, HEADER_H - 2), (w, HEADER_H - 2)],
              fill=ACCENT_COLOR, width=3)

    if is_valid_ticker:
        font_ticker = _load_font(88)
        font_sub    = _load_font(40)

        # 종목명
        draw.text((60, 306), ticker, font=font_ticker, fill=TEXT_PRIMARY)

        # 티커 아래 포인트 언더바
        bbox = draw.textbbox((0, 0), ticker, font=font_ticker)
        bar_w = bbox[2] - bbox[0]
        draw.rectangle([(60, 398), (60 + bar_w, 402)], fill=ACCENT_COLOR)

        # 부제 (subtitle 앞 28자)
        if subtitle:
            draw.text((62, 350), subtitle[:28], font=font_sub,
                      fill=TEXT_SECONDARY)
    else:
        # 티커 없음 → subtitle을 헤더 중앙에 표시
        font_title = _load_font(56)
        lines = _wrap_text(subtitle, 20)
        y = 300 + (HEADER_H - 300 - len(lines) * 70) // 2
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font_title)
            lw = bbox[2] - bbox[0]
            draw.text(((w - lw) // 2, y), line, font=font_title,
                      fill=TEXT_PRIMARY)
            y += 72


# ---------------------------------------------------------------------------
# 차트 letterbox 배치
# ---------------------------------------------------------------------------

def _letterbox_into_zone(chart_img, zone_w: int, zone_h: int) -> np.ndarray:
    """
    차트 이미지를 zone_w×zone_h 캔버스에 letterbox로 중앙 배치합니다.
    차트 전체가 손실 없이 보입니다.
    """
    from PIL import Image

    scale = min(zone_w / chart_img.width, zone_h / chart_img.height)
    new_w = int(chart_img.width  * scale)
    new_h = int(chart_img.height * scale)
    resized = chart_img.resize((new_w, new_h), Image.LANCZOS)

    canvas = Image.new("RGB", (zone_w, zone_h), BG_COLOR)
    x = (zone_w - new_w) // 2
    y = (zone_h - new_h) // 2
    canvas.paste(resized, (x, y))
    return np.array(canvas)


# ---------------------------------------------------------------------------
# 씬별 클립 빌더
# ---------------------------------------------------------------------------

def _build_chart_clip(scene, chart_path: Path, duration: float, w: int, h: int):
    """
    이미지 씬 (stock_chart, company_image 등):
      - 상단 헤더: ticker + subtitle
      - 중앙 차트 영역: letterbox + Ken Burns 줌 (1.0→1.04)
      - 하단 여백: 다크 배경 (ASS 자막용)
    """
    from PIL import Image
    from moviepy import VideoClip

    chart_img  = Image.open(str(chart_path)).convert("RGB")
    chart_zone = _letterbox_into_zone(chart_img, w, CHART_ZONE_H)  # (CHART_ZONE_H, w, 3)

    # 헤더 포함 정적 기본 프레임 생성
    base_img = _make_dark_canvas(w, h)
    _draw_header(base_img, scene, w)
    base_arr = np.array(base_img)

    # Ken Burns: 차트 영역 내에서만 줌 (미세하게)
    ch, cw = chart_zone.shape[:2]

    def make_frame(t: float):
        progress = t / max(duration, 0.001)
        zoom = 1.0 + 0.04 * progress

        crop_w = int(cw / zoom)
        crop_h = int(ch / zoom)
        x0 = (cw - crop_w) // 2
        y0 = (ch - crop_h) // 2
        cropped = chart_zone[y0:y0 + crop_h, x0:x0 + crop_w]

        from PIL import Image as PILImage
        zoomed = np.array(
            PILImage.fromarray(cropped).resize((cw, ch), PILImage.LANCZOS)
        )
        frame = base_arr.copy()
        frame[HEADER_H:HEADER_H + CHART_ZONE_H, :] = zoomed
        return frame

    return VideoClip(make_frame, duration=duration).with_fps(30)


def _build_footage_clip(scene, video_path: Path, duration: float,
                        w: int, h: int):
    """
    footage 씬: 영상을 차트 영역(1080×1080)에 letterbox 배치.
    """
    from moviepy import VideoFileClip, VideoClip, concatenate_videoclips
    from moviepy import vfx

    clip = VideoFileClip(str(video_path), audio=False)

    if clip.duration > duration:
        clip = clip.subclipped(0, duration)
    elif clip.duration < duration:
        loops = int(duration / clip.duration) + 1
        clip = concatenate_videoclips([clip] * loops).subclipped(0, duration)

    # 차트 영역(w × CHART_ZONE_H)에 fit
    scale = min(w / clip.w, CHART_ZONE_H / clip.h)
    new_w = int(clip.w * scale)
    new_h = int(clip.h * scale)
    clip = clip.with_effects([vfx.Resize((new_w, new_h))])

    base_img = _make_dark_canvas(w, h)
    _draw_header(base_img, scene, w)

    x_off = (w - new_w) // 2
    y_off = HEADER_H + (CHART_ZONE_H - new_h) // 2

    def make_frame(t: float):
        vf = clip.get_frame(t)
        frame = np.array(base_img).copy()
        frame[y_off:y_off + new_h, x_off:x_off + new_w] = vf
        return frame

    return VideoClip(make_frame, duration=duration).with_fps(30)


def _build_title_card(scene, duration: float, w: int, h: int):
    """
    title_card 씬: 전체 프레임을 브랜딩 카드로 구성.
    자막은 하단 여백(1480~1920px)의 ASS burn-in으로 표시됩니다.
    """
    from PIL import Image, ImageDraw
    from moviepy import ImageClip

    img  = _make_dark_canvas(w, h)
    draw = ImageDraw.Draw(img)

    # 상하 액센트 바
    draw.rectangle([(0, 0), (w, 5)],       fill=ACCENT_COLOR)
    draw.rectangle([(0, h - 5), (w, h)],   fill=ACCENT_COLOR)
    # 중앙 수평선
    draw.line([(80, h // 2 - 2), (w - 80, h // 2 - 2)],
              fill=(50, 50, 70), width=1)

    ticker   = (getattr(scene, "ticker",   None) or "").strip()
    subtitle = (getattr(scene, "subtitle", None) or "").strip()
    is_valid_ticker = ticker and ticker not in ("N/A", "None", "")

    if is_valid_ticker:
        font_t = _load_font(140)
        font_s = _load_font(52)

        bbox = draw.textbbox((0, 0), ticker, font=font_t)
        tw   = bbox[2] - bbox[0]
        draw.text(((w - tw) // 2, 760), ticker, font=font_t, fill=ACCENT_COLOR)

        if subtitle:
            bbox2 = draw.textbbox((0, 0), subtitle[:24], font=font_s)
            sw    = bbox2[2] - bbox2[0]
            draw.text(((w - sw) // 2, 930), subtitle[:24],
                      font=font_s, fill=TEXT_SECONDARY)
    else:
        font_s = _load_font(62)
        lines  = _wrap_text(subtitle, 18)
        y = h // 2 - len(lines) * 80 // 2
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font_s)
            lw   = bbox[2] - bbox[0]
            draw.text(((w - lw) // 2, y), line, font=font_s, fill=TEXT_PRIMARY)
            y += 86

    return ImageClip(np.array(img), duration=duration).with_fps(30)


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
        from moviepy import AudioFileClip, CompositeAudioClip, concatenate_videoclips

        w, h, fps = self._cfg.width, self._cfg.height, self._cfg.fps
        clips = []

        for i, (scene, asset_path, narration_path) in enumerate(
            zip(scenes, asset_paths, narration_paths)
        ):
            duration = scene.duration
            logger.info("씬 %d/%d 조립 중 (%s, %.1fs)",
                        i + 1, len(scenes), scene.visual_type, duration)

            visual = self._build_visual(scene, asset_path, duration, w, h)

            if narration_path and narration_path.exists():
                audio = AudioFileClip(str(narration_path))
                if audio.duration > duration:
                    audio = audio.subclipped(0, duration)
                visual = visual.with_audio(audio)

            clips.append(visual)

        final = concatenate_videoclips(clips, method="compose")

        if bgm_path and bgm_path.exists():
            bgm_audio = AudioFileClip(str(bgm_path))
            if bgm_audio.duration > final.duration:
                bgm_audio = bgm_audio.subclipped(0, final.duration)
            if final.audio:
                mixed = CompositeAudioClip([final.audio, bgm_audio])
                final = final.with_audio(mixed)
            else:
                final = final.with_audio(bgm_audio)

        out_path = self._output_dir / output_name
        final.write_videofile(
            str(out_path),
            fps=fps,
            codec=self._cfg.codec,
            audio_codec=self._cfg.audio_codec,
            audio_bitrate=self._cfg.audio_bitrate,
            ffmpeg_params=["-crf", str(self._cfg.crf),
                           "-preset", self._cfg.preset],
            logger=None,
        )
        logger.info("영상 저장: %s", out_path)
        return out_path

    def _build_visual(self, scene, asset_path: Optional[Path],
                      duration: float, w: int, h: int):
        if scene.visual_type == "title_card" or asset_path is None:
            return _build_title_card(scene, duration, w, h)

        suffix = asset_path.suffix.lower()
        if suffix in (".jpg", ".jpeg", ".png", ".webp"):
            try:
                return _build_chart_clip(scene, asset_path, duration, w, h)
            except Exception as e:
                logger.warning("차트 클립 생성 실패: %s", e)
                return _build_title_card(scene, duration, w, h)
        elif suffix in (".mp4", ".mov", ".avi", ".webm"):
            try:
                return _build_footage_clip(scene, asset_path, duration, w, h)
            except Exception as e:
                logger.warning("영상 클립 생성 실패: %s", e)
                return _build_title_card(scene, duration, w, h)
        else:
            return _build_title_card(scene, duration, w, h)
