"""Unit tests for modules/thumbnail_generator.py."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from modules.thumbnail_generator import (
    PILThumbnailGenerator,
    THUMBNAIL_HEIGHT,
    THUMBNAIL_WIDTH,
    create_thumbnail_generator,
)


class TestPILThumbnailGenerator(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._out_dir = Path(self._tmpdir.name)

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_generates_png_file(self):
        gen = PILThumbnailGenerator(output_dir=self._out_dir)
        out = self._out_dir / "test_thumb.png"
        result = gen.generate("NVDA Record High", "AI Stocks Rally", out)

        self.assertTrue(result.image_path.exists())
        self.assertEqual(result.provider, "pil")
        self.assertEqual(result.width, THUMBNAIL_WIDTH)
        self.assertEqual(result.height, THUMBNAIL_HEIGHT)

    def test_empty_title_raises(self):
        gen = PILThumbnailGenerator(output_dir=self._out_dir)
        with self.assertRaises(ValueError):
            gen.generate("  ", output_path=self._out_dir / "bad.png")

    def test_factory_creates_pil(self):
        gen = create_thumbnail_generator("pil", output_dir=self._out_dir)
        self.assertIsInstance(gen, PILThumbnailGenerator)

    def test_factory_rejects_unknown(self):
        with self.assertRaises(ValueError):
            create_thumbnail_generator("unknown")


if __name__ == "__main__":
    unittest.main()
