# BGM Manager Module

**File:** `modules/bgm_manager.py`

## Responsibility

Prepares a background music track for video composition: loops or trims the audio to
match the total video duration, ducks the volume during narration windows, and applies
fade-in / fade-out before exporting as WAV.

Uses **pydub** for all audio manipulation.

## Key Classes

### BGMConfig

```python
@dataclass
class BGMConfig:
    bgm_path: Path
    video_duration: float       # seconds — target length
    default_volume: float = 0.12   # 0.0–1.0 linear scale
    duck_volume: float = 0.04      # volume during narration
    fade_in: float = 1.0           # seconds
    fade_out: float = 2.0          # seconds
```

### BGMManager

```python
manager = BGMManager(output_dir="assets/audio")
out_wav = manager.prepare(config, narration_windows, output_name="bgm_prepared.wav")
```

`output_dir` is created automatically.

## BGMManager.prepare()

```python
def prepare(
    self,
    config: BGMConfig,
    narration_windows: Optional[list[tuple[float, float]]] = None,
    output_name: str = "bgm_prepared.wav",
) -> Path:
```

Workflow:

1. **Load** — `AudioSegment.from_file(config.bgm_path)` (any format pydub supports).
2. **Loop** — repeat the segment until it exceeds `target_ms` (`_loop_to_length`), then trim with `[:target_ms]`.
3. **Global volume** — apply `default_volume` as a dB offset via `_db_change()`.
4. **Duck** — if `narration_windows` is provided, reduce volume to `duck_volume` inside each window (`_duck()`).
5. **Fade** — `.fade_in(fade_in_ms).fade_out(fade_out_ms)`.
6. **Export** — `.export(out_path, format="wav")`.

Returns the path of the exported WAV.

## Volume Helpers

### _db_change(volume_ratio)

Converts a 0–1 linear ratio to dB:

```python
20 * log10(volume_ratio)   # 0 dB at ratio=1.0, -60 dB near 0
```

Used to compute both the global gain and the per-window duck delta.

### _duck()

```python
def _duck(bgm, windows, duck_vol, base_vol):
    duck_db = _db_change(duck_vol) - _db_change(base_vol)
    ...
```

Splits the audio at window boundaries, lowers each ducked segment by `duck_db` relative
to the global level, then re-joins the segments in order.
Windows are sorted by start time before processing.
No crossfade is applied (hard cut at window edges).

## Usage in Pipeline

`Pipeline._step_bgm()` calls this module:

```python
narration_windows = [(offset_i, offset_i + duration_i) for each scene]
cfg = BGMConfig(
    bgm_path=Path(job.bgm_file),
    video_duration=sum(scene.duration for scene in scenes),
)
bgm_wav = manager.prepare(cfg, narration_windows, output_name=f"bgm_{job.job_id}.wav")
```

The returned WAV is then passed to `VideoComposer.compose(bgm_path=...)` where it is
mixed with the narration audio using MoviePy's `CompositeAudioClip`.

## Default Values

| Setting | Default | Notes |
|---------|---------|-------|
| `default_volume` | 0.12 (12%) | Keeps BGM unobtrusive |
| `duck_volume` | 0.04 (4%) | 3× quieter during speech |
| `fade_in` | 1.0 s | Avoids hard cut at video start |
| `fade_out` | 2.0 s | Smooth end |

## Dependencies

```
pip install pydub
# ffmpeg must be on PATH for non-WAV/MP3 input formats
```
