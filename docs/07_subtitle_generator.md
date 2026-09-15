# Subtitle Generator Module

**File:** `modules/subtitle_generator.py`

## Responsibility

Converts scene narration data into timed subtitle files (.ass / .srt) and burns them into the composed video using FFmpeg.

## Key Classes & Data

| Symbol | Description |
|--------|-------------|
| `SubtitleStyle` | Font, size, colour, outline, shadow, position config |
| `SubtitleEntry` | A single timed subtitle: `start`, `end` (seconds), `text` |
| `ASSGenerator` | Writes an `.ass` file from `list[SubtitleEntry]` |
| `SRTGenerator` | Writes an `.srt` file from `list[SubtitleEntry]` |
| `SubtitleBuilder` | Derives `SubtitleEntry` list from scenes + TTS durations + offsets |
| `burn_subtitles()` | Calls FFmpeg `subtitles=` filter to bake ASS into the video |

### SubtitleStyle defaults

```python
SubtitleStyle(
    font_name  = "NotoSansJP-Bold",   # auto-swapped to Meiryo on Windows
    font_size  = 52,
    primary_color  = "&H00FFFFFF",    # white  (ASS ABGR)
    outline_color  = "&H00000000",    # black
    back_color     = "&H80000000",    # 50% transparent black
    bold      = True,
    outline   = 3,
    shadow    = 1,
    margin_v  = 80,                   # px from bottom
    alignment = 2,                    # numpad 2 = bottom-center
)
```

### SubtitleEntry

```python
@dataclass
class SubtitleEntry:
    start: float   # seconds
    end: float     # seconds
    text: str
```

## Typical Usage

```python
from modules.subtitle_generator import (
    ASSGenerator, SRTGenerator, SubtitleBuilder, burn_subtitles
)

builder = SubtitleBuilder()
entries = builder.build(scenes, tts_durations, time_offsets)

ass_gen = ASSGenerator()
ass_path = ass_gen.generate(entries, Path("output/subs.ass"))

# optional SRT
srt_gen = SRTGenerator()
srt_gen.generate(entries, Path("output/subs.srt"))

final = burn_subtitles(
    input_video  = Path("output/raw_video.mp4"),
    subtitle_file = ass_path,
    output_video  = Path("output/final.mp4"),
)
```

## SubtitleBuilder.build()

```python
def build(
    self,
    scenes: list[SceneDefinition],
    tts_durations: list[float],
    time_offsets: list[float],
) -> list[SubtitleEntry]:
```

- Each scene produces one entry spanning `offset` → `offset + duration - 0.1s` (0.1 s gap prevents overlap).
- `scene.subtitle` is used as the display text.

## ASSGenerator.generate()

Produces a standard ASS v4.00+ file:

1. **Script Info** — `PlayResX: 1080`, `PlayResY: 1920`
2. **V4+ Styles** — single `Default` style from `SubtitleStyle`
3. **Events** — one `Dialogue` line per `SubtitleEntry`

Timestamp format: `H:MM:SS.cs` (centiseconds).
ASS special characters (`{`, `}`) are escaped automatically.

## burn_subtitles()

```python
def burn_subtitles(
    input_video: Path,
    subtitle_file: Path,
    output_video: Path,
    ffmpeg_bin: str = "",
) -> Path:
```

FFmpeg binary search order: `ffmpeg_bin` argument → PATH → `imageio_ffmpeg` bundle.

**Windows path workaround:** FFmpeg's `subtitles=` filter misparses Windows drive letters (e.g. `C:`).
Solution: the function runs FFmpeg with `cwd=subtitle_file.parent` and passes only the **filename** (not the full path) to the filter.
The `.ass` file is also patched in-place to replace `NotoSansJP-Bold` with `Meiryo` before the subprocess call.

FFmpeg encode settings: `-c:v libx264 -crf 23 -preset medium -c:a copy`

## Meiryo Font Fallback Chain

`_load_font()` in `video_composer.py` tries these paths in order:

1. `C:/Windows/Fonts/meiryo.ttc`
2. `C:/Windows/Fonts/YuGothB.ttc`
3. `C:/Windows/Fonts/msgothic.ttc`
4. `C:/Windows/Fonts/arial.ttf`
5. `ImageFont.load_default()`

The same chain is applied in `burn_subtitles` for the ASS file's font field.
