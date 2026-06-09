from scraper.lib import Beer, fetch, find_cheapest_beer_svbr

# TODO: revert source_url to https://www.riche.se/meny/ once their site
# migration completes — riche.se currently serves a wetail.dev certificate
# and redirects to the riche-dev.wetail.dev staging host.
META = {
    "id": "riche",
    "name": "Riche",
    "address": "Birger Jarlsgatan 4, 114 34 Stockholm",
    "lat": 59.3346,
    "lon": 18.0742,
    "source_url": "https://riche-dev.wetail.dev/meny/",
}


def scrape() -> Beer | None:
    return find_cheapest_beer_svbr(fetch(META["source_url"]))
