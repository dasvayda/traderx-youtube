"""
translator.py — Korean → Japanese LLM translation module.

Supports pluggable providers: OpenAI, Gemini, Claude.
Preserves stock ticker symbols and financial terminology.
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data Types
# ---------------------------------------------------------------------------

@dataclass
class TranslationResult:
    original_korean: str
    translated_japanese: str
    provider: str
    model: str


# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
あなたは金融・株式市場の専門翻訳者です。
以下のルールに従って、韓国語のスクリプトを自然な日本語に翻訳してください。

ルール:
1. 株式ティッカーシンボル（例: TSLA, AAPL, NVDA）はそのまま英語で残す。
2. 金融専門用語は正確な日本語の業界用語を使う（例: 損益計算書 → 損益計算書）。
3. 自然な話し言葉のトーンを維持する（YouTube視聴者向け）。
4. 数字・パーセント・ドル金額の形式は変えない。
5. 翻訳文のみを出力し、説明や注釈を加えない。
"""


# ---------------------------------------------------------------------------
# Abstract Base
# ---------------------------------------------------------------------------

class BaseTranslator(ABC):
    """Provider-agnostic translation interface."""

    @abstractmethod
    def translate(self, korean_text: str) -> TranslationResult:
        ...

    def _protect_tickers(self, text: str) -> tuple[str, dict[str, str]]:
        """Replace ticker symbols with placeholders to prevent mutation."""
        ticker_pattern = re.compile(r'\b([A-Z]{1,5})\b')
        placeholders: dict[str, str] = {}
        protected = text

        for i, match in enumerate(ticker_pattern.finditer(text)):
            ticker = match.group(1)
            placeholder = f"__TICKER_{i}__"
            placeholders[placeholder] = ticker
            protected = protected.replace(ticker, placeholder, 1)

        return protected, placeholders

    def _restore_tickers(self, text: str, placeholders: dict[str, str]) -> str:
        for placeholder, ticker in placeholders.items():
            text = text.replace(placeholder, ticker)
        return text


# ---------------------------------------------------------------------------
# OpenAI Provider
# ---------------------------------------------------------------------------

class OpenAITranslator(BaseTranslator):
    def __init__(self, model: str = "gpt-4o", temperature: float = 0.3):
        try:
            from openai import OpenAI
        except ImportError as e:
            raise ImportError("pip install openai") from e

        self._client = OpenAI()
        self._model = model
        self._temperature = temperature

    def translate(self, korean_text: str) -> TranslationResult:
        logger.info("OpenAI translation start (model=%s)", self._model)

        response = self._client.chat.completions.create(
            model=self._model,
            temperature=self._temperature,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": korean_text},
            ],
        )
        japanese = response.choices[0].message.content.strip()
        logger.info("OpenAI translation complete (%d chars)", len(japanese))

        return TranslationResult(
            original_korean=korean_text,
            translated_japanese=japanese,
            provider="openai",
            model=self._model,
        )


# ---------------------------------------------------------------------------
# Gemini Provider
# ---------------------------------------------------------------------------

class GeminiTranslator(BaseTranslator):
    def __init__(self, model: str = "gemini-1.5-pro", temperature: float = 0.3):
        try:
            import google.generativeai as genai
            import os
            genai.configure(api_key=os.environ["GEMINI_API_KEY"])
            self._genai = genai
        except ImportError as e:
            raise ImportError("pip install google-generativeai") from e

        self._model_name = model
        self._temperature = temperature

    def translate(self, korean_text: str) -> TranslationResult:
        logger.info("Gemini translation start (model=%s)", self._model_name)

        model = self._genai.GenerativeModel(
            model_name=self._model_name,
            system_instruction=_SYSTEM_PROMPT,
            generation_config={"temperature": self._temperature},
        )
        response = model.generate_content(korean_text)
        japanese = response.text.strip()
        logger.info("Gemini translation complete (%d chars)", len(japanese))

        return TranslationResult(
            original_korean=korean_text,
            translated_japanese=japanese,
            provider="gemini",
            model=self._model_name,
        )


# ---------------------------------------------------------------------------
# Claude Provider
# ---------------------------------------------------------------------------

class ClaudeTranslator(BaseTranslator):
    def __init__(self, model: str = "claude-sonnet-4-6", temperature: float = 0.3):
        try:
            import anthropic
        except ImportError as e:
            raise ImportError("pip install anthropic") from e

        self._client = anthropic.Anthropic()
        self._model = model
        self._temperature = temperature

    def translate(self, korean_text: str) -> TranslationResult:
        logger.info("Claude translation start (model=%s)", self._model)

        message = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            temperature=self._temperature,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": korean_text}],
        )
        japanese = message.content[0].text.strip()
        logger.info("Claude translation complete (%d chars)", len(japanese))

        return TranslationResult(
            original_korean=korean_text,
            translated_japanese=japanese,
            provider="claude",
            model=self._model,
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_translator(provider: str = "openai", **kwargs) -> BaseTranslator:
    """Return the appropriate translator for the given provider name."""
    registry: dict[str, type[BaseTranslator]] = {
        "openai": OpenAITranslator,
        "gemini": GeminiTranslator,
        "claude": ClaudeTranslator,
    }
    cls = registry.get(provider.lower())
    if cls is None:
        raise ValueError(f"Unknown translation provider: {provider!r}. Choose from {list(registry)}")
    return cls(**kwargs)
