"""Debug probe: fetch candidate menu pages and dump DOM evidence.

Run on GitHub Actions (runners have internet). For each probe target it
records reachability, discovers menu links from root pages, and prints the
ancestor chain + nearest price node for beer-ish lines so we can write
correct CSS selectors.
"""

from __future__ import annotations

import re
import sys
import traceback
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "sv-SE,sv;q=0.9,en;q=0.8",
}
TIMEOUT = 15
MENU_LINK_RE = re.compile(r"meny|menu|dryck|drink|bar(?:en)?\b|vinlista", re.I)
BEER_RE = re.compile(
    r"öl|beer|fatöl|ipa|lager|pils|stout|porter|witbier|weiss|ale\b"
    r"|menabrea|mariestad|carlsberg|heineken|norrlands|eriksberg|staropramen"
    r"|kronenbourg|spendrup|melleruds|sleepy bulldog|omnipollo|brooklyn|guinness",
    re.I,
)
PRICE_RE = re.compile(r"\b(\d{2,3})\s*(?::-|kr|sek|,-)?\b")
SECTION_HEAD_RE = re.compile(r"dryck|öl|bar(?:en)?\b|drinks|beverage", re.I)
HTML_DIR = Path("html")

# (label, url, options) — options: follow (probe menu links), links (dump all
# links), sections (dump text after dryck/öl/bar headings), svbr (dump all
# Svenska Brasserier menu items with their section titles).
PROBES = [
    # Existing restaurants that still need DOM evidence
    ("teatergrillen", "https://teatergrillen.se/meny/", {"svbr"}),
    ("godot_root", "https://godot.se/", {"follow", "links"}),
    ("bobonne_menyer", "https://bobonne.se/menyer/", {"sections", "links"}),
    ("lisa_elmqvist", "https://www.lisaelmqvist.se/restaurang/restaurangmeny", {"links"}),
    # Replacement candidates, round 2
    ("hillenberg_baren", "https://hillenberg.se/baren/", {"sections", "links"}),
    ("nybrogatan38_menyer", "https://nybrogatan38.com/menyer", {"follow", "links", "sections"}),
    ("grodan", "https://www.grodan.se/", {"links"}),
    ("tavernabrillo", "https://www.tavernabrillo.se/meny/", {"svbr", "follow"}),
    ("east", "https://www.east.se/", {"follow"}),
    ("astoria", "https://brasserieastoria.com/", {"follow"}),
    ("paco", "https://pa-co.se/", {"follow"}),
    ("hantverket", "https://restauranghantverket.se/", {"follow"}),
    ("eriks_bakficka", "https://eriks.se/", {"follow"}),
]


def get(url: str):
    try:
        return requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True), None
    except Exception as exc:  # noqa: BLE001
        return None, f"{type(exc).__name__}: {exc}"


