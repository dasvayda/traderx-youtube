# Video Composer Module

**File:** `modules/video_composer.py`

## Responsibility

Assembles per-scene visual clips, narration audio, and optional BGM into a single
1080×1920 MP4 file using MoviePy 2.x.

## 3-Zone Layout (redesigned 2026-09-15)

```
┌─────────────────┐  0 px
│   HEADER ZONE   │  종목명 · 타이틀       HEADER_H    = 400 px
├─────────────────┤  400 px
│                 │
│  CHART / VIDEO  │  letterbox 비주얼      CHART_ZONE_H = 1080 px
│                 │
├─────────────────┤  1480 px
│  SUBTITLE ZONE  │  ASS burn-in 전용      FOOTER_H    = 440 px
└─────────────────┘  1920 px
```

### Colour Palette

| Token | Value (RGB) | Usage |
|-------|-------------|-------|
| `BG_COLOR` | `(18, 18, 30)` | Dark navy background |
| `ACCENT_COLOR` | `(38, 166, 154)` | Teal accent lines / ticker underbar |
| `TEXT_PRIMARY` | `(255, 255, 255)` | Ticker, title text |
| `TEXT_SECONDARY` | `(180, 180, 200)` | Subtitle hint, subheading |

### YouTube Shorts Safe Area

| Edge | Reserved | Reason |
|------|----------|--------|
| Top 15% (288 px) | Do not draw | YouTube search / title UI |
| Bottom 20% (384 px) | Do not draw | Like / subscribe buttons |
| Right 11% (119 px) | 140 px min margin | Reaction button column |

Header text starts at y = 300 px (below the 288 px UI zone).

## Key Classes

### VideoConfig

```python
@dataclass
class VideoConfig:
    width: int = 1080
    height: int = 1920
    fps: int = 30
    codec: str = "libx264"
    audio_codec: str = "aac"
    audio_bitrate: str = "128k"
    crf: int = 23
    preset: str = "medium"
```

### VideoComposer.compose()

```python
def compose(
    self,
    scenes: list[SceneDefinition],
    asset_paths: list[Optional[Path]],
    narration_paths: list[Optional[Path]],
    bgm_path: Optional[Path] = None,
    output_name: str = "output.mp4",
) -> Path:
```

Steps:
1. Build one video clip per scene using `_build_visual()`.
2. Attach narration audio to each clip.
3. Concatenate all clips with `concatenate_videoclips(method="compose")`.
4. Mix BGM on top of the concatenated audio (if provided).
5. Write the final MP4 via `write_videofile()`.

## Scene Clip Builders

### _build_chart_clip() — image scenes

Used when `scene.visual_type` is `stock_chart`, `company_image`, etc.

1. Open the chart image with Pillow.
2. `_letterbox_into_zone(chart_img, 1080, 1080)` — scale with `min(zone_w/img_w, zone_h/img_h)` so the entire chart is visible, centred on `BG_COLOR`.
3. Draw the header zone (`_draw_header()`).
4. Apply **Ken Burns** zoom inside the chart area only: zoom 1.0 → 1.04 over the clip duration.

### _build_footage_clip() — video scenes

Used when the asset is `.mp4`, `.mov`, `.avi`, or `.webm`.

1. Load with `VideoFileClip(audio=False)`.
2. Loop or trim to match `scene.duration`.
3. `vfx.Resize` to fit the 1080×1080 chart zone (letterbox scale).
4. Overlay on the dark canvas with the header drawn.

### _build_title_card() — fallback / title_card scenes

Used when `scene.visual_type == "title_card"` or no asset is available.

- Full-frame branded card with top/bottom ACCENT bars and a centre horizontal rule.
- Ticker name displayed at 140 px font, centred.
- Subtitle hint in 52 px font below the ticker.

## _letterbox_into_zone()

```python
def _letterbox_into_zone(chart_img, zone_w: int, zone_h: int) -> np.ndarray:
    scale = min(zone_w / chart_img.width, zone_h / chart_img.height)
    ...
```

Preserves the full chart without cropping. Letterbox bars are filled with `BG_COLOR`.

## _draw_header()

Draws into the 0–400 px zone:

| y (px) | Content |
|--------|---------|
| 300 | YouTube safe zone boundary |
| 306 | Ticker text — 88 px Meiryo |
| 348–398 | ACCENT underbar below ticker (width = text bbox width) |
| 350 | Subtitle hint — 40 px, first 28 chars |
| 398 | Bottom ACCENT line (3 px, full width) |

If no valid ticker: subtitle text is wrapped at 20 chars/line and centred vertically between 300 px and 400 px.

## Ken Burns Implementation

```python
zoom = 1.0 + 0.04 * (t / duration)   # 1.00 → 1.04
crop_w = int(cw / zoom)
crop_h = int(ch / zoom)
# centre crop, then resize back to (cw, ch)
```

Zoom is constrained to the chart zone only; the header and footer rows are static.
