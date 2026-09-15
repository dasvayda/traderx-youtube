# TraderX — Backlog

ID 형식: `YYYYMMDD-NNN` (생성일 + 당일 순번)

---

## 범례
- `[ ]` 미구현
- `[x]` 구현 완료

---

## 📄 문서 (docs/)

| ID | 상태 | 항목 | 비고 |
|----|------|------|------|
| 20260902-001 | `[x]` | `docs/01_translator.md` | 완료 |
| 20260902-002 | `[x]` | `docs/02_script_parser.md` | 완료 |
| 20260902-003 | `[x]` | `docs/03_scene_generator.md` | 완료 |
| 20260902-004 | `[x]` | `docs/04_asset_manager.md` | 완료 |
| 20260902-005 | `[x]` | `docs/05_chart_generator.md` | 완료 |
| 20260902-006 | `[x]` | `docs/06_tts_engine.md` | 완료 |
| 20260902-007 | `[ ]` | `docs/07_subtitle_generator.md` | `SubtitleStyle` 데이터클래스 (font, size, color, outline), `SubtitleEntry(start_sec, end_sec, text)`, `ASSGenerator.generate(entries, out_path)` — ASS 헤더 + Dialogue 라인 생성, `SRTGenerator.generate()`, `SubtitleBuilder.build(scenes, durations, offsets) → list[SubtitleEntry]`, `burn_subtitles(video, sub, out) → Path` — FFmpeg `subtitles=` 필터 사용; Windows에서 경로 공백 오류 회피를 위해 `cwd=sub_dir`로 실행, Meiryo 폰트 폴백 체인 |
| 20260902-008 | `[ ]` | `docs/08_video_composer.md` | **3-zone 레이아웃** (2026-09-15 재설계): `HEADER_H=400` (0~400px, 종목명+타이틀), `CHART_ZONE_H=1080` (400~1480px, letterbox 차트), `FOOTER_H=440` (1480~1920px, ASS 자막 전용); 색상: `BG_COLOR=(18,18,30)`, `ACCENT_COLOR=(38,166,154)`; `_letterbox_into_zone()` — `min(zone_w/img_w, zone_h/img_h)` 스케일로 전체 차트 보존; Ken Burns: 차트 영역 내 zoom 1.0→1.04; `_draw_header()` — Meiryo 88px 티커 + 40px 부제 + 하단 ACCENT 라인; YouTube Shorts 안전 영역: 상단 15%(288px), 하단 20%(384px), 우측 11%(119px) |
| 20260902-009 | `[ ]` | `docs/09_bgm_manager.md` | `BGMConfig(volume, duck_volume, fade_in, fade_out)`, `BGMManager.prepare(bgm_path, total_duration) → Path` — pydub로 루프 반복 후 원하는 길이로 trim; `duck()` — 나레이션 구간(narration_windows) 동안 볼륨을 `duck_volume`으로 낮추고 전후 crossfade; `fade_in/fade_out` 적용 후 WAV 출력; 기본 볼륨 0.12, 덕킹 시 0.04 |
| 20260902-010 | `[ ]` | `docs/10_pipeline.md` | `Job` 데이터클래스 (`job_id`, `script_ko`, `scenes`, `status`, `created_at`), `JobStatus` 열거형 (`PENDING/RUNNING/DONE/FAILED`), `Pipeline.run(job) → Job` — 단계: translate → parse → scene_gen → asset_fetch → tts → subtitle → compose → bgm_mix; `BatchQueue` — JSON 직렬화로 재시작 지원 (`cache/jobs/{job_id}.json`); `max_workers=3` 병렬 씬 처리 |

---

## 🧩 코어 모듈 (modules/)

