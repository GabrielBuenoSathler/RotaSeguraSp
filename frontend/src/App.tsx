import { useState } from "react";

import MapView from "./components/MapView";
import { api } from "./services/api";

import type { Coordinates, RouteResult } from "./types/route";

import "./App.css";

export default function App() {
  const [origin, setOrigin] = useState<Coordinates | null>(null);
  const [destination, setDestination] = useState<Coordinates | null>(
    null
  );

  const [selecting, setSelecting] = useState<
    "origin" | "destination"
  >("origin");

  const [transportMode, setTransportMode] = useState("auto");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<RouteResult | null>(null);

  const [geometry, setGeometry] = useState<
    [number, number][] | null
  >(null);

  /**
   * Seleciona um ponto no mapa.
   * O primeiro clique define a origem.
   * O segundo clique define o destino.
   */
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

  /**
   * Limpa a origem, o destino e os resultados.
   */
  function clearSelection() {
    setOrigin(null);
    setDestination(null);
    setResult(null);
    setGeometry(null);
    setError("");
    setSelecting("origin");
  }

  /**
   * Cria a solicitação no backend e calcula a rota
   * utilizando o endpoint do Valhalla.
   */
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
      // 1. Criar a solicitação de rota.
      // Os nomes dos campos correspondem ao schema do FastAPI.

      const createResponse = await api.post("/rota/", {
        origin_lat: origin.lat,
        origin_lon: origin.lon,
        destination_lat: destination.lat,
        destination_lon: destination.lon,
        transport_mode: transportMode,
      });

      // 2. Recuperar o ID retornado pela API.

      const requestId =
        createResponse.data.id ??
        createResponse.data.route_request_id;

      if (requestId == null) {
        throw new Error(
          "A API não retornou o ID da solicitação de rota."
        );
      }

      // 3. Solicitar o cálculo da rota.

      const calculateResponse = await api.post(
        `/rota/${requestId}/calculate`
      );

      const data: RouteResult = calculateResponse.data;

      // 4. Salvar o resultado na interface.

      setResult({
        ...data,
        route_request_id: requestId,
      });

      // 5. Converter GeoJSON para o formato do Leaflet.
      //
      // GeoJSON utiliza [longitude, latitude].
      // Leaflet utiliza [latitude, longitude].

      if (data.geometry?.coordinates) {
        const points: [number, number][] =
          data.geometry.coordinates.map(
            ([longitude, latitude]) =>
              [latitude, longitude] as [number, number]
          );

        setGeometry(points);
      }
    } catch (err: unknown) {
      console.error("Erro ao calcular rota:", err);

      if (
        typeof err === "object" &&
        err !== null &&
        "response" in err
      ) {
        const response = (
          err as {
            response?: {
              status?: number;
              data?: {
                detail?: string | object | unknown[];
              };
            };
          }
        ).response;

        const detail = response?.data?.detail;

        if (typeof detail === "string") {
          setError(detail);
        } else if (detail !== undefined) {
          setError(JSON.stringify(detail));
        } else {
          setError(
            `Erro HTTP ${response?.status ?? "desconhecido"}. ` +
              "Verifique o backend."
          );
        }
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Erro desconhecido ao calcular a rota.");
      }
    } finally {
      setLoading(false);
    }
  }

  /**
   * Converte a duração em segundos para um formato legível.
   */
  function formatDuration(seconds?: number): string {
    if (seconds === undefined) {
      return "—";
    }

    const minutes = Math.round(seconds / 60);

    if (minutes < 60) {
      return `${minutes} min`;
    }

    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;

    return `${hours} h ${remainingMinutes} min`;
  }

  /**
   * Formata as coordenadas para exibição.
   */
  function formatCoordinate(
    point: Coordinates | null
  ): string {
    if (!point) {
      return "Selecione no mapa";
    }

    return `${point.lat.toFixed(5)}, ${point.lon.toFixed(5)}`;
  }

  return (
    <main className="app">
      {/* Cabeçalho */}

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

      {/* Área principal */}

      <section className="workspace">
        {/* Painel lateral */}

        <aside className="sidebar">
          <h2>Planejar rota</h2>

          <p className="instructions">
            Clique no mapa para selecionar os pontos.
            Primeiro escolha a origem e depois o destino.
          </p>

          {/* Origem */}

          <button
            type="button"
            className={`selection-item ${
              selecting === "origin" ? "active" : ""
            }`}
            onClick={() => setSelecting("origin")}
          >
            <span className="point-icon origin-icon">
              A
            </span>

            <span className="selection-text">
              <strong>Origem</strong>

              <small>{formatCoordinate(origin)}</small>
            </span>
          </button>

          {/* Destino */}

          <button
            type="button"
            className={`selection-item ${
              selecting === "destination" ? "active" : ""
            }`}
            onClick={() => setSelecting("destination")}
          >
            <span className="point-icon destination-icon">
              B
            </span>

            <span className="selection-text">
              <strong>Destino</strong>

              <small>{formatCoordinate(destination)}</small>
            </span>
          </button>

          {/* Meio de transporte */}

          <label
            htmlFor="transport"
            className="field-label"
          >
            Meio de transporte
          </label>

          <select
            id="transport"
            className="transport-select"
            value={transportMode}
            onChange={(event) =>
              setTransportMode(event.target.value)
            }
          >
            <option value="auto">Carro</option>
            <option value="bicycle">Bicicleta</option>
            <option value="pedestrian">A pé</option>
            <option value="motorcycle">Motocicleta</option>
          </select>

          {/* Calcular */}

          <button
            type="button"
            className="primary-button"
            onClick={calculateRoute}
            disabled={!origin || !destination || loading}
          >
            {loading ? "Calculando..." : "Calcular rota"}
          </button>

          {/* Limpar */}

          <button
            type="button"
            className="secondary-button"
            onClick={clearSelection}
            disabled={loading}
          >
            Limpar seleção
          </button>

          {/* Mensagens de erro */}

          {error && (
            <div
              className="error-message"
              role="alert"
            >
              <strong>Erro</strong>

              <p>{error}</p>
            </div>
          )}

          {/* Resultado */}

          {result && (
            <section className="route-result">
              <h3>Resultado da rota</h3>

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
                  <span>Duração estimada</span>

                  <strong>
                    {formatDuration(
                      result.duration_seconds
                    )}
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
                  A rota foi processada, mas a API ainda
                  precisa retornar sua geometria para que
                  o trajeto seja desenhado no mapa.
                </p>
              )}
            </section>
          )}

          {/* Aviso sobre segurança */}

          <div className="disclaimer">
            <strong>Sobre a segurança</strong>

            <p>
              O MVP ainda precisa integrar os dados de
              criminalidade para comparar o risco dos
              trajetos. Uma rota calculada não é
              necessariamente uma rota mais segura.
            </p>
          </div>
        </aside>

        {/* Mapa */}

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

      {/* Rodapé */}

      <footer className="footer">
        RotaSegura · MVP em desenvolvimento · Mapas © OpenStreetMap
      </footer>
    </main>
  );
}


















