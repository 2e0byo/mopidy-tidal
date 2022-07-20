"""A heap implementation for the lru cache."""
from enum import Enum
from heapq import heappop, heappush
from itertools import count
from typing import Any


class Heap:
    _states = Enum("states", "REMOVED")

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
    def entries(self):
        return self._heap_map.keys()

    def __contains__(self, x: Any):
        return x in self._heap_map

    def remove(self, item: Any):
        """Remove an entry by"""
        el = self._heap_map.pop(item)
        el[1] = self._states.REMOVED

    def pop(self) -> Any:
        """Pop."""
        while (val := heappop(self._heap))[1] == self._states.REMOVED:
            pass
        del self._heap_map[val[1]]
        return val[1]

    def push(self, item: Any):
        """Push."""
        entry = [next(self._count), item]
        self._heap_map[item] = entry
        heappush(self._heap, entry)

    def move_to_top(self, item: Any):
        """Move an item to the top of the queue, i.e max valued."""
        self.remove(item)
        self.push(item)
