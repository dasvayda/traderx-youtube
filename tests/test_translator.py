"""Unit tests for modules/translator.py (no API keys required)."""

from __future__ import annotations

import unittest

from modules.translator import (
    BaseTranslator,
    TranslationResult,
    build_system_prompt,
    create_translator,
    validate_source_language,
    validate_target_language,
)


class _StubTranslator(BaseTranslator):
    """Minimal translator for testing without LLM API calls."""

    def translate(self, text: str) -> TranslationResult:
        return self._make_result(text, f"[{self._target_language}]{text}", "stub", "test-model")


class TestLanguageValidation(unittest.TestCase):
    def test_validate_source_language_ko(self):
        self.assertEqual(validate_source_language("ko"), "ko")

    def test_validate_source_language_rejects_unknown(self):
        with self.assertRaises(ValueError):
            validate_source_language("fr")

    def test_validate_target_language_ja(self):
        self.assertEqual(validate_target_language("ja"), "ja")

    def test_validate_target_language_en(self):
        self.assertEqual(validate_target_language("EN"), "en")

    def test_validate_target_language_rejects_unknown(self):
        with self.assertRaises(ValueError):
            validate_target_language("de")


class TestSystemPrompt(unittest.TestCase):
    def test_default_prompt_mentions_japanese(self):
        prompt = build_system_prompt("ko", "ja")
        self.assertIn("Japanese", prompt)
        self.assertIn("Korean", prompt)

    def test_english_target_prompt(self):
        prompt = build_system_prompt("ko", "en")
        self.assertIn("English", prompt)
        self.assertIn("TSLA", prompt)

    def test_chinese_target_prompt(self):
        prompt = build_system_prompt("ko", "zh")
        self.assertIn("Chinese", prompt)


class TestTranslationResult(unittest.TestCase):
    def test_backward_compatible_aliases(self):
        result = TranslationResult(
            original_text="테슬라",
            translated_text="テスラ",
            source_language="ko",
            target_language="ja",
            provider="stub",
            model="test",
        )
        self.assertEqual(result.original_korean, "테슬라")
        self.assertEqual(result.translated_japanese, "テスラ")


class TestStubTranslator(unittest.TestCase):
    def test_translate_uses_target_language(self):
        translator = _StubTranslator(source_language="ko", target_language="en")
        result = translator.translate("NVDA 주가 상승")
        self.assertEqual(result.target_language, "en")
        self.assertIn("[en]", result.translated_text)
        self.assertEqual(result.original_text, "NVDA 주가 상승")

    def test_create_translator_rejects_invalid_target(self):
        with self.assertRaises(ValueError):
            create_translator(provider="openai", target_language="de", model="gpt-4o")

    def test_create_translator_rejects_unknown_provider(self):
        with self.assertRaises(ValueError):
            create_translator(provider="unknown")


if __name__ == "__main__":
    unittest.main()
