"""Shared scraper for International Bar's chain-wide menu.

All International Bar locations in central Stockholm share one menu at
internationalbar.se/menu/ (WordPress/Elementor, server-rendered). Beer items
are <h4> lines like "CARLSBERG EXPORT 45/55:-" inside the same
div.elementor-widget-wrap as the section <h1> headings "Draught beer" /
"Bottles". The lib's generic price regex misses these because ":-" at end
of string fails its trailing word boundary, so we parse the lines here.

The leading underscore keeps this helper out of scraper.main's module
discovery; the per-location modules import from it.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from scraper.lib import Beer, fetch

MENU_URL = "https://internationalbar.se/menu/"

_SECTION_RE = re.compile(r"^(draught beer|bottles)$", re.IGNORECASE)
_ITEM_RE = re.compile(r"^(?P<name>.+?)\s+(?P<p1>\d{2,3})(?:\s*/\s*(?P<p2>\d{2,3}))?\s*:-$")


def cheapest_beer_from_menu() -> Beer | None:
    soup = BeautifulSoup(fetch(MENU_URL), "lxml")
    best: Beer | None = None
    seen_wraps: set[int] = set()
    for heading in soup.find_all(["h1", "h2", "h3"]):
        title = " ".join(heading.get_text(" ", strip=True).split())
        if not _SECTION_RE.match(title):
            continue
        wrap = heading.find_parent("div", class_="elementor-widget-wrap") or heading.parent
        if wrap is None or id(wrap) in seen_wraps:
            continue
        seen_wraps.add(id(wrap))
        collecting = False
        for el in wrap.find_all(["h1", "h2", "h3", "h4"]):
            text = " ".join(el.get_text(" ", strip=True).split())
            if el.name != "h4":
                # A new section heading: only beer sections turn collection on.
                collecting = bool(_SECTION_RE.match(text))
                continue
            if not collecting:
                continue
            m = _ITEM_RE.match(text)
            if not m:
                continue
            name = m.group("name").strip(" .,-–")
            if len(name) < 4:  # skip stubs like "Fr."
                continue
            prices = [int(m.group("p1"))]
            if m.group("p2"):
                prices.append(int(m.group("p2")))
            price = min(prices)
            if not 30 <= price <= 300:
                continue
            beer = Beer(name=name[:80].title(), volume_cl=None, price_sek=price)
            if best is None or beer.price_sek < best.price_sek:
                best = beer
    return best
