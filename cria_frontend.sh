#!/usr/bin/env bash

set -e

# ==========================================
# RotaSegura - Gerador de arquivos frontend
# Não instala pacotes nem inicia servidores.
# ==========================================

ROOT_DIR="$(pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"

echo "======================================"
echo " Criando frontend do RotaSegura"
echo "======================================"

# Verificar se o projeto Vite já existe
if [ ! -f "$FRONTEND_DIR/package.json" ]; then
  echo "ERRO: frontend/package.json não encontrado."
  echo
  echo "Execute primeiro:"
  echo "  cd \"$ROOT_DIR\""
  echo "  npm create vite@latest frontend -- --template react-ts"
  exit 1
fi

cd "$FRONTEND_DIR"

# Criar diretórios
mkdir -p src/components
mkdir -p src/services
mkdir -p src/types

# ==========================================
# 1. Variáveis de ambiente
# ==========================================

cat >.env <<'EOF'
VITE_API_URL=http://localhost:8000
EOF

# ==========================================
# 2. Tipos TypeScript
# ==========================================

cat >src/types/route.ts <<'EOF'
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
EOF

# ==========================================
# 3. Cliente da API
# ==========================================

cat >src/services/api.ts <<'EOF'
import axios from "axios";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});
EOF

# ==========================================
# 4. Componente do mapa
# ==========================================

cat >src/components/MapView.tsx <<'EOF'
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
            fillColor: "#16a34a",
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
            fillColor: "#dc2626",
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
            color: "#2563eb",
            weight: 6,
            opacity: 0.85,
          }}
        />
      )}
    </MapContainer>
  );
}
EOF

# ==========================================
# 5. Aplicação principal
# ==========================================

cat >src/App.tsx <<'EOF'
import { useState } from "react";

import MapView from "./components/MapView";
import { api } from "./services/api";

import type { Coordinates, RouteResult } from "./types/route";

import "./App.css";

