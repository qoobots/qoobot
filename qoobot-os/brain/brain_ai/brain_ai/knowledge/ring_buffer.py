"""
brain_ai/knowledge/ring_buffer.py — Fixed-size circular buffer for recent events.
"""
from __future__ import annotations

from collections import deque
from threading import Lock
from typing import Generic, Iterator, TypeVar

T = TypeVar("T")


class RingBuffer(Generic[T]):
    """
    Thread-safe fixed-capacity ring buffer (FIFO).
    Oldest items are evicted when capacity is exceeded.
    """

    def __init__(self, capacity: int = 100) -> None:
        self._capacity = capacity
        self._buf: deque[T] = deque(maxlen=capacity)
        self._lock = Lock()

    def push(self, item: T) -> None:
        with self._lock:
            self._buf.append(item)

    def pop(self) -> T:
        with self._lock:
            return self._buf.popleft()

    def peek_last(self, n: int = 1) -> list[T]:
        with self._lock:
            items = list(self._buf)
            return items[-n:] if n <= len(items) else items[:]

    def peek_first(self, n: int = 1) -> list[T]:
        with self._lock:
            return list(self._buf)[:n]

    def all(self) -> list[T]:
        with self._lock:
            return list(self._buf)

    def clear(self) -> None:
        with self._lock:
            self._buf.clear()

    def __len__(self) -> int:
        return len(self._buf)

    def __iter__(self) -> Iterator[T]:
        with self._lock:
            yield from list(self._buf)

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def is_full(self) -> bool:
        return len(self._buf) >= self._capacity
