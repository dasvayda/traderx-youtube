"""
agent_orchestrator.py — LangGraph-based multi-node pipeline for automated
YouTube Shorts production.

Node chain:
  NewsNode → ScriptNode → TranslateNode → SceneNode → PipelineNode

Each node reads from and writes to a shared AgentState TypedDict.

Dependencies:
  pip install langgraph>=0.1 langchain-openai>=0.1
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional, TypedDict

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()
load_dotenv("config/.env")


# ---------------------------------------------------------------------------
# Shared state
# ---------------------------------------------------------------------------

class AgentState(TypedDict):
    # Inputs
    tickers: list[str]
    job_id: str
    output_name: str
    bgm_file: Optional[str]
    config: dict

    # NewsNode output
    news_context: str           # formatted text for LLM

    # ScriptNode output
    korean_script: str

    # TranslateNode output
    japanese_script: str

    # SceneNode output
    scenes: list[dict]          # serialised SceneDefinition dicts

    # PipelineNode output
    final_video_path: Optional[str]
    error: Optional[str]


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------

def news_node(state: AgentState) -> AgentState:
    """Fetch stock news for the requested tickers."""
    from modules.news_fetcher import NewsFetcher

    tickers = state["tickers"]
    logger.info("[NewsNode] Fetching news for: %s", tickers)

    api_key = os.environ.get("ALPHA_VANTAGE_KEY", "")
    fetcher = NewsFetcher(api_key=api_key)

    try:
        if api_key:
            items = fetcher.fetch(tickers, limit=10)
        else:
            logger.warning("[NewsNode] No ALPHA_VANTAGE_KEY; news_context will be empty")
            items = []
        context = fetcher.to_scene_context(items, max_items=5)
    except Exception as exc:
        logger.warning("[NewsNode] News fetch failed: %s — continuing without news", exc)
        context = ""

    return {**state, "news_context": context}


def script_node(state: AgentState) -> AgentState:
    """Generate a Korean script from market quotes and news context."""
    from modules.script_writer import create_script_writer, fetch_quotes, MarketQuote
    from modules.news_fetcher import parse_news_feed

    tickers = state["tickers"]
    cfg = state.get("config", {})
    llm_cfg = cfg.get("llm", {})
    logger.info("[ScriptNode] Writing script for tickers: %s", tickers)

    try:
        quotes = fetch_quotes(tickers)
    except Exception as exc:
        logger.warning("[ScriptNode] yfinance fetch failed: %s — using placeholder quotes", exc)
        quotes = [MarketQuote(ticker=t, price=0.0, change_percent=0.0) for t in tickers]

    # Reconstruct news items from context string (cheap path)
    # For the LLM we pass the pre-formatted context string via a minimal NewsItem wrapper
    news_items = None
    if state.get("news_context"):
        from modules.news_fetcher import NewsItem
        news_items = [
            NewsItem(
                title=state["news_context"],
                summary="",
                source="",
                url="",
                tickers=tickers,
                published_at="",
            )
        ]

    writer = create_script_writer(
        provider=llm_cfg.get("provider", "openai"),
        model=llm_cfg.get("model", "gpt-4o"),
        temperature=llm_cfg.get("temperature", 0.5),
    )
    draft = writer.write(quotes, news_items)
    logger.info("[ScriptNode] Script written (%d chars)", len(draft.korean_script))
    return {**state, "korean_script": draft.korean_script}


def translate_node(state: AgentState) -> AgentState:
    """Translate the Korean script into Japanese."""
    from modules.translator import create_translator

    cfg = state.get("config", {})
    llm_cfg = cfg.get("llm", {})
    trans_cfg = cfg.get("translation", {})
    logger.info("[TranslateNode] Translating script")

    translator = create_translator(
        provider=llm_cfg.get("provider", "openai"),
        model=llm_cfg.get("model", "gpt-4o"),
        temperature=llm_cfg.get("temperature", 0.3),
        source_language=trans_cfg.get("source_language", "ko"),
        target_language=trans_cfg.get("target_language", "ja"),
    )
    result = translator.translate(state["korean_script"])
    logger.info("[TranslateNode] Translation complete (%d chars)", len(result.translated_japanese))
    return {**state, "japanese_script": result.translated_japanese}


def scene_node(state: AgentState) -> AgentState:
    """Parse the Japanese script into scenes and enrich with LLM visual metadata."""
    from modules.script_parser import ScriptParser
    from modules.scene_generator import create_scene_generator

    cfg = state.get("config", {})
    llm_cfg = cfg.get("llm", {})
    logger.info("[SceneNode] Parsing and enriching scenes")

    parser = ScriptParser()
    scenes = parser.parse(state["japanese_script"])

    gen = create_scene_generator(
        provider=llm_cfg.get("provider", "openai"),
        model=llm_cfg.get("model", "gpt-4o"),
    )
    enriched = gen.enrich(scenes)
    scene_dicts = [s.to_dict() for s in enriched]
    logger.info("[SceneNode] %d scenes generated", len(scene_dicts))
    return {**state, "scenes": scene_dicts}


def pipeline_node(state: AgentState) -> AgentState:
    """Run the full video production pipeline for the prepared job data."""
    from modules.pipeline import Pipeline, Job, JobStatus

    cfg = state.get("config", {})
    logger.info("[PipelineNode] Starting video production for job: %s", state["job_id"])

    job = Job(
        job_id=state["job_id"],
        korean_script=state["korean_script"],
        output_name=state.get("output_name", "output.mp4"),
        bgm_file=state.get("bgm_file"),
    )
    # Inject pre-computed data to skip redundant steps
    job.japanese_script = state["japanese_script"]
    job.scenes = state["scenes"]

    pipeline = Pipeline(cfg)

    # Skip translate/parse/scene steps — already done by earlier nodes
    from modules.pipeline import JobStatus as JS
    try:
        job = pipeline._step_assets(job)
        job = pipeline._step_tts(job)
        job = pipeline._step_bgm(job)
        job = pipeline._step_compose(job)
        job = pipeline._step_subtitles(job)
        job.status = JS.COMPLETE
        logger.info("[PipelineNode] Video complete: %s", job.final_path)
        return {**state, "final_video_path": job.final_path, "error": None}
    except Exception as exc:
        logger.exception("[PipelineNode] Pipeline failed: %s", exc)
        return {**state, "final_video_path": None, "error": str(exc)}


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def build_graph():
    """Construct and compile the LangGraph StateGraph."""
    try:
        from langgraph.graph import StateGraph, END
    except ImportError as e:
        raise ImportError(
            "langgraph is required: pip install langgraph>=0.1"
        ) from e

    graph = StateGraph(AgentState)

    graph.add_node("news",      news_node)
    graph.add_node("script",    script_node)
    graph.add_node("translate", translate_node)
    graph.add_node("scene",     scene_node)
    graph.add_node("pipeline",  pipeline_node)

    graph.set_entry_point("news")
    graph.add_edge("news",      "script")
    graph.add_edge("script",    "translate")
    graph.add_edge("translate", "scene")
    graph.add_edge("scene",     "pipeline")
    graph.add_edge("pipeline",  END)

    return graph.compile()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_agent(
    tickers: list[str],
    job_id: str,
    config: dict,
    output_name: str = "output.mp4",
    bgm_file: Optional[str] = None,
) -> AgentState:
    """
    Run the full agent pipeline for a given list of tickers.

    Returns the final AgentState, including `final_video_path` on success
    or `error` on failure.

    Example::

        import yaml
        config = yaml.safe_load(open("config/settings.yaml"))
        state = run_agent(["NVDA", "TSLA"], job_id="job_001", config=config)
        print(state["final_video_path"])
    """
    app = build_graph()

    initial_state: AgentState = {
        "tickers": tickers,
        "job_id": job_id,
        "output_name": output_name,
        "bgm_file": bgm_file,
        "config": config,
        "news_context": "",
        "korean_script": "",
        "japanese_script": "",
        "scenes": [],
        "final_video_path": None,
        "error": None,
    }

    logger.info("Starting agent run: tickers=%s job_id=%s", tickers, job_id)
    result: AgentState = app.invoke(initial_state)
    return result
