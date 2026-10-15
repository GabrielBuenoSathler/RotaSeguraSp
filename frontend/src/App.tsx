import { useEffect, useRef, useState } from "react";

import MapView from "./components/MapView";
import PointSearch from "./components/PointSearch";
import { api } from "./services/api";
import { recommendedRoute } from "./utils/routeRecommendation";

import type {
  CalculateResponse, Coordinates, RiskData, RouteOption, RouteResult,
} from "./types/route";

import "./App.css";

export default function App() {
  const [origin, setOrigin] = useState<Coordinates | null>(null);
  const [destination, setDestination] =
    useState<Coordinates | null>(null);

  const [selecting, setSelecting] = useState<
    "origin" | "destination" | null>("origin");

  const crimePanel = useRef<HTMLDetailsElement>(null);
  const [activePanel, setActivePanel] = useState<"planner" | "map" | "routes" | "crimes">("planner");
  const [selectedMonth, setSelectedMonth] = useState("todos");
  const [originName, setOriginName] = useState("");
  const [destinationName, setDestinationName] = useState("");

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

  useEffect(() => {
    if (!origin || originName) return;
    const controller = new AbortController();
    api.get<{ display_name: string } | null>("/places/reverse", {
      params: origin, signal: controller.signal, timeout: 15000,
    }).then(({ data }) => {
      setOriginName(data?.display_name || "Rua não identificada — ponto selecionado no mapa");
    }).catch(() => {
      if (!controller.signal.aborted) setOriginName("Endereço indisponível — ponto selecionado no mapa");
    });
    return () => controller.abort();
  }, [origin, originName]);

  useEffect(() => {
    if (!destination || destinationName) return;
    const controller = new AbortController();
    api.get<{ display_name: string } | null>("/places/reverse", {
      params: destination, signal: controller.signal, timeout: 15000,
    }).then(({ data }) => {
      setDestinationName(data?.display_name || "Rua não identificada — ponto selecionado no mapa");
    }).catch(() => {
      if (!controller.signal.aborted) setDestinationName("Endereço indisponível — ponto selecionado no mapa");
    });
    return () => controller.abort();
  }, [destination, destinationName]);

  function invalidateResult() {
    setResult(null);
    setRisk(null);
    setGeometry(null);
    setOptions([]);
  }

  function chooseRoute(option: RouteOption) {
    setSelectedMonth("todos");
    setResult(option.route);
    setRisk(option.risk);
    setGeometry(option.route.geometry?.coordinates.map(
      ([lon, lat]): [number, number] => [lat, lon]
    ) ?? null);
  }

  function useCurrentLocation() {
    if (!navigator.geolocation) {
      setError("Seu navegador não oferece localização. Busque uma rua ou escolha no mapa.");
      return;
    }
    setLocating(true);
    setError("");
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        invalidateResult();
        setOriginName("");
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
    setOriginName(destinationName);
    setDestinationName(originName);
    setSelecting("origin");
    setOrigin(destination);
    setDestination(origin);
  }

  /**
   * Seleciona um ponto no mapa.
   * O primeiro clique define a origem.
   * O segundo clique define o destino.
   */
  function selectPoint(point: Coordinates, name = "") {
    if (busy || !selecting) return;
    setError("");
    invalidateResult();

    if (selecting === "origin") {
      setOrigin(point);
      setOriginName(name);
      setSelecting("destination");
    } else {
      setDestination(point);
      setDestinationName(name);
    }
  }

  /**
   * Limpa a origem, o destino e os resultados.
   */
  function clearSelection() {
    setOriginName("");
    setDestinationName("");
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
        `/rota/${requestId}/calculate`,
        undefined,
        { headers: { Authorization: `Bearer ${createResponse.data.access_token}` } }
      );

      const data = calculateResponse.data;
      const routeOptions = [{ route: data.route, risk: data.risk }, ...data.alternatives];
      setOptions(routeOptions);
      chooseRoute(recommendedRoute(routeOptions) ?? routeOptions[0]);
      setSelecting(null);
      setActivePanel("map");
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

    return "Identificando rua…";
  }

  const recommendation = recommendedRoute(options);
  const recommendedId = recommendation?.route.calculated_route_id;
  const selectedIndex = options.findIndex(option => option.route.calculated_route_id === result?.calculated_route_id);
  const analysis = risk?.status.success ? risk.result : null;
  const monthGroups = analysis?.ocorrencias_por_mes ?? [];
  const selectedGroup = monthGroups.find(group => (group.mes ?? "sem-data") === selectedMonth);
  const visibleCrimes = selectedMonth === "todos" ? analysis?.riscos_por_crime : selectedGroup?.crimes;
  const visibleCount = selectedMonth === "todos" ? analysis?.quantidade_ocorrencias : selectedGroup?.quantidade_ocorrencias;
  const monthLabel = (month: string | null) => month ? new Date(`${month}T12:00:00`).toLocaleDateString("pt-BR", { month: "long", year: "numeric" }) : "Data não informada";
  const number = (value: number) => value.toLocaleString("pt-BR", { maximumFractionDigits: 2 });
  const routeName = (index: number) => index === 0 ? "Trajeto principal" : `Alternativa ${index}`;

  return (
    <main className="app">
      <header className="header">
        <div><h1>RotaSegura<span>SP</span></h1><p>Planeje seu trajeto. Compare as ocorrências próximas.</p></div>
        <span className="status">Versão experimental</span>
      </header>
      <nav className="panel-navigation" aria-label="Painéis do trajeto">
        {([['planner', 'Planejar'], ['map', 'Mapa'], ['routes', 'Rotas'], ['crimes', 'Crimes']] as const).map(([panel, label]) =>
          <button key={panel} aria-pressed={activePanel === panel} disabled={(panel === "routes" || panel === "crimes") && !result} onClick={() => setActivePanel(panel)}>{label}</button>
        )}
      </nav>
      <div className={`workspace ${result ? "has-results" : ""}`} data-panel={activePanel}>
        <aside className="planner" aria-labelledby="planner-title">
          <h2 id="planner-title">Seu trajeto</h2>
          <p className="hint">Busque um endereço ou selecione os pontos no mapa.</p>
          <div className="point-list">
            {(["origin", "destination"] as const).map((target, index) => (
              <button key={target} type="button" className="selection-item" aria-pressed={selecting === target}
                disabled={busy || !!result} onClick={() => setSelecting(target)}>
                <span className="point-icon">{index === 0 ? "A" : "B"}</span>
                <span><strong>{index === 0 ? "Origem" : "Destino"}</strong>
                <small title={(index === 0 ? originName : destinationName) || undefined}>{(index === 0 ? originName : destinationName) || formatCoordinate(index === 0 ? origin : destination)}</small></span>
              </button>
            ))}
          </div>
          {result ? <button className="secondary-button" disabled={busy} onClick={() => { invalidateResult(); setSelecting("origin"); setActivePanel("planner"); }}>Editar pontos</button> : <>
            {selecting && <PointSearch key={selecting} target={selecting} disabled={busy} onSelect={selectPoint} onSearching={setSearching} />}
            <div className="point-actions">
              <button className="text-button" disabled={busy} onClick={useCurrentLocation}>{locating ? "Obtendo localização…" : "Usar minha localização"}</button>
              <button className="text-button" disabled={busy || !origin || !destination} onClick={swapPoints}>Inverter pontos</button>
            </div>
          </>}
          <label htmlFor="transport" className="field-label">Meio de transporte</label>
          <select id="transport" disabled={busy} value={transportMode} onChange={event => { setTransportMode(event.target.value); invalidateResult(); setSelecting("origin"); setError(""); }}>
            <option value="auto">Carro</option><option value="bicycle">Bicicleta</option><option value="pedestrian">A pé</option><option value="motorcycle">Motocicleta</option>
          </select>
          <button className="primary-button" disabled={!origin || !destination || busy} onClick={calculateRoute}>{loading ? "Calculando trajeto…" : result ? "Recalcular rota" : "Calcular rota"}</button>
          <button className="text-button clear-button" disabled={busy || (!origin && !destination)} onClick={clearSelection}>Limpar seleção</button>
          <p className="selection-help" role="status" aria-live="polite">{loading ? "Calculando o trajeto e analisando as ocorrências." : result ? "Selecione um trajeto para comparar seus detalhes." : !origin ? "Defina a origem para começar." : !destination ? "Agora defina o destino." : "Origem e destino definidos. Você já pode calcular."}</p>
          {error && <div className="error-message" role="alert">{error}</div>}
        </aside>

        <section className={`map-section ${selecting && !busy ? "is-editing" : ""}`} aria-label="Mapa dos trajetos">
          <div className="map-toolbar"><strong>{result ? routeName(selectedIndex) : "São Paulo, SP"}</strong><span>{busy ? "Aguarde…" : selecting ? `Clique para definir ${selecting === "origin" ? "a origem" : "o destino"}` : "Selecione uma alternativa no mapa"}</span></div>
          <MapView origin={origin} destination={destination} geometry={geometry} options={options} recommendedId={recommendedId} selectedId={result?.calculated_route_id}
            editing={!!selecting && !busy} onSelectPoint={selectPoint} onChooseRoute={chooseRoute} />
          <div className="map-legend"><span><b>A</b> Origem</span><span><b>B</b> Destino</span><span><i /> {recommendation ? "Recomendada" : "Trajeto"}</span><span><i className="alternative-line" /> Alternativas</span></div>
        </section>

        {options.length > 0 && <section className="comparison" aria-labelledby="comparison-title">
          <div className="section-heading"><h2 id="comparison-title">Compare os trajetos</h2><span>{options.length} {options.length === 1 ? "trajeto encontrado" : "trajetos encontrados"}</span></div>
          <p className="hint">A recomendada tem a menor pontuação de exposição entre as rotas com análise disponível. Considere também tempo e distância.</p>
          <div className="route-options">{options.map((option, index) => {
            const data = option.risk.status.success ? option.risk.result : null;
            const crimes = data?.riscos_por_crime ?? [];
            return <article className="route-option" key={option.route.calculated_route_id} data-recommended={recommendedId === option.route.calculated_route_id} data-selected={result?.calculated_route_id === option.route.calculated_route_id}>
              <button className="route-select" aria-pressed={result?.calculated_route_id === option.route.calculated_route_id} onClick={() => chooseRoute(option)}>
                <span className="route-option-heading"><strong>{routeName(index)}{recommendedId === option.route.calculated_route_id && <small className="recommended-badge">Recomendada</small>}</strong><span>{result?.calculated_route_id === option.route.calculated_route_id ? "Selecionada" : "Selecionar"}</span></span>
                <span className="route-metrics"><span><small>Tempo</small><b>{formatDuration(option.route.duration_seconds)}</b></span><span><small>Distância</small><b>{option.route.distance_km === undefined ? "—" : `${number(option.route.distance_km)} km`}</b></span><span><small>Ocorrências</small><b>{data ? number(data.quantidade_ocorrencias) : "—"}</b></span></span>
                <span className="exposure-score">{data ? `${number(data.pontuacao_ajustada)} pontos de exposição` : "Análise indisponível"}</span>
              </button>
              <div className="crime-preview">{crimes.length ? <ul>{crimes.slice(0, 3).map(crime => <li key={crime.crime}><span>{crime.crime}</span><strong>{number(crime.quantidade_ocorrencias)}</strong></li>)}</ul> : <p className="hint">{!data ? option.risk.status.message : data.quantidade_ocorrencias === 0 ? "Nenhuma ocorrência registrada próxima ao trajeto." : "Detalhamento dos crimes indisponível."}</p>}
                {crimes.length > 3 && <button className="text-button" onClick={() => { chooseRoute(option); requestAnimationFrame(() => { if (crimePanel.current) { crimePanel.current.open = true; setActivePanel("crimes"); crimePanel.current.focus(); } }); }}>Ver todos os {crimes.length} tipos de crime</button>}
              </div>
            </article>;
          })}</div>
        </section>}

        {risk && <details ref={crimePanel} tabIndex={-1} className="crime-panel" id="crime-details" key={result?.calculated_route_id} open>
          <summary>Crimes próximos · {routeName(selectedIndex)}</summary>
          <div className="panel-body">{analysis ? <>
            <p className="hint">Registros em até {analysis.raio_analise_metros} metros deste trajeto, ordenados pela pontuação de exposição.</p>
            {analysis.data_agrupamento_configurada ? <div className="month-filter">
              <label htmlFor="occurrence-month" className="field-label">Data das ocorrências</label>
              <select id="occurrence-month" value={selectedMonth} onChange={event => setSelectedMonth(event.target.value)}>
                <option value="todos">Todo o período ({number(analysis.quantidade_ocorrencias)})</option>
                {monthGroups.map(group => <option key={group.mes ?? "sem-data"} value={group.mes ?? "sem-data"}>{monthLabel(group.mes)} ({number(group.quantidade_ocorrencias)})</option>)}
              </select>
              <p className="hint" role="status">{number(visibleCount ?? 0)} ocorrências · {selectedMonth === "todos" ? "todo o período" : monthLabel(selectedGroup?.mes ?? null)}. O filtro altera esta lista; a comparação das rotas considera todo o período analisado.</p>
            </div> : <p className="hint">A classificação por data ainda não está disponível nesta base.</p>}
            {visibleCrimes?.length ? <ul className="crime-risk-list">{visibleCrimes.map(crime => <li key={crime.crime}>
              <div><strong>{crime.crime}</strong><span>{number(crime.quantidade_ocorrencias)} ocorrências próximas</span></div>
              <span className="crime-score">{number(crime.pontuacao_ajustada)}<small>pontos de exposição</small></span>
            </li>)}</ul> : <p>{analysis.quantidade_ocorrencias === 0 ? "Nenhuma ocorrência registrada no corredor analisado." : "O detalhamento por tipo de crime não está disponível."}</p>}
            <details className="methodology"><summary>Como a análise funciona</summary>
              <p>A pontuação considera a gravidade e a proximidade das ocorrências. Ela é um indicador experimental, não uma probabilidade de sofrer um crime.</p>
              <dl><div><dt>Pontuação original</dt><dd>{number(analysis.pontuacao_original)}</dd></div><div><dt>Pontuação ajustada</dt><dd>{number(analysis.pontuacao_ajustada)}</dd></div><div><dt>Pontos ajustados por km</dt><dd>{analysis.pontos_ajustados_por_km === null ? "Indisponível" : number(analysis.pontos_ajustados_por_km)}</dd></div></dl>
              <p>Fonte: {analysis.fonte}. Atualização: {analysis.atualizado_em ? new Date(`${analysis.atualizado_em}T12:00:00`).toLocaleDateString("pt-BR") : "não informada"}.</p>
              <p>{analysis.filtro_temporal_aplicado && analysis.periodo_inicio && analysis.periodo_fim ? `Período: ${new Date(analysis.periodo_inicio).toLocaleDateString("pt-BR")} a ${new Date(analysis.periodo_fim).toLocaleDateString("pt-BR")}.` : "Período: todas as datas da base; filtro temporal não configurado."}</p>
            </details>
          </> : <p role="status">{risk.status.message}</p>}
          {!geometry && <p className="hint">O desenho deste trajeto está indisponível no mapa.</p>}
          </div>
        </details>}
      </div>
      <footer className="footer"><p>Os registros não garantem a segurança de uma rota. Ausência de ocorrências na base não significa ausência de risco.</p><span>RotaSegura SP · Dados de ocorrências e mapas OpenStreetMap</span></footer>
    </main>
  );
}
