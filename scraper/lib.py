"""Shared helpers for per-restaurant scrapers.

Per-restaurant modules import `fetch`, `Beer`, and `find_cheapest_beer` from
here. The generic `find_cheapest_beer` walks the page looking for an Öl /
Beer / Drinks heading and reads price + name + volume from the items that
follow. It is a starting point — most sites will need a small site-specific
selector override (see `scraper/restaurants/_template.py`).
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Iterable

import requests
from bs4 import BeautifulSoup, Tag

USER_AGENT = (
    "alkoholperkrona-bot/0.1 "
    "(+https://github.com/zune-b/testla-; daily menu scrape; respects robots.txt)"
)
REQUEST_TIMEOUT_S = 15
RATE_LIMIT_S = 1.0

_last_request_at = 0.0


def fetch(url: str) -> str:
    """GET `url` with a polite UA and a 1 req/s global rate limit."""
    global _last_request_at
    elapsed = time.monotonic() - _last_request_at
    if elapsed < RATE_LIMIT_S:
        time.sleep(RATE_LIMIT_S - elapsed)
    resp = requests.get(
        url,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "sv,en;q=0.8"},
        timeout=REQUEST_TIMEOUT_S,
    )
    _last_request_at = time.monotonic()
    resp.raise_for_status()
    return resp.text


@dataclass(frozen=True)
class Beer:
    name: str
    volume_cl: int | None
    price_sek: int

    @property
    def kr_per_cl(self) -> float | None:
        if not self.volume_cl:
            return None
        return round(self.price_sek / self.volume_cl, 2)

    def to_json(self) -> dict:
        return {
            "name": self.name,
            "volume_cl": self.volume_cl,
            "price_sek": self.price_sek,
            "kr_per_cl": self.kr_per_cl,
        }


_PRICE_RE = re.compile(r"(\d{2,4})\s*(?:kr|:-|sek)\b", re.IGNORECASE)
_PRICE_BARE_RE = re.compile(r"\b(\d{2,4})\b")
_VOLUME_RE = re.compile(r"(\d{2,3})\s*cl\b", re.IGNORECASE)
_BEER_HEADING_RE = re.compile(r"\b(öl|ol|beer|öl\s*&|drycker|dryck|drinks)\b", re.IGNORECASE)
_BEER_NEGATIVE_RE = re.compile(r"\b(vin|wine|cocktail|sprit|spirit|champagne)\b", re.IGNORECASE)


def parse_price(text: str) -> int | None:
    """Extract an SEK price like "89 kr", "89:-", "89 SEK"."""
    m = _PRICE_RE.search(text)
    if m:
        return int(m.group(1))
    return None


def parse_volume(text: str) -> int | None:
    """Extract a volume in cl like "50 cl"."""
    m = _VOLUME_RE.search(text)
    if m:
        return int(m.group(1))
    return None


def _strip(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _candidate_section(soup: BeautifulSoup) -> Tag | None:
    """Find the <section>/<div> following an Öl/Beer heading."""
    for h in soup.find_all(re.compile(r"^h[1-6]$")):
        heading_text = _strip(h.get_text())
        if _BEER_HEADING_RE.search(heading_text) and not _BEER_NEGATIVE_RE.search(heading_text):
            sibling = h.find_next_sibling()
            if sibling:
                return sibling
            return h.parent
    return None


def _iter_item_lines(scope: Tag) -> Iterable[str]:
    items = scope.find_all(["li", "p", "tr", "div"])
    if not items:
        for line in scope.get_text("\n").splitlines():
            yield _strip(line)
        return
    for it in items:
        yield _strip(it.get_text(" "))


def find_cheapest_beer(html: str) -> Beer | None:
    """Generic heuristic scraper.

    Strategy:
    1. Find a heading containing "öl"/"beer".
    2. In the section that follows, look at each item.
    3. For each item with a price + a name (plausibly a beer), keep it.
    4. Return the lowest-priced one.

    Returns None if nothing plausible was found — in which case the
    per-restaurant module should provide a site-specific override.
    """
    soup = BeautifulSoup(html, "lxml")
    section = _candidate_section(soup)
    scopes = [section] if section else [soup]
    candidates: list[Beer] = []
    for scope in scopes:
        for line in _iter_item_lines(scope):
            if not line or len(line) > 200:
                continue
            if _BEER_NEGATIVE_RE.search(line):
                continue
            price = parse_price(line)
            if price is None or price < 30 or price > 300:
                continue
            volume = parse_volume(line)
            name = _strip(re.sub(_PRICE_RE, "", line))
            name = _strip(re.sub(_VOLUME_RE, "", name)).rstrip(",.-– ")
            if not name or len(name) < 2:
                continue
            candidates.append(Beer(name=name[:80], volume_cl=volume, price_sek=price))
    if not candidates:
        return None
    return min(candidates, key=lambda b: b.price_sek)
