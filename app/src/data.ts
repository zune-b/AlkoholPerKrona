import Constants from "expo-constants";
import bundled from "../assets/restaurants.json";
import type { Restaurant } from "./types";

const FETCH_TIMEOUT_MS = 5000;

const dataUrl: string =
  (Constants.expoConfig?.extra as { dataUrl?: string } | undefined)?.dataUrl ??
  "https://raw.githubusercontent.com/zune-b/testla-/main/data/restaurants.json";

export async function loadRestaurants(): Promise<Restaurant[]> {
  try {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), FETCH_TIMEOUT_MS);
    const resp = await fetch(dataUrl, { signal: ctrl.signal });
    clearTimeout(t);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const json = (await resp.json()) as Restaurant[];
    if (!Array.isArray(json) || json.length === 0) throw new Error("empty");
    return json;
  } catch {
    return bundled as Restaurant[];
  }
}
