from scraper.lib import Beer, fetch, find_cheapest_beer

META = {
    "id": "bestick",
    "name": "Bistro Bestick",
    "address": "Karlavägen 41, 114 49 Stockholm",
    "lat": 59.3398,
    "lon": 18.0876,
    "source_url": "https://www.bestick.nu/meny",
}


def scrape() -> Beer | None:
    return find_cheapest_beer(fetch(META["source_url"]))
