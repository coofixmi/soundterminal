import hashlib
import os
import re
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.myinstants.com"
TRENDING_URL = f"{BASE_URL}/en/index/us/"
SEARCH_URL = f"{BASE_URL}/en/search/"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0 Safari/537.36 SoundpadApp/1.0"
)


class MyInstantsScraper:
    def __init__(self, cache_dir: Path, timeout: int = 15):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def fetch_trending(self, page: int = 1) -> List[Dict[str, str]]:
        try:
            page = int(page)
        except Exception:
            page = 1
        if page < 1:
            page = 1
        url = TRENDING_URL if page == 1 else f"{TRENDING_URL}?page={page}"
        return self._fetch_page(url)

    def search(self, query: str, page: int = 1) -> List[Dict[str, str]]:
        q = (query or "").strip()
        if not q:
            return self.fetch_trending(page=page)
        try:
            page = int(page)
        except Exception:
            page = 1
        if page < 1:
            page = 1
        url = f"{SEARCH_URL}?name={quote_plus(q)}&page={page}"
        return self._fetch_page(url)

    def _fetch_page(self, url: str) -> List[Dict[str, str]]:
        try:
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
        except Exception as e:
            print(f"[scraper] fetch error {url}: {e}")
            return []
        return self._parse_instants(resp.text)

    def _parse_instants(self, html: str) -> List[Dict[str, str]]:
        soup = BeautifulSoup(html, "html.parser")
        results: List[Dict[str, str]] = []
        seen = set()

        # primary selector; fallback to any button with play(...) onclick
        buttons = soup.select("button.small-button")
        if not buttons:
            buttons = soup.select("button[onclick*='play(']")

        for btn in buttons:
            onclick = btn.get("onclick") or ""
            # capture first argument of play('...') or play("..."); extra args allowed
            m = re.search(r"play\(\s*['\"]([^'\"]+)['\"]", onclick)
            if not m:
                continue
            sound_path = m.group(1).strip()
            if not sound_path:
                continue
            mp3_url = urljoin(BASE_URL + "/", sound_path.lstrip("/"))

            inst_div = btn.find_parent(class_="instant")
            name = None
            if inst_div:
                link = inst_div.select_one(".instant-link")
                if link:
                    name = link.get_text(strip=True)
            if not name:
                name = btn.get("title") or os.path.basename(sound_path.split("?")[0]) or "sound"

            key = mp3_url
            if key in seen:
                continue
            seen.add(key)
            results.append(
                {
                    "id": hashlib.sha1(mp3_url.encode("utf-8")).hexdigest()[:16],
                    "name": name,
                    "url": mp3_url,
                }
            )
        return results

    def cache_path_for(self, sound: Dict[str, str]) -> Path:
        url = sound.get("url", "")
        sid = sound.get("id") or hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
        name = os.path.basename(url.split("?")[0]) or f"{sid}.mp3"
        name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
        if not name.lower().endswith(".mp3"):
            name += ".mp3"
        return self.cache_dir / f"{sid}_{name}"

    def ensure_cached(self, sound: Dict[str, str]) -> Optional[Path]:
        url = sound.get("url")
        if not url:
            return None
        path = self.cache_path_for(sound)
        if path.exists() and path.stat().st_size > 0:
            return path
        try:
            with self.session.get(url, stream=True, timeout=self.timeout) as r:
                r.raise_for_status()
                tmp = path.with_suffix(path.suffix + ".tmp")
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                tmp.replace(path)
            return path
        except Exception as e:
            print(f"[scraper] download error {url}: {e}")
            try:
                if path.exists():
                    path.unlink()
            except Exception:
                pass
            try:
                tmp = path.with_suffix(path.suffix + ".tmp")
                if tmp.exists():
                    tmp.unlink()
            except Exception:
                pass
            return None

    def resolve_local_path(self, sound: Dict[str, str]) -> Optional[Path]:
        local = sound.get("local_path")
        if local:
            p = Path(local)
            if p.exists():
                return p
        return self.ensure_cached(sound)
