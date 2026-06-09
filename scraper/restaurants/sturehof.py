from scraper.lib import Beer, fetch, find_cheapest_beer

META = {
    "id": "sturehof",
    "name": "Sturehof",
    "address": "Stureplan 2, 114 35 Stockholm",
    "lat": 59.3358,
    "lon": 18.0743,
    "source_url": "https://www.sturehof.com/menyer-och-drycker/",
}


def scrape() -> Beer | None:
    return find_cheapest_beer(fetch(META["source_url"]))
