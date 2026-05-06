from scraper.lib import Beer, fetch, find_cheapest_beer

META = {
    "id": "bagatelle",
    "name": "Bagatelle",
    "address": "Östermalmstorg 2, 114 42 Stockholm",
    "lat": 59.3360,
    "lon": 18.0810,
    "source_url": "https://www.bagatelle.se/meny",
}


def scrape() -> Beer | None:
    return find_cheapest_beer(fetch(META["source_url"]))
