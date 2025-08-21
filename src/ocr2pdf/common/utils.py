from __future__ import annotations

from typing import overload


@overload
def clamp(x: int, lb: int, ub: int) -> int: ...


@overload
def clamp(x: float, lb: float, ub: float) -> float: ...


def clamp(x: int | float, lb: int | float, ub: int | float) -> int | float:
    return max(lb, min(x, ub))
