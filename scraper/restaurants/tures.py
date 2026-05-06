from scraper.lib import Beer, fetch, find_cheapest_beer

META = {
    "id": "tures",
    "name": "Tures",
    "address": "Sibyllegatan 47, 114 42 Stockholm",
    "lat": 59.3373,
    "lon": 18.0822,
    "source_url": "https://www.tures.se/meny",
}


def scrape() -> Beer | None:
    return find_cheapest_beer(fetch(META["source_url"]))
