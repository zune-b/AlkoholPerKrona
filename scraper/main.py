"""Run all restaurant scrapers and write data/restaurants.json.

Usage: `python -m scraper.main`

Behaviour:
- For each restaurant module, run scrape().
- On success, emit a fresh entry with last_updated = now (UTC).
- On failure (network error, no beer found, exception), keep the previous
  entry from data/restaurants.json (if any) and mark `stale: true`.
- Always overwrite data/restaurants.json with the merged result so the file
  remains valid even if every scraper fails.

Exit code is 0 unless the output file could not be written. Individual
scraper failures are logged but don't fail the run, so a flaky restaurant
doesn't block the cron job from updating the others.
"""

from __future__ import annotations

import importlib
import json
import pkgutil
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

from scraper import restaurants as restaurants_pkg
from scraper.lib import Beer

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "restaurants.json"


def _discover_modules() -> list:
    mods = []
    for info in pkgutil.iter_modules(restaurants_pkg.__path__):
        if info.name.startswith("_"):
            continue
        mods.append(importlib.import_module(f"scraper.restaurants.{info.name}"))
    mods.sort(key=lambda m: m.META["id"])
    return mods


def _load_previous() -> dict[str, dict]:
    if not OUTPUT_PATH.exists():
        return {}
    try:
        existing = json.loads(OUTPUT_PATH.read_text())
        return {entry["id"]: entry for entry in existing}
    except (json.JSONDecodeError, KeyError):
        return {}


def _entry(meta: dict, beer: Beer, now: str) -> dict:
    return {
        "id": meta["id"],
        "name": meta["name"],
        "address": meta["address"],
        "lat": meta["lat"],
        "lon": meta["lon"],
        "source_url": meta["source_url"],
        "cheapest_beer": beer.to_json(),
        "last_updated": now,
        "stale": False,
    }


def _stale_entry(meta: dict, prev: dict | None, now: str, reason: str) -> dict:
    base = {
        "id": meta["id"],
        "name": meta["name"],
        "address": meta["address"],
        "lat": meta["lat"],
        "lon": meta["lon"],
        "source_url": meta["source_url"],
        "cheapest_beer": prev["cheapest_beer"] if prev else None,
        "last_updated": prev["last_updated"] if prev else now,
        "stale": True,
        "stale_reason": reason,
    }
    return base


def main() -> int:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    prev = _load_previous()
    out: list[dict] = []
    failures = 0
    for mod in _discover_modules():
        meta = mod.META
        try:
            beer = mod.scrape()
        except Exception as exc:  # noqa: BLE001 — we want to keep going
            print(f"[scrape:{meta['id']}] FAIL: {exc}", file=sys.stderr)
            traceback.print_exc()
            out.append(_stale_entry(meta, prev.get(meta["id"]), now, str(exc)))
            failures += 1
            continue
        if beer is None:
            print(f"[scrape:{meta['id']}] no beer found", file=sys.stderr)
            out.append(_stale_entry(meta, prev.get(meta["id"]), now, "no beer found"))
            failures += 1
            continue
        print(f"[scrape:{meta['id']}] OK: {beer.name} {beer.price_sek} kr", file=sys.stderr)
        out.append(_entry(meta, beer, now))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print(f"Wrote {len(out)} entries to {OUTPUT_PATH} ({failures} failures)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
