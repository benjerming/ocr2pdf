from __future__ import annotations

from typing import Any, Callable, Generic, TypeVar

T = TypeVar("T")


class lazyproperty(Generic[T]):
    def __init__(self, func: Callable[..., T]) -> None:
        self.func = func
        self.attr_name = func.__name__

    def __get__(self, instance: Any, owner: type | None = None) -> T:
        if instance is None:
            return self  # type: ignore

        if not hasattr(instance, f"_cached_{self.attr_name}"):
            value = self.func(instance)
            setattr(instance, f"_cached_{self.attr_name}", value)

        return getattr(instance, f"_cached_{self.attr_name}")

    def __set_name__(self, owner: type, name: str) -> None:
        self.attr_name = name
