from __future__ import unicode_literals

import logging
import math
from hashlib import md5
from pathlib import Path
from threading import Lock, Thread
from time import sleep
from urllib.request import urlretrieve

from mopidy import backend

from mopidy_tidal import Extension, context
from mopidy_tidal.heap import Heap

logger = logging.getLogger(__name__)


class CachingRetriever:
    def __init__(
        self,
        cache_dir: str,
        max_size: int = 100,
        directory: str = "track_cache",
        timeout_s: int = 1,
    ):
        if max_size and max_size <= 0:
            raise ValueError(f"Invalid cache size: {max_size}")

        self._cache_dir = Path(cache_dir, directory).resolve()
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        for fn in self._cache_dir.glob("*.dirty"):
            fn.with_suffix("").unlink(missing_ok=True)
            fn.unlink()
        self._heap = Heap(self._cache_dir.glob("*"))
        self._max_size = max_size
        self._lock = Lock()
        self.timeout_s = timeout_s

    @staticmethod
    def file_url(p: Path):
        """Generate the file url to a given path."""
        return f"file://{p.resolve()}"

    @staticmethod
    def hash(key: str):
        """Hash a key."""
        return md5(key.encode()).hexdigest()

    def trim(self):
        """Trim cachedir."""
        while len(self._heap) > self._max_size:
            p = self._heap.pop()
            p.unlink()

    def _background_retrieve(self, url: str, outf: Path):
        """Retrieve url in background."""
        logger.debug("Starting url retrieval")
        dirtyf = outf.with_suffix(".dirty")
        if dirtyf.exists():  # TODO race condition? probably not in practice.
            return
        dirtyf.write_text("")
        urlretrieve(url, str(outf))
        dirtyf.unlink()
        with self._lock:
            self._heap.push(outf)

    def cached(self, key: str):
        return key in self._heap

    @staticmethod
    def _viable(f: Path):
        BUFFER_SIZE = 2**18
        return f.exists() and f.stat().st_size > BUFFER_SIZE

    def get_cached(self, key: str) -> str:
        """Get a cached file."""
        outf = self._cache_dir / self.hash(key)
        self._heap.move_to_top(outf)
        self.trim()
        return self.file_url(outf)

    def download(self, key: str, url: str) -> str:
        """Download a file."""
        outf = self._cache_dir / self.hash(key)
        Thread(target=self._background_retrieve, args=(url, outf)).start()
        self.trim()

        attempt = 0
        max_attempts = math.ceil(self.timeout_s / 0.01)
        while not (viable := self._viable(outf)) and attempt < max_attempts:
            attempt += 1
            sleep(0.01)

        if not viable:
            raise Exception(f"Failed to fetch {key}.")

        return self.file_url(outf)

    def get(self, key: str, url: str) -> str:
        """Get the path to a file url, downloading if needed."""
        try:
            return self.get_cached(key)
        except KeyError:
            return self.download(key, url)


class TidalPlaybackProvider(backend.PlaybackProvider):
    def __init__(self, *args, **kwargs):
        config = context.get_config()["tidal"]
        self.caching_retriever = CachingRetriever(
            Extension.get_cache_dir(context.get_config()),
            max_size=config["track_cache_size"],
            timeout_s=config["track_cache_timeout"],
        )
        self._cache_enabled = config["track_cache_enabled"]
        super().__init__(*args, **kwargs)

    def translate_uri(self, uri):
        logger.info("TIDAL uri: %s", uri)
        parts = uri.split(":")
        track_id = int(parts[4])
        if self._cache_enabled:
            try:
                final_url = self.caching_retriever.get_cached(uri)
            except KeyError:
                remote_url = self.backend._session.get_media_url(track_id)
                final_url = self.caching_retriever.get(uri, remote_url)
        else:
            final_url = self.backend._session.get_media_url(track_id)

        logger.info("transformed into %s", final_url)
        return final_url
