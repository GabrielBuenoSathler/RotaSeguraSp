import { useEffect } from "react";

import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Polyline,
  Popup,
  useMap,
  useMapEvents,
} from "react-leaflet";

import type { Coordinates } from "../types/route";

interface MapViewProps {
  origin: Coordinates | null;
  destination: Coordinates | null;
  geometry: [number, number][] | null;
  onSelectPoint: (point: Coordinates) => void;
}

function MapClickHandler({
  onSelectPoint,
}: {
  onSelectPoint: (point: Coordinates) => void;
}) {
  useMapEvents({
    click(event) {
      onSelectPoint({
        lat: event.latlng.lat,
        lon: event.latlng.lng,
      });
    },
  });

  return null;
}

function FitRoute({
  origin,
  destination,
  geometry,
}: {
  origin: Coordinates | null;
  destination: Coordinates | null;
  geometry: [number, number][] | null;
}) {
  const map = useMap();

  useEffect(() => {
    if (geometry && geometry.length > 1) {
      map.fitBounds(geometry, { padding: [40, 40] });
      return;
    }

    if (origin && destination) {
      map.fitBounds(
        [
          [origin.lat, origin.lon],
          [destination.lat, destination.lon],
        ],
        { padding: [40, 40] }
      );
      return;
    }

    const point = origin ?? destination;

    if (point) {
      map.setView([point.lat, point.lon], 15);
    }
  }, [map, origin, destination, geometry]);

  return null;
}

export default function MapView({
  origin,
  destination,
  geometry,
  onSelectPoint,
}: MapViewProps) {
  return (
    <MapContainer
      center={[-23.5505, -46.6333]}
      zoom={12}
      className="map-container"
      scrollWheelZoom
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      <MapClickHandler onSelectPoint={onSelectPoint} />

      <FitRoute
        origin={origin}
        destination={destination}
        geometry={geometry}
      />

      {origin && (
        <CircleMarker
          center={[origin.lat, origin.lon]}
          radius={9}
          pathOptions={{
            color: "#ffffff",
            fillColor: "#0f766e",
            fillOpacity: 1,
            weight: 3,
          }}
        >
          <Popup>Origem</Popup>
        </CircleMarker>
      )}

      {destination && (
        <CircleMarker
          center={[destination.lat, destination.lon]}
          radius={9}
          pathOptions={{
            color: "#ffffff",
            fillColor: "#d97745",
            fillOpacity: 1,
            weight: 3,
          }}
        >
          <Popup>Destino</Popup>
        </CircleMarker>
      )}

      {geometry && geometry.length > 0 && (
        <Polyline
          positions={geometry}
          pathOptions={{
            color: "#0f766e",
            weight: 6,
            opacity: 0.85,
          }}
        />
      )}
    </MapContainer>
  );
}