| ID | 상태 | 항목 | 비고 |
|----|------|------|------|
| 20260902-011 | `[x]` | `modules/translator.py` | OpenAI / Gemini / Claude 지원 |
| 20260902-012 | `[x]` | `modules/script_parser.py` | 씬 분할 |
| 20260902-013 | `[x]` | `modules/scene_generator.py` | LLM 씬 보강 |
| 20260902-014 | `[x]` | `modules/asset_manager.py` | Pexels / Pixabay 검색 및 캐시 |
| 20260902-015 | `[x]` | `modules/chart_generator.py` | 업로드 이미지 레지스트리 |
| 20260902-016 | `[x]` | `modules/tts_engine.py` | OpenAI / Azure / Google / ElevenLabs |
| 20260902-017 | `[x]` | `modules/subtitle_generator.py` | ASS/SRT + FFmpeg burn-in |
| 20260902-018 | `[x]` | `modules/video_composer.py` | MoviePy 2.x Ken Burns + 조립 |
| 20260902-019 | `[x]` | `modules/bgm_manager.py` | BGM 루프 + 덕킹 |
| 20260902-020 | `[x]` | `modules/pipeline.py` | 전체 파이프라인 오케스트레이션 |

---

## 🖥️ UI

| ID | 상태 | 항목 | 비고 |
|----|------|------|------|
| 20260902-021 | `[x]` | `app.py` — 탭 1: 스크립트 입력 | 완료 |
| 20260902-022 | `[x]` | `app.py` — 탭 2: 번역 | 완료 |
| 20260902-023 | `[x]` | `app.py` — 탭 3: 씬 계획 + 이미지 첨부 | 완료 |
| 20260902-024 | `[x]` | `app.py` — 탭 4: 영상 생성 + 다운로드 | 완료 |
| 20260902-025 | `[x]` | `app.py` — 탭 5: 배치 처리 | 완료 |

---

## 🚀 확장 기능 (Future Extension)

| ID | 상태 | 항목 | 비고 |
|----|------|------|------|
| 20260902-026 | `[x]` | `modules/news_fetcher.py` | Alpha Vantage 뉴스 수집 + JSON 캐시 로드 |
| 20260902-027 | `[x]` | `modules/script_writer.py` | yfinance 시세 + 뉴스 → 한국어 스크립트 (LLM) |
| 20260902-028 | `[x]` | `modules/thumbnail_generator.py` | PIL 텍스트 썸네일 + DALL-E 3 옵션 |
| 20260902-029 | `[x]` | `modules/youtube_uploader.py` | YouTube Data API v3 업로드 자동화 |
| 20260902-030 | `[ ]` | Agent 오케스트레이션 | `pipeline.py`를 LangGraph 노드로 래핑: `NewsNode` (news_fetcher) → `ScriptNode` (script_writer) → `TranslateNode` → `SceneNode` → `PipelineNode` (video 생성); 각 노드는 `AgentState` TypedDict를 공유 상태로 전달; CrewAI 대안: `ResearchAgent`(news) + `WriterAgent`(script) + `ProducerAgent`(pipeline); 의존성: `langgraph>=0.1`, `langchain-openai>=0.1`; 진입점: `modules/agent_orchestrator.py` |
| 20260915-001 | `[x]` | `modules/video_composer.py` 3-zone Shorts 레이아웃 재설계 | letterbox 차트 + 헤더/푸터 영역 분리 (commit 1e6ba11) |
| 20260902-031 | `[x]` | 다국어 지원 | translator 타겟 언어 파라미터화 (ja/en/zh/es/vi) |
| 20260912-001 | `[ ]` | Higgsfield AI 영상 클립 생성 연동 | footage 씬 전용; 무료 티어는 워터마크·크레딧 제한으로 실효성 낮음 → 프로덕션 Starter($19/월) 기준으로 도입 검토 |
| 20260912-002 | `[ ]` | 로컬 Wan 2.2 (1.3B) 폴백 클립 생성 | VRAM 4~6GB 이상 환경에서 무료 로컬 추론; Higgsfield 미인증 또는 크레딧 소진 시 자동 폴백 |
| 20260912-003 | `[ ]` | LTX-Video 2.3 로컬 클립 생성 (고사양) | VRAM 8GB+ 환경; Wan 2.2 대비 속도 우수, 720p 5초 클립 RTX4090 기준 1분 이내 |
