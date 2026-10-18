"""Rate-limited, cached EDGAR fetcher. Every URL is fetched at most once."""
import gzip
import hashlib
import os
import threading
import time
from pathlib import Path

import requests

BASE = "https://www.sec.gov"


class RateLimiter:
    def __init__(self, per_sec: float):
        self.interval = 1.0 / per_sec
        self.lock = threading.Lock()
        self.next_t = 0.0

    def wait(self):
        with self.lock:
            now = time.monotonic()
            t = max(now, self.next_t)
            self.next_t = t + self.interval
        delay = t - now
        if delay > 0:
            time.sleep(delay)


class Edgar:
    def __init__(self, cfg: dict):
        e = cfg["edgar"]
        self.cache = Path(e["cache_dir"])
        self.cache.mkdir(parents=True, exist_ok=True)
        self.limiter = RateLimiter(e["rate_limit_per_sec"])
        self.timeout = e.get("timeout_sec", 60)
        self.headers = {
            "User-Agent": e["user_agent"],
            "Accept-Encoding": "gzip, deflate",
        }   # Host is set by requests from the URL (data.sec.gov and www.sec.gov both used)
        self._local = threading.local()

    def _session(self) -> requests.Session:
        s = getattr(self._local, "s", None)
        if s is None:
            s = requests.Session()
            s.headers.update(self.headers)
            self._local.s = s
        return s

    def cache_path(self, url: str) -> Path:
        rel = url.replace(BASE + "/", "")
        if len(rel) > 200:
            rel = hashlib.sha1(rel.encode()).hexdigest()
        return self.cache / "raw" / (rel + ".gz")

    def get(self, url: str, force: bool = False) -> bytes:
        p = self.cache_path(url)
        if p.exists() and not force:
            with gzip.open(p, "rb") as f:
                return f.read()
        if os.environ.get("EDGAR_OFFLINE"):      # notebook runs from cache only: a miss is an error, never a fetch
            raise RuntimeError(f"EDGAR_OFFLINE is set and {url} is not in the cache ({p})")
        data = self._fetch(url)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        with gzip.open(tmp, "wb", compresslevel=6) as f:
            f.write(data)
        tmp.replace(p)
        return data

    def _fetch(self, url: str) -> bytes:
        last = None
        for attempt in range(6):
            self.limiter.wait()
            try:
                r = self._session().get(url, timeout=self.timeout)
            except requests.RequestException as ex:
                last = ex
                time.sleep(2 ** attempt)
                continue
            if r.status_code == 200:
                return r.content
            if r.status_code in (429, 503, 403):
                last = RuntimeError(f"HTTP {r.status_code}")
                time.sleep(5 * (attempt + 1))
                continue
            r.raise_for_status()
        raise RuntimeError(f"fetch failed {url}: {last}")

    def is_cached(self, url: str) -> bool:
        return self.cache_path(url).exists()


def submission_url(cik: str | int, accession: str) -> str:
    """Full submission text file (header + every document)."""
    acc_nodash = accession.replace("-", "")
    return f"{BASE}/Archives/edgar/data/{int(cik)}/{acc_nodash}/{accession}.txt"


def form_index_url(year: int, qtr: int) -> str:
    return f"{BASE}/Archives/edgar/full-index/{year}/QTR{qtr}/form.idx"
