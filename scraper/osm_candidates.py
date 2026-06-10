"""Auto-grow data/candidates.json from OpenStreetMap.

Run as: python -m scraper.osm_candidates  (weekly via osm-discovery.yml)

Queries the Overpass API for pubs/bars/biergartens with a website tag
inside the central-Stockholm bounding box (the same box scraper/validate.py
enforces) and appends any venue we don't already know about. The nightly
discovery pass then tries each candidate's site with the generic beer
parser — venues with parseable HTML menus get promoted into the app
automatically.

Dedup sources: existing candidates, venues already in restaurants.json,
and data/candidates_blocklist.json (dead sites / no-price venues / false
positives we've manually ruled out). Total candidate count is capped so
the nightly run stays fast.
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

import requests

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CANDIDATES_PATH = DATA_DIR / "candidates.json"
RESTAURANTS_PATH = DATA_DIR / "restaurants.json"
BLOCKLIST_PATH = DATA_DIR / "candidates_blocklist.json"

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
# Central Stockholm — matches scraper/validate.py's bounds.
BBOX = "59.28,17.95,59.40,18.20"
QUERY = f"""
[out:json][timeout:90];
(
  nwr["amenity"~"^(pub|bar|biergarten)$"]["website"]({BBOX});
  nwr["amenity"~"^(pub|bar|biergarten)$"]["contact:website"]({BBOX});
);
out center tags;
"""
MAX_CANDIDATES = 120


def _slug(name: str) -> str:
    s = unicodedata.normalize("NFKD", name.lower())
    s = s.replace("å", "a").replace("ä", "a").replace("ö", "o")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s[:40] or "venue"


def _host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").removeprefix("www.")
    except ValueError:
        return ""


def main() -> int:
    candidates = json.loads(CANDIDATES_PATH.read_text())
    restaurants = json.loads(RESTAURANTS_PATH.read_text())
    block = json.loads(BLOCKLIST_PATH.read_text()) if BLOCKLIST_PATH.exists() else {}

    known_ids = {c["id"] for c in candidates} | {r["id"] for r in restaurants}
    known_ids |= set(block.get("ids", []))
    known_hosts = {_host(c["url"]) for c in candidates}
    known_hosts |= {_host(r["source_url"]) for r in restaurants}
    known_hosts |= set(block.get("hosts", []))
    known_hosts.discard("")

    try:
        resp = requests.post(OVERPASS_URL, data={"data": QUERY}, timeout=120)
        resp.raise_for_status()
        elements = resp.json().get("elements", [])
    except Exception as exc:  # noqa: BLE001 — weekly retry handles transients
        print(f"Overpass query failed (will retry next week): {exc}", file=sys.stderr)
        return 0

    added = 0
    for el in sorted(elements, key=lambda e: e.get("tags", {}).get("name", "")):
        tags = el.get("tags", {})
        name = tags.get("name")
        url = tags.get("website") or tags.get("contact:website")
        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")
        if not (name and url and lat and lon):
            continue
        if not url.startswith("http"):
            url = "https://" + url
        cid = _slug(name)
        host = _host(url)
        if cid in known_ids or not host or host in known_hosts:
            continue
        if len(candidates) >= MAX_CANDIDATES:
            print(f"cap reached ({MAX_CANDIDATES}); stopping", file=sys.stderr)
            break
        street = tags.get("addr:street", "")
        nr = tags.get("addr:housenumber", "")
        address = f"{street} {nr}".strip() or "Stockholm"
        if "stockholm" not in address.lower():
            address += ", Stockholm"
        candidates.append(
            {
                "id": cid,
                "name": name,
                "address": address,
                "lat": round(float(lat), 5),
                "lon": round(float(lon), 5),
                "url": url,
            }
        )
        known_ids.add(cid)
        known_hosts.add(host)
        added += 1
        print(f"+ {name} ({url})", file=sys.stderr)

    if added:
        CANDIDATES_PATH.write_text(
            json.dumps(candidates, ensure_ascii=False, indent=2) + "\n"
        )
    print(f"osm: {added} new candidates, {len(candidates)} total", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
