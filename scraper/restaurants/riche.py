from scraper.lib import Beer, fetch, find_cheapest_beer

META = {
    "id": "riche",
    "name": "Riche",
    "address": "Birger Jarlsgatan 4, 114 34 Stockholm",
    "lat": 59.3346,
    "lon": 18.0742,
    "source_url": "https://www.riche.se/meny/",
}


def scrape() -> Beer | None:
    return find_cheapest_beer(fetch(META["source_url"]))
