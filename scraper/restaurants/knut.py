from scraper.lib import Beer, fetch, find_cheapest_beer

META = {
    "id": "knut",
    "name": "Knut Östermalm",
    "address": "Riddargatan 6, 114 35 Stockholm",
    "lat": 59.3338,
    "lon": 18.0804,
    "source_url": "https://www.knutostermalm.se/meny",
}


def scrape() -> Beer | None:
    return find_cheapest_beer(fetch(META["source_url"]))
