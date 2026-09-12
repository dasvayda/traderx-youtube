# TTS Engine Module

**File:** `modules/tts_engine.py`

## Responsibility

Synthesizes Japanese narration audio for each scene using a pluggable TTS provider.
Output files (MP3) are written to `assets/audio/` and used by `video_composer.py`
for lip-sync timing and scene duration calculation.

## Key Classes

| Class | Description |
|-------|-------------|
| `BaseTTSEngine` | Abstract base with `synthesize(text, output_path) → TTSResult` |
| `OpenAITTSEngine` | OpenAI `tts-1` / `tts-1-hd` via the OpenAI Python SDK |
| `AzureTTSEngine` | Azure Cognitive Services Speech (`ja-JP-NanamiNeural`, etc.) |
| `GoogleTTSEngine` | Google Cloud Text-to-Speech (`ja-JP-Neural2-B`, etc.) |
| `ElevenLabsTTSEngine` | ElevenLabs REST API (`eleven_multilingual_v2`) |

## Output

```python
@dataclass
class TTSResult:
    audio_path: Path
    duration_seconds: float   # measured via pydub after synthesis
    provider: str
    voice: str
```

Duration is measured from the generated file using `pydub`. If measurement fails,
`estimate_duration()` falls back to ~4.5 characters per second.

## Factory

```python
from modules.tts_engine import create_tts_engine

engine = create_tts_engine(provider="openai", voice="shimmer", model="tts-1-hd")
result = engine.synthesize(
    "NVDAが史上最高値を更新しました。",
    Path("assets/audio/narration_scene01.mp3"),
)
print(result.duration_seconds)
```

## Switching Providers

Change `tts.provider` in `config/settings.yaml`:

```yaml
tts:
  provider: "openai"         # openai | azure | google | elevenlabs
  openai_voice: "shimmer"    # alloy | echo | fable | onyx | nova | shimmer
  openai_model: "tts-1-hd"
  azure_voice: "ja-JP-NanamiNeural"
  azure_region: "japaneast"
  google_voice: "ja-JP-Neural2-B"
  elevenlabs_voice_id: ""
  sample_rate: 24000
```

The Streamlit sidebar (`app.py`) also exposes a TTS provider selector at runtime.

## API Keys

| Provider | Environment Variable | Extra Setup |
|----------|---------------------|-------------|
| OpenAI | `OPENAI_API_KEY` | — |
| Azure | `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION` | `pip install azure-cognitiveservices-speech` |
| Google | `GOOGLE_APPLICATION_CREDENTIALS` | `pip install google-cloud-texttospeech` |
| ElevenLabs | `ELEVENLABS_API_KEY` | Set `elevenlabs_voice_id` in settings |

## Provider Details

### OpenAI

- Default voice: `shimmer`
- Output format: MP3
- Voices: `alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer`

### Azure Speech

- Default voice: `ja-JP-NanamiNeural`
- Writes directly to the output file path via `AudioOutputConfig`
- Raises `RuntimeError` if synthesis does not complete

### Google Cloud TTS

- Default voice: `ja-JP-Neural2-B`, language `ja-JP`
- Requires a service account JSON at `GOOGLE_APPLICATION_CREDENTIALS`
- Output format: MP3

### ElevenLabs

- Uses `eleven_multilingual_v2` model
- Requires a valid `voice_id` (configured in `settings.yaml`)
- Output: raw audio bytes written to the output path

## Pipeline Integration

In `pipeline.py` → `_step_tts`:

```
for each scene:
  1. synthesize(scene.narration, assets/audio/narration_{job_id}_scene{N}.mp3)
  2. update scene.duration = actual_audio_duration + 0.5s padding
  3. append audio path to job.narration_paths
```

If TTS fails for a scene, the path is set to `None` and a warning is logged;
the pipeline continues without aborting the job.

## Error Handling

- Missing optional SDK → `ImportError` with install hint
- Azure synthesis failure → `RuntimeError`
- ElevenLabs HTTP error → `requests` exception propagated
- Per-scene failures in pipeline are caught and logged (non-fatal)
