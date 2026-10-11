export interface Coordinates {
  lat: number;
  lon: number;
}

export interface RouteResult {
  route_request_id?: number;
  calculated_route_id?: number;
  distance_km?: number;
  duration_seconds?: number;
  geometry_points?: number;
  geometry?: {
    type: "LineString";
    coordinates: [number, number][];
  };
  message?: string;
}
