# Pipeline Module

**File:** `modules/pipeline.py`

## Responsibility

Orchestrates every module end-to-end for a single `Job`, exposing progress callbacks
and JSON-based resume support. Also provides `BatchQueue` for sequential multi-job
processing.

## Key Types

### JobStatus (enum)

```python
class JobStatus(str, Enum):
    PENDING        = "pending"
    TRANSLATING    = "translating"
    PARSING        = "parsing"
    SCENE_PLANNING = "scene_planning"
    ASSET_COLLECTION = "asset_collection"
    TTS            = "tts"
    BGM            = "bgm"
    COMPOSING      = "composing"
    SUBTITLING     = "subtitling"
    COMPLETE       = "complete"
    FAILED         = "failed"
```

### Job (dataclass)

```python
@dataclass
class Job:
    job_id: str
    korean_script: str
    output_name: str = "output.mp4"
    bgm_file: Optional[str] = None
    status: JobStatus = JobStatus.PENDING
    error: Optional[str] = None

    # Populated during processing
    japanese_script: Optional[str] = None
    scenes: list[dict] = ...            # serialised SceneDefinition dicts
    asset_paths: list[Optional[str]] = ...
    narration_paths: list[Optional[str]] = ...
    bgm_prepared_path: Optional[str] = None
    video_path: Optional[str] = None    # raw (no subtitles)
    final_path: Optional[str] = None    # with subtitles
```

JSON round-trip via `job.save(path)` / `Job.load(path)`. `status` is serialised as a
string. `scenes` is a list of `SceneDefinition.to_dict()` dicts.

## Pipeline

### Constructor

```python
pipeline = Pipeline(config: dict, progress_callback: Callable[[Job], None] | None)
```

`config` is the parsed `config/settings.yaml` dict. All module instances are created
once in `__init__` and reused across jobs.

### Pipeline.run()

```python
result_job = pipeline.run(job)
```

Executes steps in order. On any exception, sets `job.status = FAILED` and
`job.error = str(exc)`. The progress callback is called after each status transition.

### Step sequence

| # | Method | Module | Input → Output |
|---|--------|--------|----------------|
| 1 | `_step_translate` | `translator.py` | `korean_script` → `japanese_script` |
| 2 | `_step_parse` | `script_parser.py` | `japanese_script` → `scenes[]` |
| 3 | `_step_scene_plan` | `scene_generator.py` | `scenes[]` → enriched `scenes[]` |
| 4 | `_step_assets` | `asset_manager.py` + `chart_generator.py` | `scenes[]` → `asset_paths[]` |
| 5 | `_step_tts` | `tts_engine.py` | `scenes[].narration` → `narration_paths[]`, updates `scene.duration` |
| 6 | `_step_bgm` | `bgm_manager.py` | `bgm_file` + `narration_windows` → `bgm_prepared_path` |
| 7 | `_step_compose` | `video_composer.py` | assets + narration + BGM → `video_path` |
| 8 | `_step_subtitles` | `subtitle_generator.py` | `video_path` + `scenes` → `final_path` |

BGM step is **skipped** if `job.bgm_file` is not set or the file does not exist.

## BatchQueue

```python
queue = BatchQueue(pipeline, jobs_dir="output/jobs")
queue.submit(job)        # saves job JSON to jobs_dir/{job_id}.json
results = queue.run_all()  # processes all PENDING/non-terminal jobs
```

`run_all()` iterates `.json` files alphabetically. Jobs already in `COMPLETE` or
`FAILED` status are skipped, enabling resume after a partial run.

## Config Loading

```python
config = load_config("config/settings.yaml")
```

Reads `settings.yaml` with PyYAML. Relevant top-level keys used by Pipeline:

| Key | Used by |
|-----|---------|
| `llm.provider` | translator, scene_generator |
| `llm.model` | translator, scene_generator |
| `translation.*` | translator |
| `tts.*` | tts_engine |
| `video.*` | video_composer |
| `bgm.*` | bgm_manager |
| `subtitles.*` | subtitle_generator style |
| `assets.cache_dir` | asset_manager |
| `pipeline.output_dir` | video_composer output dir |

API keys are loaded from `.env` and `config/.env` via `python-dotenv`.

## Resume Pattern

```python
job = Job.load(Path("output/jobs/job_001.json"))
if job.status != JobStatus.COMPLETE:
    job = pipeline.run(job)
```

Currently `run()` always executes all steps from the beginning. Per-step resume
(skipping already-completed steps) is not implemented but can be added by checking
`job.status` at the start of each `_step_*` method.
