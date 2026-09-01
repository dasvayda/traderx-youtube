# TraderX — YouTube Shorts Generator 📈

> **한국어** | [English](#english) | [日本語](#日本語)

---

## 한국어

### 이게 뭔가요?

한국어로 작성된 주식 시장 스크립트를 넣으면, **일본어 YouTube Shorts 영상(MP4)**을 자동으로 만들어주는 AI 파이프라인입니다.

```
한국어 스크립트 → 번역 → 씬 분할 → 이미지·음성 합성 → MP4 완성
```

### 주요 기능

- 🌐 **자동 번역** — 한국어 스크립트를 일본어로 변환 (OpenAI / Gemini / Claude 선택)
- 🎬 **씬 자동 분할** — LLM이 스크립트를 장면 단위로 나누고 시각 타입을 결정
- 🖼️ **이미지 수집** — 씬에 맞는 사진·영상을 Pexels / Pixabay에서 자동 다운로드
- 📊 **차트 첨부** — 직접 캡처한 차트 이미지를 씬에 연결 가능
- 🔊 **일본어 TTS** — 자연스러운 일본어 음성 합성 (OpenAI / Azure / Google / ElevenLabs)
- 📝 **자막 자동 생성** — ASS 포맷 자막을 영상에 직접 삽입
- 🎵 **BGM 믹싱** — 배경음악 루프 + 나레이션 구간 자동 음량 조절
- 🖥️ **Streamlit UI** — 코드 없이 웹 브라우저에서 전부 조작 가능

### 출력 포맷

| 항목 | 값 |
|------|----|
| 해상도 | 1080 × 1920 (9:16 Shorts) |
| 프레임 | 30 FPS |
| 길이 | 30 ~ 60초 |
| 코덱 | H.264 / AAC 128kbps |
| 포맷 | MP4 |

### 빠른 시작

**1. 패키지 설치**
```bash
pip install -r requirements.txt
```

**2. API 키 설정**
```bash
cp config/.env.example .env
# .env 파일을 열어 API 키 입력
```

**3. 앱 실행**
```bash
streamlit run app.py
```

**4. 사용 순서**

① 스크립트 입력 탭에서 한국어 스크립트 붙여넣기  
② 번역 탭에서 일본어 번역 실행  
③ 씬 계획 탭에서 씬 자동 생성 + 차트 이미지 첨부  
④ 영상 생성 탭에서 MP4 완성 및 다운로드  

### 필요한 API 키

| 서비스 | 용도 | 무료 여부 |
|--------|------|-----------|
| OpenAI | 번역 + TTS | 유료 |
| Pexels | 스톡 이미지·영상 | 무료 |
| Pixabay | 스톡 이미지·영상 | 무료 |
| Azure / Google / ElevenLabs | TTS (선택) | 플랜별 상이 |

---

## English

### What is this?

A Python pipeline that takes a **Korean stock market script** and automatically produces a **Japanese YouTube Shorts video (MP4)**.

```
Korean Script → Translate → Scene Split → Visuals + Voice → MP4
```

### Features

- 🌐 **Auto Translation** — Korean to Japanese via OpenAI / Gemini / Claude
- 🎬 **Scene Planning** — LLM splits the script into scenes and picks the visual type per scene
- 🖼️ **Asset Collection** — Automatically downloads matching images/clips from Pexels & Pixabay
- 📊 **Chart Attachment** — Attach your own chart screenshots to any scene
- 🔊 **Japanese TTS** — Natural Japanese voice synthesis (OpenAI / Azure / Google / ElevenLabs)
- 📝 **Subtitles** — ASS-format subtitles burned directly into the video
- 🎵 **BGM Mixing** — Background music loop with auto-ducking during narration
- 🖥️ **Streamlit UI** — Full browser-based interface, no coding required

### Output Specification

| Property | Value |
|----------|-------|
| Resolution | 1080 × 1920 (9:16 Shorts) |
| Frame rate | 30 FPS |
| Duration | 30 – 60 seconds |
| Codec | H.264 / AAC 128 kbps |
| Container | MP4 |

### Quick Start

**1. Install dependencies**
```bash
pip install -r requirements.txt
```

**2. Set up API keys**
```bash
cp config/.env.example .env
# Open .env and fill in your API keys
```

**3. Run the app**
```bash
streamlit run app.py
```

**4. Workflow**

① Paste your Korean script in the **Script** tab  
② Run translation in the **Translate** tab  
③ Auto-generate scenes and attach chart images in the **Scenes** tab  
④ Generate and download the finished MP4 in the **Generate** tab  

### Required API Keys

| Service | Purpose | Free? |
|---------|---------|-------|
| OpenAI | Translation + TTS | Paid |
| Pexels | Stock images & video | Free |
| Pixabay | Stock images & video | Free |
| Azure / Google / ElevenLabs | TTS (optional) | Plan-dependent |

---

## 日本語

### これは何ですか？

韓国語で書いた株式市場のスクリプトを入力すると、**日本語の YouTube Shorts 動画（MP4）** を自動で生成する AI パイプラインです。

```
韓国語スクリプト → 翻訳 → シーン分割 → 画像・音声合成 → MP4 完成
```

### 主な機能

- 🌐 **自動翻訳** — 韓国語スクリプトを日本語に変換（OpenAI / Gemini / Claude から選択）
- 🎬 **シーン自動分割** — LLM がスクリプトをシーン単位に分け、ビジュアルタイプを決定
- 🖼️ **素材収集** — シーンに合った画像・映像を Pexels / Pixabay から自動ダウンロード
- 📊 **チャート添付** — キャプチャしたチャート画像を各シーンに添付可能
- 🔊 **日本語 TTS** — 自然な日本語音声合成（OpenAI / Azure / Google / ElevenLabs）
- 📝 **字幕自動生成** — ASS 形式の字幕を動画に直接焼き込み
- 🎵 **BGM ミキシング** — BGM ループ＋ナレーション中の自動音量ダッキング
- 🖥️ **Streamlit UI** — ブラウザ上ですべて操作可能、コーディング不要

### 出力仕様

| 項目 | 値 |
|------|----|
| 解像度 | 1080 × 1920（9:16 Shorts） |
| フレームレート | 30 FPS |
| 長さ | 30 〜 60 秒 |
| コーデック | H.264 / AAC 128kbps |
| フォーマット | MP4 |

### クイックスタート

**1. パッケージをインストール**
```bash
pip install -r requirements.txt
```

**2. API キーを設定**
```bash
cp config/.env.example .env
# .env ファイルを開いて API キーを入力
```

**3. アプリを起動**
```bash
streamlit run app.py
```

**4. 使い方の流れ**

① **スクリプト入力** タブで韓国語スクリプトを貼り付け  
② **翻訳** タブで日本語翻訳を実行  
③ **シーン計画** タブで自動生成 ＋ チャート画像を添付  
④ **動画生成** タブで MP4 を完成・ダウンロード  

### 必要な API キー

| サービス | 用途 | 無料？ |
|----------|------|--------|
| OpenAI | 翻訳 + TTS | 有料 |
| Pexels | ストック画像・映像 | 無料 |
| Pixabay | ストック画像・映像 | 無料 |
| Azure / Google / ElevenLabs | TTS（任意） | プランによる |

---

## Project Structure

```
traderx-youtube/
├── app.py                  # Streamlit UI
├── config/
│   ├── settings.yaml       # App configuration
│   └── .env.example        # API key template
├── modules/
│   ├── translator.py       # Korean → Japanese translation
│   ├── script_parser.py    # Script → scene list
│   ├── scene_generator.py  # LLM scene enrichment
│   ├── asset_manager.py    # Image/video search & cache
│   ├── chart_generator.py  # User chart image registry
│   ├── tts_engine.py       # Japanese TTS synthesis
│   ├── subtitle_generator.py # ASS/SRT + FFmpeg burn-in
│   ├── video_composer.py   # MoviePy video assembly
│   ├── bgm_manager.py      # BGM loop & ducking
│   └── pipeline.py         # End-to-end orchestration
└── docs/                   # Module documentation
```

## License

MIT
