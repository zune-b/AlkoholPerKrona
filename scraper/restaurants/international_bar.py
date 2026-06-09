"""International Bar — budget bar chain; Norrmalm flagship (Norrlandsgatan 23).

The chain publishes one shared menu at internationalbar.se/menu/ (WordPress/
Elementor, server-rendered). We try the generic heuristic first and fall
back to walking Elementor price-list items (name in
span.elementor-price-list-title, price in span.elementor-price-list-price)
under an Öl heading.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from scraper.lib import Beer, fetch, find_cheapest_beer, parse_volume

META = {
    "id": "international_bar",
    "name": "International Bar (Norrmalm)",
    "address": "Norrlandsgatan 23, 111 43 Stockholm",
    "lat": 59.3370,
    "lon": 18.0699,
    "source_url": "https://internationalbar.se/menu/",
}

_PRICE_DIGITS_RE = re.compile(r"\b(\d{2,3})\b")
_NEGATIVE_RE = re.compile(r"vin|wine|cocktail|sprit|cider|drink", re.IGNORECASE)
_BEER_HINT_RE = re.compile(
    r"öl|beer|ipa|lager|pils|stout|porter|\bale\b|guinness|heineken|carlsberg"
    r"|norrlands|mariestad|falcon|pripps|åbro|krusovice|krušovice|staropramen"
    r"|tuborg|eriksberg|budvar|spendrup",
    re.IGNORECASE,
)


def _from_price_list(soup: BeautifulSoup) -> Beer | None:
    best: Beer | None = None
    for li in soup.select("li.elementor-price-list-item"):
        title = li.select_one(".elementor-price-list-title")
        price_el = li.select_one(".elementor-price-list-price")
        if title is None or price_el is None:
            continue
        li_text = li.get_text(" ", strip=True)
        name = " ".join(title.get_text(" ", strip=True).split())
        if not name or _NEGATIVE_RE.search(li_text) or not _BEER_HINT_RE.search(li_text):
            continue
        m = _PRICE_DIGITS_RE.search(price_el.get_text(" ", strip=True))
        if not m:
            continue
        price = int(m.group(1))
        if not 30 <= price <= 300:
            continue
        beer = Beer(
            name=name[:80],
            volume_cl=parse_volume(li.get_text(" ", strip=True)),
            price_sek=price,
        )
        if best is None or beer.price_sek < best.price_sek:
            best = beer
    return best


def scrape() -> Beer | None:
    html = fetch(META["source_url"])
    beer = _from_price_list(BeautifulSoup(html, "lxml"))
    if beer is not None:
        return beer
    return find_cheapest_beer(html)
