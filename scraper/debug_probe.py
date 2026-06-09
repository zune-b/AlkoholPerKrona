"""Debug probe: fetch each restaurant's root + menu page and dump DOM evidence.

Run on GitHub Actions (runners have internet). For each restaurant module it
records reachability, discovers real menu links from the root page, and prints
heading/beer-line context so we can write correct CSS selectors.
"""

from __future__ import annotations

import importlib
import pkgutil
import re
import sys
import traceback
from pathlib import Path
from urllib.parse import urlsplit, urljoin

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import scraper.restaurants as restaurants_pkg  # noqa: E402

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
MENU_LINK_RE = re.compile(r"meny|menu|dryck|drink|vin|bar", re.I)
BEER_RE = re.compile(r"öl|beer|fatöl|ipa|lager", re.I)
HTML_DIR = Path("html")


def get(url: str, allow_insecure_fallback: bool = False):
    """GET with redirects; optionally retry with verify=False on SSL errors."""
    try:
        return requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True), None
    except requests.exceptions.SSLError as exc:
        if allow_insecure_fallback:
            try:
                resp = requests.get(
                    url, headers=HEADERS, timeout=TIMEOUT,
                    allow_redirects=True, verify=False,
                )
                return resp, f"SSL ERROR, retried with verify=False: {exc}"
            except Exception as exc2:  # noqa: BLE001
                return None, f"SSL fallback also failed: {exc2}"
        return None, f"SSL ERROR: {exc}"
    except Exception as exc:  # noqa: BLE001
        return None, f"{type(exc).__name__}: {exc}"


def describe(label: str, resp, err: str | None):
    if err:
        print(f"  [{label}] WARNING: {err}")
    if resp is None:
        print(f"  [{label}] NO RESPONSE")
        return
    ctype = resp.headers.get("Content-Type", "?")
    print(f"  [{label}] {resp.status_code} final={resp.url} type={ctype} len={len(resp.content)}")


def js_rendered_check(html: str) -> str:
    notes = []
    text_len = len(BeautifulSoup(html, "lxml").get_text(strip=True))
    if "__NEXT_DATA__" in html:
        notes.append("__NEXT_DATA__ (Next.js)")
    if 'id="root"' in html or 'id="app"' in html:
        notes.append("SPA root div")
    if "wp-content" in html:
        notes.append("WordPress")
    if "squarespace" in html.lower():
        notes.append("Squarespace")
    if "wixsite" in html.lower() or "wix.com" in html.lower() or "wixstatic" in html.lower():
        notes.append("Wix")
    script_len = sum(len(s.get_text()) for s in BeautifulSoup(html, "lxml").find_all("script"))
    notes.append(f"visible_text={text_len} script_chars={script_len}")
    if text_len < 500 and script_len > 5000:
        notes.append("LIKELY JS-RENDERED")
    return "; ".join(notes)


def probe(module) -> None:
    meta = module.META
    rid = meta["id"]
    src = meta["source_url"]
    parts = urlsplit(src)
    root = f"{parts.scheme}://{parts.netloc}/"
    insecure_ok = rid == "riche"

    print(f"\n===== {rid} =====")
    print(f"  source_url={src}")

    root_resp, root_err = get(root, allow_insecure_fallback=insecure_ok)
    describe("root", root_resp, root_err)
    menu_resp, menu_err = get(src, allow_insecure_fallback=insecure_ok)
    describe("menu", menu_resp, menu_err)

    HTML_DIR.mkdir(exist_ok=True)
    if root_resp is not None:
        (HTML_DIR / f"{rid}_root.html").write_bytes(root_resp.content)
    if menu_resp is not None:
        (HTML_DIR / f"{rid}_menu.html").write_bytes(menu_resp.content)

    # Discover real menu links from root page
    if root_resp is not None and root_resp.ok and "html" in root_resp.headers.get("Content-Type", ""):
        soup = BeautifulSoup(root_resp.text, "lxml")
        seen = set()
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(" ", strip=True)[:60]
            if MENU_LINK_RE.search(href) or MENU_LINK_RE.search(text):
                full = urljoin(str(root_resp.url), href)
                if full not in seen:
                    seen.add(full)
                    links.append(f"    link: {full}  text={text!r}")
        print(f"  [root menu-ish links: {len(links)}]")
        for line in links[:12]:
            print(line)
        if len(links) > 12:
            print(f"    ... and {len(links) - 12} more")

    # Analyse the menu page
    if menu_resp is not None and menu_resp.status_code == 200:
        ctype = menu_resp.headers.get("Content-Type", "")
        if "pdf" in ctype:
            print("  [menu] is a PDF")
            return
        if "html" not in ctype:
            print(f"  [menu] non-HTML content-type: {ctype}")
            return
        html = menu_resp.text
        print(f"  [menu render check] {js_rendered_check(html)}")
        soup = BeautifulSoup(html, "lxml")
        heads = [
            f"    <{h.name} class={h.get('class')}> {h.get_text(' ', strip=True)[:70]}"
            for h in soup.find_all(re.compile("^h[1-6]$"))
            if h.get_text(strip=True)
        ]
        print(f"  [headings: {len(heads)}]")
        for line in heads[:15]:
            print(line)
        if len(heads) > 15:
            print(f"    ... and {len(heads) - 15} more")

        print("  [beer-ish lines]")
        printed = 0
        seen_lines = set()
        for el in soup.find_all(string=BEER_RE):
            parent = el.parent
            if parent.name in ("script", "style"):
                continue
            txt = " ".join(str(el).split())[:90]
            key = (parent.name, txt)
            if key in seen_lines or not txt:
                continue
            seen_lines.add(key)
            gp = parent.parent
            gp_desc = f"{gp.name}.{gp.get('class')}" if gp else "?"
            print(f"    <{parent.name} class={parent.get('class')}> (in {gp_desc}): {txt}")
            printed += 1
            if printed >= 40:
                print("    ... (truncated at 40)")
                break
        if printed == 0:
            print("    (none found)")


def main() -> None:
    requests.packages.urllib3.disable_warnings()  # for verify=False fallback
    for info in pkgutil.iter_modules(restaurants_pkg.__path__):
        if info.name.startswith("_"):
            continue
        try:
            module = importlib.import_module(f"scraper.restaurants.{info.name}")
            probe(module)
        except Exception:  # noqa: BLE001
            print(f"\n===== {info.name} =====")
            print("  PROBE CRASHED:")
            traceback.print_exc(file=sys.stdout)
    print("\n===== done =====")


if __name__ == "__main__":
    main()
