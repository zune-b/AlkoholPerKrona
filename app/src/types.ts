export type Beer = {
  name: string;
  volume_cl: number | null;
  price_sek: number;
  kr_per_cl: number | null;
};

export type Restaurant = {
  id: string;
  name: string;
  address: string;
  lat: number;
  lon: number;
  source_url: string;
  cheapest_beer: Beer | null;
  last_updated: string;
  stale?: boolean;
  stale_reason?: string;
  discovered?: boolean;
};
