"""A heap implementation for the lru cache."""
from dataclasses import dataclass
from enum import Enum, auto
from heapq import heappop, heappush
from itertools import count
from typing import Any, Generic, NamedTuple, Self, TypeVar

# _states = Enum("states", "REMOVED")


class _State(int, Enum):
    PRESENT = auto()
    REMOVED = auto()


@dataclass
class _Node:
    obj: Any
    state: _State
    weight: int

    def __eq__(self, other: Self) -> bool:
        return self.weight == other.weight

    def __lt__(self, other: Self) -> bool:
        return self.weight < other.weight

    def __gt__(self, other: Self) -> bool:
        return self.weight > other.weight


_T = TypeVar("_T")


class Heap(Generic[_T]):
    """A heap where node weighting comes from insertion order."""

    def __init__(self, initial=None):
        self._heap = []
        self._heap_map = {}
        self._count = count()
        if initial:
            for x in initial:
                self.push(x)

    def __len__(self):
        return len(self._heap)

    @property
    def entries(self) -> tuple:
        return tuple(self._heap_map.keys())

    def __contains__(self, x: _T):
        return x in self._heap_map

    def remove(self, item: _T):
        """Remove an entry by"""
        node = self._heap_map.pop(item)
        # Mark for removal when heap popped
        node.state = _State.REMOVED

    def pop(self) -> _T:
        """Pop."""
        while (node := heappop(self._heap)).state is _State.REMOVED:
            pass
        del self._heap_map[node.obj]
        return node.obj

    def push(self, item: _T):
        """Push."""
        node = _Node(item, _State.PRESENT, next(self._count))
        self._heap_map[item] = node  # keep reference for out-of-order operations
        heappush(self._heap, node)

    def move_to_top(self, item: Any):
        """Move an item to the top of the queue, i.e max valued."""
        self.remove(item)
        self.push(item)
