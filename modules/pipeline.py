"""
pipeline.py — End-to-end job orchestration.

Coordinates all modules in sequence:
  1. Translate Korean script → Japanese
  2. Parse Japanese text → scenes
  3. Enrich scenes with LLM visual metadata
  4. Generate/download visual assets per scene
  5. Synthesize TTS narration per scene
  6. Prepare BGM
  7. Compose video
  8. Burn subtitles

Jobs are represented as dataclasses and can be serialised for resume support.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

import yaml
from dotenv import load_dotenv

from modules.translator import create_translator, TranslationResult
from modules.script_parser import ScriptParser, SceneDefinition
from modules.scene_generator import create_scene_generator
from modules.chart_generator import get_chart   # 사용자 업로드 차트 레지스트리
from modules.asset_manager import AssetManager
from modules.tts_engine import create_tts_engine
from modules.subtitle_generator import (
    ASSGenerator, SubtitleBuilder, SubtitleStyle, burn_subtitles
)
from modules.bgm_manager import BGMManager, BGMConfig
from modules.video_composer import VideoComposer, VideoConfig

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Job status
# ---------------------------------------------------------------------------

class JobStatus(str, Enum):
    PENDING = "pending"
    TRANSLATING = "translating"
    PARSING = "parsing"
    SCENE_PLANNING = "scene_planning"
    ASSET_COLLECTION = "asset_collection"
    TTS = "tts"
    BGM = "bgm"
    COMPOSING = "composing"
    SUBTITLING = "subtitling"
    COMPLETE = "complete"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Job dataclass
# ---------------------------------------------------------------------------

@dataclass
class Job:
    job_id: str
    korean_script: str
    output_name: str = "output.mp4"
    bgm_file: Optional[str] = None    # path to BGM audio file
    status: JobStatus = JobStatus.PENDING
    error: Optional[str] = None

    # Populated during processing
    japanese_script: Optional[str] = None
    scenes: list[dict] = field(default_factory=list)   # serialised SceneDefinitions
    asset_paths: list[Optional[str]] = field(default_factory=list)
    narration_paths: list[Optional[str]] = field(default_factory=list)
    bgm_prepared_path: Optional[str] = None
    video_path: Optional[str] = None
    final_path: Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "Job":
        data = dict(data)
        data["status"] = JobStatus(data["status"])
        return cls(**data)

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
                        encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "Job":
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

def load_config(config_path: str = "config/settings.yaml") -> dict:
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class Pipeline:
    """
    Orchestrates all modules for a single Job.

    Usage::

        pipeline = Pipeline(config)
        job = Job(job_id="job_001", korean_script="...", output_name="video.mp4")
        result_job = pipeline.run(job)
    """

    def __init__(
        self,
        config: dict,
        progress_callback: Optional[Callable[[Job], None]] = None,
    ):
        self._cfg = config
        self._cb = progress_callback or (lambda j: None)

        load_dotenv()
        load_dotenv("config/.env")

        # ── Module instances ─────────────────────────────────────────
        llm_cfg = config.get("llm", {})
        trans_cfg = config.get("translation", {})
        tts_cfg = config.get("tts", {})
        video_cfg = config.get("video", {})
        bgm_cfg_dict = config.get("bgm", {})
        assets_cfg = config.get("assets", {})

        self._translator = create_translator(
            provider=llm_cfg.get("provider", "openai"),
            model=llm_cfg.get("model", "gpt-4o"),
            temperature=llm_cfg.get("temperature", 0.3),
            source_language=trans_cfg.get("source_language", "ko"),
            target_language=trans_cfg.get("target_language", "ja"),
        )
        self._parser = ScriptParser()
        self._scene_gen = create_scene_generator(
            provider=llm_cfg.get("provider", "openai"),
            model=llm_cfg.get("model", "gpt-4o"),
        )
        self._asset_mgr = AssetManager(
            pexels_api_key=os.environ.get("PEXELS_API_KEY", ""),
            pixabay_api_key=os.environ.get("PIXABAY_API_KEY", ""),
            cache_dir=assets_cfg.get("cache_dir", "cache"),
        )

        tts_provider = tts_cfg.get("provider", "openai")
        tts_kwargs: dict = {}
        if tts_provider == "openai":
            tts_kwargs = {
                "voice": tts_cfg.get("openai_voice", "shimmer"),
                "model": tts_cfg.get("openai_model", "tts-1-hd"),
            }
        elif tts_provider == "azure":
            tts_kwargs = {
                "voice": tts_cfg.get("azure_voice", "ja-JP-NanamiNeural"),
                "region": tts_cfg.get("azure_region", "japaneast"),
            }
        elif tts_provider == "xtts":
            tts_kwargs = {
                "speaker_wav": tts_cfg.get("xtts_speaker_wav", "samples/speaker.wav"),
                "language": tts_cfg.get("xtts_language", "ja"),
                "device": tts_cfg.get("xtts_device", ""),
            }
        self._tts = create_tts_engine(provider=tts_provider, **tts_kwargs)

        sub_style = SubtitleStyle(
            font_name=config.get("subtitles", {}).get("font", "NotoSansJP-Bold"),
            font_size=config.get("subtitles", {}).get("font_size", 52),
        )
        self._sub_builder = SubtitleBuilder()
        self._ass_gen = ASSGenerator(
            style=sub_style,
            video_width=video_cfg.get("width", 1080),
            video_height=video_cfg.get("height", 1920),
        )
        self._bgm_mgr = BGMManager(output_dir="assets/audio")
        self._composer = VideoComposer(
            config=VideoConfig(
                width=video_cfg.get("width", 1080),
                height=video_cfg.get("height", 1920),
                fps=video_cfg.get("fps", 30),
                codec=video_cfg.get("codec", "libx264"),
                crf=video_cfg.get("crf", 23),
                preset=video_cfg.get("preset", "medium"),
            ),
            output_dir=config.get("pipeline", {}).get("output_dir", "output"),
        )

        self._bgm_defaults = bgm_cfg_dict

    # ------------------------------------------------------------------

    def run(self, job: Job) -> Job:
        """Execute the full pipeline for a job. Returns the updated job."""
        try:
            job = self._step_translate(job)
            job = self._step_parse(job)
            job = self._step_scene_plan(job)
            job = self._step_assets(job)
            job = self._step_tts(job)
            job = self._step_bgm(job)
            job = self._step_compose(job)
            job = self._step_subtitles(job)
            job.status = JobStatus.COMPLETE
            logger.info("Job %s complete: %s", job.job_id, job.final_path)
        except Exception as exc:
            logger.exception("Job %s failed: %s", job.job_id, exc)
            job.status = JobStatus.FAILED
            job.error = str(exc)

        self._cb(job)
        return job

    # ------------------------------------------------------------------
    # Steps

    def _step_translate(self, job: Job) -> Job:
        job.status = JobStatus.TRANSLATING
        self._cb(job)
        result: TranslationResult = self._translator.translate(job.korean_script)
        job.japanese_script = result.translated_japanese
        return job

    def _step_parse(self, job: Job) -> Job:
        job.status = JobStatus.PARSING
        self._cb(job)
        scenes = self._parser.parse(job.japanese_script)
        job.scenes = [s.to_dict() for s in scenes]
        return job

    def _step_scene_plan(self, job: Job) -> Job:
        job.status = JobStatus.SCENE_PLANNING
        self._cb(job)
        scenes = [SceneDefinition.from_dict(d) for d in job.scenes]
        enriched = self._scene_gen.enrich(scenes)
        job.scenes = [s.to_dict() for s in enriched]
        return job

    def _step_assets(self, job: Job) -> Job:
        job.status = JobStatus.ASSET_COLLECTION
        self._cb(job)
        scenes = [SceneDefinition.from_dict(d) for d in job.scenes]
        paths: list[Optional[str]] = []

        for scene in scenes:
            path: Optional[Path] = None

            # 사용자가 업로드한 차트 이미지를 우선 사용
            uploaded_chart = get_chart(scene.scene_id)
            if uploaded_chart:
                path = uploaded_chart
                logger.info("Scene %d: using uploaded chart image %s", scene.scene_id, path)
            elif scene.visual_type not in ("stock_chart", "market_chart"):
                # 차트 외 타입은 외부 에셋 검색
                path = self._asset_mgr.get_asset_for_scene(scene)
            else:
                # stock_chart 인데 업로드된 이미지가 없으면 None → title_card 폴백
                logger.warning(
                    "Scene %d: visual_type=%s but no chart image uploaded; will use title card",
                    scene.scene_id, scene.visual_type,
                )

            paths.append(str(path) if path else None)

        job.asset_paths = paths
        return job

    def _step_tts(self, job: Job) -> Job:
        job.status = JobStatus.TTS
        self._cb(job)
        scenes = [SceneDefinition.from_dict(d) for d in job.scenes]
        narr_paths: list[Optional[str]] = []

        for i, scene in enumerate(scenes):
            out_path = Path("assets/audio") / f"narration_{job.job_id}_scene{i+1:02d}.mp3"
            try:
                result = self._tts.synthesize(scene.narration, out_path)
                # Update scene duration to match actual audio length
                scene.duration = round(result.duration_seconds + 0.5, 1)
                narr_paths.append(str(result.audio_path))
            except Exception as exc:
                logger.warning("TTS failed for scene %d: %s", scene.scene_id, exc)
                narr_paths.append(None)

        job.scenes = [s.to_dict() for s in scenes]
        job.narration_paths = narr_paths
        return job

    def _step_bgm(self, job: Job) -> Job:
        if not job.bgm_file or not Path(job.bgm_file).exists():
            logger.info("No BGM file specified; skipping BGM step")
            return job

        job.status = JobStatus.BGM
        self._cb(job)

        scenes = [SceneDefinition.from_dict(d) for d in job.scenes]
        total_duration = sum(s.duration for s in scenes)

        # Narration windows for ducking
        offset = 0.0
        windows: list[tuple[float, float]] = []
        for s in scenes:
            windows.append((offset, offset + s.duration))
            offset += s.duration

        cfg = BGMConfig(
            bgm_path=Path(job.bgm_file),
            video_duration=total_duration,
            default_volume=self._bgm_defaults.get("default_volume", 0.12),
            duck_volume=self._bgm_defaults.get("duck_volume", 0.04),
            fade_in=self._bgm_defaults.get("fade_in", 1.0),
            fade_out=self._bgm_defaults.get("fade_out", 2.0),
        )
        bgm_path = self._bgm_mgr.prepare(cfg, narration_windows=windows,
                                          output_name=f"bgm_{job.job_id}.wav")
        job.bgm_prepared_path = str(bgm_path)
        return job

    def _step_compose(self, job: Job) -> Job:
        job.status = JobStatus.COMPOSING
        self._cb(job)

        scenes = [SceneDefinition.from_dict(d) for d in job.scenes]
        asset_paths = [Path(p) if p else None for p in job.asset_paths]
        narr_paths = [Path(p) if p else None for p in job.narration_paths]
        bgm_path = Path(job.bgm_prepared_path) if job.bgm_prepared_path else None

        raw_video = self._composer.compose(
            scenes=scenes,
            asset_paths=asset_paths,
            narration_paths=narr_paths,
            bgm_path=bgm_path,
            output_name=f"raw_{job.output_name}",
        )
        job.video_path = str(raw_video)
        return job

    def _step_subtitles(self, job: Job) -> Job:
        job.status = JobStatus.SUBTITLING
        self._cb(job)

        scenes = [SceneDefinition.from_dict(d) for d in job.scenes]

        # Compute time offsets
        offsets: list[float] = []
        t = 0.0
        for s in scenes:
            offsets.append(t)
            t += s.duration

        durations = [s.duration for s in scenes]
        entries = self._sub_builder.build(scenes, durations, offsets)

        sub_path = Path("output") / f"subtitles_{job.job_id}.ass"
        self._ass_gen.generate(entries, sub_path)

        final_path = Path("output") / job.output_name
        burn_subtitles(
            input_video=Path(job.video_path),
            subtitle_file=sub_path,
            output_video=final_path,
        )
        job.final_path = str(final_path)
        return job


# ---------------------------------------------------------------------------
# Batch Queue
# ---------------------------------------------------------------------------

class BatchQueue:
    """Simple sequential batch processor with progress logging."""

    def __init__(self, pipeline: Pipeline, jobs_dir: str | Path = "output/jobs"):
        self._pipeline = pipeline
        self._jobs_dir = Path(jobs_dir)
        self._jobs_dir.mkdir(parents=True, exist_ok=True)

    def submit(self, job: Job) -> None:
        job_file = self._jobs_dir / f"{job.job_id}.json"
        job.save(job_file)
        logger.info("Job submitted: %s", job.job_id)

    def run_all(self) -> list[Job]:
        job_files = sorted(self._jobs_dir.glob("*.json"))
        results: list[Job] = []

        for jf in job_files:
            job = Job.load(jf)
            if job.status in (JobStatus.COMPLETE, JobStatus.FAILED):
                continue
            logger.info("Processing job: %s", job.job_id)
            job = self._pipeline.run(job)
            job.save(jf)
            results.append(job)

        return results
