import { useEffect, useMemo, useRef, useState } from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";
import MapView, { Callout, Marker, PROVIDER_DEFAULT } from "react-native-maps";
import { loadRestaurants } from "./data";
import { PinCallout } from "./PinCallout";
import { PriceMarker } from "./PriceMarker";
import { RankList, sortByValue } from "./RankList";
import type { Restaurant } from "./types";

const OSTERMALM = {
  latitude: 59.3365,
  longitude: 18.0795,
  latitudeDelta: 0.014,
  longitudeDelta: 0.014,
};

export function MapScreen() {
  const [restaurants, setRestaurants] = useState<Restaurant[] | null>(null);
  const [listExpanded, setListExpanded] = useState(false);
  const [mapReady, setMapReady] = useState(false);
  const mapRef = useRef<MapView>(null);

  useEffect(() => {
    loadRestaurants().then(setRestaurants);
  }, []);

  useEffect(() => {
    if (!mapReady || !restaurants?.length) return;
    mapRef.current?.fitToCoordinates(
      restaurants.map((r) => ({ latitude: r.lat, longitude: r.lon })),
      {
        edgePadding: { top: 100, right: 50, bottom: 140, left: 50 },
        animated: false,
      },
    );
  }, [mapReady, restaurants]);

  const bestId = useMemo(() => {
    if (!restaurants) return null;
    const best = sortByValue(restaurants)[0];
    return best && !best.stale && best.cheapest_beer ? best.id : null;
  }, [restaurants]);

  if (!restaurants) {
    return (
      <View style={styles.loading}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  const flyTo = (r: Restaurant) => {
    setListExpanded(false);
    mapRef.current?.animateToRegion(
      { latitude: r.lat, longitude: r.lon, latitudeDelta: 0.005, longitudeDelta: 0.005 },
      400,
    );
  };

  return (
    <View style={styles.container}>
      <MapView
        ref={mapRef}
        style={styles.map}
        provider={PROVIDER_DEFAULT}
        initialRegion={OSTERMALM}
        onMapReady={() => setMapReady(true)}
        showsUserLocation
        showsMyLocationButton
      >
        {restaurants.map((r) => (
          <Marker
            key={r.id}
            coordinate={{ latitude: r.lat, longitude: r.lon }}
            tracksViewChanges={false}
            anchor={{ x: 0.5, y: 1 }}
            centerOffset={{ x: 0, y: -17 }}
          >
            <PriceMarker r={r} isBest={r.id === bestId} />
            <Callout tooltip>
              <View style={styles.callout}>
                <PinCallout r={r} />
              </View>
            </Callout>
          </Marker>
        ))}
      </MapView>
      <View style={styles.banner} pointerEvents="none">
        <Text style={styles.bannerText}>alkoholperkrona · Stockholm</Text>
      </View>
      <RankList
        restaurants={restaurants}
        expanded={listExpanded}
        onToggle={() => setListExpanded((v) => !v)}
        onPick={flyTo}
      />
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
