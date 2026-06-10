import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scraper.lib import Beer, fetch, fetch_pdf_text, find_cheapest_beer_in_text

META = {
    "id": "hillenberg",
    "name": "Hillenberg",
    "address": "Humlegårdsgatan 14, 114 46 Stockholm",
    "lat": 59.3367,
    "lon": 18.0758,
    "source_url": "https://hillenberg.se/baren/",
}


def scrape() -> Beer | None:
    # The drink list (incl. beer) is a seasonal PDF linked from the bar page,
    # e.g. /wp-content/uploads/.../drinklista-var-2026.pdf.
    soup = BeautifulSoup(fetch(META["source_url"]), "lxml")
    a = soup.find("a", href=re.compile(r"drinklista[^\"']*\.pdf", re.IGNORECASE))
    if a is None:
        return None
    pdf_url = urljoin(META["source_url"], a["href"])
    return find_cheapest_beer_in_text(fetch_pdf_text(pdf_url))
