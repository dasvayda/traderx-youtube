"""Unit tests for modules/script_writer.py."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from modules.news_fetcher import NewsItem
from modules.script_writer import (
    MarketQuote,
    ScriptWriter,
    build_user_prompt,
    extract_script,
)


class TestBuildUserPrompt(unittest.TestCase):
    def test_includes_quotes(self):
        quotes = [
            MarketQuote("NVDA", 950.0, 3.5, "NVIDIA"),
            MarketQuote("AAPL", 210.0, -1.2, "Apple"),
        ]
        prompt = build_user_prompt(quotes)
        self.assertIn("NVDA", prompt)
        self.assertIn("$950.00", prompt)
        self.assertIn("+3.50%", prompt)
        self.assertIn("-1.20%", prompt)

    def test_includes_news(self):
        quotes = [MarketQuote("TSLA", 250.0, 8.0)]
        news = [
            NewsItem(
                title="Tesla autopilot update",
                summary="Stock jumped after software release.",
                source="CNBC",
                url="https://example.com",
                tickers=["TSLA"],
                published_at="20260101",
            )
        ]
        prompt = build_user_prompt(quotes, news)
        self.assertIn("Tesla autopilot update", prompt)
        self.assertIn("TSLA", prompt)


class TestExtractScript(unittest.TestCase):
    def test_plain_text(self):
        self.assertEqual(extract_script("안녕하세요"), "안녕하세요")

    def test_strips_markdown_fence(self):
        raw = "```\n안녕하세요!\nNVDA 주가 상승.\n```"
        self.assertEqual(extract_script(raw), "안녕하세요!\nNVDA 주가 상승.")


class TestScriptWriterMock(unittest.TestCase):
    def test_write_calls_llm(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "안녕하세요! NVDA가 상승했습니다."
        mock_client.chat.completions.create.return_value = mock_response

        writer = ScriptWriter(llm_client=mock_client, model="gpt-4o")
        quotes = [MarketQuote("NVDA", 900.0, 2.0)]
        draft = writer.write(quotes)

        self.assertIn("NVDA", draft.korean_script)
        self.assertEqual(draft.tickers, ["NVDA"])
        mock_client.chat.completions.create.assert_called_once()


if __name__ == "__main__":
    unittest.main()
