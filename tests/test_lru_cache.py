import shutil
from pathlib import Path

import pytest

from mopidy_tidal.lru_cache import LruCache, SearchCache


@pytest.fixture
def lru_cache(config):
    cache_dir = config["core"]["cache_dir"]
    return LruCache(max_items_ram=8, persist=True, directory="cache")


def test_cache_public_attributes_respect_initialisation(config):
    l = LruCache(max_items_ram=1678, persist=True, directory="cache")
    assert l.max_items_ram == 1678
    assert l.persist
    l = LruCache(max_items_ram=1679, persist=False, directory="cache")
    assert l.max_items_ram == 1679
    assert not l.persist


def test_value_overwritten(lru_cache):
    assert not lru_cache.keys()
    lru_cache["tidal:uri:val"] = "initial"
    assert lru_cache["tidal:uri:val"] == "initial"
    lru_cache["tidal:uri:val"] = "hi"
    assert lru_cache["tidal:uri:val"] == "hi"


def test_simple_stored_objects_retrieved_correctly(lru_cache):
    assert not lru_cache.keys()
    lru_cache["tidal:uri:val"] = "hi"
    lru_cache["tidal:uri:none"] = None
    assert lru_cache["tidal:uri:val"] == "hi" == lru_cache.get("tidal:uri:val")
    assert lru_cache["tidal:uri:none"] is None
    assert len(lru_cache) == 2


def test_complex_stored_objects_retrieved_correctly(lru_cache):
    assert not lru_cache.keys()
    lru_cache["tidal:uri:otherval"] = {"complex": "object", "with": [0, 1]}
    assert (
        lru_cache["tidal:uri:otherval"]
        == {"complex": "object", "with": [0, 1]}
        == lru_cache.get("tidal:uri:otherval")
    )
    assert len(lru_cache) == 1


def test_failed_lookup_with_persistence_raises_keyerror(lru_cache):
    with pytest.raises(KeyError):
        lru_cache["tidal:uri:nonsuch"]


def test_failed_lookup_without_persistence_raises_keyerror(config):
    l = LruCache(persist=False)
    with pytest.raises(KeyError):
        l["tidal:uri:nonsuch"]


def test_update_sets_multiple_values(lru_cache):
    lru_cache.update({"tidal:uri:val": "hi", "tidal:uri:otherval": 17})
    assert lru_cache["tidal:uri:val"] == "hi"
    assert lru_cache["tidal:uri:otherval"] == 17
    assert "tidal:uri:val" in lru_cache
    assert "tidal:uri:nonesuch" not in lru_cache


@pytest.mark.gt_3_7
@pytest.mark.gt_3_8
def test_orequals_update_set_multiple_values(lru_cache):
    assert "tidal:uri:val" not in lru_cache
    lru_cache |= {"tidal:uri:val": "hi", "tidal:uri:otherval": 17}
    assert lru_cache["tidal:uri:val"] == "hi"
    assert lru_cache["tidal:uri:otherval"] == 17


def test_get_default_returns_default(lru_cache):
    uniq = object()
    assert lru_cache.get("tidal:uri:nonsuch", default=uniq) is uniq


def test_prune_removes_key(lru_cache):
    lru_cache.update({"tidal:uri:val": "hi", "tidal:uri:otherval": 17})
    assert "tidal:uri:val" in lru_cache
    lru_cache.prune("tidal:uri:val")
    assert "tidal:uri:val" not in lru_cache
    assert "tidal:uri:otherval" in lru_cache


def test_prune_all_removes_all(lru_cache):
    lru_cache.update({"tidal:uri:val": "hi", "tidal:uri:otherval": 17})
    assert "tidal:uri:val" in lru_cache
    assert "tidal:uri:otherval" in lru_cache
    lru_cache.prune_all()
    assert "tidal:uri:val" not in lru_cache
    assert "tidal:uri:otherval" not in lru_cache
    assert len(lru_cache) == 0


def test_persisted_items_retrieved_by_new_instance(config):
    l = LruCache(max_items_ram=8, persist=True, directory="cache")
    l.update({"tidal:uri:val": "hi", "tidal:uri:otherval": 17, "tidal:uri:none": None})
    del l
    new_l = LruCache(max_items_ram=8, persist=True, directory="cache")
    new_l["tidal:uri:anotherval"] = 18
    assert new_l["tidal:uri:val"] == "hi"
    assert new_l["tidal:uri:otherval"] == 17
    assert new_l["tidal:uri:anotherval"] == 18
    assert new_l["tidal:uri:none"] is None


