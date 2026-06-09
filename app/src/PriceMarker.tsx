import { StyleSheet, Text, View } from "react-native";
import type { Restaurant } from "./types";

type Props = { r: Restaurant; isBest: boolean };

export function PriceMarker({ r, isBest }: Props) {
  const beer = r.cheapest_beer;
  const label = beer ? `${beer.price_sek}:-` : "—";
  return (
    <View style={styles.wrap}>
      <View
        style={[
          styles.bubble,
          r.stale ? styles.bubbleStale : styles.bubbleFresh,
          isBest && styles.bubbleBest,
        ]}
      >
        {isBest ? <Text style={styles.crown}>👑</Text> : null}
        <Text style={[styles.price, r.stale && styles.priceStale]}>{label}</Text>
      </View>
      <View
        style={[
          styles.pointer,
          r.stale ? styles.pointerStale : styles.pointerFresh,
          isBest && styles.pointerBest,
        ]}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { alignItems: "center" },
  bubble: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
    borderWidth: 1.5,
    shadowColor: "#000",
    shadowOpacity: 0.2,
    shadowRadius: 3,
    shadowOffset: { width: 0, height: 1 },
    elevation: 3,
  },
  bubbleFresh: { backgroundColor: "tomato", borderColor: "#c43a25" },
  bubbleStale: { backgroundColor: "#9a9a9a", borderColor: "#7c7c7c" },
  bubbleBest: { backgroundColor: "#f5b942", borderColor: "#c98f1b" },
  crown: { fontSize: 11, marginRight: 3 },
  price: { color: "white", fontWeight: "700", fontSize: 13 },
  priceStale: { color: "#eee" },
  pointer: {
    width: 0,
    height: 0,
    borderLeftWidth: 5,
    borderRightWidth: 5,
    borderTopWidth: 7,
    borderLeftColor: "transparent",
    borderRightColor: "transparent",
    marginTop: -1,
  },
  pointerFresh: { borderTopColor: "#c43a25" },
  pointerStale: { borderTopColor: "#7c7c7c" },
  pointerBest: { borderTopColor: "#c98f1b" },
});
