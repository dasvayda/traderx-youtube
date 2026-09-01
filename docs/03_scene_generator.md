# Scene Generator Module

**File:** `modules/scene_generator.py`

## Responsibility

Enriches raw `SceneDefinition` objects with LLM-derived visual metadata:
- `visual_type` (chart / footage / company_image / …)
- `visual_query` (English search keywords)
- `ticker` (stock symbol if applicable)
- `chart_period`, `transition`, `annotations`

## Prompt Strategy

The system prompt instructs the LLM to act as a YouTube Shorts video producer
specialising in U.S. equity markets. It outputs a strict JSON array, with one
object per scene, preserving `scene_id` ordering.

`response_format={"type": "json_object"}` is used with OpenAI to guarantee
parseable output.

## Fallback Handling

If the LLM returns a different number of scenes than expected, `_merge_fallback`
merges by `scene_id`, keeping original values for any missing scenes.

## Usage

```python
from openai import OpenAI
from modules.scene_generator import SceneGenerator

gen = SceneGenerator(llm_client=OpenAI(), model="gpt-4o")
enriched_scenes = gen.enrich(raw_scenes)
```

## Factory

```python
from modules.scene_generator import create_scene_generator
gen = create_scene_generator(provider="openai", model="gpt-4o")
```
