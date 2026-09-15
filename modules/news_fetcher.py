"""
news_fetcher.py — Stock news collection for script/scene generation.

Fetches headlines from Alpha Vantage NEWS_SENTIMENT API.
Can also load cached JSON for offline use.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

import requests

logger = logging.getLogger(__name__)

_ALPHA_VANTAGE_BASE = "https://www.alphavantage.co/query"


@dataclass
class NewsItem:
    title: str
    summary: str
    source: str
    url: str
    tickers: list[str]
    published_at: str
    sentiment_label: str = ""
    sentiment_score: float = 0.0


def parse_news_feed(feed: list[dict]) -> list[NewsItem]:
    """Convert Alpha Vantage feed entries into NewsItem objects."""
    items: list[NewsItem] = []
    for entry in feed:
        tickers = [
            ts.get("ticker", "")
            for ts in entry.get("ticker_sentiment", [])
            if ts.get("ticker")
        ]
        sentiment = entry.get("overall_sentiment_label", "")
        score_raw = entry.get("overall_sentiment_score", 0)
        try:
            score = float(score_raw)
        except (TypeError, ValueError):
            score = 0.0

        items.append(
            NewsItem(
                title=entry.get("title", "").strip(),
                summary=entry.get("summary", "").strip(),
                source=entry.get("source", "").strip(),
                url=entry.get("url", "").strip(),
                tickers=tickers,
                published_at=entry.get("time_published", "").strip(),
                sentiment_label=sentiment,
                sentiment_score=score,
            )
        )
    return items


def format_news_context(items: list[NewsItem], max_items: int = 5) -> str:
    """Format news items as plain text for LLM prompts."""
    lines: list[str] = []
    for item in items[:max_items]:
        tickers = ", ".join(item.tickers) if item.tickers else "N/A"
        lines.append(f"- [{tickers}] {item.title}")
        if item.summary:
            lines.append(f"  {item.summary[:200]}")
    return "\n".join(lines)


class NewsFetcher:
    """Fetch stock news from Alpha Vantage or a local JSON cache."""

    def __init__(self, api_key: str = "", timeout: int = 15):
        self._api_key = api_key or os.environ.get("ALPHA_VANTAGE_KEY", "")
        self._timeout = timeout

    def fetch(
        self,
        tickers: list[str],
        limit: int = 10,
    ) -> list[NewsItem]:
        if not self._api_key:
            raise ValueError(
                "ALPHA_VANTAGE_KEY is not set. Add it to .env or pass api_key."
            )
        if not tickers:
            raise ValueError("At least one ticker is required")

        params = {
            "function": "NEWS_SENTIMENT",
            "tickers": ",".join(tickers),
            "limit": str(limit),
            "apikey": self._api_key,
        }
        url = f"{_ALPHA_VANTAGE_BASE}?{urlencode(params)}"
        logger.info("Fetching news for tickers: %s", tickers)

        resp = requests.get(url, timeout=self._timeout)
        resp.raise_for_status()
        data = resp.json()

        if "feed" not in data:
            message = data.get("Information") or data.get("Note") or str(data)
            raise RuntimeError(f"Alpha Vantage news API error: {message}")

        items = parse_news_feed(data["feed"])
        logger.info("Fetched %d news items", len(items))
        return items

    def load_from_file(self, path: str | Path) -> list[NewsItem]:
        """Load news from a saved Alpha Vantage JSON response."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if isinstance(data, list):
            return parse_news_feed(data)
        if "feed" in data:
            return parse_news_feed(data["feed"])
        raise ValueError("JSON must contain a 'feed' array or be a feed list")

    def to_scene_context(self, items: list[NewsItem], max_items: int = 5) -> str:
        """Return formatted text suitable for scene_generator / script_writer."""
        return format_news_context(items, max_items=max_items)
