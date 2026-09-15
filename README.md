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

**2. (선택) API 키 없이 샘플 영상 테스트**

설치만 하면 바로 돌려볼 수 있음. 번역·TTS·LLM은 Mock 데이터를 쓰고, 영상 합성·자막만 실제 모듈로 동작함.

```bash
python test_pipeline.py
# 결과: output/test_final.mp4
```

API 키가 없어도 위 명령으로 30초 내외 Shorts 샘플 MP4를 만들 수 있음.  
나레이션은 무음이고, 차트는 PIL로 생성한 테스트 이미지를 사용함.

**3. API 키 설정 (실제 AI 기능 사용 시)**

```bash
cp config/.env.example .env
# .env 파일을 열어 필요한 키 입력
```

**4. 앱 실행**
```bash
streamlit run app.py
```

**5. 사용 순서**

① 스크립트 입력 탭에서 한국어 스크립트 붙여넣기  
② 번역 탭에서 일본어 번역 실행  
③ 씬 계획 탭에서 씬 자동 생성 + 차트 이미지 첨부  
④ 영상 생성 탭에서 MP4 완성 및 다운로드  

### API 키가 뭔가요? 왜 필요한가요?

이 프로젝트는 **외부 AI·미디어 서비스**를 호출해서 영상을 만듦.  
각 서비스는 본인 계정으로 **API 키**(인증 문자열)를 발급받아야 사용할 수 있음.

| 파이프라인 단계 | 하는 일 | 키가 필요한 이유 |
|----------------|---------|-----------------|
| 번역 | 한국어 → 일본어 변환 | OpenAI / Gemini / Claude 같은 LLM API 호출 |
| 씬 계획 | 스크립트를 장면으로 분할 | LLM이 씬별 이미지·차트 타입 결정 |
| 이미지 수집 | 씬에 맞는 사진·영상 | Pexels / Pixabay 검색 API |
| TTS | 일본어 나레이션 음성 | OpenAI TTS 등 음성 합성 API |
| 차트 | 주가 차트 이미지 | **키 불필요** — TradingView 등에서 캡처 후 직접 업로드 |
| 영상 합성·자막 | MP4 조립 | **키 불필요** — 로컬 MoviePy + FFmpeg |

키 없이도 `test_pipeline.py`로 **영상 합성 흐름만** 검증 가능함.  
Streamlit UI에서 번역·TTS·씬 자동 생성을 쓰려면 **최소 1개 LLM 키**가 필요함.

### 필수 vs 선택

| 구분 | 키 | 없으면 어떻게 되나 |
|------|-----|-------------------|
| **필수 (UI 전체 사용)** | LLM 1개 (OpenAI / Gemini / Claude 중 택1) | 번역·씬 계획 불가 |
| **권장** | `OPENAI_API_KEY` | OpenAI를 TTS까지 쓰면 키 하나로 번역+음성 처리 가능 |
| **권장** | `PEXELS_API_KEY` | 차트 외 씬 배경 이미지를 못 가져옴 (title_card 폴백) |
| **선택** | `PIXABAY_API_KEY` | Pexels 실패 시 이미지 폴백 |
| **선택** | Azure / Google / ElevenLabs TTS | OpenAI TTS 대신 다른 음성 엔진 사용 |
| **선택** | `ALPHA_VANTAGE_KEY` | `news_fetcher` / `script_writer` 뉴스·스크립트 자동 생성 |
| **선택** | YouTube OAuth | YouTube 업로드 탭 자동 업로드 |

### API 키 발급 방법

`.env` 파일에 아래 변수명으로 저장함. **`.env`는 Git에 올리지 말 것.**

#### LLM (번역 + 씬 계획) — 하나만 있어도 됨

