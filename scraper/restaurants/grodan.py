import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scraper.lib import Beer, fetch, fetch_pdf_text, find_cheapest_beer_in_text

META = {
    "id": "grodan",
    "name": "Grodan Grev Ture",
    "address": "Grev Turegatan 16, 114 46 Stockholm",
    "lat": 59.3376,
    "lon": 18.0758,
    "source_url": "https://www.grodan.se/grevture",
}


def scrape() -> Beer | None:
    # Drinks live in the "kvällsmeny & dryck" PDF linked from the venue page
    # (e.g. /media/.../kvallsmeny-dryck_2026_gt__v-22.pdf).
    soup = BeautifulSoup(fetch(META["source_url"]), "lxml")
    a = soup.find("a", href=re.compile(r"dryck[^\"']*\.pdf", re.IGNORECASE))
    if a is None:
        return None
    pdf_url = urljoin(META["source_url"], a["href"])
    return find_cheapest_beer_in_text(fetch_pdf_text(pdf_url))
