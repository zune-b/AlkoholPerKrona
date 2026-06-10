"""Soldaten Švejk — Czech beer hall on Södermalm, budget classic.

The drinks page svejk.se/dryck/ is a server-rendered WordPress table. The
"TJECKISK FATÖL 0,5l" section header is an <h2> inside a table row; the
beer rows that follow look like "Bernard ljus, opastöriserad | 94" until the
next section header (CIDER). Prices are bare integers, so the generic lib
helper cannot parse them and we read the table directly.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from scraper.lib import Beer, fetch

META = {
    "id": "soldaten_svejk",
    "name": "Soldaten Švejk",
    "address": "Östgötagatan 35, 116 25 Stockholm",
    "lat": 59.3125,
    "lon": 18.0748,
    "source_url": "https://svejk.se/dryck/",
}

_ROW_RE = re.compile(r"^(?P<name>.+?)\s+(?P<price>\d{2,3})\s*$")


def scrape() -> Beer | None:
    soup = BeautifulSoup(fetch(META["source_url"]), "lxml")
    anchor = None
    for h2 in soup.find_all("h2"):
        if "FATÖL" in h2.get_text(" ", strip=True).upper():
            anchor = h2
            break
    if anchor is None:
        return None
    table = anchor.find_parent("table")
    if table is None:
        return None
    best: Beer | None = None
    collecting = False
    for tr in table.find_all("tr"):
        heading = tr.find(re.compile(r"^h[1-6]$"))
        if heading is not None:
            collecting = heading is anchor
            continue
        if not collecting:
            continue
        text = " ".join(tr.get_text(" ", strip=True).split())
        m = _ROW_RE.match(text)
        if not m:
            continue
        name = m.group("name").strip(" .,-–")
        price = int(m.group("price"))
        if len(name) < 3 or not 30 <= price <= 300:
            continue
        if re.search(r"alkoholfri", name, re.IGNORECASE):
            continue
        volume = 33 if re.search(r"0[.,]33", name) else 50  # section header says 0,5l
        beer = Beer(name=name[:80], volume_cl=volume, price_sek=price)
        if best is None or beer.price_sek < best.price_sek:
            best = beer
    return best
