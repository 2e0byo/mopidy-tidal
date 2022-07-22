from __future__ import unicode_literals

import logging
import math
from collections import namedtuple
from hashlib import md5
from multiprocessing import Lock, Process
from pathlib import Path
from re import search
from time import sleep
from urllib.request import urlretrieve

from mopidy import backend

from mopidy_tidal import Extension, context
from mopidy_tidal.heap import Heap

logger = logging.getLogger(__name__)


def _parse_size(s: str) -> int:
    """Parse a human-readable file size into bytes."""
    number, unit = search("([0-9]+\.*[0-9]*) *([kmgt]*)", s.lower()).groups()
    multipliers = {"k": 1e3, "m": 1e6, "g": 1e9, "t": 1e12}
    return int(float(number) * multipliers.get(unit, 1))


_Download = namedtuple("_Download", "process, outf")


class CachingRetriever:
    MAX_DOWNLOADS = 2  # Max parallel downloads.  Setting this to 1 minimises bandwidth, but prevents returning to tracks which failed to buffer.

    def __init__(
        self,
        cache_dir: str,
        max_size: str = "300M",
        directory: str = "track_cache",
        timeout_s: int = 1,
    ):
        self._max_size = _parse_size(max_size)

        self._cache_dir = Path(cache_dir, directory).resolve()
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        for fn in self._cache_dir.glob("*.dirty"):
            fn.with_suffix("").unlink(missing_ok=True)
            fn.unlink()
        self._heap = Heap(
            sorted(self._cache_dir.glob("*"), key=lambda p: p.stat().st_atime)
        )
        self._lock = Lock()
        self.timeout_s = timeout_s
        self._background_downloads: list[_Download] = []

    @staticmethod
    def file_url(p: Path):
        """Generate the file url to a given path."""
        return f"file://{p.resolve()}"

    @staticmethod
    def hash(key: str):
        """Hash a key."""
        return md5(key.encode()).hexdigest()

    @staticmethod
    def _dirsize(d: Path) -> int:
        return sum(p.stat().st_size for p in d.glob("*") if p.is_file())

    def _oversize(self):
        return self._dirsize(self._cache_dir) > self._max_size

    def trim(self):
        """Trim cachedir."""
        while self._oversize():
            p = self._heap.pop()
            p.unlink()

    def _background_retrieve(self, url: str, outf: Path):
        """Retrieve url in background."""
        logger.debug("TIDAL Starting url retrieval")
        dirtyf = outf.with_suffix(".dirty")
        if dirtyf.exists():  # TODO race condition? probably not in practice.
            return
        dirtyf.write_text("")
        try:
            urlretrieve(url, str(outf))
            with self._lock:
                self._heap.push(outf)
        except Exception:
            outf.unlink(missing_ok=True)
        dirtyf.unlink()

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
        self._background_downloads = [
            d for d in self._background_downloads if d.process.is_alive()
        ]
        for download in self._background_downloads[self.MAX_DOWNLOADS - 1 :]:
            logger.debug("TIDAL Stopping previous track download.")

            download.process.terminate()
            download.process.join(1)
            if download.process.is_alive():
                download.process.kill()

            download.outf.unlink(missing_ok=True)
            download.outf.with_suffix(".dirty").unlink(missing_ok=True)

        download = _Download(
            Process(target=self._background_retrieve, args=(url, outf)), outf
        )
        download.process.start()
        self._background_downloads.append(download)
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
