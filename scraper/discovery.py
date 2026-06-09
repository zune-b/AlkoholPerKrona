"""Daily discovery pass: auto-add candidate venues that the generic parser can read.

Run as: python -m scraper.discovery  (after scraper.main, before scraper.validate)

Reads data/candidates.json — a hand-curated backlog of venues we'd like in the
app but haven't written dedicated scrapers for. Each candidate is tried with
the generic find_cheapest_beer heuristic:

- success      -> the venue is added to data/restaurants.json (discovered: true)
- fail, but it was discovered on an earlier day -> kept, marked stale
- fail, never seen working                      -> skipped (no data pollution)

Venues with dedicated modules in scraper/restaurants/ always win over a
candidate with the same id. Growing the app = appending one JSON object to
data/candidates.json; the next nightly run does the rest.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from scraper.lib import fetch, find_cheapest_beer

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CANDIDATES_PATH = DATA_DIR / "candidates.json"
OUTPUT_PATH = DATA_DIR / "restaurants.json"


def main() -> int:
    if not CANDIDATES_PATH.exists():
        print("no candidates.json — nothing to discover", file=sys.stderr)
        return 0

    candidates = json.loads(CANDIDATES_PATH.read_text())
    entries = json.loads(OUTPUT_PATH.read_text()) if OUTPUT_PATH.exists() else []
    by_id = {e["id"]: e for e in entries}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    added = updated = kept_stale = skipped = 0
    for cand in candidates:
        cid = cand["id"]
        previous = by_id.get(cid)
        if previous is not None and not previous.get("discovered"):
            # A dedicated module owns this id; the candidate is redundant.
            continue
        try:
            beer = find_cheapest_beer(fetch(cand["url"]))
        except Exception as exc:  # noqa: BLE001 — one bad site must not stop the pass
            print(f"[discover:{cid}] FAIL: {exc}", file=sys.stderr)
            beer = None
        if beer is not None:
            by_id[cid] = {
                "id": cid,
                "name": cand["name"],
                "address": cand["address"],
                "lat": cand["lat"],
                "lon": cand["lon"],
                "source_url": cand["url"],
                "cheapest_beer": beer.to_json(),
                "last_updated": now,
                "stale": False,
                "discovered": True,
            }
            if previous is None:
                added += 1
                print(f"[discover:{cid}] NEW: {beer.name} {beer.price_sek} kr", file=sys.stderr)
            else:
                updated += 1
                print(f"[discover:{cid}] OK: {beer.name} {beer.price_sek} kr", file=sys.stderr)
        elif previous is not None:
            previous["stale"] = True
            previous.setdefault("stale_reason", "discovery scrape failed")
            kept_stale += 1
        else:
            skipped += 1

    out = sorted(by_id.values(), key=lambda e: e["id"])
    OUTPUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print(
        f"discovery: {added} new, {updated} refreshed, {kept_stale} kept stale, "
        f"{skipped} not yet scrapeable — {len(out)} total entries",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