def test_corrupt_persisted_item_is_discarded(config):
    l = LruCache(max_items_ram=8, persist=True, directory="cache")
    l.update({"tidal:uri:val": "hi", "tidal:uri:otherval": 17})
    del l
    Path(config["core"]["cache_dir"], "tidal/cache/uri/tidal-uri-val.cache").write_text(
        "hahaha"
    )

    new_l = LruCache(max_items_ram=8, persist=True, directory="cache")
    assert new_l["tidal:uri:otherval"] == 17
    with pytest.raises(KeyError):
        new_l["tidal:uri:val"]


def test_item_deleted_from_disk_raises_keyerror(config):
    l = LruCache(max_items_ram=8, persist=True, directory="cache")
    l.update({"tidal:uri:val": "hi", "tidal:uri:otherval": 17})
    del l
    Path(config["core"]["cache_dir"], "tidal/cache/uri/tidal-uri-val.cache").unlink()

    new_l = LruCache(max_items_ram=8, persist=True, directory="cache")
    assert new_l["tidal:uri:otherval"] == 17
    with pytest.raises(KeyError):
        new_l["tidal:uri:val"]


def test_prune_nonexistent_item_continues_silently(config):
    l = LruCache(max_items_ram=8, persist=True, directory="cache")
    l["tidal:uri:val"] = "hi"
    l.prune("tidal:uri:nonsuch")


def test_prune_item_deleted_from_disk_continues_silently(config):
    l = LruCache(max_items_ram=8, persist=True, directory="cache")
    l.update({"tidal:uri:val": "hi", "tidal:uri:otherval": 17})
    del l
    Path(config["core"]["cache_dir"], "tidal/cache/uri/tidal-uri-val.cache").unlink()

    new_l = LruCache(max_items_ram=8, persist=True, directory="cache")
    assert not len(new_l)
    new_l.prune("tidal:uri:otherval")
    new_l.prune("tidal:uri:val")


def test_cache_is_limited_by_max_items_in_ram(lru_cache):
    lru_cache.update({f"tidal:uri:{val}": val for val in range(8)})
    assert len(lru_cache) == 8
    lru_cache["tidal:uri:8"] = 8
    assert lru_cache == {f"tidal:uri:{val}": val for val in range(1, 9)}


def test_unlimited_cache_grows_without_limit_in_ram(config):
    l = LruCache(max_items_ram=0, persist=False)
    assert not l.max_items_ram
    l.update({f"tidal:uri:{val}": val for val in range(2**12)})
    assert len(l) == 2**12


def test_migrate_moves_old_file(lru_cache):
    uri = "tidal:uri:val"
    value = "hi"
    lru_cache[uri] = value
    assert lru_cache[uri] == value

    cache_file = lru_cache.cache_file(uri)
    new_style_cache_file = cache_file.with_stem("-".join(uri.split(":")))
    assert cache_file == new_style_cache_file, "Cache filename not dash-separated"

    # Rename the cache filename to match the old file format
    old_style_cache_dir = cache_file.parent / "va"
    old_style_cache_dir.mkdir()
    old_style_cache_file = cache_file.parent / f"va/{uri}.cache"
    cache_file.rename(old_style_cache_file)

    # Remove the in-memory cache element in order to force a filesystem reload
    lru_cache.pop(uri)
    cached_value = lru_cache.get(uri)
    assert cached_value == value

    assert new_style_cache_file.exists()
    assert not old_style_cache_file.exists()


def test_migrate_deletes_old_file_when_new_present(lru_cache):
    uri = "tidal:uri:val"
    value = "hi"
    lru_cache[uri] = value
    assert lru_cache[uri] == value

    cache_file = lru_cache.cache_file(uri)
    new_style_cache_file = cache_file.with_stem("-".join(uri.split(":")))
    assert cache_file == new_style_cache_file, "Cache filename not dash-separated"

    old_style_cache_dir = cache_file.parent / "va"
    old_style_cache_dir.mkdir()
    old_style_cache_file = cache_file.parent / f"va/{uri}.cache"
    shutil.copy(cache_file, old_style_cache_file)
    assert old_style_cache_file.exists()

    # Remove the in-memory cache element in order to force a filesystem reload
    lru_cache.pop(uri)
    cached_value = lru_cache.get(uri)
    assert cached_value == value
    assert new_style_cache_file.exists()
    assert not old_style_cache_file.exists()


@pytest.mark.xfail
def test_cache_is_lru(lru_cache):
    lru_cache.update({f"tidal:uri:{val}": val for val in range(8)})
    lru_cache["tidal:uri:0"]
    lru_cache["tidal:uri:8"] = 8
    assert lru_cache == {f"tidal:uri:{val}": val for val in (0, *range(2, 9))}
