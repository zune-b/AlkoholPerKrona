import { Linking, StyleSheet, Text, View } from "react-native";
import type { Restaurant } from "./types";

type Props = { r: Restaurant };

function formatUpdated(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const days = Math.floor((Date.now() - d.getTime()) / 86_400_000);
  if (days <= 0) return "today";
  if (days === 1) return "1 day ago";
  return `${days} days ago`;
}

export function PinCallout({ r }: Props) {
  const beer = r.cheapest_beer;
  return (
    <View style={styles.card}>
      <Text style={styles.title}>{r.name}</Text>
      {beer ? (
        <>
          <Text style={styles.beer}>{beer.name}</Text>
          <View style={styles.row}>
            <Text style={styles.price}>{beer.price_sek} kr</Text>
            {beer.volume_cl ? <Text style={styles.volume}>· {beer.volume_cl} cl</Text> : null}
            {beer.kr_per_cl ? <Text style={styles.perCl}>· {beer.kr_per_cl} kr/cl</Text> : null}
          </View>
        </>
      ) : (
        <Text style={styles.unavailable}>No price available yet</Text>
      )}
      <Text style={styles.updated}>
        Updated {formatUpdated(r.last_updated)}
        {r.stale ? "  ·  ⚠ stale" : ""}
      </Text>
      <Text style={styles.link} onPress={() => Linking.openURL(r.source_url)}>
        Open menu →
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { width: 240, paddingVertical: 4 },
  title: { fontSize: 16, fontWeight: "600", marginBottom: 4 },
  beer: { fontSize: 14, color: "#333", marginBottom: 4 },
  row: { flexDirection: "row", alignItems: "baseline", marginBottom: 4 },
  price: { fontSize: 18, fontWeight: "700" },
  volume: { fontSize: 13, color: "#666", marginLeft: 6 },
  perCl: { fontSize: 13, color: "#666", marginLeft: 6 },
  unavailable: { fontSize: 13, color: "#999", marginVertical: 4 },
  updated: { fontSize: 11, color: "#888", marginTop: 2 },
  link: { fontSize: 12, color: "#1a73e8", marginTop: 6 },
});
