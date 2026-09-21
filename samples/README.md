# samples/

XTTS-v2 목소리 클로닝용 레퍼런스 오디오 파일을 여기에 저장합니다.

## 파일 요건

| 항목 | 권장 사양 |
|------|-----------|
| 포맷 | WAV (PCM 16-bit) 또는 MP3 |
| 길이 | 3초 이상 (6~30초가 최적) |
| 노이즈 | 배경 잡음·음악 없을 것 |
| 언어 | 타겟 언어(ja)로 녹음 권장 |

## 설정 방법

1. `samples/speaker.wav` 로 저장 (기본 경로)
2. 또는 `config/settings.yaml`에서 경로 변경:

```yaml
tts:
  provider: "xtts"
  xtts_speaker_wav: "samples/my_voice.wav"
  xtts_language: "ja"
```

## 빠른 시작 — 본인 목소리 녹음

```bash
# Windows 마이크 녹음 (10초)
python -c "
import sounddevice as sd
import soundfile as sf
import numpy as np
duration = 10
fs = 22050
print('녹음 시작... (10초)')
data = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
sd.wait()
sf.write('samples/speaker.wav', data, fs)
print('저장 완료: samples/speaker.wav')
"
```

또는 기존 영상에서 오디오만 추출:

```bash
ffmpeg -i your_video.mp4 -vn -acodec pcm_s16le -ar 22050 -ac 1 samples/speaker.wav
```

## .gitignore

개인 목소리 파일은 커밋하지 않는 것을 권장합니다.
`.gitignore`에 `samples/*.wav`, `samples/*.mp3` 를 추가하세요.
