"""Validate data/restaurants.json before it is committed.

Run as: python -m scraper.validate

Exits non-zero with a clear message if the data violates the expected
shape, so the GitHub Actions workflow never commits corrupt JSON.
Staleness is allowed -- this checks shape, not freshness.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "restaurants.json"

EXPECTED_COUNT = 10

# Östermalm bounding box
LAT_MIN, LAT_MAX = 59.30, 59.37
LON_MIN, LON_MAX = 18.04, 18.13

PRICE_MIN, PRICE_MAX = 30, 300
VOLUME_MIN, VOLUME_MAX = 10, 100
KR_PER_CL_TOLERANCE = 0.05

REQUIRED_KEYS = (
    "id",
    "name",
    "address",
    "lat",
    "lon",
    "source_url",
    "cheapest_beer",
    "last_updated",
    "stale",
)


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _validate_beer(beer: object, errors: list[str], where: str) -> None:
    if beer is None:
        return
    if not isinstance(beer, dict):
        errors.append(f"{where}: cheapest_beer must be null or an object, got {type(beer).__name__}")
        return

    name = beer.get("name")
    if not isinstance(name, str) or not name.strip():
        errors.append(f"{where}: cheapest_beer.name must be a non-empty string, got {name!r}")

    price = beer.get("price_sek")
    if not _is_int(price) or not (PRICE_MIN <= price <= PRICE_MAX):
        errors.append(
            f"{where}: cheapest_beer.price_sek must be an int in [{PRICE_MIN}, {PRICE_MAX}], got {price!r}"
        )

    volume = beer.get("volume_cl")
    if volume is not None and (not _is_int(volume) or not (VOLUME_MIN <= volume <= VOLUME_MAX)):
        errors.append(
            f"{where}: cheapest_beer.volume_cl must be null or an int in [{VOLUME_MIN}, {VOLUME_MAX}], got {volume!r}"
        )
        volume = None  # do not attempt the ratio check with a bad volume

    kr_per_cl = beer.get("kr_per_cl")
    if kr_per_cl is not None and not _is_number(kr_per_cl):
        errors.append(f"{where}: cheapest_beer.kr_per_cl must be null or a number, got {kr_per_cl!r}")
    elif kr_per_cl is not None and volume is not None and _is_int(price):
        expected = price / volume
        if abs(kr_per_cl - expected) > KR_PER_CL_TOLERANCE:
            errors.append(
                f"{where}: cheapest_beer.kr_per_cl={kr_per_cl} inconsistent with "
                f"price_sek/volume_cl={expected:.4f} (tolerance {KR_PER_CL_TOLERANCE})"
            )


def _validate_entry(entry: object, index: int, errors: list[str]) -> None:
    where = f"entry[{index}]"
    if not isinstance(entry, dict):
        errors.append(f"{where}: must be an object, got {type(entry).__name__}")
        return
    if isinstance(entry.get("id"), str):
        where = f"entry[{index}] ({entry['id']})"

    missing = [key for key in REQUIRED_KEYS if key not in entry]
    if missing:
        errors.append(f"{where}: missing required keys: {', '.join(missing)}")

    for key in ("id", "name", "address"):
        if key in entry and (not isinstance(entry[key], str) or not entry[key].strip()):
            errors.append(f"{where}: {key} must be a non-empty string, got {entry[key]!r}")

    lat = entry.get("lat")
    if "lat" in entry and (not _is_number(lat) or not (LAT_MIN <= lat <= LAT_MAX)):
        errors.append(f"{where}: lat must be a number in [{LAT_MIN}, {LAT_MAX}], got {lat!r}")

    lon = entry.get("lon")
    if "lon" in entry and (not _is_number(lon) or not (LON_MIN <= lon <= LON_MAX)):
        errors.append(f"{where}: lon must be a number in [{LON_MIN}, {LON_MAX}], got {lon!r}")

    source_url = entry.get("source_url")
    if "source_url" in entry and (
        not isinstance(source_url, str) or not source_url.startswith("https://")
    ):
        errors.append(f"{where}: source_url must start with https://, got {source_url!r}")

    last_updated = entry.get("last_updated")
    if "last_updated" in entry:
        if not isinstance(last_updated, str):
            errors.append(f"{where}: last_updated must be an ISO-8601 string, got {last_updated!r}")
        else:
            try:
                datetime.fromisoformat(last_updated)
            except ValueError:
                errors.append(f"{where}: last_updated is not valid ISO-8601: {last_updated!r}")

    if "stale" in entry and not isinstance(entry["stale"], bool):
        errors.append(f"{where}: stale must be a boolean, got {entry['stale']!r}")

    if "cheapest_beer" in entry:
        _validate_beer(entry["cheapest_beer"], errors, where)


def validate(path: Path = DATA_PATH) -> list[str]:
    errors: list[str] = []

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"cannot read {path}: {exc}"]

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return [f"{path} is not valid JSON: {exc}"]

    if not isinstance(data, list):
        return [f"top-level value must be a JSON array, got {type(data).__name__}"]

    if len(data) != EXPECTED_COUNT:
        errors.append(f"expected exactly {EXPECTED_COUNT} entries, found {len(data)}")

    ids = [e.get("id") for e in data if isinstance(e, dict) and "id" in e]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        errors.append(f"duplicate ids: {', '.join(map(str, duplicates))}")

    for index, entry in enumerate(data):
        _validate_entry(entry, index, errors)

    if not errors:
        stale = sum(1 for e in data if e.get("stale") is True)
        fresh = len(data) - stale
        print(f"OK: {len(data)} entries validated — {fresh} fresh, {stale} stale")

    return errors


def main() -> int:
    errors = validate()
    if errors:
        print(f"VALIDATION FAILED for {DATA_PATH} ({len(errors)} problem(s)):", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
