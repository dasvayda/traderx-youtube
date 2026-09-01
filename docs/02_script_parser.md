# Script Parser Module

**File:** `modules/script_parser.py`

## Responsibility

Splits a Japanese script into a list of `SceneDefinition` objects.
Estimates scene duration from character count (~4.5 chars/sec for Japanese TTS).

## Algorithm

1. Split text on double newlines (paragraph = scene).
2. If a paragraph exceeds `MAX_CHARS_PER_SCENE` (120), split further on `。！？`.
3. Merge short sentences into the buffer until the threshold is reached.
4. Assign scene IDs and estimate durations.

## SceneDefinition Schema

```python
@dataclass
class SceneDefinition:
    scene_id: int
    duration: float
    narration: str
    subtitle: str          # ≤ 40 chars
    visual_type: str       # filled later by scene_generator
    visual_query: str      # filled later by scene_generator
    ticker: Optional[str]
    chart_period: str
    transition: str
    annotations: list[str]
```

## Usage

```python
from modules.script_parser import ScriptParser

parser = ScriptParser()
scenes = parser.parse(japanese_text)
parser.save_scenes(scenes, "output/scenes.json")
```

## Persistence

- `save_scenes(scenes, path)` → writes JSON
- `load_scenes(path)` → reads JSON back to `list[SceneDefinition]`
