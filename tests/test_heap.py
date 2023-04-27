import pytest

from mopidy_tidal.heap import Heap


def test_push_pop_returns_data_in_correct_order():
    h = Heap()
    data = ["a", "c", "d"]
    for x in data:
        h.push(x)
    assert data == [h.pop() for _ in range(3)]


def test_heap_returns_data_in_order_passed_at_initialisation():
    data = ["a", "c", "d", "new"]
    h = Heap(data)
    assert data == [h.pop() for _ in range(4)]


def test_removed_data_is_discarded():
    data = ["a", "c", "d", "new"]
    h = Heap(data)
    h.remove("d")
    data.remove("d")
    assert data == [h.pop() for _ in range(3)]
    assert not h._heap_map, "Memory leak"
    assert not h._heap, "Memory leak"


def test_move_to_top_moves_to_next_pop():
    data = ["a", "c", "d", "new"]
    h = Heap(data)
    h.move_to_top("c")
    assert ["a", "d", "new", "c"] == [h.pop() for _ in range(4)]


def test_attempt_to_remove_nonexistent_data_raises_keyerror():
    data = ["a", "c", "d", "new"]
    h = Heap(data)
    with pytest.raises(KeyError):
        h.remove("asdf")


def test_attempt_to_move_to_top_nonexistent_data_raises_key_error_and_leaves_heap_unmodified():
    data = ["a", "c", "d", "new"]
    h = Heap(data)
    _heap = h._heap[:]
    _heap_map = h._heap_map.copy()
    with pytest.raises(KeyError):
        h.move_to_top("asdf")
    assert h._heap == _heap, "heap modified"
    assert h._heap_map == _heap_map, "heap modified"


def test_heap_len():
    data = ["a", "c", "d", "new"]
    h = Heap(data)
    assert len(h) == 4
    h.push("newer")
    assert len(h) == 5
    for _ in range(2):
        h.pop()
    assert len(h) == 3


def test_heap_contains():
    data = ["a", "c", "d", "new"]
    h = Heap(data)
    assert all(x in h for x in data)
    assert "nonsuch" not in h


def test_heap_entries():
    data = ("a", "c", "d", "new")
    h = Heap(data)
    assert h.entries == data
    h.push("newer")
    assert h.entries == (*data, "newer")
