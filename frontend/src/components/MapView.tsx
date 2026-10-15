import { Fragment, useEffect } from "react";

import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Polyline,
  Popup,
  Tooltip,
  useMap,
  useMapEvents,
} from "react-leaflet";

import CrimeHeatmap from "./CrimeHeatmap";
import type { HeatCell, Coordinates, RouteOption } from "../types/route";

interface MapViewProps {
  heatCells: HeatCell[];
  heatGroups: string[];
  heatMonth: string;
  origin: Coordinates | null;
  destination: Coordinates | null;
  geometry: [number, number][] | null;
  onSelectPoint: (point: Coordinates) => void;
  options: RouteOption[];
  selectedId?: number;
  recommendedId?: number;
  editing: boolean;
  onChooseRoute: (option: RouteOption) => void;
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
  options,
}: {
  origin: Coordinates | null;
  destination: Coordinates | null;
  geometry: [number, number][] | null;
  options: RouteOption[];
}) {
  const map = useMap();

  useEffect(() => {
    function fit() {
      map.invalidateSize({ pan: false });
      const allPoints = options.flatMap(option => option.route.geometry?.coordinates.map(([lon, lat]): [number, number] => [lat, lon]) ?? []);
      if (allPoints.length > 1) {
        map.fitBounds(allPoints, { padding: [48, 48], animate: false });
      } else if (geometry && geometry.length > 1) {
        map.fitBounds(geometry, { padding: [40, 40], animate: false });
      } else if (origin && destination) {
        map.fitBounds([[origin.lat, origin.lon], [destination.lat, destination.lon]], { padding: [40, 40], animate: false });
      } else {
        const point = origin ?? destination;
        if (point) map.setView([point.lat, point.lon], 15);
      }
    }
    fit();
    const observer = new ResizeObserver(fit);
    observer.observe(map.getContainer());
    return () => observer.disconnect();
  }, [map, origin, destination, geometry, options]);

  return null;
}

function labelPosition(points: [number, number][], fraction: number): [number, number] {
  const lengths = points.slice(1).map((point, index) => Math.hypot(
    point[0] - points[index][0],
    (point[1] - points[index][1]) * Math.cos(point[0] * Math.PI / 180),
  ));
  let remaining = lengths.reduce((sum, length) => sum + length, 0) * fraction;
  for (let i = 0; i < lengths.length; i++) {
    if (remaining <= lengths[i] && lengths[i] > 0) {
      const ratio = remaining / lengths[i];
      return [points[i][0] + (points[i + 1][0] - points[i][0]) * ratio,
        points[i][1] + (points[i + 1][1] - points[i][1]) * ratio];
    }
    remaining -= lengths[i];
  }
  return points[0];
}

export default function MapView({
  origin,
  destination,
  geometry,
  onSelectPoint, options, selectedId, recommendedId, editing, onChooseRoute, heatCells, heatGroups, heatMonth,
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

      <CrimeHeatmap cells={heatCells} groups={heatGroups} month={heatMonth} />

      {editing && <MapClickHandler onSelectPoint={onSelectPoint} />}

      <FitRoute
        origin={origin}
        destination={destination}
        geometry={geometry}
        options={options}
      />

      {origin && (
        <CircleMarker
          pane="markerPane"
          center={[origin.lat, origin.lon]}
          radius={16}
          pathOptions={{
            color: "#ffffff",
            fillColor: "#2854cf",
            fillOpacity: 1,
            weight: 3,
          }}
        >
          <Tooltip permanent direction="center" className="point-label">A</Tooltip><Popup>Origem</Popup>
        </CircleMarker>
      )}

      {destination && (
        <CircleMarker
          pane="markerPane"
          center={[destination.lat, destination.lon]}
          radius={16}
          pathOptions={{
            color: "#ffffff",
            fillColor: "#2854cf",
            fillOpacity: 1,
            weight: 3,
          }}
        >
          <Tooltip permanent direction="center" className="point-label">B</Tooltip><Popup>Destino</Popup>
        </CircleMarker>
      )}

      {[...options].sort((a, b) => {
        const rank = (option: RouteOption) => option.route.calculated_route_id === recommendedId ? 2 : option.route.calculated_route_id === selectedId ? 1 : 0;
        return rank(a) - rank(b);
      }).map(option => {
        if (!option.route.geometry?.coordinates.length) return null;
        const index = options.indexOf(option);
        const recommended = option.route.calculated_route_id === recommendedId;
        const selected = option.route.calculated_route_id === selectedId;
        const positions = option.route.geometry.coordinates.map(([lon, lat]): [number, number] => [lat, lon]);
        const minutes = option.route.duration_seconds === undefined ? null : Math.round(option.route.duration_seconds / 60);
        return <Fragment key={option.route.calculated_route_id}><Polyline positions={positions} interactive={false}
          pathOptions={{ color: "#ffffff", weight: recommended ? 11 : 9, opacity: 1 }} />
          <Polyline positions={positions} bubblingMouseEvents={false} className={recommended ? "recommended-route" : "alternative-route"}
            pathOptions={{ color: recommended ? "#2854cf" : selected ? "#424957" : "#8c9ebc", weight: recommended ? 7 : 5, opacity: 1, bubblingMouseEvents: false, className: recommended ? "recommended-route" : "alternative-route" }}
            eventHandlers={{ click: () => onChooseRoute(option) }}>
          </Polyline>
          <CircleMarker center={labelPosition(positions, 0.3 + index * 0.2)} radius={0} interactive={false}>
            <Tooltip permanent direction="top" offset={[0, -8]}
              className={`route-map-label ${recommended ? "is-recommended" : ""}`} interactive>
              <span onClick={() => onChooseRoute(option)}>{minutes === null ? (index === 0 ? "Trajeto principal" : `Alternativa ${index}`) : `${minutes} min`}{recommended ? " · Recomendada" : selected ? " · Selecionada" : ""}</span>
            </Tooltip>
          </CircleMarker>
        </Fragment>;
      })}

    </MapContainer>
  );
}
