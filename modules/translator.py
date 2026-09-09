"""
translator.py — Korean → target-language LLM translation module.

Supports pluggable providers: OpenAI, Gemini, Claude.
Preserves stock ticker symbols and financial terminology.
Target language is configurable (default: Japanese).
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Language Registry
# ---------------------------------------------------------------------------

SUPPORTED_SOURCE_LANGUAGES: dict[str, str] = {
    "ko": "Korean",
}

SUPPORTED_TARGET_LANGUAGES: dict[str, str] = {
    "ja": "Japanese",
    "en": "English",
    "zh": "Chinese",
    "es": "Spanish",
    "vi": "Vietnamese",
}

# ---------------------------------------------------------------------------
# Data Types
# ---------------------------------------------------------------------------

@dataclass
class TranslationResult:
    original_text: str
    translated_text: str
    source_language: str
    target_language: str
    provider: str
    model: str

    @property
    def original_korean(self) -> str:
        """Backward-compatible alias."""
        return self.original_text

    @property
    def translated_japanese(self) -> str:
        """Backward-compatible alias (works for any target language)."""
        return self.translated_text


# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------

def build_system_prompt(source_language: str = "ko", target_language: str = "ja") -> str:
    """Build a provider-agnostic system prompt for the given language pair."""
    source_language = validate_source_language(source_language)
    target_language = validate_target_language(target_language)

    source_name = SUPPORTED_SOURCE_LANGUAGES[source_language]
    target_name = SUPPORTED_TARGET_LANGUAGES[target_language]

    return f"""\
You are a professional financial and stock market translator.
Translate the following {source_name} script into natural {target_name}.

Rules:
1. Keep stock ticker symbols (e.g. TSLA, AAPL, NVDA) in English unchanged.
2. Use accurate financial industry terminology in {target_name}.
3. Maintain a conversational YouTube-friendly tone.
4. Do not change numbers, percentages, or dollar amounts.
5. Output only the translation — no explanations or annotations.
"""


def validate_source_language(code: str) -> str:
    code = code.lower()
    if code not in SUPPORTED_SOURCE_LANGUAGES:
        supported = ", ".join(SUPPORTED_SOURCE_LANGUAGES)
        raise ValueError(f"Unsupported source language: {code!r}. Choose from: {supported}")
    return code


def validate_target_language(code: str) -> str:
    code = code.lower()
    if code not in SUPPORTED_TARGET_LANGUAGES:
        supported = ", ".join(SUPPORTED_TARGET_LANGUAGES)
        raise ValueError(f"Unsupported target language: {code!r}. Choose from: {supported}")
    return code


# ---------------------------------------------------------------------------
# Abstract Base
# ---------------------------------------------------------------------------

class BaseTranslator(ABC):
    """Provider-agnostic translation interface."""

    def __init__(
        self,
        source_language: str = "ko",
        target_language: str = "ja",
    ):
        self._source_language = validate_source_language(source_language)
        self._target_language = validate_target_language(target_language)
        self._system_prompt = build_system_prompt(self._source_language, self._target_language)

    @property
    def source_language(self) -> str:
        return self._source_language

    @property
    def target_language(self) -> str:
        return self._target_language

    @abstractmethod
    def translate(self, text: str) -> TranslationResult:
        ...

    def _make_result(self, original: str, translated: str, provider: str, model: str) -> TranslationResult:
        return TranslationResult(
            original_text=original,
            translated_text=translated,
            source_language=self._source_language,
            target_language=self._target_language,
            provider=provider,
            model=model,
        )

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
    def __init__(
        self,
        model: str = "gpt-4o",
        temperature: float = 0.3,
        source_language: str = "ko",
        target_language: str = "ja",
    ):
        super().__init__(source_language=source_language, target_language=target_language)
        try:
            from openai import OpenAI
        except ImportError as e:
            raise ImportError("pip install openai") from e

        self._client = OpenAI()
        self._model = model
        self._temperature = temperature

    def translate(self, text: str) -> TranslationResult:
        logger.info(
            "OpenAI translation start (model=%s, %s→%s)",
            self._model, self._source_language, self._target_language,
        )

        response = self._client.chat.completions.create(
            model=self._model,
            temperature=self._temperature,
            messages=[
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": text},
            ],
        )
        translated = response.choices[0].message.content.strip()
        logger.info("OpenAI translation complete (%d chars)", len(translated))

        return self._make_result(text, translated, "openai", self._model)


# ---------------------------------------------------------------------------
# Gemini Provider
# ---------------------------------------------------------------------------

class GeminiTranslator(BaseTranslator):
    def __init__(
        self,
        model: str = "gemini-1.5-pro",
        temperature: float = 0.3,
        source_language: str = "ko",
        target_language: str = "ja",
    ):
        super().__init__(source_language=source_language, target_language=target_language)
        try:
            import google.generativeai as genai
            import os
            genai.configure(api_key=os.environ["GEMINI_API_KEY"])
            self._genai = genai
        except ImportError as e:
            raise ImportError("pip install google-generativeai") from e

        self._model_name = model
        self._temperature = temperature

    def translate(self, text: str) -> TranslationResult:
        logger.info(
            "Gemini translation start (model=%s, %s→%s)",
            self._model_name, self._source_language, self._target_language,
        )

        model = self._genai.GenerativeModel(
            model_name=self._model_name,
            system_instruction=self._system_prompt,
            generation_config={"temperature": self._temperature},
        )
        response = model.generate_content(text)
        translated = response.text.strip()
        logger.info("Gemini translation complete (%d chars)", len(translated))

        return self._make_result(text, translated, "gemini", self._model_name)


# ---------------------------------------------------------------------------
# Claude Provider
# ---------------------------------------------------------------------------

class ClaudeTranslator(BaseTranslator):
    def __init__(
        self,
        model: str = "claude-sonnet-4-6",
        temperature: float = 0.3,
        source_language: str = "ko",
        target_language: str = "ja",
    ):
        super().__init__(source_language=source_language, target_language=target_language)
        try:
            import anthropic
        except ImportError as e:
            raise ImportError("pip install anthropic") from e

        self._client = anthropic.Anthropic()
        self._model = model
        self._temperature = temperature

    def translate(self, text: str) -> TranslationResult:
        logger.info(
            "Claude translation start (model=%s, %s→%s)",
            self._model, self._source_language, self._target_language,
        )

        message = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            temperature=self._temperature,
            system=self._system_prompt,
            messages=[{"role": "user", "content": text}],
        )
        translated = message.content[0].text.strip()
        logger.info("Claude translation complete (%d chars)", len(translated))

        return self._make_result(text, translated, "claude", self._model)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_translator(
    provider: str = "openai",
    source_language: str = "ko",
    target_language: str = "ja",
    **kwargs,
) -> BaseTranslator:
    """Return the appropriate translator for the given provider name."""
    registry: dict[str, type[BaseTranslator]] = {
        "openai": OpenAITranslator,
        "gemini": GeminiTranslator,
        "claude": ClaudeTranslator,
    }
    cls = registry.get(provider.lower())
    if cls is None:
        raise ValueError(f"Unknown translation provider: {provider!r}. Choose from {list(registry)}")
    return cls(
        source_language=source_language,
        target_language=target_language,
        **kwargs,
    )
