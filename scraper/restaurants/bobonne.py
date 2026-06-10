from scraper.lib import Beer, fetch, find_cheapest_beer

META = {
    "id": "bobonne",
    "name": "Brasserie Bobonne",
    "address": "Storgatan 12, 114 51 Stockholm",
    "lat": 59.3349,
    "lon": 18.0820,
    "source_url": "https://bobonne.se/menyer/",
}


def scrape() -> Beer | None:
    return find_cheapest_beer(fetch(META["source_url"]))
