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
| 20260902-004 | `[ ]` | `docs/04_asset_manager.md` | 파일 없음 |
| 20260902-005 | `[x]` | `docs/05_chart_generator.md` | 완료 |
| 20260902-006 | `[ ]` | `docs/06_tts_engine.md` | 파일 없음 |
| 20260902-007 | `[ ]` | `docs/07_subtitle_generator.md` | 파일 없음 |
| 20260902-008 | `[ ]` | `docs/08_video_composer.md` | 파일 없음 |
| 20260902-009 | `[ ]` | `docs/09_bgm_manager.md` | 파일 없음 |
| 20260902-010 | `[ ]` | `docs/10_pipeline.md` | 파일 없음 |

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
| 20260902-026 | `[ ]` | `modules/news_fetcher.py` | 뉴스 자동 수집 → scene_generator 연동 |
| 20260902-027 | `[ ]` | `modules/script_writer.py` | 시장 데이터 → 스크립트 자동 생성 (LLM) |
| 20260902-028 | `[ ]` | `modules/thumbnail_generator.py` | 썸네일 생성 (DALL-E / Stable Diffusion) |
| 20260902-029 | `[x]` | `modules/youtube_uploader.py` | YouTube Data API v3 업로드 자동화 |
| 20260902-030 | `[ ]` | Agent 오케스트레이션 | pipeline을 LangGraph / CrewAI 노드로 래핑 |
| 20260902-031 | `[ ]` | 다국어 지원 | translator 타겟 언어 파라미터화 (현재 ja 고정) |
