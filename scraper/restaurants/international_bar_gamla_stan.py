"""International Bar Gamla Stan — user-requested budget bar (chain location).

Address cross-checked against internationalbar.se/gamla-stan/ ("Mälartorget
13 Stockholm"). The whole chain shares one menu; parsing lives in
scraper/restaurants/_international.py.
"""

from scraper.lib import Beer
from scraper.restaurants._international import MENU_URL, cheapest_beer_from_menu

META = {
    "id": "international_bar_gamla_stan",
    "name": "International Bar Gamla Stan",
    "address": "Mälartorget 13, 111 27 Stockholm",
    "lat": 59.3232,
    "lon": 18.0673,
    "source_url": MENU_URL,
}


def scrape() -> Beer | None:
    return cheapest_beer_from_menu()
