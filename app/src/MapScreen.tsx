import { useEffect, useState } from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";
import MapView, { Callout, Marker, PROVIDER_DEFAULT } from "react-native-maps";
import { loadRestaurants } from "./data";
import { PinCallout } from "./PinCallout";
import type { Restaurant } from "./types";

const OSTERMALM = {
  latitude: 59.3365,
  longitude: 18.0795,
  latitudeDelta: 0.014,
  longitudeDelta: 0.014,
};

export function MapScreen() {
  const [restaurants, setRestaurants] = useState<Restaurant[] | null>(null);

  useEffect(() => {
    loadRestaurants().then(setRestaurants);
  }, []);

  if (!restaurants) {
    return (
      <View style={styles.loading}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <MapView
        style={styles.map}
        provider={PROVIDER_DEFAULT}
        initialRegion={OSTERMALM}
        showsUserLocation
        showsMyLocationButton
      >
        {restaurants.map((r) => (
          <Marker
            key={r.id}
            coordinate={{ latitude: r.lat, longitude: r.lon }}
            pinColor={r.stale ? "gray" : "tomato"}
          >
            <Callout tooltip>
              <View style={styles.callout}>
                <PinCallout r={r} />
              </View>
            </Callout>
          </Marker>
        ))}
      </MapView>
      <View style={styles.banner} pointerEvents="none">
        <Text style={styles.bannerText}>alkoholperkrona · Östermalm</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  map: { flex: 1 },
  loading: { flex: 1, alignItems: "center", justifyContent: "center" },
  banner: {
    position: "absolute",
    top: 60,
    alignSelf: "center",
    backgroundColor: "rgba(255,255,255,0.92)",
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
  },
  bannerText: { fontSize: 13, fontWeight: "600", color: "#222" },
  callout: {
    backgroundColor: "white",
    borderRadius: 8,
    padding: 10,
    shadowColor: "#000",
    shadowOpacity: 0.18,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 2 },
    elevation: 4,
  },
});
