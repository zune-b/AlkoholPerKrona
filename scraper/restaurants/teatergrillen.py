from scraper.lib import Beer, fetch, find_cheapest_beer_svbr

META = {
    "id": "teatergrillen",
    "name": "Teatergrillen",
    "address": "Nybrogatan 3, 114 34 Stockholm",
    "lat": 59.3340,
    "lon": 18.0764,
    "source_url": "https://teatergrillen.se/meny/",
}


def scrape() -> Beer | None:
    return find_cheapest_beer_svbr(fetch(META["source_url"]))
