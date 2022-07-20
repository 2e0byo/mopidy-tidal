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