def render_check(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    notes = []
    text_len = len(soup.get_text(strip=True))
    for marker, name in [
        ("__NEXT_DATA__", "Next.js"), ("wp-content", "WordPress"),
        ("squarespace", "Squarespace"), ("wixstatic", "Wix"),
        ("cdn.shopify", "Shopify"), ("svbr-menu-module", "SvBr-theme"),
    ]:
        if marker.lower() in html.lower():
            notes.append(name)
    script_len = sum(len(s.get_text()) for s in soup.find_all("script"))
    notes.append(f"visible_text={text_len} script_chars={script_len}")
    if text_len < 500 and script_len > 5000:
        notes.append("LIKELY JS-RENDERED")
    return "; ".join(notes)


def node_desc(t: Tag | None) -> str:
    if t is None:
        return "?"
    cls = ".".join(t.get("class") or [])
    return f"{t.name}{'.' + cls if cls else ''}"


def ancestor_chain(el, depth: int = 4) -> str:
    parts = []
    t = el.parent if isinstance(el, NavigableString) else el
    while t is not None and t.name not in ("body", "html", "[document]") and len(parts) < depth:
        parts.append(node_desc(t))
        t = t.parent
    return " < ".join(parts)


def nearest_price(el) -> str:
    """Walk up from a beer text node looking for a price-bearing node nearby."""
    t = el.parent if isinstance(el, NavigableString) else el
    for _ in range(4):
        if t is None:
            break
        text = " ".join(t.get_text(" ", strip=True).split())
        if PRICE_RE.search(text):
            return f"price-node=<{node_desc(t)}> text={text[:140]!r}"
        t = t.parent
    return "price-node=NONE within 4 ancestors"


def dump_beer_lines(soup: BeautifulSoup) -> None:
    printed = 0
    seen = set()
    for el in soup.find_all(string=BEER_RE):
        if el.parent.name in ("script", "style", "title", "meta", "a", "nav"):
            continue
        txt = " ".join(str(el).split())[:90]
        if not txt or txt in seen:
            continue
        seen.add(txt)
        print(f"    LINE: {txt!r}")
        print(f"      chain: {ancestor_chain(el)}")
        print(f"      {nearest_price(el)}")
        printed += 1
        if printed >= 30:
            print("    ... (truncated at 30)")
            break
    if printed == 0:
        print("    (no beer-ish lines found)")


def dump_svbr_items(soup: BeautifulSoup) -> None:
    print("  [svbr items]")
    for field in soup.select("li.svbr-menu-module-tabs__field"):
        title = field.find("h3", class_="menu__item--title")
        print(f"    SECTION: {title.get_text(' ', strip=True) if title else '(none)'}")
        for item in field.select("span.menu__item--second-title-and-price"):
            print(f"      ITEM: {' '.join(item.get_text(' ', strip=True).split())[:110]}")


def dump_sections(soup: BeautifulSoup) -> None:
    print("  [sections after dryck/öl/bar headings]")
    for h in soup.find_all(re.compile("^h[1-6]$")):
        head = h.get_text(" ", strip=True)
        if not head or not SECTION_HEAD_RE.search(head):
            continue
        scope = h.parent.parent if h.parent and h.parent.parent else h.parent
        text = " ".join(scope.get_text(" ", strip=True).split())[:700]
        print(f"    HEAD {node_desc(h)}: {head[:60]!r}")
        print(f"      scope <{node_desc(scope)}>: {text}")


def dump_links(soup: BeautifulSoup, base: str) -> None:
    print("  [all links]")
    seen = set()
    for a in soup.find_all("a", href=True):
        full = urljoin(base, a["href"])
        if full in seen:
            continue
        seen.add(full)
        print(f"    {full}  text={a.get_text(' ', strip=True)[:50]!r}")
        if len(seen) >= 40:
            print("    ... (truncated at 40)")
            break


def analyse(label: str, url: str, opts: set[str]) -> None:
    print(f"\n===== {label} =====")
    print(f"  url={url}")
    resp, err = get(url)
    if err or resp is None:
        print(f"  FETCH FAILED: {err}")
        return
    ctype = resp.headers.get("Content-Type", "?")
    print(f"  {resp.status_code} final={resp.url} type={ctype} len={len(resp.content)}")
    if resp.status_code != 200 or "html" not in ctype:
        return
    HTML_DIR.mkdir(exist_ok=True)
    (HTML_DIR / f"{label}.html").write_bytes(resp.content)
    html = resp.text
    print(f"  [render] {render_check(html)}")
    soup = BeautifulSoup(html, "lxml")
    heads = [
        f"    <{h.name} class={h.get('class')}> {h.get_text(' ', strip=True)[:70]}"
        for h in soup.find_all(re.compile("^h[1-6]$"))
        if h.get_text(strip=True)
    ]
    print(f"  [headings: {len(heads)}]")
    for line in heads[:20]:
        print(line)
    print("  [beer-ish lines]")
    dump_beer_lines(soup)
    if "svbr" in opts:
        dump_svbr_items(soup)
    if "sections" in opts:
        dump_sections(soup)
    if "links" in opts:
        dump_links(soup, str(resp.url))

    if "follow" in opts:
        seen, links = set(), []
        for a in soup.find_all("a", href=True):
            text = a.get_text(" ", strip=True)[:60]
            if MENU_LINK_RE.search(a["href"]) or MENU_LINK_RE.search(text):
                full = urljoin(str(resp.url), a["href"]).split("#")[0]
                if full not in seen and urlsplit(full).netloc == urlsplit(str(resp.url)).netloc:
                    seen.add(full)
                    links.append((full, text))
        print(f"  [menu-ish links: {len(links)}]")
        for full, text in links[:10]:
            print(f"    link: {full}  text={text!r}")
        for i, (full, _) in enumerate(links[:3]):
            if full.rstrip("/") != str(resp.url).rstrip("/"):
                analyse(f"{label}_link{i}", full, {"sections"})


def main() -> None:
    for label, url, opts in PROBES:
        try:
            analyse(label, url, opts)
        except Exception:  # noqa: BLE001
            print(f"  PROBE CRASHED for {label}:")
            traceback.print_exc(file=sys.stdout)
    print("\n===== done =====")


if __name__ == "__main__":
    main()
