# alkoholperkrona

iOS app showing the cheapest beer at 10 restaurants in Stockholm Östermalm,
on a map. Tap a pin → see the price.

```
┌──────────────────┐         ┌─────────────────────┐
│  scraper/ (py)   │  daily  │  data/              │
│  10 site scripts │ ──────► │  restaurants.json   │
│  + GitHub Action │         │  (committed)        │
└──────────────────┘         └──────────┬──────────┘
                                        │ raw.githubusercontent.com
                                        ▼
                             ┌─────────────────────┐
                             │  app/  (Expo iOS)   │
                             │  Map + pins         │
                             └─────────────────────┘
```

## Restaurants tracked

Sturehof, Riche, Tures, Brasserie Godot, Teatergrillen, Brasserie Bobonne,
Hillenberg, Nybrogatan 38, Grodan Grev Ture, Lisa Elmqvist.

(Bistro Bestick, Bagatelle and Knut Östermalm were dropped — their sites
are gone or unreachable — and replaced with Hillenberg, Nybrogatan 38 and
Grodan Grev Ture.)

Each has its own scraper at `scraper/restaurants/<id>.py`. Add or remove a
restaurant by adding/removing one file (see `_template.py`).

## Run the scraper locally

```bash
cd scraper
pip install -r requirements.txt
python -m scraper.main
# writes ../data/restaurants.json
```

Parsers in `scraper/lib.py`: `find_cheapest_beer_svbr` for the Svenska
Brasserier WordPress theme (Sturehof, Riche, Teatergrillen),
`find_cheapest_beer_in_text` for PDF drink lists (Lisa Elmqvist,
Hillenberg, Nybrogatan 38, Grodan), and the generic `find_cheapest_beer`
heading heuristic as a fallback. Sites that don't publish beer prices at
all (currently Brasserie Godot and Brasserie Bobonne) are kept and simply
marked `stale` by the orchestrator. For a new site, override `scrape()`
in that restaurant's module with site-specific selectors (<40 lines).

## Run the iOS app

You need an iPhone with the free [Expo Go](https://apps.apple.com/se/app/expo-go/id982107779)
app installed.

```bash
cd app
npm install
npx expo start
```

Scan the QR code with the iPhone camera → opens in Expo Go → see the map.

The app fetches `data/restaurants.json` from GitHub raw on each launch and
falls back to the bundled copy at `app/assets/restaurants.json` if the
network call fails.

## GitHub Action

`.github/workflows/scrape.yml` runs the scraper daily at 04:17 UTC and
commits a refreshed `data/restaurants.json` if anything changed. You can
trigger it manually from the Actions tab.

> The action needs `contents: write` permission, which is already set in
> the workflow file. If pushes fail, check **Settings → Actions → General →
> Workflow permissions** and ensure "Read and write permissions" is enabled.

## Data shape

```json
{
  "id": "sturehof",
  "name": "Sturehof",
  "address": "Stureplan 2, 114 35 Stockholm",
  "lat": 59.3358,
  "lon": 18.0743,
  "source_url": "https://www.sturehof.com/menyer-och-drycker/",
  "cheapest_beer": {
    "name": "Norrlands Guld",
    "volume_cl": 50,
    "price_sek": 89,
    "kr_per_cl": 1.78
  },
  "last_updated": "2026-05-06T04:17:00+00:00",
  "stale": false
}
```

`stale: true` means the last scrape didn't find a beer (the menu format
changed, the site was down, etc.); in that case `cheapest_beer` is the
last known value or `null`.

## Caveats

- **The seed `data/restaurants.json` has placeholder prices** marked
  `stale: true`. Real values arrive after the first successful scraper
  run (locally or via GitHub Actions).
- **Scrapers break.** When a restaurant redesigns its site, that one
  scraper will start returning nothing and that restaurant will go
  stale. The fix is to update its `scrape()` override.
- **Lat/lon are approximate.** They're hard-coded once per restaurant —
  edit the `META` dict in the corresponding module to refine.
- **Menus may not list beer prices online** — many Swedish restaurants
  publish only food menus on the web. If a restaurant always returns
  "no beer found", swap it out for another in `scraper/restaurants/`.
- **Robots / ToS.** The scraper identifies itself in the User-Agent,
  rate-limits to 1 req/s, and runs once a day. Don't crank that up.
