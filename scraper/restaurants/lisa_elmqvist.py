import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scraper.lib import Beer, fetch, fetch_pdf_text, find_cheapest_beer_in_text

META = {
    "id": "lisa_elmqvist",
    "name": "Lisa Elmqvist",
    "address": "Östermalms Saluhall, Nybrogatan 31, 114 39 Stockholm",
    "lat": 59.3361,
    "lon": 18.0795,
    "source_url": "https://www.lisaelmqvist.se/restaurang/restaurangmeny",
}


def scrape() -> Beer | None:
    # The full menu incl. the drinks list is only published as a PDF
    # ("Ladda ner meny här" -> /files/restaurang/matochvinmeny.pdf).
    soup = BeautifulSoup(fetch(META["source_url"]), "lxml")
    a = soup.find("a", href=re.compile(r"meny[^\"']*\.pdf$", re.IGNORECASE))
    if a is None:
        return None
    pdf_url = urljoin(META["source_url"], a["href"])
    return find_cheapest_beer_in_text(fetch_pdf_text(pdf_url))
