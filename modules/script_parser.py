"""
script_parser.py — Raw script text → structured scene list.

Splits a script into logical segments (scenes) using simple heuristics
(paragraph breaks, sentence length). The scene_generator module then
enriches these segments with LLM-derived visual recommendations.
"""

from __future__ import annotations

import re
import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data Model
# ---------------------------------------------------------------------------

@dataclass
class SceneDefinition:
    scene_id: int
    duration: float                    # seconds
    narration: str                     # Japanese narration text
    subtitle: str                      # Subtitle text (may be shorter than narration)
    visual_type: str = "stock_chart"   # stock_chart | company_image | footage | generated
    visual_query: str = ""             # Search keyword for asset retrieval
    ticker: Optional[str] = None       # Primary stock ticker if applicable
    chart_period: str = "1mo"          # yfinance period string
    transition: str = "fade"           # fade | slide | zoom | none
    annotations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SceneDefinition":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class ScriptParser:
    """
    Splits a plain-text Japanese script into scene segments.

    Strategy:
    1. Split on blank lines (paragraph = scene).
    2. If a paragraph is very long (> max_chars_per_scene), split further on
       sentence boundaries (。！？).
    3. Estimate scene duration from character count (~4 chars/sec for Japanese TTS).
    """

    CHARS_PER_SECOND = 4.5      # average Japanese TTS speed
    MAX_CHARS_PER_SCENE = 120   # split threshold

    def __init__(self, chars_per_second: float = CHARS_PER_SECOND,
                 max_chars: int = MAX_CHARS_PER_SCENE):
        self._cps = chars_per_second
        self._max_chars = max_chars

    # ------------------------------------------------------------------

    def parse(self, japanese_text: str) -> list[SceneDefinition]:
        """Return list of SceneDefinition from a Japanese script string."""
        segments = self._split_segments(japanese_text)
        scenes: list[SceneDefinition] = []

        for idx, seg in enumerate(segments, start=1):
            text = seg.strip()
            if not text:
                continue
            duration = max(3.0, len(text) / self._cps)
            duration = round(duration, 1)

            scene = SceneDefinition(
                scene_id=idx,
                duration=duration,
                narration=text,
                subtitle=self._make_subtitle(text),
                visual_type="stock_chart",   # will be overridden by scene_generator
                visual_query="",
            )
            scenes.append(scene)
            logger.debug("Scene %d: %d chars, %.1fs", idx, len(text), duration)

        logger.info("Parsed %d scenes from script", len(scenes))
        return scenes

    # ------------------------------------------------------------------

    def _split_segments(self, text: str) -> list[str]:
        """Split text into segments by blank lines, then by sentence if too long."""
        raw_paragraphs = re.split(r'\n{2,}', text.strip())
        segments: list[str] = []

        for para in raw_paragraphs:
            para = para.replace('\n', ' ').strip()
            if len(para) <= self._max_chars:
                segments.append(para)
            else:
                segments.extend(self._split_sentences(para))

        return segments

    def _split_sentences(self, text: str) -> list[str]:
        """Split long paragraph on Japanese sentence-ending punctuation."""
        parts = re.split(r'(?<=[。！？])\s*', text)
        merged: list[str] = []
        buffer = ""

        for part in parts:
            if len(buffer) + len(part) <= self._max_chars:
                buffer += part
            else:
                if buffer:
                    merged.append(buffer.strip())
                buffer = part

        if buffer:
            merged.append(buffer.strip())

        return merged

    def _make_subtitle(self, text: str, max_len: int = 40) -> str:
        """Truncate narration text for subtitle display."""
        if len(text) <= max_len:
            return text
        return text[:max_len - 1] + "…"

    # ------------------------------------------------------------------
    # Persistence helpers

    def save_scenes(self, scenes: list[SceneDefinition], path: str | Path) -> None:
        Path(path).write_text(
            json.dumps([s.to_dict() for s in scenes], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Saved %d scenes to %s", len(scenes), path)

    def load_scenes(self, path: str | Path) -> list[SceneDefinition]:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        scenes = [SceneDefinition.from_dict(d) for d in data]
        logger.info("Loaded %d scenes from %s", len(scenes), path)
        return scenes


# ---------------------------------------------------------------------------
# Script file loader
# ---------------------------------------------------------------------------

def load_script_file(path: str | Path) -> str:
    """Load a .txt or .md script file, returning its text content."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Script file not found: {path}")
    return p.read_text(encoding="utf-8").strip()