| 변수명 | 서비스 | 왜 필요한가 | 발급 위치 | 비용 |
|--------|--------|------------|----------|------|
| `OPENAI_API_KEY` | OpenAI | 기본 LLM. TTS도 같이 쓸 수 있음 | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | 유료 (사용량 과금) |
| `GEMINI_API_KEY` | Google Gemini | OpenAI 대신 번역·씬 계획 | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | 무료 티어 있음 |
| `ANTHROPIC_API_KEY` | Claude | OpenAI 대신 번역·씬 계획 | [console.anthropic.com](https://console.anthropic.com/) | 유료 |

`config/settings.yaml`의 `llm.provider`에서 사용할 서비스를 선택함.

#### TTS (일본어 나레이션) — `tts.provider`에 맞는 키만

| 변수명 | 서비스 | 왜 필요한가 | 발급 위치 | 비용 |
|--------|--------|------------|----------|------|
| `OPENAI_API_KEY` | OpenAI TTS | 씬별 나레이션 MP3 생성 | 위와 동일 | 유료 |
| `AZURE_SPEECH_KEY` | Azure Speech | Neural TTS (`ja-JP-NanamiNeural` 등) | [Azure AI Speech](https://azure.microsoft.com/products/ai-services/text-to-speech) | 무료 티어 있음 |
| `AZURE_SPEECH_REGION` | Azure | 리전 (예: `japaneast`) | Azure 포털에서 확인 | — |
| `GOOGLE_APPLICATION_CREDENTIALS` | Google Cloud TTS | 서비스 계정 JSON 파일 경로 | [Cloud TTS](https://cloud.google.com/text-to-speech) | 무료 티어 있음 |
| `ELEVENLABS_API_KEY` | ElevenLabs | 고품질 다국어 TTS | [elevenlabs.io](https://elevenlabs.io/) | 무료 티어 있음 |

#### 이미지·영상 (씬 배경)

| 변수명 | 서비스 | 왜 필요한가 | 발급 위치 | 비용 |
|--------|--------|------------|----------|------|
| `PEXELS_API_KEY` | Pexels | 씬 키워드로 세로형 사진·영상 검색 | [pexels.com/api](https://www.pexels.com/api/) | **무료** |
| `PIXABAY_API_KEY` | Pixabay | Pexels 실패 시 이미지 폴백 | [pixabay.com/api/docs](https://pixabay.com/api/docs/) | **무료** |

차트 씬(`stock_chart`)은 API 대신 **사용자가 직접 캡처한 이미지**를 UI에서 첨부함.

#### 확장 기능 (선택)

| 변수명 | 서비스 | 왜 필요한가 | 발급 위치 | 비용 |
|--------|--------|------------|----------|------|
| `ALPHA_VANTAGE_KEY` | Alpha Vantage | 종목 뉴스 수집 (`news_fetcher`) | [alphavantage.co/support](https://www.alphavantage.co/support/#api-key) | **무료** (일일 호출 제한) |
| `YOUTUBE_CLIENT_SECRETS_FILE` | Google OAuth | YouTube 자동 업로드 | [Google Cloud Console](https://console.cloud.google.com/) → YouTube Data API v3 활성화 → OAuth 클라이언트 ID | 무료 (할당량 제한) |

#### 키가 필요 없는 것

| 항목 | 설명 |
|------|------|
| 주가 시세 (`yfinance`) | `script_writer`의 시세 조회 — 무료, 키 없음 |
| 차트 이미지 | TradingView / Yahoo Finance 캡처 후 업로드 |
| 영상 합성·자막 | 로컬 MoviePy + FFmpeg |
| 샘플 테스트 | `python test_pipeline.py` — 전부 Mock |

### .env 설정 예시

```bash
# 최소 구성 (OpenAI만 사용)
OPENAI_API_KEY=sk-proj-xxxxxxxx

# 이미지까지 자동 수집하려면 추가
PEXELS_API_KEY=xxxxxxxx

# Pexels 폴백
PIXABAY_API_KEY=xxxxxxxx
```

설정 후 `streamlit run app.py`를 실행하면 `.env`가 자동 로드됨 (`python-dotenv`).

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

**2. (Optional) Test without API keys**

```bash
python test_pipeline.py
# Output: output/test_final.mp4
```

Uses mock data for translation/TTS/scene planning; video composition and subtitles use real modules. No narration audio (silent WAV). No API keys required.

**3. Set up API keys (for full AI features)**
```bash
cp config/.env.example .env
# Open .env and fill in the keys you need
```

**4. Run the app**
```bash
streamlit run app.py
```

**5. Workflow**

① Paste your Korean script in the **Script** tab  
② Run translation in the **Translate** tab  
③ Auto-generate scenes and attach chart images in the **Scenes** tab  
④ Generate and download the finished MP4 in the **Generate** tab  

### What Are API Keys? Why Do I Need Them?

This project calls **external AI and media services**. Each service requires an **API key** (authentication token) tied to your account.

| Pipeline step | What it does | Why a key is needed |
|---------------|--------------|---------------------|
| Translation | Korean → Japanese | LLM API (OpenAI / Gemini / Claude) |
| Scene planning | Split script into scenes | LLM decides visual type per scene |
| Asset collection | Photos & clips per scene | Pexels / Pixabay search API |
| TTS | Japanese narration | Speech synthesis API |
| Charts | Stock chart images | **No key** — upload your own screenshots |
| Video assembly | MP4 output | **No key** — local MoviePy + FFmpeg |

Run `python test_pipeline.py` to verify the video pipeline without any keys.  
The Streamlit UI requires **at least one LLM key** for translation and scene planning.

### Required vs Optional

| Tier | Key | If missing |
|------|-----|------------|
| **Required (full UI)** | One LLM key (OpenAI / Gemini / Claude) | Translation & scene planning won't work |
| **Recommended** | `OPENAI_API_KEY` | One key covers both LLM and TTS when using OpenAI |
| **Recommended** | `PEXELS_API_KEY` | No background images for non-chart scenes |
| **Optional** | `PIXABAY_API_KEY` | Fallback when Pexels fails |
| **Optional** | Azure / Google / ElevenLabs TTS | Alternative voice engines |
| **Optional** | `ALPHA_VANTAGE_KEY` | News fetch & auto script generation |
| **Optional** | YouTube OAuth | Auto upload in the YouTube tab |

### How to Get API Keys

Store values in `.env` (never commit this file). See `config/.env.example` for variable names.

| Variable | Service | Purpose | Get it at | Cost |
|----------|---------|---------|-----------|------|
| `OPENAI_API_KEY` | OpenAI | Translation, scene planning, TTS | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | Paid |
| `GEMINI_API_KEY` | Gemini | Alternative LLM | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | Free tier |
| `ANTHROPIC_API_KEY` | Claude | Alternative LLM | [console.anthropic.com](https://console.anthropic.com/) | Paid |
| `PEXELS_API_KEY` | Pexels | Stock images & video | [pexels.com/api](https://www.pexels.com/api/) | Free |
| `PIXABAY_API_KEY` | Pixabay | Image fallback | [pixabay.com/api/docs](https://pixabay.com/api/docs/) | Free |
| `AZURE_SPEECH_KEY` | Azure Speech | TTS (optional) | [Azure AI Speech](https://azure.microsoft.com/products/ai-services/text-to-speech) | Free tier |
| `GOOGLE_APPLICATION_CREDENTIALS` | Google Cloud TTS | TTS (optional) | [Cloud TTS](https://cloud.google.com/text-to-speech) | Free tier |
| `ELEVENLABS_API_KEY` | ElevenLabs | TTS (optional) | [elevenlabs.io](https://elevenlabs.io/) | Free tier |
| `ALPHA_VANTAGE_KEY` | Alpha Vantage | News headlines (optional) | [alphavantage.co/support](https://www.alphavantage.co/support/#api-key) | Free (rate limited) |
| `YOUTUBE_CLIENT_SECRETS_FILE` | Google OAuth | YouTube upload (optional) | [Google Cloud Console](https://console.cloud.google.com/) | Free (quota limits) |

**No key needed:** stock quotes via `yfinance`, chart uploads, video composition, `test_pipeline.py`.

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

**2.（任意）API キーなしでサンプル動画テスト**

```bash
python test_pipeline.py
# 出力: output/test_final.mp4
```

翻訳・TTS・シーン計画はモックデータを使用。動画合成と字幕は実際のモジュールで動作。API キー不要。

**3. API キーを設定（AI 機能を使う場合）**
```bash
cp config/.env.example .env
# .env ファイルを開いて必要なキーを入力
```

**4. アプリを起動**
```bash
streamlit run app.py
```

**5. 使い方の流れ**

① **スクリプト入力** タブで韓国語スクリプトを貼り付け  
② **翻訳** タブで日本語翻訳を実行  
③ **シーン計画** タブで自動生成 ＋ チャート画像を添付  
④ **動画生成** タブで MP4 を完成・ダウンロード  

### API キーとは？なぜ必要？

このプロジェクトは**外部 AI・メディアサービス**を呼び出して動画を生成します。  
各サービスはアカウントで **API キー**（認証文字列）を発行する必要があります。

| パイプライン段階 | 処理内容 | キーが必要な理由 |
|-----------------|----------|-----------------|
| 翻訳 | 韓国語 → 日本語 | LLM API（OpenAI / Gemini / Claude） |
| シーン計画 | スクリプトをシーン分割 | LLM がビジュアルタイプを決定 |
| 素材収集 | シーン用の写真・映像 | Pexels / Pixabay 検索 API |
| TTS | 日本語ナレーション | 音声合成 API |
| チャート | 株価チャート画像 | **キー不要** — キャプチャ画像をアップロード |
| 動画合成・字幕 | MP4 出力 | **キー不要** — ローカル MoviePy + FFmpeg |

`python test_pipeline.py` でキーなしの動画合成テストが可能。  
Streamlit UI の翻訳・シーン自動生成には **LLM キーを 1 つ以上**必要。

### 必須 vs 任意

| 区分 | キー | ない場合 |
|------|------|----------|
| **必須（UI 全体）** | LLM 1 つ（OpenAI / Gemini / Claude） | 翻訳・シーン計画不可 |
| **推奨** | `OPENAI_API_KEY` | 1 キーで翻訳 + TTS 可能 |
| **推奨** | `PEXELS_API_KEY` | チャート以外の背景画像なし |
| **任意** | `PIXABAY_API_KEY` | Pexels 失敗時のフォールバック |
| **任意** | Azure / Google / ElevenLabs TTS | 別の音声エンジン |
| **任意** | `ALPHA_VANTAGE_KEY` | ニュース・スクリプト自動生成 |
| **任意** | YouTube OAuth | YouTube 自動アップロード |

### API キーの取得方法

`.env` に保存（Git にコミットしない）。変数名は `config/.env.example` を参照。

| 変数名 | サービス | 用途 | 取得先 | 料金 |
|--------|----------|------|--------|------|
| `OPENAI_API_KEY` | OpenAI | 翻訳・シーン計画・TTS | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | 有料 |
| `GEMINI_API_KEY` | Gemini | 代替 LLM | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | 無料枠あり |
| `ANTHROPIC_API_KEY` | Claude | 代替 LLM | [console.anthropic.com](https://console.anthropic.com/) | 有料 |
| `PEXELS_API_KEY` | Pexels | ストック画像・映像 | [pexels.com/api](https://www.pexels.com/api/) | 無料 |
| `PIXABAY_API_KEY` | Pixabay | 画像フォールバック | [pixabay.com/api/docs](https://pixabay.com/api/docs/) | 無料 |
| `ALPHA_VANTAGE_KEY` | Alpha Vantage | ニュース収集（任意） | [alphavantage.co/support](https://www.alphavantage.co/support/#api-key) | 無料（制限あり） |
| `YOUTUBE_CLIENT_SECRETS_FILE` | Google OAuth | YouTube アップロード（任意） | [Google Cloud Console](https://console.cloud.google.com/) | 無料（枠あり） |

**キー不要:** `yfinance` 株価、`test_pipeline.py`、チャートアップロード、動画合成。

---

## Project Structure

```
traderx-youtube/
├── app.py                  # Streamlit UI
├── test_pipeline.py        # API-key-free sample video test
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
│   ├── pipeline.py         # End-to-end orchestration
│   ├── news_fetcher.py     # Alpha Vantage news (optional)
│   ├── script_writer.py    # Auto script from market data (optional)
│   └── thumbnail_generator.py # Thumbnail images (optional)
├── tests/                  # Unit tests (python -m unittest discover -s tests)
└── docs/                   # Module documentation
```

## License

MIT
