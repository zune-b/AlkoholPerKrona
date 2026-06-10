from scraper.lib import Beer, fetch, find_cheapest_beer_svbr

META = {
    "id": "sturehof",
    "name": "Sturehof",
    "address": "Stureplan 2, 114 35 Stockholm",
    "lat": 59.3358,
    "lon": 18.0743,
    "source_url": "https://sturehof.com/meny/",
}


def scrape() -> Beer | None:
    return find_cheapest_beer_svbr(fetch(META["source_url"]))
