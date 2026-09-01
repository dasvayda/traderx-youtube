"""
scene_generator.py — LLM-powered scene enrichment.

Takes the raw list of SceneDefinitions produced by script_parser and
asks an LLM to fill in:
  - visual_type
  - visual_query (search keywords)
  - ticker (if applicable)
  - chart_period
  - transition
  - annotations
  - refined duration
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from modules.script_parser import SceneDefinition

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------

_SCENE_PLAN_SYSTEM = """\
あなたは米国株式市場に特化したYouTube Shortsのビデオプロデューサーです。
以下のナレーションシーンリストに対して、各シーンに最適なビジュアル情報を付加してください。

visual_type の選択肢:
- "stock_chart"   : 株価チャート（個別銘柄）
- "market_chart"  : 市場全体チャート（SPY, QQQ など）
- "company_image" : 企業ロゴ・製品画像
- "news_image"    : ニュース・決算スクリーンショット
- "footage"       : 金融・市場の映像クリップ
- "title_card"    : テキストのみのタイトルカード

出力はJSONの配列のみ。余分なテキスト・説明は不要。
必ず元のシーンIDと同じ順序で返してください。

各シーンのフィールド:
{
  "scene_id": <int>,
  "duration": <float, 秒>,
  "narration": "<そのまま>",
  "subtitle": "<40文字以内に要約>",
  "visual_type": "<上記から選択>",
  "visual_query": "<英語の検索キーワード>",
  "ticker": "<銘柄コードまたはnull>",
  "chart_period": "<1d|5d|1mo|3mo|6mo|1y, デフォルト1mo>",
  "transition": "<fade|slide|zoom|none>",
  "annotations": ["<注釈文字列>"]
}
"""


# ---------------------------------------------------------------------------
# SceneGenerator
# ---------------------------------------------------------------------------

class SceneGenerator:
    """Enriches raw scenes with LLM-derived visual metadata."""

    def __init__(self, llm_client: Any, model: str = "gpt-4o",
                 temperature: float = 0.4):
        """
        Args:
            llm_client: An openai.OpenAI() compatible client
                        (or any object with .chat.completions.create).
            model: Model identifier string.
            temperature: Sampling temperature.
        """
        self._client = llm_client
        self._model = model
        self._temperature = temperature

    # ------------------------------------------------------------------

    def enrich(self, scenes: list[SceneDefinition]) -> list[SceneDefinition]:
        """Send scenes to LLM and return enriched SceneDefinitions."""
        raw_list = [s.to_dict() for s in scenes]
        payload = json.dumps(raw_list, ensure_ascii=False, indent=2)

        logger.info("Sending %d scenes to LLM for enrichment", len(scenes))

        response = self._client.chat.completions.create(
            model=self._model,
            temperature=self._temperature,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _SCENE_PLAN_SYSTEM},
                {"role": "user", "content": f"以下のシーンリストを処理してください:\n{payload}"},
            ],
        )

        raw_content = response.choices[0].message.content
        enriched_data = self._parse_response(raw_content)

        result: list[SceneDefinition] = []
        for item in enriched_data:
            try:
                result.append(SceneDefinition.from_dict(item))
            except Exception as exc:
                logger.warning("Failed to parse scene item %s: %s", item, exc)

        if len(result) != len(scenes):
            logger.warning(
                "LLM returned %d scenes but expected %d; falling back to originals for mismatch",
                len(result), len(scenes),
            )
            result = self._merge_fallback(scenes, result)

        logger.info("Scene enrichment complete")
        return result

    # ------------------------------------------------------------------

    def _parse_response(self, content: str) -> list[dict]:
        """Extract JSON array from LLM response (handles wrapper objects)."""
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON array embedded in text
            match = re.search(r'\[.*\]', content, re.DOTALL)
            if match:
                data = json.loads(match.group())
            else:
                raise ValueError(f"Could not parse LLM response as JSON: {content[:200]}")

        if isinstance(data, dict):
            # LLM may wrap in {"scenes": [...]}
            for key in ("scenes", "scene_list", "items", "data"):
                if key in data and isinstance(data[key], list):
                    return data[key]
            # single-key dict
            values = list(data.values())
            if len(values) == 1 and isinstance(values[0], list):
                return values[0]
            raise ValueError(f"Unexpected JSON structure: {list(data.keys())}")

        if isinstance(data, list):
            return data

        raise ValueError(f"Expected list, got {type(data)}")

    def _merge_fallback(
        self, originals: list[SceneDefinition], enriched: list[SceneDefinition]
    ) -> list[SceneDefinition]:
        """Use enriched where scene_id matches, otherwise keep original."""
        enriched_map = {s.scene_id: s for s in enriched}
        return [enriched_map.get(s.scene_id, s) for s in originals]


# ---------------------------------------------------------------------------
# Convenience factory using settings
# ---------------------------------------------------------------------------

def create_scene_generator(provider: str = "openai", model: str = "gpt-4o",
                            temperature: float = 0.4) -> SceneGenerator:
    if provider == "openai":
        from openai import OpenAI
        client = OpenAI()
    else:
        raise NotImplementedError(f"Scene generator provider {provider!r} not yet implemented")

    return SceneGenerator(llm_client=client, model=model, temperature=temperature)