export default function App() {
  const [origin, setOrigin] = useState<Coordinates | null>(null);
  const [destination, setDestination] =
    useState<Coordinates | null>(null);

  const [selecting, setSelecting] = useState<
    "origin" | "destination"
  >("origin");

  const [transportMode, setTransportMode] = useState("auto");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<RouteResult | null>(null);

  const [geometry, setGeometry] =
    useState<[number, number][] | null>(null);

  function selectPoint(point: Coordinates) {
    setError("");
    setResult(null);
    setGeometry(null);

    if (selecting === "origin") {
      setOrigin(point);
      setSelecting("destination");
    } else {
      setDestination(point);
    }
  }

  function clearSelection() {
    setOrigin(null);
    setDestination(null);
    setResult(null);
    setGeometry(null);
    setError("");
    setSelecting("origin");
  }

  async function calculateRoute() {
    if (!origin || !destination) {
      setError("Selecione a origem e o destino no mapa.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);
    setGeometry(null);

    try {
      /*
       * CONTRATO ESPERADO:
       *
       * POST /rota/
       * {
       *   "origin": {"lat": -23.55, "lon": -46.63},
       *   "destination": {"lat": -23.56, "lon": -46.64},
       *   "transport_mode": "auto"
       * }
       *
       * POST /rota/{id}/calculate
       *
       * Adapte o primeiro POST ao schema real do backend.
       */

      const createResponse = await api.post("/rota/", {
        origin: {
          lat: origin.lat,
          lon: origin.lon,
        },
        destination: {
          lat: destination.lat,
          lon: destination.lon,
        },
        transport_mode: transportMode,
      });

      const requestId =
        createResponse.data.id ??
        createResponse.data.route_request_id;

      if (requestId == null) {
        throw new Error(
          "A API não retornou o ID da solicitação."
        );
      }

      const response = await api.post(
        `/rota/${requestId}/calculate`
      );

      const data: RouteResult = response.data;

      setResult({
        ...data,
        route_request_id: requestId,
      });

      if (data.geometry?.coordinates) {
        setGeometry(
          data.geometry.coordinates.map(
            ([lon, lat]) => [lat, lon] as [number, number]
          )
        );
      }
    } catch (err: unknown) {
      if (typeof err === "object" && err !== null && "response" in err) {
        const response = (
          err as {
            response?: {
              status?: number;
              data?: { detail?: string | object };
            };
          }
        ).response;

        const detail = response?.data?.detail;

        setError(
          typeof detail === "string"
            ? detail
            : `Erro HTTP ${response?.status ?? "desconhecido"}. ` +
              "Confira os endpoints e os schemas da API."
        );
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Erro desconhecido ao calcular a rota.");
      }
    } finally {
      setLoading(false);
    }
  }

  function formatDuration(seconds?: number) {
    if (seconds === undefined) return "—";

    const minutes = Math.round(seconds / 60);

    if (minutes < 60) {
      return `${minutes} min`;
    }

    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;

    return `${hours} h ${remainingMinutes} min`;
  }

  function formatCoordinate(point: Coordinates | null) {
    if (!point) return "Selecione no mapa";

    return `${point.lat.toFixed(5)}, ${point.lon.toFixed(5)}`;
  }

  return (
    <main className="app">
      <header className="header">
        <div>
          <p className="eyebrow">MOBILIDADE URBANA</p>
          <h1>RotaSegura</h1>
          <p className="subtitle">
            Planeje seu trajeto por São Paulo.
          </p>
        </div>

        <span className="status">MVP</span>
      </header>

      <section className="workspace">
        <aside className="sidebar">
          <h2>Planejar rota</h2>

          <p className="instructions">
            Clique no mapa para selecionar os pontos.
            Primeiro escolha a origem e depois o destino.
          </p>

          <button
            type="button"
            className={`selection-item ${
              selecting === "origin" ? "active" : ""
            }`}
            onClick={() => setSelecting("origin")}
          >
            <span className="point-icon origin-icon">A</span>
            <span className="selection-text">
              <strong>Origem</strong>
              <small>{formatCoordinate(origin)}</small>
            </span>
          </button>

          <button
            type="button"
            className={`selection-item ${
              selecting === "destination" ? "active" : ""
            }`}
            onClick={() => setSelecting("destination")}
          >
            <span className="point-icon destination-icon">B</span>
            <span className="selection-text">
              <strong>Destino</strong>
              <small>{formatCoordinate(destination)}</small>
            </span>
          </button>

          <label htmlFor="transport" className="field-label">
            Meio de transporte
          </label>

          <select
            id="transport"
            className="transport-select"
            value={transportMode}
            onChange={(event) => setTransportMode(event.target.value)}
          >
            <option value="auto">Carro</option>
            <option value="bicycle">Bicicleta</option>
            <option value="pedestrian">A pé</option>
            <option value="motorcycle">Motocicleta</option>
          </select>

          <button
            type="button"
            className="primary-button"
            onClick={calculateRoute}
            disabled={!origin || !destination || loading}
          >
            {loading ? "Calculando..." : "Calcular rota"}
          </button>

          <button
            type="button"
            className="secondary-button"
            onClick={clearSelection}
          >
            Limpar seleção
          </button>

          {error && (
            <div className="error-message" role="alert">
              <strong>Erro</strong>
              <p>{error}</p>
            </div>
          )}

          {result && (
            <section className="route-result">
              <h3>Resultado</h3>

              <div className="result-grid">
                <div className="result-card">
                  <span>Distância</span>
                  <strong>
                    {result.distance_km !== undefined
                      ? `${result.distance_km.toFixed(2)} km`
                      : "—"}
                  </strong>
                </div>

                <div className="result-card">
                  <span>Duração</span>
                  <strong>
                    {formatDuration(result.duration_seconds)}
                  </strong>
                </div>
              </div>

              {result.route_request_id !== undefined && (
                <p className="request-id">
                  Solicitação #{result.route_request_id}
                </p>
              )}

              {!geometry && (
                <p className="hint">
                  Para desenhar a rota, a API precisa retornar
                  sua geometria ou disponibilizar um endpoint
                  para consultá-la.
                </p>
              )}
            </section>
          )}

          <div className="disclaimer">
            <strong>Sobre a segurança</strong>
            <p>
              O MVP ainda precisa integrar os dados de criminalidade
              para comparar o risco dos trajetos. Uma rota calculada
              não é necessariamente uma rota mais segura.
            </p>
          </div>
        </aside>

        <section className="map-section">
          <div className="map-toolbar">
            <span>
              {selecting === "origin"
                ? "Selecione a origem"
                : "Selecione o destino"}
            </span>
            <span>São Paulo, SP</span>
          </div>

          <MapView
            origin={origin}
            destination={destination}
            geometry={geometry}
            onSelectPoint={selectPoint}
          />
        </section>
      </section>

      <footer className="footer">
        RotaSegura · MVP em desenvolvimento · Mapas © OpenStreetMap
      </footer>
    </main>
  );
}
EOF

# ==========================================
# 6. Estilos da aplicação
# ==========================================

cat >src/App.css <<'EOF'
:root {
  font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont,
    "Segoe UI", sans-serif;
  color: #172033;
  background: #f4f6fa;
  font-synthesis: none;
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  min-width: 320px;
}

button,
select {
  font: inherit;
}

button {
  cursor: pointer;
}

button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  padding: 20px 32px;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
}

.eyebrow {
  margin: 0 0 5px;
  color: #64748b;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 1.8px;
}

.header h1 {
  margin: 0;
  font-size: 29px;
}

.subtitle {
  margin: 5px 0 0;
  color: #64748b;
  font-size: 14px;
}

.status {
  padding: 8px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 20px;
  color: #475569;
  font-size: 12px;
  font-weight: 700;
}

.workspace {
  flex: 1;
  display: grid;
  grid-template-columns: 350px minmax(0, 1fr);
  gap: 20px;
  padding: 20px;
}

.sidebar,
.map-section {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  box-shadow: 0 5px 20px rgb(15 23 42 / 4%);
}

.sidebar {
  padding: 24px;
}

.sidebar h2 {
  margin: 0;
  font-size: 21px;
}

.instructions {
  margin: 10px 0 20px;
  color: #64748b;
  font-size: 13px;
  line-height: 1.6;
}

.selection-item {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  margin-bottom: 10px;
  padding: 13px;
  text-align: left;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
}

.selection-item.active {
  background: #eff6ff;
  border-color: #2563eb;
}

.point-icon {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  color: #fff;
  border-radius: 50%;
  font-size: 13px;
  font-weight: 800;
}

.origin-icon {
  background: #16a34a;
}

.destination-icon {
  background: #dc2626;
}

.selection-text {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
}

.selection-text strong {
  font-size: 13px;
}

.selection-text small {
  color: #64748b;
  font-size: 11px;
  overflow-wrap: anywhere;
}

.field-label {
  display: block;
  margin: 22px 0 8px;
  font-size: 13px;
  font-weight: 700;
}

.transport-select {
  width: 100%;
  padding: 12px;
  background: #fff;
  border: 1px solid #cbd5e1;
  border-radius: 9px;
}

.primary-button,
.secondary-button {
  width: 100%;
  min-height: 44px;
  margin-top: 12px;
  padding: 12px;
  border-radius: 9px;
  font-size: 13px;
  font-weight: 750;
}

.primary-button {
  color: #fff;
  background: #1d4ed8;
  border: 1px solid #1d4ed8;
}

.primary-button:hover:not(:disabled) {
  background: #1e40af;
}

.secondary-button {
  color: #334155;
  background: #fff;
  border: 1px solid #cbd5e1;
}

.error-message {
  margin-top: 18px;
  padding: 13px;
  color: #991b1b;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 9px;
  font-size: 12px;
  overflow-wrap: anywhere;
}

.error-message p {
  line-height: 1.5;
}

.route-result {
  margin-top: 22px;
  padding-top: 20px;
  border-top: 1px solid #e2e8f0;
}

.route-result h3 {
  font-size: 15px;
}

.result-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.result-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
  padding: 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 9px;
}

