import { FlatList, Pressable, StyleSheet, Text, View } from "react-native";
import type { Restaurant } from "./types";

type Props = {
  restaurants: Restaurant[];
  expanded: boolean;
  onToggle: () => void;
  onPick: (r: Restaurant) => void;
};

export function rankValue(r: Restaurant): number {
  const beer = r.cheapest_beer;
  if (!beer) return Number.POSITIVE_INFINITY;
  // Rank by kr/cl when volume is known, otherwise assume 40 cl so
  // volume-less entries still sort roughly right instead of sinking.
  return beer.kr_per_cl ?? beer.price_sek / 40;
}

export function sortByValue(restaurants: Restaurant[]): Restaurant[] {
  return [...restaurants].sort((a, b) => {
    if (!!a.stale !== !!b.stale) return a.stale ? 1 : -1;
    return rankValue(a) - rankValue(b);
  });
}

export function RankList({ restaurants, expanded, onToggle, onPick }: Props) {
  const sorted = sortByValue(restaurants);
  return (
    <View style={styles.panel}>
      <Pressable onPress={onToggle} style={styles.handle}>
        <Text style={styles.handleText}>
          {expanded ? "▼  Topplista — kr/cl" : "▲  Topplista — kr/cl"}
        </Text>
      </Pressable>
      {expanded && (
        <FlatList
          data={sorted}
          keyExtractor={(r) => r.id}
          style={styles.list}
          renderItem={({ item, index }) => {
            const beer = item.cheapest_beer;
            return (
              <Pressable onPress={() => onPick(item)} style={styles.row}>
                <Text style={styles.rank}>{index + 1}</Text>
                <View style={styles.rowBody}>
                  <Text style={styles.name} numberOfLines={1}>
                    {item.name}
                    {item.stale ? "  ⚠" : ""}
                  </Text>
                  {beer ? (
                    <Text style={styles.detail} numberOfLines={1}>
                      {beer.name}
                      {beer.volume_cl ? ` · ${beer.volume_cl} cl` : ""}
                    </Text>
                  ) : (
                    <Text style={styles.detail}>Inget pris ännu</Text>
                  )}
                </View>
                {beer ? (
                  <View style={styles.rowRight}>
                    <Text style={styles.price}>{beer.price_sek} kr</Text>
                    {beer.kr_per_cl ? (
                      <Text style={styles.perCl}>{beer.kr_per_cl.toFixed(2)} kr/cl</Text>
                    ) : null}
                  </View>
                ) : null}
              </Pressable>
            );
          }}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  panel: {
    position: "absolute",
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: "rgba(255,255,255,0.97)",
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
    shadowColor: "#000",
    shadowOpacity: 0.15,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: -2 },
    elevation: 8,
    maxHeight: "55%",
  },
  handle: { alignItems: "center", paddingVertical: 10 },
  handleText: { fontSize: 13, fontWeight: "600", color: "#444" },
  list: { paddingHorizontal: 12 },
  row: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 9,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: "#ddd",
  },
  rank: { width: 26, fontSize: 15, fontWeight: "700", color: "#999" },
  rowBody: { flex: 1, marginRight: 8 },
  name: { fontSize: 15, fontWeight: "600", color: "#222" },
  detail: { fontSize: 12, color: "#777", marginTop: 1 },
  rowRight: { alignItems: "flex-end" },
  price: { fontSize: 15, fontWeight: "700", color: "#222" },
  perCl: { fontSize: 11, color: "#777", marginTop: 1 },
});
