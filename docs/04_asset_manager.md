# Asset Manager Module

**File:** `modules/asset_manager.py`

## Responsibility

Searches Pexels and Pixabay for portrait-oriented images and short video clips,
downloads them to a local cache, and returns file paths for the video pipeline.

Chart scenes (`stock_chart`, `market_chart`) are **not** handled here — those use
`chart_generator.py` (user-uploaded images). See [Chart Images](05_chart_generator.md).

## Key Classes

| Class | Description |
|-------|-------------|
| `AssetResult` | Dataclass: `asset_type`, `local_path`, `source_url`, `provider`, `query`, `width`, `height` |
| `AssetCache` | File-based cache keyed by MD5 of source URL; index stored in `cache/asset_index.json` |
| `PexelsProvider` | Pexels REST API — images + videos |
| `PixabayProvider` | Pixabay REST API — images only |
| `AssetManager` | High-level orchestrator used by `pipeline.py` |

## Search Priority

When `AssetManager.get_asset_for_scene(scene)` is called:

1. `visual_type == "footage"` → search Pexels **videos** (portrait, HD preferred)
2. All other types → search Pexels **images**, then Pixabay images as fallback
3. Returns `None` if no provider is configured or all searches fail

> Pipeline `_step_assets` checks uploaded chart images **before** calling this module.

## Usage

```python
from modules.asset_manager import AssetManager
from modules.script_parser import SceneDefinition

mgr = AssetManager(
    pexels_api_key="your-pexels-key",
    pixabay_api_key="your-pixabay-key",
    cache_dir="cache",
    assets_dir="assets",
)

scene = SceneDefinition.from_dict({
    "scene_id": 1,
    "visual_type": "company_image",
    "visual_query": "Apple headquarters",
    "ticker": "AAPL",
    # ... other fields
})

path = mgr.get_asset_for_scene(scene)   # Path or None
```

## API Keys

Set in `.env` (see `config/.env.example`):

```
PEXELS_API_KEY=
PIXABAY_API_KEY=
```

Pipeline reads them via `os.environ` at startup. If a key is missing, that provider
is skipped silently (the other provider is still tried).

## Cache Behaviour

- Downloaded files are stored under `cache/` with an MD5 filename (e.g. `a3f2…c1.jpg`)
- `cache/asset_index.json` maps URL hash → local path
- Re-running the same query does **not** re-download if the cached file still exists
- Configure `assets.max_cache_age_days` in `settings.yaml` (not yet enforced in code)

## Pipeline Integration

In `pipeline.py` → `_step_assets`:

```
for each scene:
  1. get_chart(scene_id)          → uploaded chart image (priority)
  2. elif not stock_chart type    → AssetManager.get_asset_for_scene()
  3. else (chart, no upload)      → None → video_composer uses title_card fallback
```

## Visual Type → Asset Source

| `visual_type` | Asset source |
|---------------|--------------|
| `stock_chart` | User upload via `chart_generator` |
| `market_chart` | User upload via `chart_generator` |
| `footage` | Pexels video |
| `company_image` | Pexels image → Pixabay fallback |
| `title_card` | No external asset (text overlay in composer) |
| `news_image` | Pexels image → Pixabay fallback |

## Configuration

`config/settings.yaml`:

```yaml
assets:
  pexels_per_page: 5
  pixabay_per_page: 5
  cache_dir: "cache"
  max_cache_age_days: 7
```

## Error Handling

- Provider HTTP errors are logged as warnings; the next provider is tried
- Missing API keys disable that provider without raising
- `get_asset_for_scene` never raises — returns `None` on total failure
