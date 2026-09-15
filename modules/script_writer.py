"""
script_writer.py — Generate Korean YouTube Shorts scripts from market data + news.

Uses an LLM to turn ticker quotes and optional news headlines into a narration script.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Optional

from modules.news_fetcher import NewsItem, format_news_context

logger = logging.getLogger(__name__)

_SCRIPT_SYSTEM = """\
당신은 미국 주식 시장 전문 YouTube Shorts 스크립트 작가입니다.
제공된 시세·뉴스 데이터를 바탕으로 한국어 나레이션 스크립트를 작성하세요.

규칙:
1. 30~60초 분량 (약 200~400자)
2. 인사로 시작하고, 구독·좋아요 요청으로 마무리
3. 티커 심볼(TSLA, NVDA 등)은 영문 그대로 유지
4. 숫자·퍼센트는 구체적으로 표현
5. 스크립트 텍스트만 출력 (제목·설명·마크다운 없음)
"""


@dataclass
class MarketQuote:
    ticker: str
    price: float
    change_percent: float
    name: str = ""


@dataclass
class ScriptDraft:
    korean_script: str
    tickers: list[str]
    provider: str
    model: str


def build_user_prompt(
    quotes: list[MarketQuote],
    news_items: Optional[list[NewsItem]] = None,
) -> str:
    """Build the LLM user prompt from market data and optional news."""
    lines = ["## 시세 데이터"]
    for q in quotes:
        label = q.name or q.ticker
        sign = "+" if q.change_percent >= 0 else ""
        lines.append(
            f"- {label} ({q.ticker}): ${q.price:.2f}, {sign}{q.change_percent:.2f}%"
        )

    if news_items:
        lines.append("")
        lines.append("## 관련 뉴스")
        lines.append(format_news_context(news_items))

    lines.append("")
    lines.append("위 데이터를 바탕으로 한국어 Shorts 스크립트를 작성하세요.")
    return "\n".join(lines)


def extract_script(text: str) -> str:
    """Strip markdown fences and surrounding whitespace from LLM output."""
    text = text.strip()
    fenced = re.match(r"^```(?:\w+)?\s*\n?(.*?)\n?```$", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    return text


def fetch_quotes(tickers: list[str]) -> list[MarketQuote]:
    """Fetch latest quotes via yfinance (no API key required)."""
    import yfinance as yf

    quotes: list[MarketQuote] = []
    for ticker in tickers:
        info = yf.Ticker(ticker)
        hist = info.history(period="2d")
        if hist.empty:
            logger.warning("No price data for %s", ticker)
            continue

        price = float(hist["Close"].iloc[-1])
        if len(hist) >= 2:
            prev = float(hist["Close"].iloc[-2])
            change_pct = ((price - prev) / prev) * 100 if prev else 0.0
        else:
            change_pct = 0.0

        name = info.info.get("shortName", ticker) if info.info else ticker
        quotes.append(
            MarketQuote(
                ticker=ticker.upper(),
                price=price,
                change_percent=round(change_pct, 2),
                name=name,
            )
        )
    return quotes


class ScriptWriter:
    """LLM-powered Korean script generator."""

    def __init__(self, llm_client: Any, model: str = "gpt-4o", temperature: float = 0.5):
        self._client = llm_client
        self._model = model
        self._temperature = temperature

    def write(
        self,
        quotes: list[MarketQuote],
        news_items: Optional[list[NewsItem]] = None,
    ) -> ScriptDraft:
        user_prompt = build_user_prompt(quotes, news_items)
        tickers = [q.ticker for q in quotes]

        logger.info("Generating script for tickers: %s", tickers)
        response = self._client.chat.completions.create(
            model=self._model,
            temperature=self._temperature,
            messages=[
                {"role": "system", "content": _SCRIPT_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
        )
        raw = response.choices[0].message.content or ""
        script = extract_script(raw)
        logger.info("Script generated (%d chars)", len(script))

        return ScriptDraft(
            korean_script=script,
            tickers=tickers,
            provider="openai",
            model=self._model,
        )


def create_script_writer(
    provider: str = "openai",
    model: str = "gpt-4o",
    temperature: float = 0.5,
) -> ScriptWriter:
    if provider == "openai":
        from openai import OpenAI
        return ScriptWriter(llm_client=OpenAI(), model=model, temperature=temperature)
    raise ValueError(f"Unknown script writer provider: {provider!r}")
