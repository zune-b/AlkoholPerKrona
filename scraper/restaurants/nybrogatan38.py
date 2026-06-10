import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scraper.lib import Beer, fetch, fetch_pdf_text, find_cheapest_beer_in_text

META = {
    "id": "nybrogatan38",
    "name": "Nybrogatan 38",
    "address": "Nybrogatan 38, 114 40 Stockholm",
    "lat": 59.3378,
    "lon": 18.0800,
    "source_url": "https://nybrogatan38.com/menyer",
}


def scrape() -> Beer | None:
    # The menus page links per-menu PDFs; the bar list ("cocktails & öl")
    # is hosted on static.thatsup.website and carries the beer prices.
    soup = BeautifulSoup(fetch(META["source_url"]), "lxml")
    for a in soup.find_all("a", href=True):
        text = a.get_text(" ", strip=True)
        if re.search(r"drinklista", a["href"], re.IGNORECASE) or re.search(
            r"\böl\b", text, re.IGNORECASE
        ):
            pdf_url = urljoin(META["source_url"], a["href"])
            return find_cheapest_beer_in_text(fetch_pdf_text(pdf_url))
    return None
