"""Append today's fresh prices to data/history.json.

Run as: python -m scraper.history  (after scraper.discovery, before validate)

data/history.json maps venue id -> [[YYYY-MM-DD, price_sek], ...] in
chronological order. Only fresh (non-stale) prices are recorded; a re-run
on the same day overwrites that day's point instead of duplicating it.
Series are capped at 180 points (~6 months of daily scrapes). The site
renders these as sparklines in the venue popups.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RESTAURANTS_PATH = DATA_DIR / "restaurants.json"
HISTORY_PATH = DATA_DIR / "history.json"
MAX_POINTS = 180


def main() -> int:
    venues = json.loads(RESTAURANTS_PATH.read_text())
    history: dict[str, list] = (
        json.loads(HISTORY_PATH.read_text()) if HISTORY_PATH.exists() else {}
    )
    today = datetime.now(timezone.utc).date().isoformat()

    added = updated = 0
    for v in venues:
        beer = v.get("cheapest_beer")
        if v.get("stale") or not beer:
            continue
        series = history.setdefault(v["id"], [])
        point = [today, beer["price_sek"]]
        if series and series[-1][0] == today:
            if series[-1][1] != beer["price_sek"]:
                series[-1] = point
                updated += 1
        else:
            series.append(point)
            added += 1
        del series[:-MAX_POINTS]

    HISTORY_PATH.write_text(
        json.dumps(dict(sorted(history.items())), ensure_ascii=False, indent=1) + "\n"
    )
    print(f"history: {added} new points, {updated} updated, {len(history)} series", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
