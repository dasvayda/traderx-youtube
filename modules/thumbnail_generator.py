"""
thumbnail_generator.py — YouTube thumbnail image generation.

Providers:
  - pil  : Local text overlay (no API key, default)
  - openai : DALL-E 3 image generation
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

THUMBNAIL_WIDTH = 1280
THUMBNAIL_HEIGHT = 720


@dataclass
class ThumbnailResult:
    image_path: Path
    width: int
    height: int
    provider: str


class BaseThumbnailGenerator(ABC):
    @abstractmethod
    def generate(
        self,
        title: str,
        subtitle: str = "",
        output_path: Path | None = None,
    ) -> ThumbnailResult:
        ...


class PILThumbnailGenerator(BaseThumbnailGenerator):
    """Create a thumbnail with gradient background and text overlay."""

    def __init__(
        self,
        width: int = THUMBNAIL_WIDTH,
        height: int = THUMBNAIL_HEIGHT,
        output_dir: str | Path = "output",
    ):
        self._width = width
        self._height = height
        self._output_dir = Path(output_dir)

    def generate(
        self,
        title: str,
        subtitle: str = "",
        output_path: Path | None = None,
    ) -> ThumbnailResult:
        from PIL import Image, ImageDraw, ImageFont

        if not title.strip():
            raise ValueError("title must not be empty")

        out = output_path or (self._output_dir / "thumbnail.png")
        out.parent.mkdir(parents=True, exist_ok=True)

        img = Image.new("RGB", (self._width, self._height), (18, 18, 30))
        draw = ImageDraw.Draw(img)

        for y in range(self._height):
            ratio = y / self._height
            color = (
                int(18 + ratio * 20),
                int(18 + ratio * 10),
                int(30 + ratio * 40),
            )
            draw.line([(0, y), (self._width, y)], fill=color)

        try:
            font_title = ImageFont.truetype("arial.ttf", 64)
            font_sub = ImageFont.truetype("arial.ttf", 36)
        except OSError:
            font_title = ImageFont.load_default()
            font_sub = ImageFont.load_default()

        draw.text((60, 280), title[:60], font=font_title, fill=(255, 255, 255))
        if subtitle:
            draw.text((60, 400), subtitle[:80], font=font_sub, fill=(180, 200, 220))

        draw.rectangle([(0, 0), (self._width, 8)], fill=(38, 166, 154))
        img.save(str(out), format="PNG")

        logger.info("PIL thumbnail saved: %s", out)
        return ThumbnailResult(out, self._width, self._height, "pil")


class OpenAIThumbnailGenerator(BaseThumbnailGenerator):
    """Generate a thumbnail via DALL-E 3."""

    def __init__(self, model: str = "dall-e-3", size: str = "1792x1024"):
        from openai import OpenAI
        self._client = OpenAI()
        self._model = model
        self._size = size

    def generate(
        self,
        title: str,
        subtitle: str = "",
        output_path: Path | None = None,
    ) -> ThumbnailResult:
        out = output_path or Path("output/thumbnail.png")
        out.parent.mkdir(parents=True, exist_ok=True)

        prompt = (
            f"YouTube thumbnail for a stock market video. "
            f"Title: {title}. Subtitle: {subtitle}. "
            f"Bold text, dark finance theme, professional."
        )
        logger.info("OpenAI DALL-E thumbnail: %s", title[:40])

        response = self._client.images.generate(
            model=self._model,
            prompt=prompt,
            size=self._size,
            n=1,
        )
        image_url = response.data[0].url
        if not image_url:
            raise RuntimeError("DALL-E returned no image URL")

        import requests
        resp = requests.get(image_url, timeout=60)
        resp.raise_for_status()
        out.write_bytes(resp.content)

        return ThumbnailResult(out, THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT, "openai")


def create_thumbnail_generator(
    provider: str = "pil",
    **kwargs,
) -> BaseThumbnailGenerator:
    registry: dict[str, type[BaseThumbnailGenerator]] = {
        "pil": PILThumbnailGenerator,
        "openai": OpenAIThumbnailGenerator,
    }
    cls = registry.get(provider.lower())
    if cls is None:
        raise ValueError(f"Unknown thumbnail provider: {provider!r}. Choose from {list(registry)}")
    return cls(**kwargs)
