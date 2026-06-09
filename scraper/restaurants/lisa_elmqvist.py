from scraper.lib import Beer, fetch, find_cheapest_beer

META = {
    "id": "lisa_elmqvist",
    "name": "Lisa Elmqvist",
    "address": "Östermalms Saluhall, Nybrogatan 31, 114 39 Stockholm",
    "lat": 59.3361,
    "lon": 18.0795,
    "source_url": "https://www.lisaelmqvist.se/restaurang/restaurangmeny",
}


def scrape() -> Beer | None:
    return find_cheapest_beer(fetch(META["source_url"]))
