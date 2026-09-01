# Translator Module

**File:** `modules/translator.py`

## Responsibility

Translates Korean stock market scripts into natural Japanese using an LLM API.
Preserves stock ticker symbols (e.g., TSLA, AAPL) and financial terminology.

## Key Classes

| Class | Description |
|-------|-------------|
| `BaseTranslator` | Abstract base with `translate(text) → TranslationResult` |
| `OpenAITranslator` | Uses `gpt-4o` via the OpenAI Python SDK |
| `GeminiTranslator` | Uses `gemini-1.5-pro` via `google-generativeai` |
| `ClaudeTranslator` | Uses `claude-sonnet-4-6` via the Anthropic SDK |

## Factory

```python
from modules.translator import create_translator

translator = create_translator(provider="openai", model="gpt-4o")
result = translator.translate("테슬라 주가가 오늘 5% 급등했습니다.")
print(result.translated_japanese)
# → "テスラの株価が本日5%急騰しました。"
```

## System Prompt Design

The system prompt instructs the LLM to:
1. Keep ticker symbols in English
2. Use proper Japanese financial industry terminology
3. Maintain a conversational YouTube tone
4. Output only the translation (no commentary)

## Output

```python
@dataclass
class TranslationResult:
    original_korean: str
    translated_japanese: str
    provider: str
    model: str
```

## Switching Providers

Change `llm.provider` in `config/settings.yaml`:
```yaml
llm:
  provider: "claude"   # openai | gemini | claude
  model: "claude-sonnet-4-6"
```
