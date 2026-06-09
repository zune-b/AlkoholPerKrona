import re

from bs4 import BeautifulSoup

from scraper.lib import Beer, fetch, is_beer_line, parse_price_and_volume

META = {
    "id": "tures",
    "name": "Tures",
    "address": "Sibyllegatan 47, 114 42 Stockholm",
    "lat": 59.3373,
    "lon": 18.0822,
    "source_url": "https://www.tures.se/",
}


def scrape() -> Beer | None:
    # Webflow one-pager: the "Öl & Cider" column is a div.menus__tab_cell
    # holding a h2.menus__tabs_subheading title and div.menu__cms_item rows.
    soup = BeautifulSoup(fetch(META["source_url"]), "lxml")
    candidates: list[Beer] = []
    for h in soup.find_all("h2", class_="menus__tabs_subheading"):
        if not re.search(r"\böl\b", h.get_text(" ", strip=True), re.IGNORECASE):
            continue
        cell = h.find_parent("div", class_="menus__tab_cell")
        if cell is None:
            continue
        for item in cell.find_all("div", class_="menu__cms_item"):
            name_el = item.find("div", class_="menu__item_name")
            wrap = item.find("div", class_="menu__item_name_wrap")
            if name_el is None or wrap is None:
                continue
            name = " ".join(name_el.get_text(" ", strip=True).split())
            if not name or not is_beer_line(name):  # drops the ciders
                continue
            parsed = parse_price_and_volume(wrap.get_text(" ", strip=True))
            if parsed is None:
                continue
            price, volume = parsed
            candidates.append(Beer(name=name[:80], volume_cl=volume, price_sek=price))
    return min(candidates, key=lambda b: b.price_sek) if candidates else None
