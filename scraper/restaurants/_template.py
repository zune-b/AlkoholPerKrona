"""Copy this file to add a new restaurant.

Each restaurant module exports:
- META: identifying info + lat/lon + the URL to scrape
- scrape(): returns a Beer (cheapest beer on the menu) or None on failure

If the generic `find_cheapest_beer` returns None or the wrong item, override
`scrape()` with a site-specific BeautifulSoup selector. Keep the override
small (<30 lines) and resilient to whitespace.
"""

from scraper.lib import Beer, fetch, find_cheapest_beer

META = {
    "id": "example",
    "name": "Example Restaurant",
    "address": "Example street 1, Stockholm",
    "lat": 59.3360,
    "lon": 18.0800,
    "source_url": "https://example.com/meny",
}


def scrape() -> Beer | None:
    return find_cheapest_beer(fetch(META["source_url"]))
