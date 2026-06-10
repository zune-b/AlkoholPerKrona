from scraper.lib import Beer, fetch, find_cheapest_beer

META = {
    "id": "godot",
    "name": "Brasserie Godot",
    "address": "Grev Turegatan 36, 114 38 Stockholm",
    "lat": 59.3404,
    "lon": 18.0790,
    "source_url": "https://godot.se/pages/meny",
}


def scrape() -> Beer | None:
    return find_cheapest_beer(fetch(META["source_url"]))
