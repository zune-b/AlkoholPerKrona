"""Pet Sounds Bar — Södermalm record-bar classic on Skånegatan.

The bar menu at petsounds.se/bar is server-rendered. Beer lives in <dl>
lists under "FATÖL" / "ÖL" <h3> headings; each row is a flex <div> with the
name in <dt> (e.g. "S:t Eriks Lager (5.0%), 40 cl") and the bare SEK price
in <dd> (e.g. "85"). The generic helper misses these because the prices
have no "kr"/":-" suffix, so we parse the rows directly.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from scraper.lib import Beer, fetch, parse_volume

META = {
    "id": "pet_sounds_bar",
    "name": "Pet Sounds Bar",
    "address": "Skånegatan 80, 116 37 Stockholm",
    "lat": 59.3138,
    "lon": 18.0837,
    "source_url": "https://petsounds.se/bar",
}

_BEER_HEADINGS = ("FATÖL", "ÖL")
_PRICE_DIGITS_RE = re.compile(r"\b(\d{2,3})\b")


def scrape() -> Beer | None:
    soup = BeautifulSoup(fetch(META["source_url"]), "lxml")
    best: Beer | None = None
    for h3 in soup.find_all("h3"):
        if h3.get_text(" ", strip=True).upper() not in _BEER_HEADINGS:
            continue
        block = h3.parent
        if block is None:
            continue
        for row in block.select("dl div"):
            dt, dd = row.find("dt"), row.find("dd")
            if dt is None or dd is None:
                continue
            name = " ".join(dt.get_text(" ", strip=True).split())
            m = _PRICE_DIGITS_RE.search(dd.get_text(" ", strip=True))
            if not name or not m:
                continue
            price = int(m.group(1))
            if not 30 <= price <= 300:
                continue
            beer = Beer(name=name[:80], volume_cl=parse_volume(name), price_sek=price)
            if best is None or beer.price_sek < best.price_sek:
                best = beer
    return best
