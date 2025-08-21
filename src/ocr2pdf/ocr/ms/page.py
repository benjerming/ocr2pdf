from __future__ import annotations

import json
import unittest
from dataclasses import dataclass
from typing import IO

import cattrs

from ...common.geometry import Rect
from ...common.lazyproperty import lazyproperty
from ...common.settings import get_settings


@dataclass
class Word:
    """
    Represents a word in the OCR result.
    """

    text: str
    boundingPolygon: Rect
    confidence: float

    @property
    def rect(self) -> Rect:
        return self.boundingPolygon

    @rect.setter
    def rect(self, rect: Rect):
        self.boundingPolygon = rect


@dataclass
class Line:
    """
    Represents a line in the OCR result.
    """

    text: str
    boundingPolygon: Rect
    words: list[Word]

    @property
    def rect(self) -> Rect:
        return self.boundingPolygon

    @rect.setter
    def rect(self, rect: Rect):
        self.boundingPolygon = rect


@dataclass(repr=False)
class Page:
    """
    Represents a page in the OCR result.
    """

    lines: list[Line]

    @classmethod
    def load(cls, f: IO[str]) -> list[Page]:
        """
        Load OCR result from a JSON file.
        """
        return cls.loads(f.read())

    @classmethod
    def loads(cls, s: str) -> list[Page]:
        """
        Load OCR result from a JSON string.
        """
        converter = cattrs.Converter()

        def map_quad_to_rect(points: list[dict[str, int]], cls: type[Rect]):
            ul, ur, lr, ll = points
            x0 = min(ul["x"], ur["x"], lr["x"], ll["x"])
            y0 = min(ul["y"], ur["y"], lr["y"], ll["y"])
            x1 = max(ul["x"], ur["x"], lr["x"], ll["x"])
            y1 = max(ul["y"], ur["y"], lr["y"], ll["y"])
            return cls(x0, y0, x1, y1)

        converter.register_structure_hook(Rect, map_quad_to_rect)
        return converter.structure(json.loads(s), list[Page])

    def dump(self):
        settings = get_settings()
        if settings.dump is None:
            return
        if not settings.dump_ocr_word_rect and not settings.dump_ocr_line_rect:
            return

        import cv2

        img = cv2.imread(str(settings.input_img_path))
        for i, line in enumerate(self.lines, 1):
            if settings.dump_ocr_word_rect:
                for word in line.words:
                    cv2.rectangle(
                        img,
                        tuple(word.boundingPolygon.p0),
                        tuple(word.boundingPolygon.p1),
                        (0, 0, 255),
                        1,
                    )
            if settings.dump_ocr_line_rect:
                cv2.putText(
                    img,
                    f"{i}",
                    tuple(line.boundingPolygon.p0),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 0, 255),
                    2,
                )
                cv2.rectangle(
                    img,
                    tuple(line.boundingPolygon.p0),
                    tuple(line.boundingPolygon.p1),
                    (255, 0, 0),
                    1,
                )

        settings.dump.mkdir(parents=True, exist_ok=True)
        stem = settings.input_img_path.stem
        dump_path = settings.dump / f"{stem}.ocr.png"
        cv2.imwrite(str(dump_path), img)

    @lazyproperty
    def rect(self) -> Rect:
        return Rect(
            x0=min(line.boundingPolygon.x0 for line in self.lines),
            y0=min(line.boundingPolygon.y0 for line in self.lines),
            x1=max(line.boundingPolygon.x1 for line in self.lines),
            y1=max(line.boundingPolygon.y1 for line in self.lines),
        )

    def __repr__(self) -> str:
        return f"Page(lines={len(self.lines)}, rect={self.rect})"


class TestOCRPage(unittest.TestCase):
    def test_load(self):
        with open("input/01.ms.json", "r", encoding="utf-8") as f:
            ocr_pages = Page.load(f)
        self.assertEqual(len(ocr_pages), 1)

    def test_loads(self):
        with open("input/01.ms.json", "r", encoding="utf-8") as f:
            s = f.read()
        ocr_pages = Page.loads(s)
        self.assertEqual(len(ocr_pages), 1)
