import { useState } from "react";

import MapView from "./components/MapView";
import PointSearch from "./components/PointSearch";
import { api } from "./services/api";

import type {
  CalculateResponse, Coordinates, RiskData, RouteOption, RouteResult,
} from "./types/route";

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
  const [risk, setRisk] = useState<RiskData | null>(null);
  const [options, setOptions] = useState<RouteOption[]>([]);
  const [locating, setLocating] = useState(false);
  const [searching, setSearching] = useState(false);
  const busy = loading || locating || searching;
  const [geometry, setGeometry] = useState<[number, number][] | null>(null);

  function invalidateResult() {
    setResult(null);
    setRisk(null);
    setGeometry(null);
    setOptions([]);
  }

  function chooseRoute(option: RouteOption) {
    setResult(option.route);
    setRisk(option.risk);
    setGeometry(option.route.geometry?.coordinates.map(
      ([lon, lat]): [number, number] => [lat, lon]
    ) ?? null);
  }

  function useCurrentLocation() {
    if (!navigator.geolocation) {
      setError("Seu navegador não oferece localização. Informe as coordenadas ou escolha no mapa.");
      return;
    }
    setLocating(true);
    setError("");
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        invalidateResult();
        setOrigin({ lat: coords.latitude, lon: coords.longitude });
        setSelecting("destination");
        setLocating(false);
      },
      () => {
        setError("Não foi possível obter sua localização. Verifique a permissão do navegador ou selecione a origem no mapa.");
        setLocating(false);
      },
      { timeout: 10000, maximumAge: 60000 }
    );
  }

  function swapPoints() {
    invalidateResult();
    setError("");
    setOrigin(destination);
    setDestination(origin);
  }

  /**
   * Seleciona um ponto no mapa.
   * O primeiro clique define a origem.
   * O segundo clique define o destino.
   */
  function selectPoint(point: Coordinates) {
    if (busy) return;
    setError("");
    invalidateResult();

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
    invalidateResult();
    setError("");
    setSelecting("origin");
  }

  /**
   * Cria a solicitação e calcula a rota e o risco.
   */
  async function calculateRoute() {
    if (busy) return;
    if (!origin || !destination) {
      setError("Selecione a origem e o destino no mapa.");
      return;
    }

    setLoading(true);
    setError("");
    invalidateResult();

    try {
      // 1. Criar a solicitação de rota.

      const createResponse = await api.post("/rota/", {
        origin_lat: origin.lat,
        origin_lon: origin.lon,
        destination_lat: destination.lat,
        destination_lon: destination.lon,
        transport_mode: transportMode,
      });

      // 2. Recuperar o ID da solicitação.

      const requestId =
        createResponse.data.id ??
        createResponse.data.route_request_id;

      if (requestId == null) {
        throw new Error(
          "A API não retornou o ID da solicitação de rota."
        );
      }

      // 3. Calcular a rota e o risco.

      const calculateResponse = await api.post<CalculateResponse>(
        `/rota/${requestId}/calculate`
      );

      const data = calculateResponse.data;
      setOptions([{ route: data.route, risk: data.risk }, ...data.alternatives]);
      chooseRoute(data);
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
        } else if (
          typeof detail === "object" &&
          detail !== null &&
          "message" in detail &&
          typeof detail.message === "string"
        ) {
          setError(detail.message);
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
          <p className="eyebrow">SÃO PAULO · MOBILIDADE CONSCIENTE</p>

          <h1><span className="brand-mark" aria-hidden="true">↗</span> RotaSegura<span className="brand-city">SP</span></h1>

          <p className="subtitle">
            Planeje seu trajeto por São Paulo.
          </p>
        </div>

        <span className="status"><span className="status-dot" /> Versão experimental</span>
      </header>

      {/* Área principal */}

      <section className="workspace">
        {/* Painel lateral */}

        <aside className="sidebar">
          <p className="eyebrow">SEU PRÓXIMO TRAJETO</p>
          <h2>Por onde vamos?</h2>

          <p className="instructions">
            Escolha a origem e o destino no mapa, por endereço ou coordenadas.
          </p>

          <ol className="planning-steps" aria-label="Etapas do planejamento">
            <li className={origin ? "complete" : "current"}>1 <span>Origem</span></li>
            <li className={destination ? "complete" : origin ? "current" : ""}>2 <span>Destino</span></li>
            <li className={result ? "complete" : origin && destination ? "current" : ""}>3 <span>Trajeto</span></li>
          </ol>

          {/* Origem */}

          <button
            type="button"
            className={`selection-item ${
              selecting === "origin" ? "active" : ""
            }`}
            aria-pressed={selecting === "origin"}
            disabled={busy}
            onClick={() => setSelecting("origin")}
          >
            <span className="point-icon origin-icon">A</span>

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
            aria-pressed={selecting === "destination"}
            disabled={busy}
            onClick={() => setSelecting("destination")}
          >
            <span className="point-icon destination-icon">B</span>

            <span className="selection-text">
              <strong>Destino</strong>

              <small>{formatCoordinate(destination)}</small>
            </span>
          </button>

          <PointSearch key={selecting} target={selecting} disabled={busy}
            onSelect={selectPoint} onSearching={setSearching} />

          <button type="button" className="secondary-button" disabled={busy}
            onClick={useCurrentLocation}>
            {locating ? "Obtendo localização…" : "Usar minha localização como origem"}
          </button>
          <button type="button" className="secondary-button"
            disabled={busy || !origin || !destination} onClick={swapPoints}>
            Inverter origem e destino
          </button>

          {/* Meio de transporte */}

          <label htmlFor="transport" className="field-label">
            Meio de transporte
          </label>

          <select
            id="transport"
            className="transport-select"
            disabled={busy}
            value={transportMode}
            onChange={(event) =>
              { setTransportMode(event.target.value);
                invalidateResult(); setError(""); }
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
            disabled={!origin || !destination || busy}
          >
            {loading ? "Calculando trajeto…" : "Calcular rota →"}
          </button>

          {/* Limpar */}

          <button
            type="button"
            className="secondary-button"
            onClick={clearSelection}
            disabled={busy}
          >
            Limpar seleção
          </button>

          <p className="selection-help" role="status" aria-live="polite">
            {loading ? "Estamos calculando o trajeto e analisando as ocorrências." : !origin ? "Comece escolhendo sua origem no mapa." : !destination ? "Agora escolha seu destino no mapa." : "Tudo pronto. Calcule para ver o trajeto e a análise."}
          </p>

          {/* Mensagens de erro */}

          {error && (
            <div className="error-message" role="alert">
              <strong>Erro</strong>

              <p>{error}</p>
            </div>
          )}

          {/* Resultado da rota */}

          {options.length > 0 && (
            <section className="route-result" aria-label="Comparação de trajetos">
              <h3>Compare os trajetos</h3>
              {options.length === 1 && <p>O serviço encontrou apenas um trajeto para estes pontos.</p>}
              {options.map((option, index) => (
                <button type="button" className="route-option"
                  key={option.route.calculated_route_id}
                  aria-pressed={result?.calculated_route_id === option.route.calculated_route_id}
                  onClick={() => chooseRoute(option)}>
                  <strong>{index === 0 ? "Trajeto principal" : `Alternativa ${index}`}</strong>
                  <span>{option.route.distance_km?.toFixed(2)} km · {formatDuration(option.route.duration_seconds)}</span>
                  <span>{option.risk.status.success && option.risk.result
                    ? `${option.risk.result.pontuacao_ajustada.toLocaleString("pt-BR")} pontos de exposição`
                    : "Análise indisponível"}</span>
                </button>
              ))}
              <p className="hint">Menor pontuação indica menor exposição às ocorrências da base. Compare também a distância e a duração.</p>
            </section>
          )}

          {result && (
            <section className="route-result" aria-live="polite">
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
                  A rota foi processada, mas a API ainda
                  precisa retornar sua geometria para que
                  o trajeto seja desenhado no mapa.
                </p>
              )}
            </section>
          )}

          {/* Resultado do cálculo de risco */}

          {risk && (
            <section className="route-result" aria-live="polite">
              <h3>Análise de risco</h3>

              {risk.status.success && risk.result ? (
                <>
                  <p>{risk.status.message}</p>

                  <div className="result-grid">
                    <div className="result-card">
                      <span>Ocorrências próximas</span>

                      <strong>
                        {risk.result.quantidade_ocorrencias.toLocaleString(
                          "pt-BR"
                        )}
                      </strong>
                    </div>

                    <div className="result-card">
                      <span>Pontuação original</span>

                      <strong>
                        {risk.result.pontuacao_original.toLocaleString(
                          "pt-BR"
                        )}
                      </strong>
                    </div>

                    <div className="result-card">
                      <span>Pontuação ajustada</span>

                      <strong>
                        {risk.result.pontuacao_ajustada.toLocaleString(
                          "pt-BR",
                          {
                            maximumFractionDigits: 2,
                          }
                        )}
                      </strong>
                    </div>

                    <div className="result-card">
                      <span>Pontos ajustados por km</span>

                      <strong>
                        {risk.result.pontos_ajustados_por_km === null
                          ? "—"
                          : risk.result.pontos_ajustados_por_km.toLocaleString(
                              "pt-BR",
                              {
                                maximumFractionDigits: 2,
                              }
                            )}
                      </strong>
                    </div>
                  </div>

                  <p className="hint">
                    Análise de ocorrências em um raio de{" "}
                    {risk.result.raio_analise_metros} metros
                    da rota.
                  </p>
                  <p className="hint">Fonte: {risk.result.fonte}. Atualização: {risk.result.atualizado_em
                    ? new Date(`${risk.result.atualizado_em}T12:00:00`).toLocaleDateString("pt-BR") : "não informada"}.</p>
                  <p className="hint">{risk.result.filtro_temporal_aplicado && risk.result.periodo_inicio && risk.result.periodo_fim
                    ? `Período: ${new Date(risk.result.periodo_inicio).toLocaleDateString("pt-BR")} a ${new Date(risk.result.periodo_fim).toLocaleDateString("pt-BR")}.`
                    : "Período: todas as datas da base; filtro temporal não configurado."}</p>
                </>
              ) : (
                <div className="error-message" role="status">
                  <strong>Risco indisponível</strong>

                  <p>{risk.status.message}</p>
                </div>
              )}
            </section>
          )}

          {/* Aviso sobre segurança */}

          <div className="disclaimer">
            <strong>Sobre a segurança</strong>

            <p>
              A pontuação é um indicador experimental de exposição
              a ocorrências registradas. Não representa uma
              probabilidade validada de vitimização nem garante
              que uma rota seja segura.
            </p>
          </div>
        </aside>

        {/* Mapa */}

        <section className="map-section">
          <div className="map-toolbar">
            <span>
              {selecting === "origin"
                ? "Clique no mapa para definir a origem"
                : "Clique no mapa para definir o destino"}
            </span>

            <span className="map-location">São Paulo, SP</span>
          </div>

          <MapView
            origin={origin}
            destination={destination}
            geometry={geometry}
            onSelectPoint={selectPoint}
          />
          <div className="map-legend" aria-label="Legenda do mapa">
            <span><i className="legend-origin" /> Origem</span>
            <span><i className="legend-destination" /> Destino</span>
            <span><i className="legend-route" /> Trajeto calculado</span>
          </div>
        </section>
      </section>

      {/* Rodapé */}

      <footer className="footer">
        RotaSegura · MVP em desenvolvimento · Mapas © OpenStreetMap
      </footer>
    </main>
  );
}
