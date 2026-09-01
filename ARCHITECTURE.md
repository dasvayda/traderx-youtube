# ARCHITECTURE.md
# AI-Powered Automated YouTube Shorts Generator — System Architecture

## Overview

This application transforms Korean stock market scripts into complete YouTube Shorts videos
targeting Japanese audiences. The pipeline covers translation, scene planning, visual asset
retrieval, chart generation, TTS narration, subtitle burning, and final video composition.

```
Korean Script → Translation → Scene Planning → Asset Collection → Video Composition → MP4
```

---

## Directory Structure

```
traderx-youtube/
│
├── app.py                        # Streamlit UI entry point
├── ARCHITECTURE.md               # This file
├── README.md                     # Setup & usage guide
├── requirements.txt
│
├── config/
│   ├── settings.yaml             # Global configuration
│   └── .env.example              # Environment variable template
│
├── scripts/                      # Raw input scripts (.txt / .md)
├── translations/                 # Korean + Japanese script pairs (JSON)
├── assets/
│   ├── charts/                   # Generated stock chart images
│   ├── images/                   # Downloaded company / news images
│   ├── videos/                   # Stock footage clips
│   └── audio/                    # TTS narration + BGM files
├── cache/                        # HTTP response cache, asset metadata
├── output/                       # Final rendered MP4 files
├── examples/                     # Example scripts, scene JSON, flow diagrams
│
├── modules/
│   ├── __init__.py
│   ├── translator.py             # Korean → Japanese LLM translation
│   ├── script_parser.py          # Scene segmentation & JSON output
│   ├── scene_generator.py        # LLM-driven scene planning
│   ├── asset_manager.py          # Asset search, download, caching
│   ├── chart_generator.py        # 사용자 업로드 차트 이미지 레지스트리
│   ├── tts_engine.py             # Pluggable TTS (OpenAI / Azure / Google / ElevenLabs)
│   ├── subtitle_generator.py     # Subtitle timing, style, ASS/SRT generation
│   ├── video_composer.py         # MoviePy video assembly engine
│   ├── bgm_manager.py            # Background music mixing & ducking
│   └── pipeline.py               # Orchestrates full end-to-end job
│
└── docs/
    ├── 01_translator.md
    ├── 02_script_parser.md
    ├── 03_scene_generator.md
    ├── 04_asset_manager.md
    ├── 05_chart_generator.md
    ├── 06_tts_engine.md
    ├── 07_subtitle_generator.md
    ├── 08_video_composer.md
    ├── 09_bgm_manager.md
    └── 10_pipeline.md
```

---

## Component Documentation Index

| # | Document | Module | Responsibility |
|---|----------|--------|----------------|
| 1 | [Translator](docs/01_translator.md) | `translator.py` | Korean → Japanese LLM translation with financial term preservation |
| 2 | [Script Parser](docs/02_script_parser.md) | `script_parser.py` | Raw text → scene list with narration, subtitle, visual hints |
| 3 | [Scene Generator](docs/03_scene_generator.md) | `scene_generator.py` | LLM-powered scene enrichment — duration, visual type, search queries |
| 4 | [Asset Manager](docs/04_asset_manager.md) | `asset_manager.py` | Multi-source image/video search, download, local cache management |
| 5 | [Chart Images](docs/05_chart_generator.md) | `chart_generator.py` | 사용자 업로드 차트 이미지 레지스트리 (자동 생성 없음) |
| 6 | [TTS Engine](docs/06_tts_engine.md) | `tts_engine.py` | Pluggable provider abstraction for Japanese neural TTS |
| 7 | [Subtitle Generator](docs/07_subtitle_generator.md) | `subtitle_generator.py` | ASS/SRT creation, style control, burn-in via FFmpeg |
| 8 | [Video Composer](docs/08_video_composer.md) | `video_composer.py` | MoviePy assembly: Ken Burns, transitions, subtitle overlay, audio mix |
| 9 | [BGM Manager](docs/09_bgm_manager.md) | `bgm_manager.py` | Royalty-free BGM looping, volume ducking during narration |
| 10 | [Pipeline](docs/10_pipeline.md) | `pipeline.py` | End-to-end job orchestration, queue, progress tracking, resume |

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                          app.py (Streamlit UI)                  │
│  Script Input ──► Edit ──► Run ──► Progress ──► Preview/Download│
└──────────────────────────────┬──────────────────────────────────┘
                               │  Job(script_text, config)
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                         pipeline.py                              │
│                                                                  │
│  1. translator.py   ──► Japanese script                          │
│  2. scene_generator.py ► List[SceneDefinition] (JSON)           │
│  3. asset_manager.py   ► Per-scene visual asset (path)          │
│     └─ chart_generator.py  (사용자 업로드 이미지 레지스트리 조회)   │
│  4. tts_engine.py      ► Per-scene audio file                   │
│  5. subtitle_generator.py ► .ass subtitle file                  │
│  6. video_composer.py  ► Assembled clip per scene               │
│  7. bgm_manager.py     ► BGM mixed                              │
│  8. video_composer.py  ► Final 1080×1920 MP4                    │
└──────────────────────────────────────────────────────────────────┘
```

---

## Scene Definition Schema

```json
{
  "scene_id": 1,
  "duration": 5.0,
  "narration": "テスラの株価は本日...",
  "subtitle": "テスラ株価 本日...",
  "visual_type": "stock_chart",
  "visual_query": "TSLA stock chart 1 month",
  "ticker": "TSLA",
  "chart_period": "1mo",
  "transition": "fade",
  "annotations": ["Support $180", "Breakout"]
}
```

---

## Configuration Layers

| Layer | File | Scope |
|-------|------|-------|
| Secrets | `.env` | API keys, never committed |
| App config | `config/settings.yaml` | Video format, TTS provider, LLM model |
| Per-job | `Job` dataclass in pipeline | Script path, output name, overrides |

---

## Provider Abstraction Pattern

Both `translator.py` and `tts_engine.py` follow the same pluggable pattern:

```python
class BaseTranslator(ABC):
    @abstractmethod
    def translate(self, text: str) -> str: ...

class OpenAITranslator(BaseTranslator): ...
class GeminiTranslator(BaseTranslator): ...
class ClaudeTranslator(BaseTranslator): ...
```

Switch providers by changing one line in `settings.yaml`.

---

## Video Output Specification

| Property | Value |
|----------|-------|
| Resolution | 1080 × 1920 (9:16) |
| Frame rate | 30 FPS |
| Duration | 30–60 seconds |
| Video codec | H.264 (libx264) |
| Audio codec | AAC 128 kbps |
| Container | MP4 |

---

## Future Extension Points

- **News Ingestion**: add `modules/news_fetcher.py` → feeds `scene_generator.py`
- **Script Auto-generation**: add `modules/script_writer.py` (LLM from market data)
- **Thumbnail**: add `modules/thumbnail_generator.py` (DALL-E / Stable Diffusion)
- **YouTube Upload**: add `modules/youtube_uploader.py` (YouTube Data API v3)
- **Agent Orchestration**: wrap `pipeline.py` as a LangGraph node / CrewAI tool
- **Multi-language**: parameterise `translator.py` target language
