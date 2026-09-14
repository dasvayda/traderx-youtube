"""
test_pipeline.py — API 키 없이 전체 파이프라인을 로컬에서 테스트합니다.

Mock:
  - 번역: 미리 작성된 일본어 스크립트 사용
  - TTS: pyttsx3 (로컬 TTS) 또는 무음 WAV 생성
  - 씬 계획: 하드코딩 씬 JSON
  - 이미지: 프로그램으로 생성한 테스트 이미지

실행:
  python test_pipeline.py
  # 결과: output/test_runs/YYYYMMDD_HHMMSS/
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# ── 프로젝트 루트를 sys.path에 추가 ─────────────────────────────────────────
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

TEST_RUNS_DIR = ROOT / "output" / "test_runs"


def create_run_dir() -> Path:
    """Create a timestamped folder for this test run."""
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = TEST_RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


# ===========================================================================
# 0. 설정 로드
# ===========================================================================

with open(ROOT / "config/settings.yaml", encoding="utf-8") as f:
    CFG = yaml.safe_load(f)


# ===========================================================================
# 1. 샘플 일본어 스크립트 (번역 Mock)
# ===========================================================================

JAPANESE_SCRIPT = """\
みなさん、こんにちは！本日は米国株式市場の重要ニュースをお届けします。

NVDAが今週、史上最高値を更新しました。AI半導体の需要急増が主な要因と見られています。

AAPLは第2四半期決算で市場予想を上回る売上を記録しました。サービス部門が過去最高売上を達成しています。

TSLAは自動運転ソフトウェアのアップデート発表後、株価が8%急騰しました。

S&P 500指数は今週2%上昇し、強気相場が続いています。来週のFRB金利決定に市場の注目が集まっています。

