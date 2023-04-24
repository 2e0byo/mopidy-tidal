import pytest

from mopidy_tidal.heap import Heap


def test_push_pop():
    h = Heap()
    data = ["a", "c", "d"]
    for x in data:
        h.push(x)
    assert data == [h.pop() for _ in range(3)]


def test_initial():
    data = ["a", "c", "d", "new"]
    h = Heap(data)
    assert data == [h.pop() for _ in range(4)]


def test_remove():
    data = ["a", "c", "d", "new"]
    h = Heap(data)
    h.remove("d")
    data.remove("d")
    assert data == [h.pop() for _ in range(3)]
    assert not h._heap_map, "Memory leak"
    assert not h._heap, "Memory leak"


def test_move_to_top():
    data = ["a", "c", "d", "new"]
    h = Heap(data)
    h.move_to_top("c")
    assert ["a", "d", "new", "c"] == [h.pop() for _ in range(4)]


def test_remove_nonexistent():
    data = ["a", "c", "d", "new"]
    h = Heap(data)
    with pytest.raises(KeyError):
        h.remove("asdf")


def test_move_to_top_nonexistent():
    data = ["a", "c", "d", "new"]
    h = Heap(data)
    _heap = h._heap[:]
    _heap_map = h._heap_map.copy()
    with pytest.raises(KeyError):
        h.move_to_top("asdf")
    assert h._heap == _heap, "heap modified"
    assert h._heap_map == _heap_map, "heap modified"


def test_len():
    data = ["a", "c", "d", "new"]
    h = Heap(data)
    assert len(h) == 4
    h.push("newer")
    assert len(h) == 5
    for _ in range(2):
        h.pop()
    assert len(h) == 3


def test_contains():
    data = ["a", "c", "d", "new"]
    h = Heap(data)
    assert all(x in h for x in data)
    assert "nonsuch" not in h


def test_entries():
    data = ("a", "c", "d", "new")
    h = Heap(data)
    assert h.entries == data
    h.push("newer")
    assert h.entries == (*data, "newer")
