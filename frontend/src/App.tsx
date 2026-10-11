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