.result-card span,
.request-id,
.hint {
  color: #64748b;
  font-size: 11px;
}

.result-card strong {
  font-size: 16px;
  overflow-wrap: anywhere;
}

.disclaimer {
  margin-top: 25px;
  padding: 14px;
  color: #475569;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  font-size: 11px;
  line-height: 1.6;
}

.disclaimer p {
  margin-bottom: 0;
}

.map-section {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 600px;
  overflow: hidden;
}

.map-toolbar {
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
  padding: 16px 18px;
  border-bottom: 1px solid #e2e8f0;
  font-size: 12px;
  font-weight: 700;
}

.map-container {
  flex: 1;
  width: 100%;
  min-height: 550px;
}

.footer {
  padding: 16px 24px;
  color: #64748b;
  text-align: center;
  font-size: 11px;
}

@media (max-width: 900px) {
  .workspace {
    grid-template-columns: 1fr;
  }

  .map-section {
    min-height: 450px;
  }

  .map-container {
    min-height: 450px;
  }
}

@media (max-width: 520px) {
  .header {
    padding: 18px;
  }

  .workspace {
    gap: 12px;
    padding: 12px;
  }

  .sidebar {
    padding: 18px;
  }

  .map-section,
  .map-container {
    min-height: 380px;
  }
}
EOF

# ==========================================
# 7. CSS global
# ==========================================

cat >src/index.css <<'EOF'
html,
body,
#root {
  width: 100%;
  min-height: 100%;
  margin: 0;
}

#root {
  min-height: 100vh;
}
EOF

# ==========================================
# 8. Entrada do React
# ==========================================

cat >src/main.tsx <<'EOF'
import React from "react";
import ReactDOM from "react-dom/client";

import "leaflet/dist/leaflet.css";
import "./index.css";

import App from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
EOF

echo
echo "======================================"
echo "Frontend criado!"
echo "======================================"
echo
echo "Arquivos criados em: $FRONTEND_DIR"
echo
echo "Nenhum pacote foi instalado."
echo "Nenhum servidor foi iniciado."
echo
echo "Para iniciar o frontend:"
echo "  cd \"$FRONTEND_DIR\""
echo "  npm run dev"
echo
