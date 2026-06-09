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


def fetch_bytes(url: str) -> bytes:
    """Like `fetch` but returns raw bytes (for PDF menus)."""
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
    return resp.content


def fetch_pdf_text(url: str) -> str:
    """Fetch a PDF and return its extracted plain text."""
    import io

    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(fetch_bytes(url)))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


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


# --- beer-line classification (shared by site-specific parsers) ---

# Strict positive match: beer styles + brands seen on Östermalm menus.
_BEER_WORD_RE = re.compile(
    r"\b(öl|veteöl|fatöl|beer|lager|ipa|ale|pils(?:ner)?|stout|porter|witbier"
    r"|weiss\w*|lambic|dunkel|hefe\w*"
    r"|mariestads?|menabrea|carlsberg|heineken|staropramen|kronenbourg"
    r"|kru[šs]ovice|norrlands|eriksberg|wisby|omaka|brooklyn|poppels|meteor"
    r"|murphy.?s|san miguel|omnipollo|guinness|paulaner|erdinger|estrella"
    r"|peroni|asahi|sapporo|pistonhead|nils oscar|stigbergets|spendrups)\b",
    re.IGNORECASE,
)
# Anything matching this is never a beer (wine, cider, spirits, soft drinks).
_NOT_BEER_RE = re.compile(
    r"\b(vin(?:er)?|wine|cocktail|drink|sprit|spirit|champagne|cider|cidre"
    r"|galipette|riesling|chardonnay|sauvignon|grappa|whisk\w*|rom|rum|gin"
    r"|vodka|tequila|mezcal|snaps|aquavit|akvavit|calvados|cognac|armagnac"
    r"|kaffe|coffee|juice|läsk|ginger beer|kombucha|mocktail)\b"
    r"|\b(19|20)\d{2}\b",  # vintage year => wine list entry
    re.IGNORECASE,
)
_NON_ALC_RE = re.compile(
    r"alkoholfri|non.?alcoholic|zero|0\s*[.,]\s*[0-5]\s*%", re.IGNORECASE
)
# "20cl 57:-" / "40cl 97" volume+price pairs (Svenska Brasserier format).
_VOL_PRICE_PAIR_RE = re.compile(r"(\d{1,3})\s*cl\s+(\d{2,3})(?:\s*:-)?\b")
# Bare price: 2-3 digits not part of a volume, percentage or decimal.
_BARE_PRICE_RE = re.compile(r"(?<![\d.,])\b(\d{2,3})\b(?!\s*(?:cl|%|[.,]\d))")

PRICE_MIN_SEK = 30
PRICE_MAX_SEK = 300


def is_beer_line(text: str) -> bool:
    """True if `text` names a beer (style/brand match, no wine/spirits words)."""
    return bool(_BEER_WORD_RE.search(text)) and not _NOT_BEER_RE.search(text)


def parse_price_and_volume(text: str) -> tuple[int, int | None] | None:
    """Extract (price_sek, volume_cl) from a menu line, lowest price wins."""
    pairs = [
        (int(p), int(v))
        for v, p in _VOL_PRICE_PAIR_RE.findall(text)
        if PRICE_MIN_SEK <= int(p) <= PRICE_MAX_SEK
    ]
    if pairs:
        return min(pairs)
    prices = [
        int(p) for p in _BARE_PRICE_RE.findall(text)
        if PRICE_MIN_SEK <= int(p) <= PRICE_MAX_SEK
    ]
    if not prices:
        return None
    return min(prices), parse_volume(text)


def _cheapest(candidates: list[tuple[Beer, bool]]) -> Beer | None:
    """Cheapest alcoholic beer; falls back to non-alcoholic if that's all."""
    alcoholic = [b for b, non_alc in candidates if not non_alc]
    pool = alcoholic or [b for b, _ in candidates]
    if not pool:
        return None
    return min(pool, key=lambda b: b.price_sek)


def find_cheapest_beer_svbr(html: str) -> Beer | None:
    """Cheapest beer on a Svenska Brasserier-theme WordPress menu page
    (Sturehof, Riche, Teatergrillen, Taverna Brillo...).

    Menu items are `span.menu__item--second-title-and-price` nodes inside
    `li.svbr-menu-module-tabs__field` columns; each column may carry a
    section title in `h3.menu__item--title` (e.g. "- Fat öl -", "Öl").
    """
    soup = BeautifulSoup(html, "lxml")
    candidates: list[tuple[Beer, bool]] = []
    for field in soup.select("li.svbr-menu-module-tabs__field"):
        title = field.find("h3", class_="menu__item--title")
        section = _strip(title.get_text(" ")) if title else ""
        beer_section = bool(
            re.search(r"\böl\b", section, re.IGNORECASE)
        ) and not _NOT_BEER_RE.search(section)
        for item in field.select("span.menu__item--second-title-and-price"):
            text = _strip(item.get_text(" "))
            if not text or _NOT_BEER_RE.search(text):
                continue
            if not beer_section and not _BEER_WORD_RE.search(text):
                continue
            parsed = parse_price_and_volume(text)
            if parsed is None:
                continue
            price, volume = parsed
            name_el = item.find("span", class_="second-title")
            name = _strip(name_el.get_text(" ")) if name_el else text
            beer = Beer(name=name[:80], volume_cl=volume, price_sek=price)
            candidates.append((beer, bool(_NON_ALC_RE.search(text))))
    return _cheapest(candidates)


def find_cheapest_beer_in_text(text: str) -> Beer | None:
    """Scan plain-text lines (e.g. extracted from a PDF menu) for beers."""
    candidates: list[tuple[Beer, bool]] = []
    for raw in text.splitlines():
        line = _strip(raw)
        if not line or len(line) > 160 or not is_beer_line(line):
            continue
        parsed = parse_price_and_volume(line)
        if parsed is None:
            continue
        price, volume = parsed
        name = _VOL_PRICE_PAIR_RE.sub(" ", line)
        name = _BARE_PRICE_RE.sub(" ", name)
        name = _strip(_VOLUME_RE.sub(" ", name)).strip(",.-–/ ")
        beer = Beer(name=(name or line)[:80], volume_cl=volume, price_sek=price)
        candidates.append((beer, bool(_NON_ALC_RE.search(line))))
    return _cheapest(candidates)


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
