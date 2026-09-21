"""
scripts/test_xtts.py — XTTS-v2 목소리 녹음 및 합성 테스트

실행:
    python scripts/test_xtts.py
"""

import sys
import time
from pathlib import Path

# ── 경로 설정 ────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

SAMPLE_WAV = ROOT / "samples" / "speaker.wav"
OUTPUT_WAV = ROOT / "output" / "test_xtts_output.wav"

TEST_TEXT = (
    "こんにちは。本日のテスラ株価をお伝えします。"
    "テスラは本日、前日比プラス三パーセントで取引を終えました。"
    "引き続き、最新の市場情報をお届けします。チャンネル登録をお願いします。"
)

RECORD_SECONDS = 10
SAMPLE_RATE = 22050


# ── 1. 마이크 녹음 ──────────────────────────────────────────

def record_sample():
    import sounddevice as sd
    import soundfile as sf
    import numpy as np

    SAMPLE_WAV.parent.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 50)
    print(f"  마이크 녹음 — {RECORD_SECONDS}초")
    print("=" * 50)
    print("  아래 문장을 자연스럽게 읽어주세요 (일본어 억양 불필요):\n")
    print("  「こんにちは、テスラの最新情報をお届けします。」\n")
    print("  또는 한국어로:\n")
    print("  「안녕하세요, 오늘의 테슬라 주가를 전해드리겠습니다.」\n")

    for i in range(3, 0, -1):
        print(f"  {i}초 후 녹음 시작...", flush=True)
        time.sleep(1)

    print("  ▶ 녹음 중... 말씀해주세요!\n")
    data = sd.rec(
        int(RECORD_SECONDS * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
    )
    sd.wait()
    print("  ■ 녹음 완료\n")

    sf.write(str(SAMPLE_WAV), data, SAMPLE_RATE)
    print(f"  저장: {SAMPLE_WAV}\n")


# ── 2. XTTS 합성 ────────────────────────────────────────────

def synthesize():
    from modules.tts_engine import XTTSEngine

    OUTPUT_WAV.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 50)
    print("  XTTS-v2 합성 시작 (첫 실행은 모델 다운로드로 수 분 소요)")
    print("=" * 50)
    print(f"\n  레퍼런스: {SAMPLE_WAV}")
    print(f"  출력:     {OUTPUT_WAV}")
    print(f"\n  텍스트:\n  {TEST_TEXT}\n")

    engine = XTTSEngine(
        speaker_wav=SAMPLE_WAV,
        language="ja",
        device="cpu",
    )

    t0 = time.time()
    result = engine.synthesize(TEST_TEXT, OUTPUT_WAV)
    elapsed = time.time() - t0

    print(f"\n  ✓ 완료 — {result.duration_seconds:.1f}초 오디오 생성 ({elapsed:.0f}초 소요)")
    print(f"  파일: {result.audio_path}\n")
    return result


# ── 3. 재생 (선택) ──────────────────────────────────────────

def play(path: Path):
    try:
        import sounddevice as sd
        import soundfile as sf
        data, fs = sf.read(str(path), dtype="float32")
        print(f"  ▶ 재생 중... ({path.name})")
        sd.play(data, fs)
        sd.wait()
        print("  재생 완료\n")
    except Exception as e:
        print(f"  재생 스킵 ({e})\n")


# ── main ────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skip-record", action="store_true",
        help="기존 samples/speaker.wav 를 재사용 (녹음 생략)",
    )
    parser.add_argument(
        "--no-play", action="store_true",
        help="합성 후 재생 생략",
    )
    args = parser.parse_args()

    if not args.skip_record:
        record_sample()
    else:
        if not SAMPLE_WAV.exists():
            print(f"ERROR: {SAMPLE_WAV} 파일이 없습니다. --skip-record 없이 실행하세요.")
            sys.exit(1)
        print(f"  기존 샘플 사용: {SAMPLE_WAV}\n")

    result = synthesize()

    if not args.no_play:
        play(result.audio_path)

    print("=" * 50)
    print("  테스트 완료!")
    print(f"  결과 파일: {result.audio_path}")
    print("=" * 50)
