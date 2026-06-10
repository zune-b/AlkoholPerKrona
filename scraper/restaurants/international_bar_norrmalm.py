"""International Bar Norrmalm — user-requested budget bar (chain flagship).

Address cross-checked against internationalbar.se/norrmalm/ ("Norrlandsgatan
23 Stockholm"). The whole chain shares one menu; parsing lives in
scraper/restaurants/_international.py.
"""

from scraper.lib import Beer
from scraper.restaurants._international import MENU_URL, cheapest_beer_from_menu

META = {
    "id": "international_bar_norrmalm",
    "name": "International Bar Norrmalm",
    "address": "Norrlandsgatan 23, 111 43 Stockholm",
    "lat": 59.3358,
    "lon": 18.0712,
    "source_url": MENU_URL,
}


def scrape() -> Beer | None:
    return cheapest_beer_from_menu()
