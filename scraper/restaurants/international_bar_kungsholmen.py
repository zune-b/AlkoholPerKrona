"""International Bar Kungsholmen — user-requested budget bar (chain location).

Address cross-checked against internationalbar.se/kungsholmen/
("Hantverkargatan 36 Stockholm"). The whole chain shares one menu; parsing
lives in scraper/restaurants/_international.py.
"""

from scraper.lib import Beer
from scraper.restaurants._international import MENU_URL, cheapest_beer_from_menu

META = {
    "id": "international_bar_kungsholmen",
    "name": "International Bar Kungsholmen",
    "address": "Hantverkargatan 36, 112 21 Stockholm",
    "lat": 59.3279,
    "lon": 18.0399,
    "source_url": MENU_URL,
}


def scrape() -> Beer | None:
    return cheapest_beer_from_menu()
