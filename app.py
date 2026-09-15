"""
app.py — TraderX YouTube Shorts 생성기 (Streamlit UI)

탭 구성:
  1. 스크립트 입력  — 한국어 스크립트 입력 / 파일 로드
  2. 번역           — 한→일 번역 + 수동 편집
  3. 씬 계획        — LLM 씬 분할 + 씬별 이미지 첨부
  4. 영상 생성      — 파이프라인 실행 + 결과 다운로드
  5. 배치           — 다중 파일 일괄 처리
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from pathlib import Path

import streamlit as st
import yaml
from dotenv import load_dotenv

load_dotenv()              # project root .env
load_dotenv("config/.env")  # alternate location

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

st.set_page_config(
    page_title="TraderX — YouTube Shorts 생성기",
    page_icon="📈",
    layout="wide",
)


@st.cache_data
def load_config() -> dict:
    with open("config/settings.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


CFG = load_config()


# ── 세션 상태 초기화 ──────────────────────────────────────────────────────────

def _init_state() -> None:
    defaults = {
        "korean_script": "",
        "japanese_script": "",
        "scenes": [],
        "job_id": str(uuid.uuid4())[:8],
        "bgm_file": None,
        "pipeline_log": [],
        "scene_images": {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


_init_state()


# ── 사이드바 ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("⚙️ 설정")

    st.subheader("LLM 제공자")
    llm_provider = st.selectbox(
        "번역 / 씬 계획에 사용할 LLM",
        ["openai", "gemini", "claude"],
        index=["openai", "gemini", "claude"].index(CFG["llm"]["provider"]),
    )

    st.subheader("번역 언어")
    from modules.translator import SUPPORTED_TARGET_LANGUAGES

    target_lang_options = list(SUPPORTED_TARGET_LANGUAGES.keys())
    default_target = CFG.get("translation", {}).get("target_language", "ja")
    target_language = st.selectbox(
        "번역 대상 언어",
        target_lang_options,
        index=target_lang_options.index(default_target) if default_target in target_lang_options else 0,
        format_func=lambda code: f"{code} — {SUPPORTED_TARGET_LANGUAGES[code]}",
    )

    st.subheader("TTS 제공자")
    tts_provider = st.selectbox(
        "일본어 음성 합성 엔진",
        ["openai", "azure", "google", "elevenlabs"],
        index=["openai", "azure", "google", "elevenlabs"].index(CFG["tts"]["provider"]),
    )

    st.subheader("배경음악 (BGM)")
    bgm_upload = st.file_uploader("BGM 파일 업로드 (mp3 / wav)", type=["mp3", "wav"])
    if bgm_upload:
        bgm_path = Path("assets/audio") / bgm_upload.name
        bgm_path.parent.mkdir(parents=True, exist_ok=True)
        bgm_path.write_bytes(bgm_upload.read())
        st.session_state["bgm_file"] = str(bgm_path)
        st.success(f"BGM 등록: {bgm_upload.name}")

    st.divider()
    st.caption("TraderX v0.1.0")


# ── 탭 ───────────────────────────────────────────────────────────────────────

tab_script, tab_translate, tab_scenes, tab_generate, tab_batch, tab_upload = st.tabs([
    "📝 스크립트 입력",
    "🌐 번역",
    "🎬 씬 계획",
    "▶️ 영상 생성",
    "📦 배치",
    "📤 YouTube 업로드",
])


# ===========================================================================
# 탭 1 — 스크립트 입력
# ===========================================================================

with tab_script:
    st.header("스크립트 입력")
    st.caption("한국어 스크립트를 직접 입력하거나 텍스트 파일을 불러오세요.")

    col_input, col_file = st.columns([3, 1])

    with col_input:
        korean = st.text_area(
            "한국어 스크립트",
            value=st.session_state["korean_script"],
            height=400,
            placeholder="여기에 한국어 스크립트를 입력하세요...",
        )
        if korean != st.session_state["korean_script"]:
            st.session_state["korean_script"] = korean

    with col_file:
        st.subheader("파일 작업")

        uploaded = st.file_uploader("스크립트 파일 불러오기", type=["txt", "md"])
        if uploaded:
            text = uploaded.read().decode("utf-8")
            st.session_state["korean_script"] = text
            st.rerun()

        save_name = st.text_input("저장 파일명", value="script.txt")
        if st.button("💾 저장") and st.session_state["korean_script"]:
            save_path = Path("scripts") / save_name
            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_path.write_text(st.session_state["korean_script"], encoding="utf-8")
            st.success(f"저장 완료: {save_path}")

        st.divider()
        existing = (
            sorted(Path("scripts").glob("*.txt")) + sorted(Path("scripts").glob("*.md"))
            if Path("scripts").exists() else []
        )
        if existing:
            sel = st.selectbox("저장된 스크립트", [p.name for p in existing])
            if st.button("📂 불러오기"):
                content = (Path("scripts") / sel).read_text(encoding="utf-8")
                st.session_state["korean_script"] = content
                st.rerun()

    st.divider()
    char_count = len(st.session_state["korean_script"])
    st.metric("글자 수", char_count)
    if char_count > 0:
        st.info(f"예상 씬 수: 약 {max(1, char_count // 150)}개 (씬당 약 5초)")


# ===========================================================================
# 탭 2 — 번역
# ===========================================================================

with tab_translate:
    target_lang_label = SUPPORTED_TARGET_LANGUAGES.get(target_language, target_language)
    st.header(f"한국어 → {target_lang_label} 번역")
    st.caption("번역 결과는 영상 자막·TTS 음성에 사용됩니다. 생성 후 직접 편집할 수 있습니다.")

    if not st.session_state["korean_script"]:
        st.warning("먼저 스크립트를 입력해 주세요.")
    else:
        col_ko, col_ja = st.columns(2)

        with col_ko:
            st.subheader("🇰🇷 원문 (한국어)")
            st.text_area(
                "",
                value=st.session_state["korean_script"],
                height=400,
                disabled=True,
                key="ko_display",
            )

        with col_ja:
            st.subheader(f"번역문 ({target_lang_label})")

            if st.button("🔄 번역 실행", type="primary"):
                with st.spinner("번역 중..."):
                    try:
                        from modules.translator import create_translator
                        translator = create_translator(
                            provider=llm_provider,
                            model=CFG["llm"]["model"],
                            temperature=CFG["llm"]["temperature"],
                            source_language=CFG.get("translation", {}).get("source_language", "ko"),
                            target_language=target_language,
                        )
                        result = translator.translate(st.session_state["korean_script"])
                        st.session_state["japanese_script"] = result.translated_text
                        st.success("번역 완료!")
                    except Exception as e:
                        st.error(f"번역 오류: {e}")

            japanese = st.text_area(
                "번역 결과 (직접 편집 가능)",
                value=st.session_state["japanese_script"],
                height=350,
                key="japanese_edit",
            )
            if japanese != st.session_state["japanese_script"]:
                st.session_state["japanese_script"] = japanese

        if st.session_state["japanese_script"]:
            trans_path = Path("translations") / f"{st.session_state['job_id']}.json"
            trans_path.parent.mkdir(parents=True, exist_ok=True)
            trans_data = {
                "korean": st.session_state["korean_script"],
                "japanese": st.session_state["japanese_script"],
            }
            if st.button("💾 번역 저장"):
                trans_path.write_text(
                    json.dumps(trans_data, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                st.success(f"저장: {trans_path}")


# ===========================================================================
# 탭 3 — 씬 계획
# ===========================================================================

with tab_scenes:
    st.header("씬 계획")
    st.caption("LLM이 스크립트를 씬으로 분할합니다. 각 씬에 차트·이미지를 직접 첨부하세요.")

    if not st.session_state["japanese_script"]:
        st.warning("먼저 번역을 완료해 주세요.")
    else:
        col_a, col_b = st.columns([1, 2])

        with col_a:
            if st.button("🎬 씬 자동 생성", type="primary"):
                with st.spinner("LLM으로 씬 분석 중..."):
                    try:
                        from modules.script_parser import ScriptParser
                        from modules.scene_generator import create_scene_generator

                        parser = ScriptParser()
                        scenes = parser.parse(st.session_state["japanese_script"])
                        gen = create_scene_generator(
                            provider=llm_provider,
                            model=CFG["llm"]["model"],
                        )
                        enriched = gen.enrich(scenes)
                        st.session_state["scenes"] = [s.to_dict() for s in enriched]
                        st.success(f"{len(enriched)}개 씬 생성 완료!")
                    except Exception as e:
                        st.error(f"씬 생성 오류: {e}")

        with col_b:
            if st.session_state["scenes"]:
                total_dur = sum(s["duration"] for s in st.session_state["scenes"])
                c1, c2 = st.columns(2)
                c1.metric("씬 수", len(st.session_state["scenes"]))
                c2.metric("예상 총 길이", f"{total_dur:.1f}초")

        if st.session_state["scenes"]:
            st.subheader("씬 목록")

            for i, scene in enumerate(st.session_state["scenes"]):
                scene_id = scene["scene_id"]
                has_image = scene_id in st.session_state["scene_images"]
                badge = "🖼️" if has_image else "❌"

                with st.expander(
                    f"씬 {scene_id} {badge} — {scene['visual_type']} ({scene['duration']}s)"
                ):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown("**내레이션 / 자막 (일본어)**")
                        scene["narration"] = st.text_area(
                            "내레이션",
                            value=scene["narration"],
                            key=f"narr_{i}",
                            height=100,
                        )
                        scene["subtitle"] = st.text_input(
                            "자막 (40자 이내)",
                            value=scene["subtitle"],
                            key=f"sub_{i}",
                        )
                        scene["duration"] = st.number_input(
                            "길이 (초)",
                            value=float(scene["duration"]),
                            min_value=1.0,
                            max_value=30.0,
                            step=0.5,
                            key=f"dur_{i}",
                        )

                    with col2:
                        st.markdown("**비주얼 설정**")
                        vtype_options = [
                            "stock_chart", "market_chart", "company_image",
                            "news_image", "footage", "title_card",
                        ]
                        vtype_labels = {
                            "stock_chart": "주식 차트",
                            "market_chart": "시장 차트",
                            "company_image": "기업 이미지",
                            "news_image": "뉴스 화면",
                            "footage": "영상 클립",
                            "title_card": "텍스트 카드",
                        }
                        scene["visual_type"] = st.selectbox(
                            "비주얼 타입",
                            vtype_options,
                            format_func=lambda x: f"{x} ({vtype_labels.get(x, '')})",
                            index=vtype_options.index(scene.get("visual_type", "stock_chart")),
                            key=f"vtype_{i}",
                        )
                        scene["visual_query"] = st.text_input(
                            "검색 키워드 (footage / company_image 용)",
                            value=scene.get("visual_query", ""),
                            key=f"vq_{i}",
                        )
                        scene["transition"] = st.selectbox(
                            "전환 효과",
                            ["fade", "slide", "zoom", "none"],
                            key=f"trans_{i}",
                        )

                    # ── 이미지 첨부 ──────────────────────────────────
                    st.divider()
                    img_col, preview_col = st.columns([2, 1])

                    with img_col:
                        st.markdown("**📎 씬 이미지 첨부** (차트 스크린샷 등)")
                        uploaded_img = st.file_uploader(
                            f"씬 {scene_id} 이미지",
                            type=["png", "jpg", "jpeg", "webp"],
                            key=f"img_upload_{scene_id}",
                            label_visibility="collapsed",
                        )
                        if uploaded_img is not None:
                            img_dir = Path("assets/charts")
                            img_dir.mkdir(parents=True, exist_ok=True)
                            img_path = img_dir / f"scene_{scene_id:02d}_{uploaded_img.name}"
                            img_path.write_bytes(uploaded_img.read())

                            from modules.chart_generator import register_chart
                            register_chart(scene_id, img_path)
                            st.session_state["scene_images"][scene_id] = str(img_path)
                            st.success(f"등록 완료: {img_path.name}")

                        if scene_id in st.session_state["scene_images"]:
                            existing_path = Path(st.session_state["scene_images"][scene_id])
                            st.caption(f"✅ 등록된 이미지: `{existing_path.name}`")
                            if st.button("🗑️ 삭제", key=f"del_img_{scene_id}"):
                                from modules.chart_generator import _chart_registry
                                _chart_registry.pop(scene_id, None)
                                st.session_state["scene_images"].pop(scene_id, None)
                                st.rerun()

                    with preview_col:
                        if scene_id in st.session_state["scene_images"]:
                            p = Path(st.session_state["scene_images"][scene_id])
                            if p.exists():
                                st.image(str(p), caption=f"씬 {scene_id}", use_column_width=True)

            st.session_state["scenes"] = [dict(s) for s in st.session_state["scenes"]]

            # 이미지 첨부 현황
            total = len(st.session_state["scenes"])
            done = len(st.session_state["scene_images"])
            if done < total:
                st.warning(
                    f"⚠️ {total - done}개 씬에 이미지가 없습니다. "
                    "이미지 없는 씬은 텍스트 카드로 대체됩니다."
                )
            else:
                st.success("✅ 모든 씬에 이미지가 설정되었습니다.")

            st.download_button(
                "📥 씬 JSON 다운로드",
                data=json.dumps(st.session_state["scenes"], ensure_ascii=False, indent=2),
                file_name="scenes.json",
                mime="application/json",
            )


# ===========================================================================
# 탭 4 — 영상 생성
# ===========================================================================

with tab_generate:
    st.header("영상 생성")

    ready = bool(st.session_state["japanese_script"]) and bool(st.session_state["scenes"])

    if not ready:
        st.warning("번역과 씬 계획을 먼저 완료해 주세요.")
    else:
        output_name = st.text_input("출력 파일명", value="output.mp4")

        generate_btn = st.button("🎬 영상 생성 시작", type="primary")

        log_placeholder = st.empty()
        progress_bar = st.progress(0)

        if generate_btn:
            st.session_state["pipeline_log"] = []

            STEPS = [
                "asset_collection", "tts", "bgm", "composing", "subtitling",
            ]
            STEP_LABELS = {
                "asset_collection": "비주얼 에셋 수집 중...",
                "tts": "일본어 음성 합성 중...",
                "bgm": "BGM 준비 중...",
                "composing": "영상 조립 중...",
                "subtitling": "자막 삽입 중...",
            }

            def on_progress(job):
                step = job.status.value
                idx = STEPS.index(step) if step in STEPS else 0
                progress_bar.progress((idx + 1) / len(STEPS))
                label = STEP_LABELS.get(step, step)
                st.session_state["pipeline_log"].append(f"✅ {label}")
                log_placeholder.markdown("\n".join(st.session_state["pipeline_log"]))

            with st.spinner("파이프라인 실행 중..."):
                try:
                    from modules.pipeline import Pipeline, Job

                    pipe = Pipeline(CFG, progress_callback=on_progress)
                    job = Job(
                        job_id=st.session_state["job_id"],
                        korean_script=st.session_state["korean_script"],
                        output_name=output_name,
                        bgm_file=st.session_state.get("bgm_file"),
                    )
                    job.japanese_script = st.session_state["japanese_script"]
                    job.scenes = st.session_state["scenes"]

                    job = pipe._step_assets(job)
                    on_progress(job)
                    job = pipe._step_tts(job)
                    on_progress(job)
                    job = pipe._step_bgm(job)
                    on_progress(job)
                    job = pipe._step_compose(job)
                    on_progress(job)
                    job = pipe._step_subtitles(job)
                    on_progress(job)

                    progress_bar.progress(1.0)

                    if job.final_path and Path(job.final_path).exists():
                        st.success("🎉 영상 생성 완료!")
                        video_bytes = Path(job.final_path).read_bytes()
                        st.video(video_bytes)
                        st.download_button(
                            "📥 영상 다운로드",
                            data=video_bytes,
                            file_name=output_name,
                            mime="video/mp4",
                        )
                    else:
                        st.error("영상 파일을 찾을 수 없습니다. 로그를 확인해 주세요.")

                except Exception as e:
                    st.error(f"오류: {e}")
                    import traceback
                    st.code(traceback.format_exc())


# ===========================================================================
# 탭 5 — 배치
# ===========================================================================

with tab_batch:
    st.header("배치 처리")
    st.caption("여러 스크립트 파일을 한 번에 처리합니다.")

    uploaded_batch = st.file_uploader(
        "스크립트 파일 업로드 (여러 개 선택 가능)",
        type=["txt", "md"],
        accept_multiple_files=True,
    )

    if uploaded_batch and st.button("📦 배치 큐에 추가"):
        from modules.pipeline import Pipeline, Job, BatchQueue

        pipe = Pipeline(CFG)
        queue = BatchQueue(pipe)

        for f in uploaded_batch:
            text = f.read().decode("utf-8")
            job = Job(
                job_id=str(uuid.uuid4())[:8],
                korean_script=text,
                output_name=f"{Path(f.name).stem}_output.mp4",
            )
            queue.submit(job)
            st.info(f"추가됨: {f.name} → job {job.job_id}")

        st.success("배치 큐에 추가 완료.")

    st.divider()
    st.subheader("큐 현황")

    jobs_dir = Path("output/jobs")
    if jobs_dir.exists():
        job_files = sorted(jobs_dir.glob("*.json"))
        if job_files:
            from modules.pipeline import Job as PipelineJob

            for jf in job_files:
                try:
                    job = PipelineJob.load(jf)
                    c1, c2, c3 = st.columns([2, 1, 2])
                    with c1:
                        st.text(f"Job: {job.job_id}")
                    with c2:
                        status_icon = {"complete": "🟢", "failed": "🔴", "pending": "⚪"}.get(
                            job.status.value, "🟡"
                        )
                        st.text(f"{status_icon} {job.status.value}")
                    with c3:
                        if job.final_path and Path(job.final_path).exists():
                            st.text(job.final_path)
                except Exception:
                    st.text(f"⚠️ {jf.name} — 읽기 오류")
        else:
            st.info("큐에 작업이 없습니다.")
    else:
        st.info("작업 디렉터리가 없습니다.")

    if st.button("▶️ 배치 실행"):
        from modules.pipeline import Pipeline, BatchQueue

        pipe = Pipeline(CFG)
        queue = BatchQueue(pipe)
        with st.spinner("배치 처리 중..."):
            results = queue.run_all()
        st.success(f"{len(results)}개 작업 완료")
        for r in results:
            if r.status.value == "complete":
                st.success(f"✅ {r.job_id}: {r.final_path}")
            else:
                st.error(f"❌ {r.job_id}: {r.error}")


# ===========================================================================
# 탭 6 — YouTube 업로드
# ===========================================================================

with tab_upload:
    st.header("YouTube 업로드")
    st.caption("생성된 영상을 YouTube Shorts에 업로드합니다.")

    # ── 업로드할 영상 선택 ────────────────────────────────────────────────
    output_dir = Path("output")
    mp4_files = sorted(output_dir.glob("*.mp4")) if output_dir.exists() else []
    mp4_files = [f for f in mp4_files if not f.name.startswith("raw_")]

    if not mp4_files:
        st.warning("업로드할 영상이 없습니다. 먼저 영상을 생성해 주세요.")
    else:
        selected_file = st.selectbox(
            "업로드할 영상 선택",
            mp4_files,
            format_func=lambda p: p.name,
        )

        st.video(str(selected_file))

        st.divider()

        # ── 업로드 방식 선택 ──────────────────────────────────────────────
        upload_mode = st.radio(
            "업로드 방식",
            ["🤖 자동 업로드 (YouTube API)", "📋 수동 업로드 (가이드)"],
            horizontal=True,
        )

        st.divider()

        # ── 공통: 메타데이터 설정 ─────────────────────────────────────────
        st.subheader("영상 정보 설정")

        from modules.youtube_uploader import (
            VideoMetadata, YouTubeUploader,
            build_metadata_from_scenes, manual_upload_guide,
        )

        # 자동 메타데이터 생성
        auto_meta = build_metadata_from_scenes(
            st.session_state.get("scenes", []),
            st.session_state.get("japanese_script", ""),
        )

        col_m1, col_m2 = st.columns([2, 1])
        with col_m1:
            meta_title = st.text_input(
                "제목 (최대 100자)",
                value=auto_meta.title,
                max_chars=100,
            )
            meta_description = st.text_area(
                "설명",
                value=auto_meta.description,
                height=150,
                max_chars=5000,
            )
            meta_tags_raw = st.text_input(
                "태그 (쉼표로 구분)",
                value=", ".join(auto_meta.tags),
            )
        with col_m2:
            meta_privacy = st.selectbox(
                "공개 범위",
                ["private", "unlisted", "public"],
                format_func=lambda x: {
                    "private": "🔒 비공개",
                    "unlisted": "🔗 일부 공개",
                    "public": "🌐 공개",
                }[x],
            )
            meta_category = st.selectbox(
                "카테고리",
                ["25", "22", "28"],
                format_func=lambda x: {
                    "25": "뉴스 & 정치 (25)",
                    "22": "인물 & 블로그 (22)",
                    "28": "과학 & 기술 (28)",
                }[x],
            )

        metadata = VideoMetadata(
            title=meta_title,
            description=meta_description,
            tags=[t.strip() for t in meta_tags_raw.split(",") if t.strip()],
            privacy=meta_privacy,
            category_id=meta_category,
        )

        st.divider()

        # ── 수동 업로드 ───────────────────────────────────────────────────
        if upload_mode.startswith("📋"):
            st.subheader("수동 업로드 가이드")
            guide = manual_upload_guide(selected_file, metadata)
            st.code(guide, language=None)
            st.link_button(
                "🎬 YouTube Studio 열기",
                "https://studio.youtube.com",
                type="primary",
            )

        # ── 자동 업로드 ───────────────────────────────────────────────────
        else:
            st.subheader("자동 업로드 (YouTube API)")

            secrets_file = os.environ.get(
                "YOUTUBE_CLIENT_SECRETS_FILE", "client_secrets.json"
            )
            secrets_exists = Path(secrets_file).exists()

            if not secrets_exists:
                st.error(
                    f"`{secrets_file}` 파일이 없습니다.\n\n"
                    "**설정 방법:**\n"
                    "1. [Google Cloud Console](https://console.cloud.google.com) 접속\n"
                    "2. YouTube Data API v3 활성화\n"
                    "3. OAuth 2.0 클라이언트 ID 생성 → JSON 다운로드\n"
                    "4. 파일을 프로젝트 루트에 `client_secrets.json` 으로 저장"
                )
            else:
                uploader = YouTubeUploader(secrets_file)
                is_auth = uploader.is_authenticated()

                col_auth, col_status = st.columns([1, 2])
                with col_auth:
                    if is_auth:
                        st.success("✅ 인증 완료")
                    else:
                        st.warning("⚠️ 인증 필요")
                        if st.button("🔑 Google 계정 인증", type="primary"):
                            try:
                                uploader.authenticate()
                                st.success("인증 완료! 페이지를 새로고침하세요.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"인증 오류: {e}")

                with col_status:
                    st.caption(
                        "인증 토큰은 `cache/youtube_token.json` 에 저장됩니다.\n"
                        "채널당 최초 1회만 인증하면 이후 자동으로 사용됩니다."
                    )

                if is_auth:
                    st.info(
                        f"📁 **업로드 대상:** `{selected_file.name}`  \n"
                        f"🔒 **공개 범위:** {meta_privacy}  \n"
                        f"📝 **제목:** {meta_title}"
                    )

                    if st.button("🚀 YouTube에 업로드", type="primary", disabled=not is_auth):
                        with st.spinner("업로드 중... 파일 크기에 따라 수 분이 걸릴 수 있습니다."):
                            try:
                                result = uploader.upload(selected_file, metadata)
                                if result.success:
                                    st.success("🎉 업로드 완료!")
                                    st.markdown(f"**YouTube URL:** {result.url}")
                                    st.markdown(f"**Shorts URL:** {result.shorts_url}")
                                    st.link_button("📺 YouTube에서 보기", result.url)
                                else:
                                    st.error(f"업로드 실패: {result.error}")
                            except Exception as e:
                                st.error(f"오류: {e}")
