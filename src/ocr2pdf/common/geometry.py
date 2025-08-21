from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterator


class Vector1D:
    def __init__(self, start: int, end: int):
        self.start = start
        self.end = end

    def copy(self) -> Vector1D:
        return Vector1D(self.start, self.end)

    @property
    def center(self) -> int:
        return round((self.start + self.end) * 0.5)

    def intersects(self, other: Vector1D) -> bool:
        return self.start < other.end and self.end > other.start

    def contains(self, other: Vector1D) -> bool:
        return self.start <= other.start < other.end <= self.end

    def at_left_of(self, other: Vector1D) -> bool:
        return self.end <= other.start

    def at_right_of(self, other: Vector1D) -> bool:
        return self.start >= other.end

    def contains_left_of(self, other: Vector1D) -> bool:
        return self.start < other.start < other.end

    def contains_right_of(self, other: Vector1D) -> bool:
        return self.start < other.end < self.end

    def contains_by(self, other: Vector1D) -> bool:
        return other.contains(self)

    def __repr__(self) -> str:
        return f"Vector1D({self.start}, {self.end})"


class Vector2D:
    def __init__(self, start: Point, end: Point):
        self.start = start
        self.end = end

    @property
    def delta_x(self) -> int:
        return self.end.x - self.start.x

    @property
    def delta_y(self) -> int:
        return self.end.y - self.start.y

    @property
    def length(self) -> float:
        return math.sqrt(self.delta_x**2 + self.delta_y**2)

    def copy(self) -> Vector2D:
        return Vector2D(self.start.copy(), self.end.copy())

    def moveto(self, start: Point) -> Vector2D:
        return Vector2D(start, self.end)

    def moveto_xy(self, x: int, y: int) -> Vector2D:
        return self.moveto(Point(x, y))

    def direct_to(self, other: Point) -> Vector2D:
        return Vector2D(self.start, other.copy())

    def direct_to_xy(self, x: int, y: int) -> Vector2D:
        return self.direct_to(Point(x, y))

    def __repr__(self) -> str:
        return f"Vector2D({self.start}, {self.end})"


@dataclass(unsafe_hash=True, frozen=True)
class Point:
    x: int
    y: int

    def copy(self) -> Point:
        return Point(self.x, self.y)

    def __iter__(self) -> Iterator[int]:
        yield self.x
        yield self.y

    def __getitem__(self, index: int) -> int:
        match index:
            case 0:
                return self.x
            case 1:
                return self.y
            case _:
                raise IndexError(f"Point index out of range: {index}")

    def __len__(self) -> int:
        return 2

    def __repr__(self) -> str:
        return f"Point({self.x}, {self.y})"