本日の動画がお役に立てましたら、チャンネル登録といいねをよろしくお願いします！
"""

# ===========================================================================
# 2. 씬 정의 (씬 계획 Mock)
# ===========================================================================

SCENES_DATA = [
    {
        "scene_id": 1,
        "duration": 4.0,
        "narration": "みなさん、こんにちは！本日は米国株式市場の重要ニュースをお届けします。",
        "subtitle": "本日の米国株式市場ニュース",
        "visual_type": "title_card",
        "visual_query": "stock market news",
        "ticker": None,
        "chart_period": "1mo",
        "transition": "fade",
        "annotations": [],
    },
    {
        "scene_id": 2,
        "duration": 5.0,
        "narration": "NVDAが今週、史上最高値を更新しました。AI半導体の需要急増が主な要因と見られています。",
        "subtitle": "NVDA 史上最高値を更新 🚀",
        "visual_type": "stock_chart",
        "visual_query": "NVDA stock chart",
        "ticker": "NVDA",
        "chart_period": "1mo",
        "transition": "fade",
        "annotations": ["史上最高値"],
    },
    {
        "scene_id": 3,
        "duration": 5.0,
        "narration": "AAPLは第2四半期決算で市場予想を上回る売上を記録しました。サービス部門が過去最高売上を達成しています。",
        "subtitle": "AAPL 決算 市場予想を上回る",
        "visual_type": "stock_chart",
        "visual_query": "AAPL Apple stock",
        "ticker": "AAPL",
        "chart_period": "1mo",
        "transition": "fade",
        "annotations": [],
    },
    {
        "scene_id": 4,
        "duration": 4.0,
        "narration": "TSLAは自動運転ソフトウェアのアップデート発表後、株価が8%急騰しました。",
        "subtitle": "TSLA +8% 急騰 ⚡",
        "visual_type": "stock_chart",
        "visual_query": "Tesla TSLA stock",
        "ticker": "TSLA",
        "chart_period": "1mo",
        "transition": "fade",
        "annotations": ["+8%"],
    },
    {
        "scene_id": 5,
        "duration": 5.0,
        "narration": "S&P 500指数は今週2%上昇し、強気相場が続いています。来週のFRB金利決定に市場の注目が集まっています。",
        "subtitle": "S&P500 今週+2% FRB注目",
        "visual_type": "market_chart",
        "visual_query": "S&P 500 stock market",
        "ticker": "SPY",
        "chart_period": "1mo",
        "transition": "fade",
        "annotations": ["+2%"],
    },
    {
        "scene_id": 6,
        "duration": 3.0,
        "narration": "本日の動画がお役に立てましたら、チャンネル登録といいねをよろしくお願いします！",
        "subtitle": "チャンネル登録・いいね お願いします！",
        "visual_type": "title_card",
        "visual_query": "",
        "ticker": None,
        "chart_period": "1mo",
        "transition": "fade",
        "annotations": [],
    },
]


# ===========================================================================
# 3. 테스트 이미지 생성 (차트 대체)
# ===========================================================================

def create_test_chart_image(scene_id: int, ticker: str, subtitle: str) -> Path:
    """PIL로 차트 대체 테스트 이미지 생성"""
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np

    w, h = 1080, 600
    bg = (18, 18, 30)
    img = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(img)

    # 배경 그라데이션 효과
    for y in range(h):
        alpha = y / h
        color = (
            int(18 + alpha * 10),
            int(18 + alpha * 15),
            int(30 + alpha * 20),
        )
        draw.line([(0, y), (w, y)], fill=color)

    # 모의 가격 선 그래프
    import random
    random.seed(scene_id * 42)
    points = []
    price = 150 + random.randint(0, 100)
    for x in range(0, w, 10):
        price += random.uniform(-5, 6)
        price = max(50, min(300, price))
        y_pos = int(h * 0.8 - (price - 50) / 250 * h * 0.6)
        points.append((x, y_pos))

    if len(points) > 1:
        draw.line(points, fill=(38, 166, 154), width=3)

    # 폰트
    try:
        font_lg = ImageFont.truetype("C:/Windows/Fonts/meiryo.ttc", 52)
        font_sm = ImageFont.truetype("C:/Windows/Fonts/meiryo.ttc", 28)
    except Exception:
        font_lg = ImageFont.load_default()
        font_sm = ImageFont.load_default()

    # 티커 텍스트 (ASCII만 사용 — PIL 호환성)
    draw.text((40, 30), ticker, font=font_lg, fill=(255, 255, 255))
    draw.text((40, 100), f"Scene {scene_id}", font=font_sm, fill=(180, 180, 200))

    out_path = ROOT / f"assets/charts/test_scene_{scene_id:02d}.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out_path))
    logger.info("테스트 이미지 생성: %s", out_path)
    return out_path


# ===========================================================================
# 4. 무음 WAV 생성 (TTS Mock)
# ===========================================================================

def create_silent_audio(duration: float, output_path: Path) -> Path:
    """pydub으로 무음 WAV를 생성합니다 (TTS API 없이 테스트)."""
    from pydub import AudioSegment
    output_path.parent.mkdir(parents=True, exist_ok=True)
    silence = AudioSegment.silent(duration=int(duration * 1000), frame_rate=24000)
    silence.export(str(output_path), format="wav")
    return output_path


# ===========================================================================
# 5. 자막 파일 생성
# ===========================================================================

def build_subtitles(scenes: list, run_dir: Path) -> Path:
    from modules.subtitle_generator import ASSGenerator, SubtitleBuilder, SubtitleStyle

    style = SubtitleStyle(font_size=52)
    builder = SubtitleBuilder()
    gen = ASSGenerator(style=style, video_width=1080, video_height=1920)

    offsets, t = [], 0.0
    for s in scenes:
        offsets.append(t)
        t += s["duration"]

    durations = [s["duration"] for s in scenes]

    class _FakeScene:
        def __init__(self, d):
            self.subtitle = d["subtitle"]
            self.duration = d["duration"]

    fake_scenes = [_FakeScene(s) for s in scenes]
    entries = builder.build(fake_scenes, durations, offsets)

    out_path = run_dir / "test_subtitles.ass"
    gen.generate(entries, out_path)
    return out_path


# ===========================================================================
# 6. 영상 조립
# ===========================================================================

def compose_video(scenes: list, asset_paths: list, narration_paths: list, run_dir: Path) -> Path:
    from modules.video_composer import VideoComposer, VideoConfig
    from modules.script_parser import SceneDefinition

    composer = VideoComposer(
        config=VideoConfig(width=1080, height=1920, fps=30, crf=23, preset="medium"),
        output_dir=str(run_dir),
    )

    scene_objs = [SceneDefinition.from_dict(s) for s in scenes]
    asset_p = [Path(p) if p else None for p in asset_paths]
    narr_p = [Path(p) if p else None for p in narration_paths]

    return composer.compose(
        scenes=scene_objs,
        asset_paths=asset_p,
        narration_paths=narr_p,
        bgm_path=None,
        output_name="test_raw.mp4",
    )


# ===========================================================================
# 7. 자막 burn-in
# ===========================================================================

def burn_subtitles(raw_video: Path, sub_file: Path, run_dir: Path) -> Path:
    from modules.subtitle_generator import burn_subtitles as _burn
    out = run_dir / "test_final.mp4"
    return _burn(raw_video, sub_file, out)


# ===========================================================================
# MAIN
# ===========================================================================

def main():
    logger.info("=" * 60)
    logger.info("TraderX 파이프라인 테스트 시작")
    logger.info("=" * 60)

    run_dir = create_run_dir()
    logger.info("출력 폴더: %s", run_dir)

    # ── Step 1: 에셋 준비 ──────────────────────────────────────────
    logger.info("[1/5] 테스트 이미지 생성 중...")
    asset_paths: list[str | None] = []
    for scene in SCENES_DATA:
        if scene["visual_type"] in ("stock_chart", "market_chart") and scene["ticker"]:
            p = create_test_chart_image(
                scene["scene_id"], scene["ticker"], scene["subtitle"]
            )
            asset_paths.append(str(p))
        else:
            asset_paths.append(None)  # title_card → 폴백

    # ── Step 2: TTS (무음 Mock) ────────────────────────────────────
    logger.info("[2/5] 무음 오디오 생성 중 (TTS Mock)...")
    narration_paths: list[str] = []
    for scene in SCENES_DATA:
        out_path = ROOT / f"assets/audio/test_narr_{scene['scene_id']:02d}.wav"
        create_silent_audio(scene["duration"], out_path)
        narration_paths.append(str(out_path))

    # ── Step 3: 자막 생성 ─────────────────────────────────────────
    logger.info("[3/5] 자막 파일 생성 중...")
    sub_file = build_subtitles(SCENES_DATA, run_dir)
    logger.info("자막 파일: %s", sub_file)

    # ── Step 4: 영상 조립 ─────────────────────────────────────────
    logger.info("[4/5] 영상 조립 중...")
    raw_video = compose_video(SCENES_DATA, asset_paths, narration_paths, run_dir)
    logger.info("Raw 영상: %s", raw_video)

    # ── Step 5: 자막 burn-in ──────────────────────────────────────
    logger.info("[5/5] 자막 삽입 중...")
    try:
        final_video = burn_subtitles(raw_video, sub_file, run_dir)
        logger.info("최종 영상: %s", final_video)
    except Exception as e:
        logger.warning("자막 burn-in 실패 (FFmpeg 미설치?): %s", e)
        logger.info("Raw 영상을 최종 결과로 사용합니다: %s", raw_video)
        final_video = raw_video

    logger.info("=" * 60)
    logger.info("테스트 완료!")
    logger.info("출력 파일: %s", final_video)
    logger.info("=" * 60)
    return final_video


if __name__ == "__main__":
    main()
