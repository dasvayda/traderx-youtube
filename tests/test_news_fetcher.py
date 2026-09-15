"""Unit tests for modules/news_fetcher.py."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from modules.news_fetcher import (
    NewsFetcher,
    NewsItem,
    format_news_context,
    parse_news_feed,
)

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_FEED = [
    {
        "title": "Test headline",
        "summary": "Test summary text.",
        "source": "TestSource",
        "url": "https://example.com/1",
        "time_published": "20260101T120000",
        "overall_sentiment_label": "Bullish",
        "overall_sentiment_score": "0.5",
        "ticker_sentiment": [{"ticker": "TSLA"}],
    }
]


class TestParseNewsFeed(unittest.TestCase):
    def test_parses_single_item(self):
        items = parse_news_feed(SAMPLE_FEED)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].title, "Test headline")
        self.assertEqual(items[0].tickers, ["TSLA"])
        self.assertEqual(items[0].sentiment_score, 0.5)

    def test_format_news_context(self):
        items = parse_news_feed(SAMPLE_FEED)
        text = format_news_context(items)
        self.assertIn("TSLA", text)
        self.assertIn("Test headline", text)


class TestNewsFetcherFile(unittest.TestCase):
    def test_load_from_fixture(self):
        fetcher = NewsFetcher()
        items = fetcher.load_from_file(FIXTURES / "sample_news.json")
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].tickers, ["NVDA"])

    def test_to_scene_context(self):
        fetcher = NewsFetcher()
        items = fetcher.load_from_file(FIXTURES / "sample_news.json")
        ctx = fetcher.to_scene_context(items, max_items=1)
        self.assertIn("NVDA", ctx)
        self.assertNotIn("AAPL", ctx)


class TestNewsFetcherAPI(unittest.TestCase):
    def test_fetch_requires_api_key(self):
        fetcher = NewsFetcher(api_key="")
        with self.assertRaises(ValueError):
            fetcher.fetch(["NVDA"])

    @patch("modules.news_fetcher.requests.get")
    def test_fetch_parses_response(self, mock_get: MagicMock):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"feed": SAMPLE_FEED}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        fetcher = NewsFetcher(api_key="test-key")
        items = fetcher.fetch(["TSLA"], limit=5)
        self.assertEqual(len(items), 1)
        self.assertIsInstance(items[0], NewsItem)


if __name__ == "__main__":
    unittest.main()
