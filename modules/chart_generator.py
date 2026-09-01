"""
chart_generator.py — 차트는 사용자가 직접 이미지로 첨부합니다.

이 모듈은 더 이상 차트를 자동 생성하지 않습니다.
사용자가 업로드한 차트 이미지 경로를 반환하는 단순 레지스트리 역할만 합니다.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# 씬별로 업로드된 차트 이미지 경로를 저장하는 레지스트리
# { scene_id: Path }
_chart_registry: dict[int, Path] = {}


def register_chart(scene_id: int, image_path: Path) -> None:
    """업로드된 차트 이미지를 씬 ID에 등록합니다."""
    _chart_registry[scene_id] = image_path
    logger.info("Chart registered for scene %d: %s", scene_id, image_path)


def get_chart(scene_id: int) -> Optional[Path]:
    """씬 ID에 등록된 차트 이미지 경로를 반환합니다. 없으면 None."""
    path = _chart_registry.get(scene_id)
    if path and path.exists():
        return path
    return None


def clear_registry() -> None:
    """레지스트리를 초기화합니다 (새 Job 시작 시 호출)."""
    _chart_registry.clear()


# app.py에서 직접 삭제 조작을 위해 노출
__all__ = ["register_chart", "get_chart", "clear_registry", "_chart_registry"]
