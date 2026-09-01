"""
asset_manager.py — Visual asset search, download, and local cache.

Searches Pexels and Pixabay for images and short video clips.
All downloads are cached locally by URL hash to avoid repeat fetches.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import quote_plus

import requests

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data Types
# ---------------------------------------------------------------------------

@dataclass
class AssetResult:
    asset_type: str          # "image" | "video"
    local_path: Path
    source_url: str
    provider: str
    query: str
    width: int = 0
    height: int = 0


# ---------------------------------------------------------------------------
# Cache Manager
# ---------------------------------------------------------------------------

class AssetCache:
    """Simple file-based cache keyed by (query, provider, index)."""

    def __init__(self, cache_dir: str | Path = "cache"):
        self._dir = Path(cache_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self._dir / "asset_index.json"
        self._index: dict[str, str] = self._load_index()

    def _load_index(self) -> dict[str, str]:
        if self._index_path.exists():
            return json.loads(self._index_path.read_text(encoding="utf-8"))
        return {}

    def _save_index(self) -> None:
        self._index_path.write_text(
            json.dumps(self._index, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _key(self, url: str) -> str:
        return hashlib.md5(url.encode()).hexdigest()

    def get(self, url: str) -> Optional[Path]:
        k = self._key(url)
        if k in self._index:
            p = Path(self._index[k])
            if p.exists():
                return p
        return None

    def put(self, url: str, data: bytes, suffix: str = ".jpg") -> Path:
        k = self._key(url)
        dest = self._dir / f"{k}{suffix}"
        dest.write_bytes(data)
        self._index[k] = str(dest)
        self._save_index()
        return dest


# ---------------------------------------------------------------------------
# Pexels Provider
# ---------------------------------------------------------------------------

class PexelsProvider:
    BASE = "https://api.pexels.com"

    def __init__(self, api_key: str, cache: AssetCache, per_page: int = 5):
        self._key = api_key
        self._cache = cache
        self._per_page = per_page

    def _headers(self) -> dict:
        return {"Authorization": self._key}

    def search_images(self, query: str) -> list[dict]:
        url = f"{self.BASE}/v1/search?query={quote_plus(query)}&per_page={self._per_page}&orientation=portrait"
        resp = requests.get(url, headers=self._headers(), timeout=10)
        resp.raise_for_status()
        return resp.json().get("photos", [])

    def search_videos(self, query: str) -> list[dict]:
        url = f"{self.BASE}/videos/search?query={quote_plus(query)}&per_page={self._per_page}&orientation=portrait"
        resp = requests.get(url, headers=self._headers(), timeout=10)
        resp.raise_for_status()
        return resp.json().get("videos", [])

    def download_image(self, photo: dict) -> Optional[AssetResult]:
        src_url = photo.get("src", {}).get("large2x") or photo.get("src", {}).get("large", "")
        if not src_url:
            return None
        cached = self._cache.get(src_url)
        if cached:
            return AssetResult("image", cached, src_url, "pexels", "")
        resp = requests.get(src_url, timeout=20)
        resp.raise_for_status()
        path = self._cache.put(src_url, resp.content, ".jpg")
        return AssetResult(
            "image", path, src_url, "pexels", "",
            width=photo.get("width", 0), height=photo.get("height", 0),
        )

    def download_video(self, video: dict) -> Optional[AssetResult]:
        files = video.get("video_files", [])
        # prefer HD portrait
        files_sorted = sorted(files, key=lambda f: f.get("height", 0), reverse=True)
        file = next((f for f in files_sorted if f.get("quality") in ("hd", "sd")), None)
        if not file:
            return None
        src_url = file["link"]
        cached = self._cache.get(src_url)
        if cached:
            return AssetResult("video", cached, src_url, "pexels", "")
        resp = requests.get(src_url, timeout=60, stream=True)
        resp.raise_for_status()
        data = b"".join(resp.iter_content(1024 * 64))
        path = self._cache.put(src_url, data, ".mp4")
        return AssetResult("video", path, src_url, "pexels", "")


# ---------------------------------------------------------------------------
# Pixabay Provider
# ---------------------------------------------------------------------------

class PixabayProvider:
    BASE = "https://pixabay.com/api"

    def __init__(self, api_key: str, cache: AssetCache, per_page: int = 5):
        self._key = api_key
        self._cache = cache
        self._per_page = per_page

    def search_images(self, query: str) -> list[dict]:
        url = (
            f"{self.BASE}/?key={self._key}&q={quote_plus(query)}"
            f"&per_page={self._per_page}&image_type=photo&orientation=vertical"
        )
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json().get("hits", [])

    def download_image(self, hit: dict) -> Optional[AssetResult]:
        src_url = hit.get("largeImageURL", "")
        if not src_url:
            return None
        cached = self._cache.get(src_url)
        if cached:
            return AssetResult("image", cached, src_url, "pixabay", "")
        resp = requests.get(src_url, timeout=20)
        resp.raise_for_status()
        path = self._cache.put(src_url, resp.content, ".jpg")
        return AssetResult("image", path, src_url, "pixabay", "",
                           width=hit.get("imageWidth", 0), height=hit.get("imageHeight", 0))


# ---------------------------------------------------------------------------
# Asset Manager (orchestrator)
# ---------------------------------------------------------------------------

class AssetManager:
    """
    High-level interface: given a scene, return a local asset path.

    Search priority:
    1. If visual_type == "stock_chart" → delegate to chart_generator
    2. Try Pexels (images first, then videos if footage requested)
    3. Try Pixabay as fallback
    4. Return placeholder if nothing found
    """

    def __init__(
        self,
        pexels_api_key: str = "",
        pixabay_api_key: str = "",
        cache_dir: str | Path = "cache",
        assets_dir: str | Path = "assets",
    ):
        self._cache = AssetCache(cache_dir)
        self._assets_dir = Path(assets_dir)

        self._pexels = PexelsProvider(pexels_api_key, self._cache) if pexels_api_key else None
        self._pixabay = PixabayProvider(pixabay_api_key, self._cache) if pixabay_api_key else None

    # ------------------------------------------------------------------

    def get_asset_for_scene(self, scene) -> Optional[Path]:
        """
        Return a local path (image or video) for the given SceneDefinition.
        Returns None if nothing could be fetched.
        """
        query = scene.visual_query or scene.ticker or "stock market"
        vtype = scene.visual_type

        if vtype == "footage":
            return self._fetch_video(query)
        else:
            return self._fetch_image(query)

    # ------------------------------------------------------------------

    def _fetch_image(self, query: str) -> Optional[Path]:
        logger.info("Fetching image for query: %r", query)

        if self._pexels:
            try:
                results = self._pexels.search_images(query)
                if results:
                    asset = self._pexels.download_image(results[0])
                    if asset:
                        logger.info("Pexels image: %s", asset.local_path)
                        return asset.local_path
            except Exception as exc:
                logger.warning("Pexels image search failed: %s", exc)

        if self._pixabay:
            try:
                results = self._pixabay.search_images(query)
                if results:
                    asset = self._pixabay.download_image(results[0])
                    if asset:
                        logger.info("Pixabay image: %s", asset.local_path)
                        return asset.local_path
            except Exception as exc:
                logger.warning("Pixabay image search failed: %s", exc)

        logger.warning("No image found for query: %r", query)
        return None

    def _fetch_video(self, query: str) -> Optional[Path]:
        logger.info("Fetching video clip for query: %r", query)

        if self._pexels:
            try:
                results = self._pexels.search_videos(query)
                if results:
                    asset = self._pexels.download_video(results[0])
                    if asset:
                        logger.info("Pexels video: %s", asset.local_path)
                        return asset.local_path
            except Exception as exc:
                logger.warning("Pexels video search failed: %s", exc)

        logger.warning("No video found for query: %r", query)
        return None