@dataclass(unsafe_hash=True, frozen=True)
class Rect:
    x0: int = field(default=0)
    y0: int = field(default=0)
    x1: int = field(default=0)
    y1: int = field(default=0)

    @classmethod
    def from_cv(cls, img) -> Rect: # img: MatLike
        return cls(0, 0, img.shape[1], img.shape[0])

    @classmethod
    def from_seq(cls, *args: int | float) -> Rect:
        return cls(
            math.floor(args[0]),
            math.floor(args[1]),
            math.ceil(args[2]),
            math.ceil(args[3]),
        )

    @property
    def size(self) -> tuple[int, int]:
        return self.w, self.h

    @property
    def p0(self) -> Point:
        return Point(self.x0, self.y0)

    @property
    def p1(self) -> Point:
        return Point(self.x1, self.y1)

    @property
    def w(self):
        return self.x1 - self.x0

    @property
    def h(self):
        return self.y1 - self.y0

    @property
    def center(self) -> Point:
        return Point(self.center_x, self.center_y)

    @property
    def center_x(self) -> int:
        return round((self.x0 + self.x1) * 0.5)

    @property
    def center_y(self) -> int:
        return round((self.y0 + self.y1) * 0.5)

    @property
    def area(self):
        return self.w * self.h

    def copy(self) -> Rect:
        return Rect(self.x0, self.y0, self.x1, self.y1)

    def empty(self) -> bool:
        return self.w <= 0 or self.h <= 0

    def moveto(self, x0: int | None = None, y0: int | None = None) -> Rect:
        if x0 is None:
            x0 = self.x0
        if y0 is None:
            y0 = self.y0
        return Rect(x0, y0, x0 + self.w, y0 + self.h)

    def move(self, dx: int | None = None, dy: int | None = None) -> Rect:
        if dx is None:
            dx = 0
        if dy is None:
            dy = 0
        return Rect(self.x0 + dx, self.y0 + dy, self.x1 + dx, self.y1 + dy)

    def with_x0(self, x0: int) -> Rect:
        return Rect(x0, self.y0, self.x1, self.y1)

    def with_y0(self, y0: int) -> Rect:
        return Rect(self.x0, y0, self.x1, self.y1)

    def with_x1(self, x1: int) -> Rect:
        return Rect(self.x0, self.y0, x1, self.y1)

    def with_y1(self, y1: int) -> Rect:
        return Rect(self.x0, self.y0, self.x1, y1)

    def with_w(self, w: int) -> Rect:
        return Rect(self.x0, self.y0, self.x0 + w, self.y1)

    def with_h(self, h: int) -> Rect:
        return Rect(self.x0, self.y0, self.x1, self.y0 + h)

    def with_size(self, w: int, h: int) -> Rect:
        return Rect(self.x0, self.y0, self.x0 + w, self.y0 + h)

    def with_p0(self, p0: Point) -> Rect:
        return Rect(p0.x, p0.y, self.x1, self.y1)

    def with_p1(self, p1: Point) -> Rect:
        return Rect(self.x0, self.y0, p1.x, p1.y)

    def expand(self, dx0: int = 0, dy0: int = 0, dx1: int = 0, dy1: int = 0) -> Rect:
        return Rect(self.x0 - dx0, self.y0 - dy0, self.x1 + dx1, self.y1 + dy1)

    def shrink(self, dx0: int = 0, dy0: int = 0, dx1: int = 0, dy1: int = 0) -> Rect:
        return self.expand(-dx0, -dy0, -dx1, -dy1)

    def relative_to(self, other: Rect) -> Rect:
        return Rect(
            self.x0 - other.x0,
            self.y0 - other.y0,
            self.x1 - other.x0,
            self.y1 - other.y0,
        )

    def relative_to_point(self, other: Point) -> Rect:
        return Rect(
            self.x0 - other.x,
            self.y0 - other.y,
            self.x1 - other.x,
            self.y1 - other.y,
        )

    def resize(
        self,
        x0: int | None = None,
        y0: int | None = None,
        x1: int | None = None,
        y1: int | None = None,
    ) -> Rect:
        return Rect(
            self.x0 if x0 is None else x0,
            self.y0 if y0 is None else y0,
            self.x1 if x1 is None else x1,
            self.y1 if y1 is None else y1,
        )

    def intersect(self, other: Rect) -> Rect:
        return Rect(
            max(self.x0, other.x0),
            max(self.y0, other.y0),
            min(self.x1, other.x1),
            min(self.y1, other.y1),
        )

    def union_xy(self, x: int, y: int) -> Rect:
        return Rect(
            min(self.x0, x),
            min(self.y0, y),
            max(self.x1, x),
            max(self.y1, y),
        )

    def union_point(self, point: Point) -> Rect:
        return self.union_xy(point.x, point.y)

    def union(self, other: Rect) -> Rect:
        return Rect(
            min(self.x0, other.x0),
            min(self.y0, other.y0),
            max(self.x1, other.x1),
            max(self.y1, other.y1),
        )

    def contains_xy(self, x: int, y: int) -> bool:
        return self.x0 <= x <= self.x1 and self.y0 <= y <= self.y1

    def contains_point(self, point: Point) -> bool:
        return self.contains_xy(point.x, point.y)

    def contains(self, other: Rect) -> bool:
        return self.contains_xy(other.x0, other.y0) and self.contains_xy(
            other.x1, other.y1
        )

    def intersects(self, other: Rect) -> bool:
        return (
            self.x0 < other.x1
            and self.x1 > other.x0
            and self.y0 < other.y1
            and self.y1 > other.y0
        )

    def equals(self, other: Rect) -> bool:
        return (
            self.x0 == other.x0
            and self.y0 == other.y0
            and self.x1 == other.x1
            and self.y1 == other.y1
        )

    def equals_tuple(self, other: tuple[int, int, int, int]) -> bool:
        return self.equals(Rect(*other))

    def __iter__(self) -> Iterator[int]:
        yield self.x0
        yield self.y0
        yield self.x1
        yield self.y1

    def __len__(self) -> int:
        return 4

    def __repr__(self) -> str:
        return (
            f"Rect({self.x0}, {self.y0}, {self.x1}, {self.y1}, w={self.w}, h={self.h})"
        )

    def __contains__(self, other: Rect) -> bool:
        return self.equals(other)

    def __and__(self, other: Rect) -> Rect:
        return self.intersect(other)

    def __or__(self, other: Rect) -> Rect:
        return self.union(other)

    def __getitem__(self, index: int) -> int:
        match index:
            case 0:
                return self.x0
            case 1:
                return self.y0
            case 2:
                return self.x1
            case 3:
                return self.y1
            case _:
                raise IndexError(f"Rect index out of range: {index}")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Rect):
            return False
        return self.equals(other)
